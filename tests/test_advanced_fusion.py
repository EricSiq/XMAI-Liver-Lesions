"""
Unit tests for Advanced Multimodal Fusion Paradigms:
- CrossModalAttentionFusion (CMAF)
- EvidentialMultimodalFusion (Subjective Logic / Dempster's Rule)
"""

import pytest
import torch
from xmai.models.fusion import CrossModalAttentionFusion, EvidentialMultimodalFusion


def test_cross_modal_attention_fusion_forward_and_gradients():
    B, dim_b, dim_t, embed_dim = 4, 256, 64, 256
    cmaf = CrossModalAttentionFusion(dim_b=dim_b, dim_t=dim_t, embed_dim=embed_dim, num_heads=4)

    z_b = torch.randn(B, dim_b, requires_grad=True)
    z_t = torch.randn(B, dim_t, requires_grad=True)

    z_fused, attn_dict = cmaf(z_b, z_t)

    assert z_fused.shape == (B, embed_dim)
    assert "attn_b_to_t" in attn_dict
    assert "attn_t_to_b" in attn_dict
    assert attn_dict["attn_b_to_t"].shape == (B, 1, 1)

    loss = z_fused.sum()
    loss.backward()

    assert z_b.grad is not None
    assert z_t.grad is not None
    assert not torch.isnan(z_b.grad).any()
    assert not torch.isnan(z_t.grad).any()


def test_cross_modal_attention_fusion_mask_awareness():
    B, dim_b, dim_t, embed_dim = 2, 256, 64, 256
    cmaf = CrossModalAttentionFusion(dim_b=dim_b, dim_t=dim_t, embed_dim=embed_dim)

    z_b = torch.randn(B, dim_b)
    z_t = torch.randn(B, dim_t)
    # Mask out clinical context for sample 1
    mod_mask = torch.tensor([[1.0, 0.0, 1.0], [1.0, 0.0, 0.0]])

    z_fused, _ = cmaf(z_b, z_t, mod_mask=mod_mask)
    assert z_fused.shape == (B, embed_dim)
    assert not torch.isnan(z_fused).any()


def test_evidential_multimodal_fusion_beliefs_and_uncertainty():
    B, dim_b, dim_t, K = 4, 256, 64, 2
    emf = EvidentialMultimodalFusion(dim_b=dim_b, dim_t=dim_t, num_classes=K)

    z_b = torch.randn(B, dim_b, requires_grad=True)
    z_t = torch.randn(B, dim_t, requires_grad=True)

    out = emf(z_b=z_b, z_t=z_t)

    assert "probs" in out
    assert "u_fused" in out
    assert "b_fused" in out

    probs = out["probs"]
    b_fused = out["b_fused"]
    u_fused = out["u_fused"]

    # Probability simplex check
    assert torch.allclose(probs.sum(dim=1), torch.ones(B), atol=1e-4)

    # Subjective logic constraint: sum(b_k) + u == 1.0
    mass_sum = b_fused.sum(dim=1, keepdim=True) + u_fused
    assert torch.allclose(mass_sum, torch.ones_like(mass_sum), atol=1e-3)

    # Gradients check
    loss = probs.sum()
    loss.backward()
    assert z_b.grad is not None
    assert z_t.grad is not None
    assert not torch.isnan(z_b.grad).any()


def test_evidential_fusion_vacuous_belief_on_missing_modality():
    B, dim_b, dim_t, K = 2, 256, 64, 2
    emf = EvidentialMultimodalFusion(dim_b=dim_b, dim_t=dim_t, num_classes=K)

    z_b = torch.randn(B, dim_b)
    # Modality T missing for all samples
    mod_mask = torch.tensor([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    out = emf(z_b=z_b, z_t=None, mod_mask=mod_mask)

    # For absent modality T, uncertainty must be 1.0 (vacuous) and belief 0
    assert torch.allclose(out["u_t"], torch.ones(B, 1), atol=1e-5)
    assert torch.allclose(out["b_t"], torch.zeros(B, K), atol=1e-5)

    # When T is vacuous, Dempster fusion should match modality B exactly
    assert torch.allclose(out["b_fused"], out["b_b"], atol=1e-4)
    assert torch.allclose(out["u_fused"], out["u_b"], atol=1e-4)
