"""
XMAI unified multimodal architecture for differential diagnosis of focal liver lesions.
Conforms to XMAI Design Document Section 7.
"""

from typing import Any, Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from xmai.models.encoders import BModeEncoder, CEUSEncoder, ClinicalEncoder
from xmai.models.fusion import MaskAwareGatedFusion


class XMAIModel(nn.Module):
    """
    Explainable Multimodal AI Network.
    Combines B-mode image (M1), CEUS cine (M2), and clinical context (M3)
    via Mask-Aware Gated Fusion (F3) with temperature scaling calibration.
    """

    def __init__(
        self,
        num_classes: int = 2,
        pretrained: bool = True,
        dim_b: int = 256,
        dim_c: int = 256,
        dim_t: int = 64,
        fused_dim: int = 256,
        dropout_p: float = 0.2,
        use_ceus: bool = False,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.use_ceus = use_ceus

        # Modality Encoders
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=dim_b)
        self.encoder_t = ClinicalEncoder(in_features=2, hidden_dim=64, out_dim=dim_t)
        self.encoder_c = CEUSEncoder(embed_dim=dim_c) if use_ceus else None

        # Mask-Aware Gated Fusion (F3)
        self.fusion = MaskAwareGatedFusion(
            dim_b=dim_b,
            dim_c=dim_c,
            dim_t=dim_t,
            fused_dim=fused_dim,
            dropout_p=dropout_p,
        )

        # Classification Head
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(fused_dim, num_classes),
        )

        # Temperature parameter for probability calibration (fixed at 1.0 until fitted)
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: Optional[torch.Tensor] = None,
        clin: Optional[torch.Tensor] = None,
        ceus: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        Multimodal forward pass.
        Returns logits, calibrated class probabilities, gate weights, and embeddings.
        """
        z_b = self.encoder_b(img) if img is not None else None
        z_t = self.encoder_t(clin) if clin is not None else None
        z_c = self.encoder_c(ceus) if (self.use_ceus and ceus is not None) else None

        # Gated fusion with availability masking
        z_f, gate_weights = self.fusion(z_b=z_b, z_c=z_c, z_t=z_t, mod_mask=mod_mask)

        # Raw logits: [B, num_classes]
        logits = self.head(z_f)

        # Calibrated probabilities via temperature scaling
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "gate_weights": gate_weights,
            "embeddings": {
                "z_b": z_b,
                "z_c": z_c,
                "z_t": z_t,
                "z_f": z_f,
            },
        }

    def set_temperature(self, temp_val: float) -> None:
        """Sets learned temperature scaling parameter for calibration."""
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)
