"""
Unit tests for unified dataset loaders (tasks.md Section 2.4 Loader test matrix):
- SMC returns image, label, age/sex vector, missing mask, patient ID.
- SYSU returns video tensor, timestamps/FPS, label, and video ID.
- TCIA returns a decoded B-mode or CEUS sample plus source traceability metadata.
- AUL returns image and masks whose dimensions match.
- A batch never contains images from a patient outside its assigned fold.
"""

from pathlib import Path
import pandas as pd
import pytest
import torch
from torch.utils.data import DataLoader

from xmai.data.datasets import SMCDataset, SYSUDataset, TCIADataset, AULDataset


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_smc_loader_matrix():
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "smc_manifest_v1.csv"
    assert manifest_path.exists(), "SMC manifest missing"
    df = pd.read_csv(manifest_path)
    # Test first 10 rows
    dataset = SMCDataset(df.head(10), workspace_root=WORKSPACE_ROOT)
    sample = dataset[0]

    assert sample["img"].shape == (3, 224, 224)
    assert sample["clin"].shape == (2,)
    assert sample["clin_miss"].shape == (2,)
    assert sample["mod_mask"].shape == (3,)
    assert isinstance(sample["patient_id"], str)
    assert sample["label"].item() in {0, 1}
    assert sample["crop_box"].shape == (4,)


def test_sysu_loader_matrix():
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "sysu_demo_manifest_v1.csv"
    assert manifest_path.exists(), "SYSU demo manifest missing"
    df = pd.read_csv(manifest_path)
    dataset = SYSUDataset(df.head(2), workspace_root=WORKSPACE_ROOT, num_frames=16, image_size=224)
    sample = dataset[0]

    assert sample["video"].shape == (16, 3, 224, 224)
    assert sample["timestamps"].shape == (16,)
    assert sample["fps"] > 0
    assert sample["label"].item() in {0, 1, 2}
    assert isinstance(sample["patient_id"], str)
    assert "video_path" in sample


def test_tcia_loader_matrix(tmp_path):
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "tcia_manifest_v1.csv"
    assert manifest_path.exists(), "TCIA manifest missing"
    df = pd.read_csv(manifest_path)
    # Pick first usable sample
    usable_df = df[df["usable_for_eval"] == True].head(2)
    dataset = TCIADataset(usable_df, workspace_root=WORKSPACE_ROOT, num_frames=16, cache_dir=tmp_path)
    sample = dataset[0]

    assert sample["bmode_frames"].shape == (16, 3, 224, 224)
    assert sample["ceus_frames"].shape == (16, 3, 224, 224)
    assert sample["timestamps"].shape == (16,)
    assert sample["label"].item() in {-1, 0, 1}
    assert isinstance(sample["patient_id"], str)
    assert "source_traceability" in sample
    assert "sop_class_uid" in sample["source_traceability"]
    assert "relative_path" in sample["source_traceability"]


def test_aul_loader_matrix():
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "aul_manifest_v1.csv"
    assert manifest_path.exists(), "AUL manifest missing"
    df = pd.read_csv(manifest_path)

    # 1. Test original resolution mode
    dataset_orig = AULDataset(df.head(5), workspace_root=WORKSPACE_ROOT, image_size=None)
    sample_orig = dataset_orig[0]

    img_c, img_h, img_w = sample_orig["img"].shape
    assert img_c == 3
    assert sample_orig["liver_mask"].shape == (1, img_h, img_w)
    assert sample_orig["mass_mask"].shape == (1, img_h, img_w)
    assert sample_orig["class_name"] in {"Normal", "Benign", "Malignant"}
    assert sample_orig["label"].item() in {0, 1, 2}

    # 2. Test fixed resize mode
    dataset_resize = AULDataset(df.head(5), workspace_root=WORKSPACE_ROOT, image_size=224)
    sample_resize = dataset_resize[0]
    assert sample_resize["img"].shape == (3, 224, 224)
    assert sample_resize["liver_mask"].shape == (1, 224, 224)
    assert sample_resize["mass_mask"].shape == (1, 224, 224)


def test_fold_batch_patient_exclusivity():
    """
    Assert that a batch never contains images from a patient outside its assigned fold.
    """
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "smc_manifest_v1.csv"
    df = pd.read_csv(manifest_path)

    for fold in range(5):
        train_df = df[df["fold"] != fold].reset_index(drop=True)
        val_df = df[df["fold"] == fold].reset_index(drop=True)

        train_patients = set(train_df["patient_id"].unique())
        val_patients = set(val_df["patient_id"].unique())

        # No patient overlap between train and val
        assert train_patients.isdisjoint(val_patients), f"Patient overlap detected in fold {fold}"

        val_dataset = SMCDataset(val_df, workspace_root=WORKSPACE_ROOT)
        loader = DataLoader(val_dataset, batch_size=8, shuffle=False)

        for batch in loader:
            batch_pids = set(batch["patient_id"])
            # Every patient in the batch must belong strictly to val_patients and NOT train_patients
            assert batch_pids.issubset(val_patients)
            assert batch_pids.isdisjoint(train_patients)
