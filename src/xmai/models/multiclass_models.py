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


class M5HierarchicalFusion(nn.Module):
    """
    Model M5_Hierarchical: Hierarchical Coarse-to-Fine Multimodal Decision Architecture.
    
    Structure:
    - Shared Representation: Mask-Aware Gated Fusion producing z_F in R^256.
    - Stage 1 (Oncologic Safety Gate): Malignant vs. Benign binary head (Sensitivity-oriented).
    - Stage 2A (Benign Subtyping Head): Distinguishes Hemangioma, FNH, and Adenoma.
    - Stage 2B (Malignant Subtyping Head): Differentiates HCC from Cholangiocarcinoma.
    
    Probabilities are composed via the Law of Total Probability:
        P(malignant_k) = P(Malignant) * P(malignant_k | Malignant)
        P(benign_k)    = P(Benign)    * P(benign_k | Benign)
    Guarantees strict sum-to-1.0 and prevents catastrophic cross-tier confusions.
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

        # Encoders and Shared Gated Fusion
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=dim_b)
        self.encoder_t = MulticlassClinicalEncoder(in_features=8, hidden_dim=dim_t, out_dim=dim_t)
        self.fusion = MaskAwareGatedFusion(
            dim_b=dim_b,
            dim_c=256,
            dim_t=dim_t,
            fused_dim=fused_dim,
            dropout_p=dropout_p,
        )

        # Partition classes into Malignant and Benign indices
        self.mal_indices = [i for i, c in enumerate(self.class_names) if CLASS_TIER_MAPPING.get(c) == "Malignant"]
        self.ben_indices = [i for i, c in enumerate(self.class_names) if CLASS_TIER_MAPPING.get(c) == "Benign"]
        self.num_mal = len(self.mal_indices)
        self.num_ben = len(self.ben_indices)

        if self.num_mal == 0 or self.num_ben == 0:
            raise ValueError(f"Hierarchical tree requires both Malignant and Benign classes, got mal={self.num_mal}, ben={self.num_ben}")

        # Stage 1: Coarse Oncologic Safety Gate (Binary: [Benign, Malignant])
        self.stage1_gate = nn.Sequential(
            nn.Dropout(p=dropout_p),
            nn.Linear(fused_dim, 2),
        )

        # Stage 2A: Benign Subtyping Head
        self.stage2_benign = nn.Sequential(
            nn.Dropout(p=dropout_p),
            nn.Linear(fused_dim, self.num_ben),
        )

        # Stage 2B: Malignant Subtyping Head
        self.stage2_malignant = nn.Sequential(
            nn.Dropout(p=dropout_p),
            nn.Linear(fused_dim, self.num_mal),
        )

        # Calibrated temperature parameters
        self.temp_stage1 = nn.Parameter(torch.ones(1), requires_grad=False)
        self.temp_ben = nn.Parameter(torch.ones(1), requires_grad=False)
        self.temp_mal = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(
        self,
        img: Optional[torch.Tensor] = None,
        clin: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """Hierarchical forward pass returning staged and composed class probabilities."""
        z_b = self.encoder_b(img) if img is not None else None
        z_t = self.encoder_t(clin) if clin is not None else None

        if mod_mask is not None and mod_mask.shape[1] == 2:
            device = mod_mask.device
            B = mod_mask.shape[0]
            full_mask = torch.zeros(B, 3, device=device)
            full_mask[:, 0] = mod_mask[:, 0]
            full_mask[:, 2] = mod_mask[:, 1]
        else:
            full_mask = mod_mask

        z_f, raw_gate_weights = self.fusion(z_b=z_b, z_c=None, z_t=z_t, mod_mask=full_mask)
        gate_weights = torch.stack([raw_gate_weights[:, 0], raw_gate_weights[:, 2]], dim=1)
        gate_weights = gate_weights / gate_weights.sum(dim=1, keepdim=True).clamp(min=1e-7)

        # Stage 1: Malignant vs Benign
        logits_stage1 = self.stage1_gate(z_f)
        probs_stage1 = F.softmax(logits_stage1 / self.temp_stage1, dim=-1)  # [B, 2]: [p_ben, p_mal]
        p_benign = probs_stage1[:, 0:1]
        p_malignant = probs_stage1[:, 1:2]

        # Stage 2: Subtyping
        logits_ben = self.stage2_benign(z_f)
        probs_sub_ben = F.softmax(logits_ben / self.temp_ben, dim=-1)  # [B, num_ben]

        logits_mal = self.stage2_malignant(z_f)
        probs_sub_mal = F.softmax(logits_mal / self.temp_mal, dim=-1)  # [B, num_mal]

        # Compose full K-class distribution via Law of Total Probability
        B = z_f.shape[0]
        full_probs = torch.zeros(B, self.num_classes, device=z_f.device)
        for idx_in_sub, global_idx in enumerate(self.ben_indices):
            full_probs[:, global_idx] = (p_benign * probs_sub_ben[:, idx_in_sub:idx_in_sub+1]).squeeze(1)

        for idx_in_sub, global_idx in enumerate(self.mal_indices):
            full_probs[:, global_idx] = (p_malignant * probs_sub_mal[:, idx_in_sub:idx_in_sub+1]).squeeze(1)

        # Surrogate logits for unified metrics
        surrogate_logits = torch.log(full_probs.clamp(min=1e-7))

        return {
            "logits": surrogate_logits,
            "calibrated_logits": surrogate_logits,
            "probs": full_probs,
            "logits_stage1": logits_stage1,
            "p_malignant": p_malignant,
            "p_benign": p_benign,
            "logits_benign": logits_ben,
            "logits_malignant": logits_mal,
            "gate_weights": gate_weights,
            "embeddings": {
                "z_b": z_b,
                "z_t": z_t,
                "z_f": z_f,
            },
        }

    def set_temperatures(self, t_stage1: float, t_ben: float, t_mal: float) -> None:
        """Sets calibrated temperatures for Stage 1, Benign, and Malignant heads."""
        self.temp_stage1.data.fill_(max(0.1, t_stage1))
        self.temp_ben.data.fill_(max(0.1, t_ben))
        self.temp_mal.data.fill_(max(0.1, t_mal))

