"""
Grad-CAM (Gradient-weighted Class Activation Mapping) for B-mode ultrasound.
Extracts spatial heatmaps ('where in the image') from the last convolutional block (ResNet layer4).
Conforms to XMAI Design Document Section 8.1.
"""

from typing import Optional, Tuple
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GradCAM:
    """
    Computes Grad-CAM heatmaps for BModeEncoder.
    Hooks into layer4 to capture activations and backward gradients.
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None

        # Register forward and backward hooks
        self.forward_handle = self.target_layer.register_forward_hook(self._forward_hook)
        self.backward_handle = self.target_layer.register_full_backward_hook(self._backward_hook)

    def _forward_hook(self, module, input, output):
        self.activations = output

    def _backward_hook(self, module, grad_in, grad_out):
        self.gradients = grad_out[0]

    def generate_heatmap(
        self,
        img_tensor: torch.Tensor,
        target_class: int,
        clin_tensor: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> np.ndarray:
        """
        Computes Grad-CAM heatmap normalized to [0, 1].
        Input: img_tensor [1, 3, H, W]
        Output: heatmap in [H, W] as float32 in [0, 1]
        """
        self.model.zero_grad()
        out = self.model(img=img_tensor, clin=clin_tensor, mod_mask=mod_mask)
        logits = out["logits"]

        score = logits[0, target_class]
        score.backward(retain_graph=True)

        # Global average pooling of gradients: [1, C, 1, 1]
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        # Weighted combination of forward activation maps
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)  # [1, 1, h, w]
        cam = F.relu(cam)

        # Interpolate to original input size
        H, W = img_tensor.shape[2], img_tensor.shape[3]
        cam = F.interpolate(cam, size=(H, W), mode="bilinear", align_corners=False)
        cam = cam.squeeze().detach().cpu().numpy()

        # Normalize to [0, 1]
        denom = (cam.max() - cam.min())
        if denom > 1e-8:
            heatmap = (cam - cam.min()) / denom
        else:
            heatmap = np.zeros_like(cam)

        return heatmap

    def remove_hooks(self):
        """Removes registered hooks."""
        if hasattr(self, "forward_handle"):
            self.forward_handle.remove()
        if hasattr(self, "backward_handle"):
            self.backward_handle.remove()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove_hooks()
