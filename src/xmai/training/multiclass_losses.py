"""
Specialized Loss Formulations for 5-Class / 6-Class Multimodal Differential Diagnosis:
- ClassBalancedFocalLoss: Resolves class imbalance using effective number of samples (Cui et al., CVPR 2019).
- HierarchicalSafetyLoss: Staged loss prioritizing high oncologic sensitivity (>= 99%) on Malignant vs Benign gate.
- MulticlassDirichletEvidentialLoss: Exact Bayesian risk and KL divergence for Subjective Logic (Sensoy et al., NeurIPS 2018).
"""

from typing import List, Optional, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ClassBalancedFocalLoss(nn.Module):
    """
    Class-Balanced Focal Loss for long-tail focal liver lesion subtyping.
    Combines effective number of samples weighting: w_y = (1 - beta) / (1 - beta^{n_y})
    with focal difficulty modulation: (1 - p_t)^gamma * log(p_t).
    """

    def __init__(
        self,
        samples_per_class: List[int],
        beta: float = 0.999,
        gamma: float = 2.0,
        num_classes: int = 5,
    ):
        super().__init__()
        self.gamma = gamma
        self.num_classes = num_classes

        # Calculate class-balanced weights
        effective_num = 1.0 - np.power(beta, samples_per_class)
        weights = (1.0 - beta) / np.array(effective_num, dtype=np.float32)
        # Normalize weights so sum equals num_classes
        weights = weights / np.sum(weights) * num_classes
        self.register_buffer("weights", torch.tensor(weights, dtype=torch.float32))

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: [B, K] unnormalized logits
            targets: [B] class indices in [0, K-1]
        """
        probs = F.softmax(logits, dim=-1)
        targets_one_hot = F.one_hot(targets, num_classes=self.num_classes).float()

        # Class-specific probability p_t
        p_t = (probs * targets_one_hot).sum(dim=-1).clamp(min=1e-7, max=1.0 - 1e-7)

        # Modulating factor (1 - p_t)^gamma
        modulating_factor = torch.pow(1.0 - p_t, self.gamma)

        # Cross entropy component -log(p_t)
        ce = -torch.log(p_t)

        # Class weights w_y
        class_weights = (self.weights.unsqueeze(0) * targets_one_hot).sum(dim=-1)

        loss = class_weights * modulating_factor * ce
        return loss.mean()


class HierarchicalSafetyLoss(nn.Module):
    """
    Two-stage hierarchical loss for M5HierarchicalFusion.
    Penalizes Malignant under-calls severely on Stage 1, while supervising subtyping on Stages 2A/2B.
    """

    def __init__(
        self,
        mal_weight: float = 2.5,
        lambda_stage1: float = 1.0,
        lambda_sub: float = 1.0,
        mal_indices: Optional[List[int]] = None,
        ben_indices: Optional[List[int]] = None,
    ):
        super().__init__()
        self.lambda_stage1 = lambda_stage1
        self.lambda_sub = lambda_sub
        self.mal_indices = mal_indices if mal_indices is not None else [0, 4]  # HCC, Cholangiocarcinoma
        self.ben_indices = ben_indices if ben_indices is not None else [1, 2, 3]  # Hemangioma, FNH, Adenoma

        # Asymmetric weights on Stage 1 to penalize false negatives for cancer
        stage1_weights = torch.tensor([1.0, mal_weight], dtype=torch.float32)
        self.stage1_criterion = nn.CrossEntropyLoss(weight=stage1_weights)
        self.ce_criterion = nn.CrossEntropyLoss()

    def forward(
        self,
        out_dict: dict,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            out_dict: output of M5HierarchicalFusion
            targets: [B] global class indices
        """
        device = targets.device

        # 1. Derive Stage 1 binary targets: 1 if Malignant, 0 if Benign
        is_mal = torch.zeros_like(targets, dtype=torch.long)
        for idx in self.mal_indices:
            is_mal = is_mal | (targets == idx)
        stage1_targets = is_mal.long()

        loss_stage1 = self.stage1_criterion(out_dict["logits_stage1"], stage1_targets)

        # 2. Stage 2B: Malignant subtyping loss (computed on malignant samples)
        mal_mask = (stage1_targets == 1)
        if mal_mask.any():
            mal_targets = targets[mal_mask]
            # Map global index to sub-index [0..num_mal-1]
            sub_mal_targets = torch.zeros_like(mal_targets)
            for sub_i, glob_i in enumerate(self.mal_indices):
                sub_mal_targets[mal_targets == glob_i] = sub_i
            loss_mal = self.ce_criterion(out_dict["logits_malignant"][mal_mask], sub_mal_targets)
        else:
            loss_mal = torch.tensor(0.0, device=device)

        # 3. Stage 2A: Benign subtyping loss (computed on benign samples)
        ben_mask = (stage1_targets == 0)
        if ben_mask.any():
            ben_targets = targets[ben_mask]
            sub_ben_targets = torch.zeros_like(ben_targets)
            for sub_i, glob_i in enumerate(self.ben_indices):
                sub_ben_targets[ben_targets == glob_i] = sub_i
            loss_ben = self.ce_criterion(out_dict["logits_benign"][ben_mask], sub_ben_targets)
        else:
            loss_ben = torch.tensor(0.0, device=device)

        total_loss = (
            self.lambda_stage1 * loss_stage1 +
            self.lambda_sub * (loss_mal + loss_ben)
        )
        return total_loss


class MulticlassDirichletEvidentialLoss(nn.Module):
    """
    Dirichlet Bayesian Risk and KL divergence loss for Subjective Logic (K classes).
    L_total = L_ACE + lambda_epoch * L_KL
    """

    def __init__(self, num_classes: int = 5, kl_anneal_epochs: int = 10):
        super().__init__()
        self.num_classes = num_classes
        self.kl_anneal_epochs = kl_anneal_epochs

    @staticmethod
    def _kl_divergence(alpha: torch.Tensor, num_classes: int) -> torch.Tensor:
        """KL divergence between Dir(alpha) and uniform flat prior Dir(1)."""
        ones = torch.ones((1, num_classes), dtype=torch.float32, device=alpha.device)
        sum_alpha = torch.sum(alpha, dim=1, keepdim=True)
        sum_ones = torch.sum(ones, dim=1, keepdim=True)

        t1 = torch.lgamma(sum_alpha) - torch.lgamma(sum_ones)
        t2 = torch.sum(torch.lgamma(ones) - torch.lgamma(alpha), dim=1, keepdim=True)
        t3 = torch.sum(
            (alpha - ones) * (torch.digamma(alpha) - torch.digamma(sum_alpha)),
            dim=1,
            keepdim=True,
        )
        kl = t1 + t2 + t3
        return kl.squeeze(-1)

    def forward(
        self,
        alpha: torch.Tensor,
        targets: torch.Tensor,
        epoch: int = 0,
    ) -> torch.Tensor:
        """
        Args:
            alpha: [B, K] Dirichlet concentration parameters (alpha = evidence + 1)
            targets: [B] class indices
            epoch: current training epoch for KL annealing
        """
        targets_one_hot = F.one_hot(targets, num_classes=self.num_classes).float()
        S = torch.sum(alpha, dim=1, keepdim=True)

        # Expected cross-entropy under Dirichlet: sum y_k (digamma(S) - digamma(alpha_k))
        ace = torch.sum(
            targets_one_hot * (torch.digamma(S) - torch.digamma(alpha)),
            dim=1,
        )

        # KL divergence regularizer (removes ground-truth evidence before calculating KL)
        tilde_alpha = targets_one_hot + (1.0 - targets_one_hot) * alpha
        kl = self._kl_divergence(tilde_alpha, self.num_classes)

        # Anneal KL weight from 0.0 to 1.0 over epochs
        annealing_coef = min(1.0, float(epoch) / float(max(1, self.kl_anneal_epochs)))
        loss = ace + annealing_coef * kl
        return loss.mean()
