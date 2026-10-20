"""
Unit tests for Multimodal Loss functions:
- CrossModalContrastiveLoss
- EvidentialBayesLoss
- CompositeMultimodalLoss
"""

import pytest
import torch
from xmai.training.losses import (
    CrossModalContrastiveLoss,
    EvidentialBayesLoss,
    CompositeMultimodalLoss,
)


def test_cross_modal_contrastive_loss():
    B, D_b, D_t = 6, 256, 64
    loss_fn = CrossModalContrastiveLoss(temperature=0.1)

    z_b = torch.randn(B, D_b, requires_grad=True)
    z_t = torch.randn(B, D_t, requires_grad=True)
    labels = torch.tensor([0, 0, 0, 1, 1, 1])

    loss = loss_fn(z_b, z_t, labels)
    assert loss.dim() == 0
    assert loss.item() >= 0.0

    loss.backward()
    assert z_b.grad is not None
    assert z_t.grad is not None
    assert not torch.isnan(z_b.grad).any()


def test_evidential_bayes_loss():
    B, K = 4, 2
    loss_fn = EvidentialBayesLoss(num_classes=K, kl_weight=0.1)

    alpha = torch.tensor([
        [4.0, 1.1],
        [1.2, 5.0],
        [3.0, 2.0],
        [1.0, 4.0],
    ], requires_grad=True)
    targets = torch.tensor([0, 1, 0, 1])

    loss = loss_fn(alpha, targets)
    assert loss.dim() == 0
    assert loss.item() >= 0.0

    loss.backward()
    assert alpha.grad is not None
    assert not torch.isnan(alpha.grad).any()


def test_composite_multimodal_loss_dispatch():
    B = 4
    comp_loss = CompositeMultimodalLoss(align_weight=0.1, evid_weight=1.0)

    # 1. Standard classification output
    std_out = {
        "logits": torch.randn(B, 2),
        "embeddings": {
            "z_b": torch.randn(B, 256),
            "z_t": torch.randn(B, 64),
        },
    }
    targets = torch.tensor([0, 1, 0, 1])
    l1 = comp_loss(std_out, targets)
    assert l1.item() > 0

    # 2. Evidential output
    ev_out = {
        "alpha_fused": torch.tensor([[3.0, 1.2], [1.1, 4.5], [2.5, 1.5], [1.2, 3.8]]),
        "logits": torch.randn(B, 2),
    }
    l2 = comp_loss(ev_out, targets)
    assert l2.item() > 0
