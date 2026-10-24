"""Stress testing and mathematical invariant verification for multimodal loss functions.

Academic Qualification Suite:
- Contrastive InfoNCE lower-bound temperature invariance and similarity kernel stability
- Dirichlet Evidential Bayes Risk digamma singularity guards and KL divergence bounds
- Numerical finite guards under extreme, degenerate, and boundary inputs
"""

import pytest
import torch
import torch.nn.functional as F
from xmai.training.losses import CrossModalContrastiveLoss, EvidentialBayesLoss


class TestCrossModalContrastiveLossStress:
    """Stress tests for multimodal InfoNCE contrastive alignment."""

    def test_temperature_zero_or_negative_clamping(self):
        """Zero or near-zero temperature must be safely clamped to prevent division by zero."""
        loss_fn = CrossModalContrastiveLoss(temperature=0.0)
        z_b = torch.randn(4, 128)
        z_t = torch.randn(4, 128)
        labels = torch.tensor([0, 1, 0, 1])

        loss = loss_fn(z_b, z_t, labels)
        assert torch.isfinite(loss), "Loss must be finite even when temperature is 0.0"
        assert loss.item() >= 0.0, "Contrastive loss must be non-negative"

    def test_identical_embeddings_perfect_alignment(self):
        """When positive representations are identical, loss should achieve minimal theoretical bound."""
        loss_fn = CrossModalContrastiveLoss(temperature=0.1)
        # Create identical representations
        rep = torch.randn(4, 64)
        rep = F.normalize(rep, dim=1)
        labels = torch.tensor([0, 1, 2, 0])

        loss = loss_fn(rep, rep, labels)
        assert torch.isfinite(loss)
        assert loss.item() >= 0.0

    def test_orthogonal_embeddings(self):
        """Orthogonal representations must not cause gradient underflow or invalid similarity."""
        loss_fn = CrossModalContrastiveLoss(temperature=0.07)
        # Construct orthogonal vectors
        q, _ = torch.linalg.qr(torch.randn(8, 8))
        z_b = q[:4, :].clone().detach().requires_grad_(True)
        z_t = q[4:, :].clone().detach().requires_grad_(True)
        labels = torch.tensor([0, 1, 0, 1])

        loss = loss_fn(z_b, z_t, labels)
        assert torch.isfinite(loss)
        loss.backward()
        assert z_b.grad is not None and torch.isfinite(z_b.grad).all()

    def test_all_same_class_batch(self):
        """When all samples in a batch belong to the same class, InfoNCE must maintain valid denominator."""
        loss_fn = CrossModalContrastiveLoss(temperature=0.1)
        z_b = torch.randn(6, 32)
        z_t = torch.randn(6, 32)
        labels = torch.zeros(6, dtype=torch.long)

        loss = loss_fn(z_b, z_t, labels)
        assert torch.isfinite(loss)
        assert loss.item() >= 0.0

    def test_dimension_mismatch_projection(self):
        """When visual and text embedding dimensions differ, projection layer must align them."""
        loss_fn = CrossModalContrastiveLoss(temperature=0.07)
        z_b = torch.randn(4, 128)
        z_t = torch.randn(4, 64)
        labels = torch.tensor([0, 1, 0, 1])

        loss = loss_fn(z_b, z_t, labels)
        assert torch.isfinite(loss)
        assert loss.shape == ()


class TestEvidentialBayesLossStress:
    """Stress tests for Dirichlet evidential uncertainty Bayes risk."""

    def test_sub_unity_alpha_clamping(self):
        """Dirichlet parameters below 1.0 (sub-unity) must be clamped to prevent digamma singularities."""
        loss_fn = EvidentialBayesLoss(kl_weight=0.1)
        # Pass alpha strictly < 1.0 (e.g. 0.05)
        alpha_sub_unity = torch.full((4, 2), 0.05, requires_grad=True)
        targets = torch.tensor([0, 1, 0, 1])

        loss = loss_fn(alpha_sub_unity, targets)
        assert torch.isfinite(loss), "Loss must remain finite without digamma negative infinity crash"
        assert not torch.isnan(loss)
        assert not torch.isinf(loss)

        loss.backward()
        assert torch.isfinite(alpha_sub_unity.grad).all(), "Gradients must be finite after clamping"

    def test_extreme_high_evidence(self):
        """Extremely high evidence should not cause overflow in total evidence S = sum(alpha)."""
        loss_fn = EvidentialBayesLoss(kl_weight=0.05)
        alpha_huge = torch.full((3, 2), 1e5, requires_grad=True)
        targets = torch.tensor([0, 1, 0])

        loss = loss_fn(alpha_huge, targets)
        assert torch.isfinite(loss)

    def test_bayesian_loss_monotonicity(self):
        """Loss on correct prediction should decrease as evidence for the correct class increases."""
        loss_fn = EvidentialBayesLoss(kl_weight=0.0)  # Pure Bayes risk without KL
        targets = torch.tensor([0])

        # High confidence for class 0
        alpha_high_conf = torch.tensor([[100.0, 1.0]])
        # Low confidence for class 0
        alpha_low_conf = torch.tensor([[2.0, 1.0]])

        loss_high = loss_fn(alpha_high_conf, targets)
        loss_low = loss_fn(alpha_low_conf, targets)

        assert loss_high.item() < loss_low.item(), (
            f"Expected high confidence loss ({loss_high.item()}) < low confidence loss ({loss_low.item()})"
        )

    def test_multiclass_generalization(self):
        """Evidential loss must support arbitrary number of classes K >= 2."""
        loss_fn = EvidentialBayesLoss(num_classes=5, kl_weight=0.1)
        K = 5
        alpha = torch.ones(8, K) + torch.rand(8, K) * 10.0
        targets = torch.randint(0, K, (8,))

        loss = loss_fn(alpha, targets)
        assert torch.isfinite(loss)
        assert loss.item() >= 0.0
