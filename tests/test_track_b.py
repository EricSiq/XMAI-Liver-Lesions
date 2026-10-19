"""
Unit tests for Phase 4 Track B temporal CEUS models and evaluation runner.
"""

from pathlib import Path
import pandas as pd
import pytest
import torch

from xmai.models.track_b_models import (
    B1MeanPooling,
    B2TemporalAttention,
    B3BiLSTM,
    B4ArterialOnly,
    create_track_b_model,
)
from xmai.training.track_b_runner import run_track_b_demo_evaluation


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_track_b_model_forward():
    B = 2
    T = 8
    video = torch.randn(B, T, 3, 224, 224)

    # B1
    m1 = B1MeanPooling(num_classes=3, pretrained=False)
    out1 = m1(video)
    assert out1["logits"].shape == (B, 3)
    assert out1["probs"].shape == (B, 3)
    assert out1["temporal_weights"] is None

    # B2
    m2 = B2TemporalAttention(num_classes=3, pretrained=False)
    out2 = m2(video)
    assert out2["logits"].shape == (B, 3)
    assert out2["temporal_weights"].shape == (B, T)
    assert torch.allclose(out2["temporal_weights"].sum(dim=-1), torch.ones(B), atol=1e-5)

    # B3
    m3 = B3BiLSTM(num_classes=3, pretrained=False)
    out3 = m3(video)
    assert out3["logits"].shape == (B, 3)

    # B4
    m4 = B4ArterialOnly(num_classes=3, early_t=4, pretrained=False)
    out4 = m4(video)
    assert out4["logits"].shape == (B, 3)


def test_track_b_factory():
    for mid in ["B1", "B2", "B3", "B4"]:
        model = create_track_b_model(mid, pretrained=False)
        assert isinstance(model, torch.nn.Module)


def test_track_b_demo_runner(tmp_path):
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "sysu_demo_manifest_v1.csv"
    assert manifest_path.exists()
    df = pd.read_csv(manifest_path).head(2)

    device = torch.device("cpu")
    results = run_track_b_demo_evaluation(
        manifest_df=df,
        workspace_root=WORKSPACE_ROOT,
        device=device,
        models=["B1", "B2"],
        results_dir=tmp_path,
    )

    assert results["dataset_completeness"] == "demo_only"
    assert "B1" in results["models"]
    assert "B2" in results["models"]
    assert (tmp_path / "B2_temporal_attention_profiles.json").exists()
    assert (tmp_path / "track_b_summary_report.json").exists()
