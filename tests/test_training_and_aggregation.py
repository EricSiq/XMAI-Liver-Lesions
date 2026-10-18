"""
Unit tests for calibration and patient aggregation.
"""

import pandas as pd
import pytest
import torch

from xmai.evaluation.patient_aggregation import aggregate_patient_predictions
from xmai.models.xmai_model import XMAIModel
from xmai.training.calibration import TemperatureScaler
from xmai.training.train_loop import train_one_epoch


def test_temperature_scaler_optimization():
    logits = torch.tensor([[2.0, -1.0], [1.5, -0.5], [-1.0, 2.5], [-0.5, 1.8]])
    labels = torch.tensor([0, 0, 1, 1])

    scaler = TemperatureScaler()
    opt_temp = scaler.fit(logits, labels, max_iter=20)
    assert opt_temp > 0.1
    scaled_logits = scaler(logits)
    assert scaled_logits.shape == logits.shape


def test_patient_aggregation_logic():
    # 2 patients: Patient A has 2 images, Patient B has 3 images
    df = pd.DataFrame([
        # Patient A (HCC)
        {"patient_id": "HCC_1", "true_label": "HCC", "prob_Hemangioma": 0.2, "prob_HCC": 0.8},
        {"patient_id": "HCC_1", "true_label": "HCC", "prob_Hemangioma": 0.4, "prob_HCC": 0.6},
        # Patient B (Hemangioma)
        {"patient_id": "Hem_2", "true_label": "Hemangioma", "prob_Hemangioma": 0.9, "prob_HCC": 0.1},
        {"patient_id": "Hem_2", "true_label": "Hemangioma", "prob_Hemangioma": 0.7, "prob_HCC": 0.3},
        {"patient_id": "Hem_2", "true_label": "Hemangioma", "prob_Hemangioma": 0.8, "prob_HCC": 0.2},
    ])

    results = aggregate_patient_predictions(df, track="A", fold=0, seed=42)
    assert len(results) == 2

    res_dict = {r.patient_id: r for r in results}
    # Patient A mean prob HCC: (0.8 + 0.6)/2 = 0.7
    assert res_dict["HCC_1"].pred_label == "HCC"
    assert res_dict["HCC_1"].prob_vector["HCC"] == pytest.approx(0.7, rel=1e-3)
    assert res_dict["HCC_1"].is_error is False

    # Patient B mean prob Hemangioma: (0.9 + 0.7 + 0.8)/3 = 0.8
    assert res_dict["Hem_2"].pred_label == "Hemangioma"
    assert res_dict["Hem_2"].prob_vector["Hemangioma"] == pytest.approx(0.8, rel=1e-3)
    assert res_dict["Hem_2"].is_error is False
