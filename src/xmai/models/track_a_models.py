"""
Track A Model Family for SMC-LUD Evaluation:
- A1: B-mode image-only ResNet-18 (primary baseline)
- A2: Clinical context-only (age/sex calibrated classifier)
- A3: Embedding Concatenation Fusion
- A4: Mask-Aware Gated Fusion (primary multimodal fusion model)
- A5: FiLM Feature-wise Linear Modulation
- A6: Late fusion of calibrated A1 and A2 predictions

Conforms to XMAI Design Document Section 7 and tasks.md Section 3.1 & 3.2.
"""

from typing import Any, Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from xmai.models.encoders import BModeEncoder, ClinicalEncoder
from xmai.models.fusion import ConcatenationFusion, FiLMFusion, MaskAwareGatedFusion
from xmai.models.xmai_model import XMAIModel


class A1BModeOnly(nn.Module):
    """
    A1: B-mode image-only classifier using ResNet-18 backbone.
    Ignores clinical context completely.
    """

    def __init__(self, num_classes: int = 2, pretrained: bool = True, embed_dim: int = 256):
        super().__init__()
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=embed_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(embed_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: torch.Tensor,
        clin: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        z_b = self.encoder_b(img)
        logits = self.head(z_b)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": {"z_b": z_b, "z_f": z_b},
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


class A2ClinicalOnly(nn.Module):
    """
    A2: Clinical-only classifier using structured context (age_z, sex).
    Ignores ultrasound imagery completely. Quantifies cohort prior.
    """

    def __init__(self, in_features: int = 2, hidden_dim: int = 64, num_classes: int = 2):
        super().__init__()
        self.encoder_t = ClinicalEncoder(in_features=in_features, hidden_dim=hidden_dim, out_dim=hidden_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: Optional[torch.Tensor] = None,
        clin: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        if clin is None:
            raise ValueError("Clinical context tensor 'clin' must be provided to A2ClinicalOnly.")
        z_t = self.encoder_t(clin)
        logits = self.head(z_t)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": {"z_t": z_t, "z_f": z_t},
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


class A3ConcatFusion(nn.Module):
    """
    A3: Concatenation Fusion [z_B; z_T] -> MLP -> Head.
    """

    def __init__(
        self,
        num_classes: int = 2,
        pretrained: bool = True,
        dim_b: int = 256,
        dim_t: int = 64,
        fused_dim: int = 256,
    ):
        super().__init__()
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=dim_b)
        self.encoder_t = ClinicalEncoder(in_features=2, hidden_dim=64, out_dim=dim_t)
        self.fusion = ConcatenationFusion(in_dim=dim_b + dim_t, fused_dim=fused_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(fused_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: torch.Tensor,
        clin: torch.Tensor,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        z_b = self.encoder_b(img)
        z_t = self.encoder_t(clin)
        z_f = self.fusion(z_b, z_t)
        logits = self.head(z_f)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": {"z_b": z_b, "z_t": z_t, "z_f": z_f},
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


class A4GatedFusion(XMAIModel):
    """
    A4: Primary Fusion Model (Mask-Aware Gated Fusion with Modality Dropout).
    Inherits directly from XMAIModel.
    """
    pass


class A5FiLMFusion(nn.Module):
    """
    A5: FiLM Conditioning (Feature-wise Linear Modulation).
    Context z_T modulates B-mode embedding: z_B' = gamma(z_T) * z_B + beta(z_T).
    """

    def __init__(
        self,
        num_classes: int = 2,
        pretrained: bool = True,
        dim_b: int = 256,
        dim_t: int = 64,
    ):
        super().__init__()
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=dim_b)
        self.encoder_t = ClinicalEncoder(in_features=2, hidden_dim=64, out_dim=dim_t)
        self.film = FiLMFusion(dim_b=dim_b, dim_t=dim_t)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(dim_b, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: torch.Tensor,
        clin: torch.Tensor,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        z_b = self.encoder_b(img)
        z_t = self.encoder_t(clin)
        z_f, gamma, beta = self.film(z_b, z_t)
        logits = self.head(z_f)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": {"z_b": z_b, "z_t": z_t, "z_f": z_f, "gamma": gamma, "beta": beta},
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


def create_track_a_model(
    model_id: str,
    pretrained: bool = True,
    dropout_p: float = 0.2,
) -> nn.Module:
    """Factory function for Track A model family."""
    if model_id in {"A1", "A1_bmode"}:
        return A1BModeOnly(pretrained=pretrained)
    elif model_id in {"A2", "A2_clinical"}:
        return A2ClinicalOnly()
    elif model_id in {"A3", "A3_concat"}:
        return A3ConcatFusion(pretrained=pretrained)
    elif model_id in {"A4", "A4_gated_fusion"}:
        return A4GatedFusion(pretrained=pretrained, dropout_p=dropout_p)
    elif model_id in {"A5", "A5_film"}:
        return A5FiLMFusion(pretrained=pretrained)
    elif model_id in {"A7", "A7_context_shuffle"}:
        # A7 uses identical A4 architecture, clinical shuffling applied during training
        return A4GatedFusion(pretrained=pretrained, dropout_p=dropout_p)
    else:
        raise ValueError(f"Unknown Track A model_id: {model_id}")
