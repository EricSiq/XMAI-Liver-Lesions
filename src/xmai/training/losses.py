"""
Multimodal Loss Functions for XMAI:
1. CrossModalContrastiveLoss: Supervised cross-modal InfoNCE alignment.
2. EvidentialBayesLoss: Dirichlet subjective logic likelihood with KL divergence penalty.
3. CompositeMultimodalLoss: Unified loss supporting standard classification,
   cross-modal feature alignment, and evidential uncertainty learning.
"""

from typing import Any, Dict, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class CrossModalContrastiveLoss(nn.Module):
    """
    Supervised cross-modal InfoNCE contrastive alignment.
    Aligns visual (z_B) and clinical context (z_T) embeddings on a shared hypersphere.
    Patients with identical clinical diagnosis (e.g. both HCC) act as positive pairs,
    preventing unimodal dominance and suppressing demographic shortcutting.
    """

    def __init__(self, temperature: float = 0.1):
        super().__init__()
        self.temperature = temperature

    def forward(
        self,
        z_b: torch.Tensor,
        z_t: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        """
        Input:
            z_b: [B, D_b]
            z_t: [B, D_t]
            labels: [B] integer targets (0: Hemangioma, 1: HCC)
        Output:
            scalar contrastive loss
        """
        B = z_b.shape[0]
        if B <= 1:
            return torch.tensor(0.0, device=z_b.device, requires_grad=True)

        # L2-normalize embeddings
        norm_b = F.normalize(z_b, p=2, dim=1)
        # If dimensions differ, project z_t to z_b dimension via adaptive linear pooling or slice
        if z_t.shape[1] != z_b.shape[1]:
            # Simple zero-padded or linear-interpolated dimension match
            z_t_proj = F.interpolate(z_t.unsqueeze(1), size=z_b.shape[1], mode="linear", align_corners=False).squeeze(1)
        else:
            z_t_proj = z_t
        norm_t = F.normalize(z_t_proj, p=2, dim=1)

        temp = max(self.temperature, 1e-4)
        # Cross-modal cosine similarity matrix: [B, B]
        sim_bt = torch.matmul(norm_b, norm_t.T) / temp

        # Positive pair mask where diagnosis agrees: [B, B]
        target_col = labels.view(-1, 1)
        pos_mask = (target_col == target_col.T).float()

        # Compute log-softmax across columns
        log_prob = F.log_softmax(sim_bt, dim=1)

        # Mean over positive pairs per row
        pos_counts = torch.clamp(pos_mask.sum(dim=1), min=1.0)
        loss = -(pos_mask * log_prob).sum(dim=1) / pos_counts

        return loss.mean()


class EvidentialBayesLoss(nn.Module):
    """
    Bayes Risk for Dirichlet distribution with KL divergence regularization penalty.
    Formulation from Sensoy et al. (NeurIPS 2018) & Han et al. (TPAMI 2022).
    """

    def __init__(self, num_classes: int = 2, kl_weight: float = 0.1):
        super().__init__()
        self.num_classes = num_classes
        self.kl_weight = kl_weight

    def forward(
        self,
        alpha: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """
        Input:
            alpha: [B, K] Dirichlet parameters >= 1.0
            targets: [B] integer labels
        Output:
            scalar evidential risk
        """
        B, K = alpha.shape
        device = alpha.device

        # Numerical safety guard: alpha must be >= 1.0
        alpha = torch.clamp(alpha, min=1.0)

        # One-hot target vector: [B, K]
        y = F.one_hot(targets, num_classes=K).float().to(device)

        # Total Dirichlet strength S = sum_k alpha_k
        S = torch.sum(alpha, dim=1, keepdim=True)  # [B, 1]

        # Expected log likelihood: sum_k y_k * (psi(S) - psi(alpha_k))
        psi_S = torch.digamma(S)
        psi_alpha = torch.digamma(alpha)
        loss_err = torch.sum(y * (psi_S - psi_alpha), dim=1)  # [B]

        # KL divergence penalty: shrinks misleading evidence (1 - y) * alpha toward 1
        alpha_tilde = y + (1.0 - y) * alpha  # keep ground truth evidence, penalize false evidence
        S_tilde = torch.sum(alpha_tilde, dim=1, keepdim=True)

        # KL(Dir(alpha_tilde) || Dir(1))
        first_term = (
            torch.lgamma(S_tilde)
            - torch.sum(torch.lgamma(alpha_tilde), dim=1, keepdim=True)
            - torch.lgamma(torch.tensor(float(K), device=device))
        )
        second_term = torch.sum(
            (alpha_tilde - 1.0) * (torch.digamma(alpha_tilde) - torch.digamma(S_tilde)),
            dim=1,
            keepdim=True,
        )
        kl_div = (first_term + second_term).squeeze(-1)  # [B]

        total_loss = loss_err + self.kl_weight * kl_div
        return total_loss.mean()


class CompositeMultimodalLoss(nn.Module):
    """
    Unified Multimodal Loss:
    L = L_ce + lambda_align * L_contrastive + lambda_evid * L_evidential
    """

    def __init__(
        self,
        weight: Optional[torch.Tensor] = None,
        label_smoothing: float = 0.05,
        align_weight: float = 0.05,
        evid_weight: float = 1.0,
        num_classes: int = 2,
    ):
        super().__init__()
        self.ce_loss = nn.CrossEntropyLoss(weight=weight, label_smoothing=label_smoothing)
        self.contrastive_loss = CrossModalContrastiveLoss(temperature=0.1)
        self.evidential_loss = EvidentialBayesLoss(num_classes=num_classes)
        self.align_weight = align_weight
        self.evid_weight = evid_weight

    def forward(
        self,
        model_out: Dict[str, Any],
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """
        Computes composite loss across available model outputs and embeddings.
        """
        # If evidential output (A9) with alpha_fused
        if "alpha_fused" in model_out:
            loss = self.evid_weight * self.evidential_loss(model_out["alpha_fused"], targets)
        else:
            # Standard Cross Entropy
            loss = self.ce_loss(model_out["logits"], targets)

        # Contrastive cross-modal feature alignment
        if self.align_weight > 0 and "embeddings" in model_out:
            embs = model_out["embeddings"]
            z_b = embs.get("z_b")
            z_t = embs.get("z_t")
            if z_b is not None and z_t is not None:
                align_l = self.contrastive_loss(z_b, z_t, targets)
                loss = loss + self.align_weight * align_l

        return loss
