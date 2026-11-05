"""
Track A Cross-Validation and Training Orchestrator.
Implements:
- Outer stratified 5-fold CV over patient-level partitions.
- Inner validation patient split (20% of train partition) for early stopping and temperature scaling.
- Training models A1, A2, A3, A4, A5, and A7 (context shuffle).
- A6 Late Fusion combining calibrated A1 and A2 probabilities.
- Content and checkpoint persistence in results/track_a/.
Conforms to tasks.md Section 3.1, 3.2, and 3.3.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from xmai.data.clinical import ClinicalFeatureProcessor
from xmai.data.datasets import SMCDataset, INT_TO_LABEL
from xmai.data.schemas import PredictionRow
from xmai.evaluation.patient_aggregation import aggregate_patient_predictions
from xmai.models.track_a_models import create_track_a_model
from xmai.training.calibration import TemperatureScaler
from xmai.training.losses import CompositeMultimodalLoss


def get_inner_split(
    train_df: pd.DataFrame,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Creates patient-stratified inner split from training fold:
    80% inner_train, 20% inner_val.
    """
    unique_patients = train_df.drop_duplicates(subset=["patient_id"]).reset_index(drop=True)
    y = unique_patients["label"].values

    sgkf = StratifiedGroupKFold(n_splits=int(1.0 / val_ratio), shuffle=True, random_state=seed)
    train_idx, val_idx = next(sgkf.split(unique_patients, y, groups=unique_patients["patient_id"]))

    train_pids = set(unique_patients.iloc[train_idx]["patient_id"])
    val_pids = set(unique_patients.iloc[val_idx]["patient_id"])

    inner_train_df = train_df[train_df["patient_id"].isin(train_pids)].reset_index(drop=True)
    inner_val_df = train_df[train_df["patient_id"].isin(val_pids)].reset_index(drop=True)

    assert train_pids.isdisjoint(val_pids), "Inner patient leakage detected"
    return inner_train_df, inner_val_df


def train_track_a_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    model_id: str,
) -> float:
    """Trains model for one epoch."""
    model.train()
    total_loss = 0.0
    count = 0

    for batch in loader:
        img = batch["img"].to(device)
        clin = batch["clin"].to(device)
        targets = batch["label"].to(device)
        mod_mask = batch["mod_mask"].to(device)

        optimizer.zero_grad()
        if model_id in {"A1", "A1_bmode"}:
            out = model(img=img)
        elif model_id in {"A2", "A2_clinical"}:
            out = model(clin=clin)
        else:
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
def evaluate_raw_logits(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    model_id: str,
) -> Tuple[torch.Tensor, torch.Tensor, pd.DataFrame]:
    """
    Evaluates dataset and returns (raw_logits, true_labels, records_df).
    """
    model.eval()
    all_logits = []
    all_labels = []
    records: List[Dict[str, Any]] = []

    for batch in loader:
        img = batch["img"].to(device)
        clin = batch["clin"].to(device)
        targets = batch["label"].to(device)
        mod_mask = batch["mod_mask"].to(device)
        patient_ids = batch["patient_id"]

        if model_id in {"A1", "A1_bmode"}:
            out = model(img=img)
        elif model_id in {"A2", "A2_clinical"}:
            out = model(clin=clin)
        else:
            out = model(img=img, clin=clin, mod_mask=mod_mask)

        all_logits.append(out["logits"].cpu())
        all_labels.append(targets.cpu())

        probs = out["probs"].cpu().numpy()
        for i, pid in enumerate(patient_ids):
            label_int = int(targets[i].item())
            records.append({
                "patient_id": pid,
                "true_label": INT_TO_LABEL[label_int],
                "prob_Hemangioma": float(probs[i, 0]),
                "prob_HCC": float(probs[i, 1]),
            })

    logits_tensor = torch.cat(all_logits, dim=0)
    labels_tensor = torch.cat(all_labels, dim=0)
    return logits_tensor, labels_tensor, pd.DataFrame(records)


def run_track_a_fold(
    manifest_df: pd.DataFrame,
    fold: int,
    model_id: str,
    workspace_root: Path,
    device: torch.device,
    epochs: int = 5,
    lr: float = 1e-4,
    batch_size: int = 16,
    seed: int = 42,
    results_dir: Optional[Path] = None,
) -> List[PredictionRow]:
    """
    Runs a single cross-validation fold:
    1. Splits manifest into train and test.
    2. Sub-splits train into inner_train and inner_val.
    3. Fits ClinicalFeatureProcessor on inner_train only.
    4. Trains model on inner_train with inner_val monitoring.
    5. Optimizes TemperatureScaler on inner_val logits.
    6. Evaluates test fold with temperature calibration.
    7. Aggregates per-patient predictions and returns validated PredictionRows.
    """
    torch.manual_seed(seed + fold)
    np.random.seed(seed + fold)

    train_df = manifest_df[manifest_df["fold"] != fold].reset_index(drop=True)
    test_df = manifest_df[manifest_df["fold"] == fold].reset_index(drop=True)

    # Context shuffle for A7
    if model_id in {"A7", "A7_context_shuffle"}:
        shuffled_train = train_df.copy()
        # Shuffle age and sex independently within train_df
        shuffled_train["age"] = np.random.permutation(shuffled_train["age"].values)
        shuffled_train["sex"] = np.random.permutation(shuffled_train["sex"].values)
        train_df = shuffled_train

    inner_train_df, inner_val_df = get_inner_split(train_df, val_ratio=0.2, seed=seed + fold)

    # Fit Clinical processor strictly on inner_train_df
    clin_proc = ClinicalFeatureProcessor().fit(inner_train_df)

    inner_train_ds = SMCDataset(inner_train_df, workspace_root, is_train=True, clinical_processor=clin_proc)
    inner_val_ds = SMCDataset(inner_val_df, workspace_root, is_train=False, clinical_processor=clin_proc)
    test_ds = SMCDataset(test_df, workspace_root, is_train=False, clinical_processor=clin_proc)

    train_loader = DataLoader(inner_train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(inner_val_ds, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    model = create_track_a_model(model_id, pretrained=True).to(device)

    # Class-weighted loss
    labels = inner_train_df["label"].map({"Hemangioma": 0, "HCC": 1}).values
    n_hcc = int((labels == 1).sum())
    n_hem = int((labels == 0).sum())
    w_hem = len(labels) / (2.0 * max(1, n_hem))
    w_hcc = len(labels) / (2.0 * max(1, n_hcc))
    class_weights = torch.tensor([w_hem, w_hcc], dtype=torch.float32, device=device)
    align_weight = 0.05 if model_id in {"A3", "A4", "A5", "A8"} else 0.0
    criterion = CompositeMultimodalLoss(
        weight=class_weights,
        label_smoothing=0.05,
        align_weight=align_weight,
        evid_weight=1.0,
    )

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    best_val_loss = float("inf")
    best_weights = None

    for epoch in range(epochs):
        train_loss = train_track_a_epoch(model, train_loader, optimizer, criterion, device, model_id)
        val_logits, val_labels, _ = evaluate_raw_logits(model, val_loader, device, model_id)
        val_loss = nn.CrossEntropyLoss()(val_logits.to(device), val_labels.to(device)).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    if best_weights is not None:
        model.load_state_dict(best_weights)

    # Post-hoc temperature calibration on inner_val logits
    val_logits, val_labels, _ = evaluate_raw_logits(model, val_loader, device, model_id)
    scaler = TemperatureScaler()
    opt_temp = scaler.fit(val_logits, val_labels)
    model.set_temperature(opt_temp)

    # Evaluate test fold
    _, _, test_preds_df = evaluate_raw_logits(model, test_loader, device, model_id)

    mod_mask_map = {
        "A1": [1, 0, 0],
        "A2": [0, 0, 1],
        "A3": [1, 0, 1],
        "A4": [1, 0, 1],
        "A5": [1, 0, 1],
        "A7": [1, 0, 1],
        "A8": [1, 0, 1],
        "A9": [1, 0, 1],
    }
    cur_mask = mod_mask_map.get(model_id[:2], [1, 0, 1])

    patient_rows = aggregate_patient_predictions(
        image_preds_df=test_preds_df,
        track="A",
        fold=fold,
        seed=seed,
        model_id=model_id,
        modality_mask=cur_mask,
    )

    if results_dir:
        results_dir = Path(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = results_dir / f"checkpoint_{model_id}_fold_{fold}.pt"
        torch.save({"model_state": model.state_dict(), "temperature": opt_temp, "fold": fold}, ckpt_path)

    return patient_rows


def run_track_a_full_cv(
    manifest_df: pd.DataFrame,
    model_id: str,
    workspace_root: Path,
    device: torch.device,
    epochs: int = 5,
    seed: int = 42,
    results_dir: Optional[Path] = None,
) -> List[PredictionRow]:
    """Runs full 5-fold CV and aggregates out-of-fold patient predictions."""
    if results_dir:
        results_dir.mkdir(parents=True, exist_ok=True)

    all_patient_preds: List[PredictionRow] = []
    for fold in range(5):
        fold_preds = run_track_a_fold(
            manifest_df=manifest_df,
            fold=fold,
            model_id=model_id,
            workspace_root=workspace_root,
            device=device,
            epochs=epochs,
            seed=seed,
            results_dir=results_dir,
        )
        all_patient_preds.extend(fold_preds)

    if results_dir:
        out_json = results_dir / f"oof_predictions_{model_id}.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in all_patient_preds], f, indent=2)

    return all_patient_preds


def run_track_a_late_fusion_cv(
    a1_preds: List[PredictionRow],
    a2_preds: List[PredictionRow],
    weight_a1: float = 0.5,
    results_dir: Optional[Path] = None,
) -> List[PredictionRow]:
    """
    Computes A6 Late Fusion by averaging calibrated probabilities from A1 and A2.
    """
    assert len(a1_preds) == len(a2_preds), "A1 and A2 prediction length mismatch"
    a2_map = {p.patient_id: p for p in a2_preds}

    late_preds: List[PredictionRow] = []
    w_a2 = 1.0 - weight_a1

    for p1 in a1_preds:
        p2 = a2_map[p1.patient_id]
        p_hem = weight_a1 * p1.prob_vector["Hemangioma"] + w_a2 * p2.prob_vector["Hemangioma"]
        p_hcc = weight_a1 * p1.prob_vector["HCC"] + w_a2 * p2.prob_vector["HCC"]

        pred_label = "HCC" if p_hcc >= p_hem else "Hemangioma"
        margin = float(abs(p_hcc - p_hem))

        row = PredictionRow(
            patient_id=p1.patient_id,
            track="A",
            fold=p1.fold,
            seed=p1.seed,
            model_id="A6_late_fusion",
            true_label=p1.true_label,
            pred_label=pred_label,
            prob_vector={"Hemangioma": round(p_hem, 6), "HCC": round(p_hcc, 6)},
            margin=round(margin, 6),
            is_calibrated=True,
            is_error=(pred_label != p1.true_label),
            is_low_margin=p1.is_low_margin,
            modality_mask=[1, 0, 1],
        )
        late_preds.append(row)

    if results_dir:
        out_json = results_dir / "oof_predictions_A6.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in late_preds], f, indent=2)

    return late_preds
