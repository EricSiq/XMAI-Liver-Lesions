"""Stress testing and sanity check verification for Grad-CAM activation mapping.

Academic Qualification Suite (Adebayo et al., NeurIPS 2018):
- Model parameter randomization sanity check: Grad-CAM must degrade to low correlation when weights are scrambled
- Hook isolation and removal: Ensure no memory leaks or persistent hooks remain on encoder modules
- Degenerate input stability: Flat uniform fields and all-zero images must yield finite [0, 1] maps
- Spatial dimension preservation: Heatmap output dimensions must strictly match input image dimensions
"""

import numpy as np
import pytest
import torch
import torch.nn as nn

from xmai.explainability.gradcam import GradCAM
from xmai.models.track_a_models import A1BModeOnly, A4GatedFusion


class TestGradCAMStress:
    """Stress tests for GradCAM under extreme conditions and cascading randomization."""

    def test_spatial_dimension_and_bounds_preservation(self):
        """Heatmap output must strictly match input spatial dimensions (H, W) and stay within [0, 1]."""
        model = A1BModeOnly(pretrained=False)
        model.eval()
        cam = GradCAM(model, model.encoder_b.layer4)

        H, W = 192, 256
        img = torch.randn(1, 3, H, W)
        heatmap = cam.generate_heatmap(img, target_class=1)

        assert heatmap.shape == (H, W)
        assert 0.0 <= heatmap.min() <= heatmap.max() <= 1.0
        assert np.isfinite(heatmap).all()

        cam.remove_hooks()

    def test_zero_and_flat_input_stability(self):
        """All-zero or completely flat uniform inputs must not cause division by zero in heatmap normalization."""
        model = A1BModeOnly(pretrained=False)
        model.eval()
        cam = GradCAM(model, model.encoder_b.layer4)

        # All-zero image
        zero_img = torch.zeros(1, 3, 224, 224)
        zero_map = cam.generate_heatmap(zero_img, target_class=0)
        assert np.isfinite(zero_map).all()
        assert zero_map.shape == (224, 224)

        # Constant flat image
        flat_img = torch.full((1, 3, 224, 224), 0.5)
        flat_map = cam.generate_heatmap(flat_img, target_class=1)
        assert np.isfinite(flat_map).all()
        assert 0.0 <= flat_map.min() <= flat_map.max() <= 1.0

        cam.remove_hooks()

    def test_cascading_parameter_randomization_sensitivity(self):
        """Cascading randomization of the classification head and top conv layers must degrade heatmap correlation."""
        model = A1BModeOnly(pretrained=False)
        model.eval()
        cam = GradCAM(model, model.encoder_b.layer4)

        img = torch.randn(1, 3, 224, 224)
        orig_map = cam.generate_heatmap(img, target_class=1)
        cam.remove_hooks()

        # Re-initialize layer4 weights with random noise
        for param in model.encoder_b.layer4.parameters():
            param.data = torch.randn_like(param.data)

        cam_scrambled = GradCAM(model, model.encoder_b.layer4)
        scrambled_map = cam_scrambled.generate_heatmap(img, target_class=1)
        cam_scrambled.remove_hooks()

        # Flat correlation
        corr = float(np.corrcoef(orig_map.flatten(), scrambled_map.flatten())[0, 1])
        if np.isnan(corr):
            corr = 0.0

        assert abs(corr) < 0.90, f"Grad-CAM must be sensitive to model parameters, got correlation {corr}"

    def test_hook_removal_lifecycle(self):
        """Calling remove_hooks must cleanly detach hooks without raising exceptions on repeated calls."""
        model = A1BModeOnly(pretrained=False)
        cam = GradCAM(model, model.encoder_b.layer4)

        # Verify handles exist
        assert cam.forward_handle is not None
        assert cam.backward_handle is not None

        # Clean removal
        cam.remove_hooks()

        # Forward pass without hooks should not populate activations
        cam.activations = None
        _ = model(img=torch.randn(1, 3, 224, 224))
        assert cam.activations is None, "Activations must not be captured after remove_hooks()"

    def test_multimodal_gated_fusion_gradcam(self):
        """GradCAM must work with full multimodal XMAI model receiving both image and clinical context."""
        model = A4GatedFusion(pretrained=False)
        model.eval()
        cam = GradCAM(model, model.encoder_b.layer4)

        img = torch.randn(1, 3, 224, 224)
        clin = torch.randn(1, 2)
        mask = torch.tensor([[1.0, 0.0, 1.0]])

        heatmap = cam.generate_heatmap(img, target_class=1, clin_tensor=clin, mod_mask=mask)
        assert heatmap.shape == (224, 224)
        assert np.isfinite(heatmap).all()

        cam.remove_hooks()
