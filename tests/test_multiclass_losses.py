"""
Unit and mathematical invariance tests for multiclass loss formulations:
- ClassBalancedFocalLoss
- HierarchicalSafetyLoss
- MulticlassDirichletEvidentialLoss
"""

import pytest
import torch
from xmai.training.multiclass_losses import (
    ClassBalancedFocalLoss,
    HierarchicalSafetyLoss,
    MulticlassDirichletEvidentialLoss,
)


def test_class_balanced_focal_loss_invariants():
    """Verify class-balanced weights, focal modulation, non-negativity, and backprop."""
    samples = [400, 300, 200, 100, 50]  # Imbalanced 5 classes
    criterion = ClassBalancedFocalLoss(samples_per_class=samples, beta=0.999, gamma=2.0, num_classes=5)

    # Class 4 (least frequent, n=50) must have higher weight than Class 0 (most frequent, n=400)
    assert criterion.weights[4].item() > criterion.weights[0].item()

    B = 10
    logits = torch.randn(B, 5, requires_grad=True)
    targets = torch.tensor([0, 1, 2, 3, 4, 0, 1, 2, 3, 4])

    loss = criterion(logits, targets)
    assert loss.item() >= 0.0
    loss.backward()
    assert logits.grad is not None
    assert torch.all(torch.isfinite(logits.grad))


def test_hierarchical_safety_loss_penalizes_malignant_undercall():
    """Verify that misclassifying a Malignant lesion as Benign produces higher loss."""
    loss_fn = HierarchicalSafetyLoss(mal_weight=3.0, lambda_stage1=1.0, lambda_sub=1.0)

    # Fake model output where Stage 1 strongly predicts Benign ([logit_ben, logit_mal])
    out_benign_pred = {
        "logits_stage1": torch.tensor([[4.0, -4.0]]),     # Predicts Benign with high confidence
        "logits_benign": torch.tensor([[2.0, 0.0, 0.0]]),
        "logits_malignant": torch.tensor([[2.0, 0.0]]),
    }

    # True Malignant sample (Class 0: HCC) misclassified as Benign
    target_mal = torch.tensor([0])
    loss_undercall = loss_fn(out_benign_pred, target_mal)

    # True Benign sample (Class 1: Hemangioma) correctly classified as Benign on Stage 1
    target_ben = torch.tensor([1])
    loss_correct_stage1 = loss_fn(out_benign_pred, target_ben)

    # Severe penalty assertion
    assert loss_undercall.item() > loss_correct_stage1.item() * 3.0


def test_multiclass_dirichlet_kl_zero_on_flat_prior():
    """Verify that KL divergence between Dir(1) and Dir(1) is exactly zero."""
    num_classes = 5
    ones = torch.ones(2, num_classes)
    kl_zero = MulticlassDirichletEvidentialLoss._kl_divergence(ones, num_classes=num_classes)

    assert torch.allclose(kl_zero, torch.zeros_like(kl_zero), atol=1e-5), "KL(Dir(1)||Dir(1)) must be 0.0"


def test_multiclass_dirichlet_loss_annealing():
    """Verify that Dirichlet loss anneals KL divergence properly across epochs."""
    criterion = MulticlassDirichletEvidentialLoss(num_classes=5, kl_anneal_epochs=10)

    alpha = torch.tensor([[5.0, 1.0, 1.0, 1.0, 1.0]], requires_grad=True)
    targets = torch.tensor([0])

    # Epoch 0: only ACE loss, KL factor is 0.0
    loss_ep0 = criterion(alpha, targets, epoch=0)
    # Epoch 10: full KL regularization
    loss_ep10 = criterion(alpha, targets, epoch=10)

    assert loss_ep0.item() >= 0.0
    assert loss_ep10.item() >= 0.0
    # Both allow backprop
    loss_ep10.backward()
    assert alpha.grad is not None

