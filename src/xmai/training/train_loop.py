"""
Training loop, evaluation, and calibration runner for Track A.
Includes:
- Class-weighted CrossEntropyLoss with light label smoothing (0.05).
- AdamW optimizer with cosine learning rate decay.
- Early stopping based on validation negative log-likelihood (log-loss).
- Post-hoc temperature scaling calibration.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from xmai.data.datasets import INT_TO_LABEL
from xmai.models.xmai_model import XMAIModel
from xmai.training.calibration import TemperatureScaler


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    """Runs a single training epoch and returns mean loss."""
    model.train()
    total_loss = 0.0
    count = 0

    for batch in loader:
        img = batch["img"].to(device)
        clin = batch["clin"].to(device)
        mod_mask = batch["mod_mask"].to(device)
        targets = batch["label"].to(device)

        optimizer.zero_grad()
        out = model(img=img, clin=clin, mod_mask=mod_mask)
        try:
            loss = criterion(out, targets)
        except TypeError:
            loss = criterion(out["logits"], targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * targets.size(0)
        count += targets.size(0)

    return total_loss / max(1, count)


@torch.no_grad()
def evaluate_dataset(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> pd.DataFrame:
    """
    Evaluates dataset and returns DataFrame of per-image predictions:
    [patient_id, true_label, prob_Hemangioma, prob_HCC, uncalibrated_logits]
    """
    model.eval()
    records: List[Dict[str, Any]] = []

    for batch in loader:
        img = batch["img"].to(device)
        clin = batch["clin"].to(device)
        mod_mask = batch["mod_mask"].to(device)
        targets = batch["label"].cpu().numpy()
        patient_ids = batch["patient_id"]

        out = model(img=img, clin=clin, mod_mask=mod_mask)
        probs = out["probs"].cpu().numpy()

        for i, pat_id in enumerate(patient_ids):
            label_int = int(targets[i])
            records.append({
                "patient_id": pat_id,
                "true_label": INT_TO_LABEL[label_int],
                "prob_Hemangioma": float(probs[i, 0]),
                "prob_HCC": float(probs[i, 1]),
            })

    return pd.DataFrame(records)
