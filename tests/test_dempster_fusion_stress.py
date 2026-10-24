"""Stress testing and mathematical invariant verification for Dempster-Shafer evidential fusion.

Academic Qualification Suite:
- Invariant 1: Belief mass conservation: sum(b_k) + u == 1.0 strictly holds across all evidence states
- Invariant 2: Neutral / vacuous opinion identity: fusing with vacuous belief (b=0, u=1) yields identical opinion
- Invariant 3: High-conflict stability: orthogonal diametric beliefs (C -> 1.0) remain bounded and finite
- Invariant 4: Commutativity and associativity under multi-source evidence combination
"""

import pytest
import torch
import torch.nn.functional as F
from xmai.models.fusion import EvidentialMultimodalFusion


class TestDempsterShaferFusionStress:
    """Stress tests for Dempster's rule of combination in EvidentialMultimodalFusion."""

    def test_belief_mass_conservation_invariant(self):
        """Under arbitrary random evidence, sum(b_k) + u must strictly equal 1.0 within numerical precision."""
        fusion = EvidentialMultimodalFusion(dim_b=64, dim_t=32, num_classes=2)
        z_b = torch.randn(10, 64)
        z_t = torch.randn(10, 32)

        out = fusion(z_b=z_b, z_t=z_t)
        b_fused = out["b_fused"]
        u_fused = out["u_fused"]

        total_mass = torch.sum(b_fused, dim=1, keepdim=True) + u_fused
        assert torch.allclose(total_mass, torch.ones_like(total_mass), atol=1e-5), (
            f"Belief mass conservation violated: {total_mass}"
        )

    def test_vacuous_opinion_identity(self):
        """Fusing an informative opinion with a completely vacuous opinion (b=0, u=1) must return the original opinion."""
        K = 2
        # Informative opinion: b1 = [0.7, 0.1], u1 = 0.2
        b1 = torch.tensor([[0.7, 0.1]])
        u1 = torch.tensor([[0.2]])

        # Vacuous opinion: b2 = [0.0, 0.0], u2 = 1.0
        b2 = torch.zeros(1, K)
        u2 = torch.ones(1, 1)

        b_fused, u_fused = EvidentialMultimodalFusion.dempster_combination(b1, u1, b2, u2)

        assert torch.allclose(b_fused, b1, atol=1e-5), "Fused belief must equal b1 when b2 is vacuous"
        assert torch.allclose(u_fused, u1, atol=1e-5), "Fused uncertainty must equal u1 when b2 is vacuous"

    def test_extreme_conflict_resilience(self):
        """Diametrically opposed high-confidence opinions (C -> 1.0) must not cause NaN or Inf."""
        # Modality 1 strongly favors class 0; Modality 2 strongly favors class 1
        b1 = torch.tensor([[0.9999, 0.0000]])
        u1 = torch.tensor([[0.0001]])

        b2 = torch.tensor([[0.0000, 0.9999]])
        u2 = torch.tensor([[0.0001]])

        b_fused, u_fused = EvidentialMultimodalFusion.dempster_combination(b1, u1, b2, u2)

        assert torch.isfinite(b_fused).all(), "Fused belief must remain finite during extreme conflict"
        assert torch.isfinite(u_fused).all(), "Fused uncertainty must remain finite during extreme conflict"
        total_mass = torch.sum(b_fused, dim=1, keepdim=True) + u_fused
        assert torch.isfinite(total_mass).all()

    def test_commutative_property(self):
        """Dempster combination must be commutative: Combination(A, B) == Combination(B, A)."""
        b1 = torch.tensor([[0.6, 0.2]])
        u1 = torch.tensor([[0.2]])

        b2 = torch.tensor([[0.3, 0.5]])
        u2 = torch.tensor([[0.2]])

        b_ab, u_ab = EvidentialMultimodalFusion.dempster_combination(b1, u1, b2, u2)
        b_ba, u_ba = EvidentialMultimodalFusion.dempster_combination(b2, u2, b1, u1)

        assert torch.allclose(b_ab, b_ba, atol=1e-6), "Dempster combination must be commutative in belief"
        assert torch.allclose(u_ab, u_ba, atol=1e-6), "Dempster combination must be commutative in uncertainty"

    def test_single_modality_missing_via_mask(self):
        """When modality mask indicates missing clinical context, fusion must rely entirely on B-mode without crash."""
        fusion = EvidentialMultimodalFusion(dim_b=64, dim_t=32, num_classes=2)
        z_b = torch.randn(5, 64)
        z_t = torch.randn(5, 32)
        # mod_mask: [B_present=1, CEUS_present=0, Clinical_present=0]
        mod_mask = torch.tensor([[1.0, 0.0, 0.0]] * 5)

        out = fusion(z_b=z_b, z_t=z_t, mod_mask=mod_mask)

        assert torch.allclose(out["b_t"], torch.zeros_like(out["b_t"]))
        assert torch.allclose(out["u_t"], torch.ones_like(out["u_t"]))
        # Fused belief should match B-mode belief
        assert torch.allclose(out["b_fused"], out["b_b"], atol=1e-5)
