"""
Multiclass Multimodal Neural Architectures for 5-Class / 6-Class Focal Liver Lesion Differential Diagnosis.
Implements:
- M5FlatGatedFusion: Generalization of Model A4 to K=5 classes with dynamic gating and modality dropout.
- M5HierarchicalFusion: Coarse-to-fine decision architecture (Stage 1 Oncologic Gate, Stage 2 Subtyping).
- M5EvidentialFusion: Subjective Logic evidential uncertainty with K-dimensional Dirichlet belief decomposition.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F

from xmai.models.encoders import BModeEncoder, MulticlassClinicalEncoder
from xmai.models.fusion import MaskAwareGatedFusion
from xmai.data.schemas import TAXONOMY_5CLASS, CLASS_TIER_MAPPING


class M5FlatGatedFusion(nn.Module):
    """
    Model M5_Gated: 5-Class Flat Mask-Aware Gated Multimodal Fusion.
    Direct generalization of Model A4 to K-class differential diagnosis.
    Fuses ResNet-18 B-mode visual embeddings with 8-variable clinical oncology profiles.
    """

    def __init__(
        self,
        num_classes: int = 5,
        pretrained: bool = True,
        dim_b: int = 256,
        dim_t: int = 128,
        fused_dim: int = 256,
        dropout_p: float = 0.2,
        class_names: Optional[List[str]] = None,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.class_names = class_names or list(TAXONOMY_5CLASS)
        if len(self.class_names) != num_classes:
            raise ValueError(f"class_names length ({len(self.class_names)}) must match num_classes ({num_classes})")

        # Modality Encoders
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=dim_b)
        self.encoder_t = MulticlassClinicalEncoder(in_features=8, hidden_dim=dim_t, out_dim=dim_t)

        # Dynamic Gating & Fusion
        self.fusion = MaskAwareGatedFusion(
            dim_b=dim_b,
            dim_c=256,  # unused placeholder
            dim_t=dim_t,
            fused_dim=fused_dim,
            dropout_p=dropout_p,
        )

        # Classification Head
        self.head = nn.Sequential(
            nn.Dropout(p=dropout_p),
            nn.Linear(fused_dim, num_classes),
        )

        # Post-hoc Temperature parameter for calibration
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: Optional[torch.Tensor] = None,
        clin: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        Forward pass.
        Args:
            img: B-mode tensor [B, 3, 224, 224] or None
            clin: 8-variable clinical tensor [B, 8] or None
            mod_mask: [B, 2] or [B, 3] modality presence mask
        """
        z_b = self.encoder_b(img) if img is not None else None
        z_t = self.encoder_t(clin) if clin is not None else None

        # Adapt mod_mask to 3-slot fusion [B-mode, CEUS(absent), Clinical]
        if mod_mask is not None and mod_mask.shape[1] == 2:
            device = mod_mask.device
            B = mod_mask.shape[0]
            # Construct [m_b, 0, m_t]
            full_mask = torch.zeros(B, 3, device=device)
            full_mask[:, 0] = mod_mask[:, 0]
            full_mask[:, 2] = mod_mask[:, 1]
        else:
            full_mask = mod_mask

        z_f, raw_gate_weights = self.fusion(z_b=z_b, z_c=None, z_t=z_t, mod_mask=full_mask)
        # Extract active gate weights [alpha_b, alpha_t]
        gate_weights = torch.stack([raw_gate_weights[:, 0], raw_gate_weights[:, 2]], dim=1)
        gate_sum = gate_weights.sum(dim=1, keepdim=True).clamp(min=1e-7)
        gate_weights = gate_weights / gate_sum

        logits = self.head(z_f)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "gate_weights": gate_weights,
            "embeddings": {
                "z_b": z_b,
                "z_t": z_t,
                "z_f": z_f,
            },
        }

    def set_temperature(self, temp_val: float) -> None:
        """Sets learned temperature scaling parameter for calibration."""
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)
