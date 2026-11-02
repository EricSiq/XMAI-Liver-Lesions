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


class M5EvidentialFusion(nn.Module):
    """
    Model M5_Evidential: Multiclass Evidential Multimodal Fusion (EUF).
    Formulates K-class predictions under Subjective Logic & Dempster-Shafer theory.
    
    Produces explicit epistemic uncertainty mass u alongside class beliefs b_1..b_K:
        sum_{k=1}^K b_k + u = 1.0
    
    When visual and clinical signals conflict across classes, the conflict metric C spikes,
    elevating vacuous uncertainty u to trigger certified safety referral.
    """

    def __init__(
        self,
        num_classes: int = 5,
        pretrained: bool = True,
        dim_b: int = 256,
        dim_t: int = 128,
        class_names: Optional[List[str]] = None,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.class_names = class_names or list(TAXONOMY_5CLASS)

        # Modality Encoders
        self.encoder_b = BModeEncoder(pretrained=pretrained, embed_dim=dim_b)
        self.encoder_t = MulticlassClinicalEncoder(in_features=8, hidden_dim=dim_t, out_dim=dim_t)

        # Modality Evidence Heads (Output non-negative evidence e_k >= 0 via Softplus)
        self.evidence_head_b = nn.Sequential(
            nn.Linear(dim_b, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes),
            nn.Softplus(),
        )

        self.evidence_head_t = nn.Sequential(
            nn.Linear(dim_t, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes),
            nn.Softplus(),
        )

        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def _evidence_to_belief(self, evidence: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Converts non-negative evidence to Dirichlet concentration alpha, belief mass, and vacuous uncertainty.
        Input: evidence [B, K] >= 0
        Output: alpha [B, K], belief [B, K], uncertainty [B, 1]
        """
        alpha = evidence + 1.0
        S = torch.sum(alpha, dim=1, keepdim=True).clamp(min=1e-7)  # Total Dirichlet strength
        belief = evidence / S                                      # [B, K]
        uncertainty = self.num_classes / S                         # [B, 1]
        return alpha, belief, uncertainty

    @staticmethod
    def dempster_combination_multiclass(
        b1: torch.Tensor, u1: torch.Tensor, b2: torch.Tensor, u2: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Dempster's Rule of Combination generalized to K classes.
        Args:
            b1, b2: [B, K] belief vectors
            u1, u2: [B, 1] epistemic uncertainty scalars
        Returns:
            b_fused: [B, K] combined belief vector
            u_fused: [B, 1] combined epistemic uncertainty
        """
        # Mutual agreement: b1_k * b2_k
        diag_agree = b1 * b2  # [B, K]
        sum_agree = torch.sum(diag_agree, dim=1, keepdim=True)  # [B, 1]

        # Multi-class conflict: C = (sum b1_i)*(sum b2_j) - sum(b1_k * b2_k)
        sum_b1 = torch.sum(b1, dim=1, keepdim=True)  # [B, 1]
        sum_b2 = torch.sum(b2, dim=1, keepdim=True)  # [B, 1]
        C = (sum_b1 * sum_b2) - sum_agree            # [B, 1]

        scale = torch.clamp(1.0 - C, min=1e-6)       # [B, 1]

        # Combined belief mass: b_k = (b1_k * b2_k + b1_k * u2 + b2_k * u1) / (1 - C)
        b_fused = (diag_agree + b1 * u2 + b2 * u1) / scale

        # Combined uncertainty: u = (u1 * u2) / (1 - C)
        u_fused = (u1 * u2) / scale

        # Strictly enforce sum-to-1.0 normalization against numerical precision drift
        total = torch.sum(b_fused, dim=1, keepdim=True) + u_fused
        b_fused = b_fused / total
        u_fused = u_fused / total

        return b_fused, u_fused

    def forward(
        self,
        img: Optional[torch.Tensor] = None,
        clin: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """Forward pass generating modality-specific and fused Dirichlet distributions."""
        B = img.shape[0] if img is not None else (clin.shape[0] if clin is not None else 1)
        device = img.device if img is not None else (clin.device if clin is not None else torch.device("cpu"))

        # Modality B: B-mode
        if img is not None:
            z_b = self.encoder_b(img)
            ev_b = self.evidence_head_b(z_b)
        else:
            z_b = torch.zeros(B, 256, device=device)
            ev_b = torch.zeros(B, self.num_classes, device=device)

        # Modality T: Clinical context
        if clin is not None:
            z_t = self.encoder_t(clin)
            ev_t = self.evidence_head_t(z_t)
        else:
            z_t = torch.zeros(B, 128, device=device)
            ev_t = torch.zeros(B, self.num_classes, device=device)

        # Apply modality mask if provided
        if mod_mask is not None:
            m_b = mod_mask[:, 0:1]
            m_t = mod_mask[:, 1:2] if mod_mask.shape[1] > 1 else torch.ones_like(m_b)
            ev_b = ev_b * m_b
            ev_t = ev_t * m_t

        alpha_b, b_b, u_b = self._evidence_to_belief(ev_b)
        alpha_t, b_t, u_t = self._evidence_to_belief(ev_t)

        # Fuse beliefs via Dempster-Shafer combination
        b_fused, u_fused = self.dempster_combination_multiclass(b_b, u_b, b_t, u_t)

        # Expected class probability: p_k = alpha_k / S = b_k + u / K
        probs = b_fused + (u_fused / self.num_classes)

        # Surrogate logits for unified evaluation & temperature scaling
        surrogate_logits = torch.log(probs.clamp(min=1e-7))
        calibrated_logits = surrogate_logits / self.temperature
        calibrated_probs = F.softmax(calibrated_logits, dim=-1)

        # Reconstructed Dirichlet parameter alpha_fused = evidence + 1
        # where evidence = b_fused * (K / u_fused)
        S_fused = (self.num_classes / u_fused.clamp(min=1e-5))
        alpha_fused = b_fused * S_fused + 1.0

        return {
            "logits": surrogate_logits,
            "calibrated_logits": calibrated_logits,
            "probs": calibrated_probs,
            "expected_probs": probs,
            "b_fused": b_fused,
            "u_fused": u_fused,
            "alpha_fused": alpha_fused,
            "b_b": b_b,
            "u_b": u_b,
            "b_t": b_t,
            "u_t": u_t,
            "embeddings": {
                "z_b": z_b,
                "z_t": z_t,
            },
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


