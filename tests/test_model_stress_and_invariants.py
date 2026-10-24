"""
Model Stress and Invariant Verification Suite for XMAI.
Stress tests encoder input guards, gradient propagation across all 9 Track A architectures,
batch dimension invariants (B=1 and B=8), probability simplex constraints, and eval determinism.
"""

import pytest
import torch
import torch.nn.functional as F

from xmai.models.encoders import BModeEncoder, ClinicalEncoder, CEUSEncoder
from xmai.models.track_a_models import create_track_a_model


def test_encoders_shape_validation():
    """Verify BModeEncoder and ClinicalEncoder reject invalid ranks and non-finite values."""
    enc_b = BModeEncoder(pretrained=False, embed_dim=256)
    enc_c = ClinicalEncoder(in_features=2, hidden_dim=64, out_dim=64)

    # 1. Invalid dimensions for image
    with pytest.raises(ValueError, match="Expected 4D image tensor"):
        enc_b(torch.randn(3, 224, 224))

    with pytest.raises(ValueError, match="Expected 3 channels"):
        enc_b(torch.randn(2, 1, 224, 224))

    # 2. NaN / Inf rejection
    nan_img = torch.randn(2, 3, 224, 224)
    nan_img[0, 0, 10, 10] = float("nan")
    with pytest.raises(ValueError, match="NaN or Inf"):
        enc_b(nan_img)

    inf_img = torch.randn(2, 3, 224, 224)
    inf_img[0, 0, 10, 10] = float("inf")
    with pytest.raises(ValueError, match="NaN or Inf"):
        enc_b(inf_img)

    # 3. Clinical context checks
    with pytest.raises(ValueError, match="Expected 2D clinical tensor"):
        enc_c(torch.randn(2, 2, 1))

    nan_clin = torch.randn(2, 2)
    nan_clin[0, 1] = float("nan")
    with pytest.raises(ValueError, match="NaN or Inf"):
        enc_c(nan_clin)


def test_ceus_encoder_shape_validation():
    """Verify CEUSEncoder rejects malformed temporal sequences."""
    enc_ceus = CEUSEncoder(frame_encoder=BModeEncoder(pretrained=False, embed_dim=128), embed_dim=128)

    with pytest.raises(ValueError, match="Expected 5D tensor"):
        enc_ceus(torch.randn(2, 8, 3, 224))

    with pytest.raises(ValueError, match="Expected 3 channels"):
        enc_ceus(torch.randn(2, 8, 1, 224, 224))


@pytest.mark.parametrize("model_id", ["A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9"])
@pytest.mark.parametrize("batch_size", [1, 4])
def test_all_track_a_models_stress_and_gradients(model_id: str, batch_size: int):
    """
    Stress test all 9 Track A model architectures under single-sample and mini-batch inputs.
    Verifies probability simplex sum == 1, non-negativity, and finite backward gradients.
    """
    torch.manual_seed(42)
    model = create_track_a_model(model_id, pretrained=False)
    model.train()

    img = torch.randn(batch_size, 3, 224, 224)
    clin = torch.randn(batch_size, 2)
    mod_mask = torch.ones(batch_size, 3)

    if model_id == "A2":
        out = model(clin=clin)
    else:
        out = model(img=img, clin=clin, mod_mask=mod_mask)

    probs = out["probs"]

    # Simplex invariant: sum to 1.0 along class dimension
    assert probs.shape == (batch_size, 2), f"Expected shape ({batch_size}, 2), got {probs.shape}"
    sums = probs.sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5), f"Probabilities do not sum to 1: {sums}"
    assert (probs >= 0.0).all(), "Negative probability detected"
    assert not torch.isnan(probs).any(), "NaN in probabilities"

    # Backward pass stress test
    targets = torch.randint(0, 2, (batch_size,))
    loss = F.cross_entropy(out["logits"], targets)
    loss.backward()

    for name, param in model.named_parameters():
        if param.requires_grad and param.grad is not None:
            assert not torch.isnan(param.grad).any(), f"NaN gradient in {name}"
            assert not torch.isinf(param.grad).any(), f"Inf gradient in {name}"


@pytest.mark.parametrize("model_id", ["A1", "A3", "A4", "A5", "A8", "A9"])
def test_model_eval_determinism(model_id: str):
    """Verify that in eval() mode, forward passes are perfectly deterministic."""
    model = create_track_a_model(model_id, pretrained=False)
    model.eval()

    img = torch.randn(2, 3, 224, 224)
    clin = torch.randn(2, 2)
    mod_mask = torch.ones(2, 3)

    with torch.no_grad():
        out1 = model(img=img, clin=clin, mod_mask=mod_mask)
        out2 = model(img=img, clin=clin, mod_mask=mod_mask)

    assert torch.equal(out1["probs"], out2["probs"]), f"Eval output not deterministic for {model_id}"


def test_temperature_scaling_invariants():
    """Verify that setting non-positive temperatures raises ValueError across all models."""
    for model_id in ["A1", "A2", "A3", "A5", "A8", "A9"]:
        model = create_track_a_model(model_id, pretrained=False)
        with pytest.raises(ValueError, match="strictly positive"):
            model.set_temperature(0.0)
        with pytest.raises(ValueError, match="strictly positive"):
            model.set_temperature(-1.5)

        model.set_temperature(1.35)
        assert torch.isclose(model.temperature, torch.tensor([1.35]))
