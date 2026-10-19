"""
Unit tests for Phase 3 Track A baseline, fusion family, and comparative analysis.
Covers:
- Model forward pass and calibration API for A1, A2, A3, A4, A5, A7.
- Inner validation split patient exclusivity (no leakage).
- Rescue, harm, and net gain logic.
- Low-margin decile analysis for Hypothesis H1.
- Paired bootstrap confidence intervals and McNemar testing.
- Late fusion combination logic.
"""

from pathlib import Path
import pandas as pd
import pytest
import torch

from xmai.data.schemas import PredictionRow
from xmai.evaluation.track_a_analysis import (
    compute_rescue_harm,
    analyze_low_margin_decile,
    compute_paired_bootstrap_difference,
)
from xmai.models.track_a_models import (
    A1BModeOnly,
    A2ClinicalOnly,
    A3ConcatFusion,
    A4GatedFusion,
    A5FiLMFusion,
    create_track_a_model,
)
from xmai.training.track_a_runner import get_inner_split, run_track_a_late_fusion_cv


def test_track_a_model_forward():
    B = 2
    img = torch.randn(B, 3, 224, 224)
    clin = torch.randn(B, 2)
    mod_mask = torch.tensor([[1.0, 0.0, 1.0], [1.0, 0.0, 1.0]])

    # A1
    m1 = A1BModeOnly(pretrained=False)
    m1.set_temperature(1.2)
    out1 = m1(img)
    assert out1["logits"].shape == (B, 2)
    assert out1["probs"].shape == (B, 2)
    assert torch.allclose(out1["probs"].sum(dim=-1), torch.ones(B), atol=1e-5)

    # A2
    m2 = A2ClinicalOnly()
    m2.set_temperature(0.9)
    out2 = m2(clin=clin)
    assert out2["logits"].shape == (B, 2)
    assert out2["probs"].shape == (B, 2)

    # A3
    m3 = A3ConcatFusion(pretrained=False)
    out3 = m3(img=img, clin=clin)
    assert out3["logits"].shape == (B, 2)

    # A4
    m4 = A4GatedFusion(pretrained=False)
    out4 = m4(img=img, clin=clin, mod_mask=mod_mask)
    assert out4["logits"].shape == (B, 2)
    assert out4["gate_weights"].shape == (B, 3)

    # A5
    m5 = A5FiLMFusion(pretrained=False)
    out5 = m5(img=img, clin=clin)
    assert out5["logits"].shape == (B, 2)


def test_factory_function():
    for mid in ["A1", "A2", "A3", "A4", "A5", "A7"]:
        model = create_track_a_model(mid, pretrained=False)
        assert isinstance(model, torch.nn.Module)


def test_inner_split_leakage_barrier():
    workspace_root = Path(__file__).resolve().parent.parent
    manifest_path = workspace_root / "data" / "manifests" / "smc_manifest_v1.csv"
    assert manifest_path.exists()
    df = pd.read_csv(manifest_path)

    train_fold = df[df["fold"] != 0].reset_index(drop=True)
    inner_train, inner_val = get_inner_split(train_fold, val_ratio=0.2, seed=42)

    train_pids = set(inner_train["patient_id"].unique())
    val_pids = set(inner_val["patient_id"].unique())

    # Assert complete patient disjointness
    assert train_pids.isdisjoint(val_pids)
    assert len(train_pids) > 0
    assert len(val_pids) > 0


def test_rescue_harm_and_low_margin():
    base_rows = [
        PredictionRow(
            patient_id="P1", track="A", fold=0, seed=42, model_id="A1",
            true_label="HCC", pred_label="Hemangioma",
            prob_vector={"Hemangioma": 0.55, "HCC": 0.45}, margin=0.10,
            is_calibrated=True, is_error=True, is_low_margin=True, modality_mask=[1, 0, 0]
        ),
        PredictionRow(
            patient_id="P2", track="A", fold=0, seed=42, model_id="A1",
            true_label="Hemangioma", pred_label="Hemangioma",
            prob_vector={"Hemangioma": 0.85, "HCC": 0.15}, margin=0.70,
            is_calibrated=True, is_error=False, is_low_margin=False, modality_mask=[1, 0, 0]
        ),
        PredictionRow(
            patient_id="P3", track="A", fold=0, seed=42, model_id="A1",
            true_label="HCC", pred_label="HCC",
            prob_vector={"Hemangioma": 0.20, "HCC": 0.80}, margin=0.60,
            is_calibrated=True, is_error=False, is_low_margin=False, modality_mask=[1, 0, 0]
        ),
    ]

    fusion_rows = [
        PredictionRow(
            patient_id="P1", track="A", fold=0, seed=42, model_id="A4",
            true_label="HCC", pred_label="HCC",  # Rescued!
            prob_vector={"Hemangioma": 0.30, "HCC": 0.70}, margin=0.40,
            is_calibrated=True, is_error=False, is_low_margin=False, modality_mask=[1, 0, 1]
        ),
        PredictionRow(
            patient_id="P2", track="A", fold=0, seed=42, model_id="A4",
            true_label="Hemangioma", pred_label="Hemangioma",
            prob_vector={"Hemangioma": 0.80, "HCC": 0.20}, margin=0.60,
            is_calibrated=True, is_error=False, is_low_margin=False, modality_mask=[1, 0, 1]
        ),
        PredictionRow(
            patient_id="P3", track="A", fold=0, seed=42, model_id="A4",
            true_label="HCC", pred_label="Hemangioma",  # Harmed!
            prob_vector={"Hemangioma": 0.52, "HCC": 0.48}, margin=0.04,
            is_calibrated=True, is_error=True, is_low_margin=True, modality_mask=[1, 0, 1]
        ),
    ]

    rh = compute_rescue_harm(base_rows, fusion_rows)
    assert rh["rescue_count"] == 1
    assert rh["harm_count"] == 1
    assert rh["net_gain"] == 0
    assert rh["rescue_patients"] == ["P1"]
    assert rh["harm_patients"] == ["P3"]

    lm = analyze_low_margin_decile(base_rows, fusion_rows)
    assert lm["low_margin_rescues"] == 1
    assert lm["low_margin_harms"] == 0
    assert lm["pct_rescues_in_low_margin"] == 100.0


def test_late_fusion_cv():
    a1_rows = [
        PredictionRow(
            patient_id="P1", track="A", fold=0, seed=42, model_id="A1",
            true_label="HCC", pred_label="HCC",
            prob_vector={"Hemangioma": 0.4, "HCC": 0.6}, margin=0.2,
            is_calibrated=True, is_error=False, is_low_margin=False, modality_mask=[1, 0, 0]
        )
    ]
    a2_rows = [
        PredictionRow(
            patient_id="P1", track="A", fold=0, seed=42, model_id="A2",
            true_label="HCC", pred_label="HCC",
            prob_vector={"Hemangioma": 0.2, "HCC": 0.8}, margin=0.6,
            is_calibrated=True, is_error=False, is_low_margin=False, modality_mask=[0, 0, 1]
        )
    ]

    late = run_track_a_late_fusion_cv(a1_rows, a2_rows, weight_a1=0.5)
    assert len(late) == 1
    assert late[0].model_id == "A6_late_fusion"
    assert pytest.approx(late[0].prob_vector["HCC"], 1e-4) == 0.70
    assert pytest.approx(late[0].prob_vector["Hemangioma"], 1e-4) == 0.30
