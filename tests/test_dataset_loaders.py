"""
Unit tests for transforms, ClinicalFeatureProcessor, and SMCDataset DataLoader.
"""

from pathlib import Path
import pandas as pd
import pytest
import torch
from torch.utils.data import DataLoader

from xmai.data.clinical import ClinicalFeatureProcessor
from xmai.data.datasets import SMCDataset
from xmai.data.transforms import get_bmode_transforms


@pytest.fixture
def workspace_root():
    return Path(__file__).parent.parent


@pytest.fixture
def manifest_df(workspace_root):
    manifest_path = workspace_root / "data" / "manifests" / "smc_manifest_v1.csv"
    assert manifest_path.exists(), "smc_manifest_v1.csv must exist before running dataset tests."
    return pd.read_csv(manifest_path)


def test_bmode_transforms():
    t_train = get_bmode_transforms(is_train=True, image_size=224)
    t_val = get_bmode_transforms(is_train=False, image_size=224)
    assert t_train is not None
    assert t_val is not None


def test_clinical_processor_train_isolation():
    # Synthetic train and val folds
    train_data = pd.DataFrame([
        {"age": 50.0, "age_missing": False, "sex": "M", "sex_missing": False},
        {"age": 70.0, "age_missing": False, "sex": "F", "sex_missing": False},
        {"age": None, "age_missing": True, "sex": "M", "sex_missing": False},
    ])

    val_data = pd.DataFrame([
        {"age": 90.0, "age_missing": False, "sex": "F", "sex_missing": False},
        {"age": None, "age_missing": True, "sex": "M", "sex_missing": False},
    ])

    proc = ClinicalFeatureProcessor().fit(train_data)
    assert proc.age_mean == 60.0
    assert proc.age_median == 60.0

    # Transform val row: age=90 should be (90 - 60) / 14.14
    val_feat, val_mask = proc.transform_row(val_data.iloc[0])
    assert val_feat[0] > 0.0  # Age above train mean
    assert val_feat[1] == 0.0  # F -> 0.0
    assert val_mask[0] == 0.0  # Not missing

    # Transform val row with missing age: should impute train median (60.0) -> z=0.0
    val_missing_feat, val_missing_mask = proc.transform_row(val_data.iloc[1])
    assert val_missing_feat[0] == pytest.approx(0.0)
    assert val_missing_mask[0] == 1.0  # Marked as missing


def test_smc_dataset_dataloader(workspace_root, manifest_df):
    train_df = manifest_df[manifest_df["fold"] != 0].head(16)
    val_df = manifest_df[manifest_df["fold"] == 0].head(8)

    # Patient isolation check
    train_patients = set(train_df["patient_id"])
    val_patients = set(val_df["patient_id"])
    assert len(train_patients.intersection(val_patients)) == 0

    proc = ClinicalFeatureProcessor().fit(train_df)

    ds_train = SMCDataset(train_df, workspace_root, is_train=True, clinical_processor=proc)
    ds_val = SMCDataset(val_df, workspace_root, is_train=False, clinical_processor=proc)

    assert len(ds_train) == 16
    assert len(ds_val) == 8

    # Test PyTorch DataLoader batching
    loader = DataLoader(ds_train, batch_size=4, shuffle=True)
    batch = next(iter(loader))

    assert "img" in batch
    assert "clin" in batch
    assert "clin_miss" in batch
    assert "mod_mask" in batch
    assert "label" in batch
    assert "patient_id" in batch

    assert batch["img"].shape == (4, 3, 224, 224)
    assert batch["img"].dtype == torch.float32
    assert batch["clin"].shape == (4, 2)
    assert batch["clin_miss"].shape == (4, 2)
    assert batch["mod_mask"].shape == (4, 3)
    assert batch["label"].shape == (4,)
    assert batch["label"].dtype == torch.long
