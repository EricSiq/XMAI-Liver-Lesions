"""
Unit and stress tests for the expanded multiclass clinical processor and neural encoder.
Verifies mathematical transformations, missingness masks, gradient flow, and shape preservation.
"""

import pytest
import numpy as np
import pandas as pd
import torch

from xmai.data.clinical import MulticlassClinicalFeatureProcessor
from xmai.models.encoders import MulticlassClinicalEncoder


def test_multiclass_clinical_processor_fit_transform():
    """Verify processor fitting, z-score normalization, and missing value imputation."""
    proc = MulticlassClinicalFeatureProcessor()

    # Fitting requires training dataframe
    df_train = pd.DataFrame({
        "age": [50.0, 60.0, 70.0, None],
        "sex": ["M", "F", "M", None],
        "cirrhosis": [1, 0, 1, None],
        "hepatitis": [1, 0, 0, None],
        "oral_contraceptives": [0, 1, 0, None],
        "metabolic_syndrome": [1, 0, 0, None],
        "afp_level": [10.0, 50.0, 200.0, None],
        "ca19_9_level": [20.0, 30.0, 100.0, None],
    })
    proc.fit(df_train)
    assert proc.is_fitted
    assert proc.age_mean == pytest.approx(60.0)
    assert proc.age_median == pytest.approx(60.0)

    # Transform complete row
    row_full = {
        "age": 60.0,
        "sex": "M",
        "cirrhosis": 1,
        "hepatitis": 1,
        "oral_contraceptives": 0,
        "metabolic_syndrome": 1,
        "afp_level": 50.0,
        "ca19_9_level": 30.0,
    }
    feat, mask = proc.transform_row(row_full)
    assert feat.shape == (8,)
    assert mask.shape == (8,)
    assert feat[0].item() == pytest.approx(0.0)  # (60 - 60) / std == 0
    assert feat[1].item() == 1.0                # Male
    assert feat[2].item() == 1.0                # Cirrhosis
    assert mask.sum().item() == 0.0             # No missing values

    # Transform missing row: check imputation
    row_missing = {
        "age": None,
        "sex": None,
        "cirrhosis": None,
        "hepatitis": None,
        "oral_contraceptives": None,
        "metabolic_syndrome": None,
        "afp_level": None,
        "ca19_9_level": None,
    }
    feat_m, mask_m = proc.transform_row(row_missing)
    assert mask_m.sum().item() == 8.0           # All 8 values missing
    assert feat_m[0].item() == pytest.approx(0.0)  # Median imputed -> 0 z-score
    assert feat_m[1].item() == 0.5              # Neutral sex representation


def test_multiclass_clinical_encoder_forward_and_gradients():
    """Verify encoder tensor dimensions, residual connection, and backpropagation gradients."""
    encoder = MulticlassClinicalEncoder(in_features=8, hidden_dim=128, out_dim=128)
    encoder.train()

    # Forward pass on batch
    B = 16
    x = torch.randn(B, 8, requires_grad=True)
    out = encoder(x)

    assert out.shape == (B, 128)
    assert not torch.isnan(out).any()
    assert not torch.isinf(out).any()

    # Backpropagation verification
    loss = out.sum()
    loss.backward()
    assert x.grad is not None
    assert torch.all(torch.isfinite(x.grad))
    assert x.grad.abs().sum() > 0.0, "Gradients must flow back to input features"


def test_multiclass_clinical_encoder_input_validation():
    """Verify that encoder rejects invalid tensor dimensions or NaN/Inf inputs."""
    encoder = MulticlassClinicalEncoder(in_features=8, out_dim=128)

    # 1D tensor rejection
    with pytest.raises(ValueError, match="Expected 2D clinical tensor"):
        encoder(torch.randn(8))

    # Incorrect feature count rejection
    with pytest.raises(ValueError, match="Expected 8 features"):
        encoder(torch.randn(4, 5))

    # NaN input rejection
    nan_tensor = torch.randn(4, 8)
    nan_tensor[0, 0] = float("nan")
    with pytest.raises(ValueError, match="NaN or Inf"):
        encoder(nan_tensor)
