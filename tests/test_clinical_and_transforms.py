"""
Unit tests for clinical fold reports and margin cropping transforms.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import pytest

from xmai.data.clinical import generate_clinical_fold_report
from xmai.data.transforms import crop_ultrasound_margins, load_bmode_image


@pytest.fixture
def workspace_root():
    return Path(__file__).parent.parent


def test_generate_clinical_fold_report(workspace_root):
    manifest_path = workspace_root / "data/manifests/smc_manifest_v1.csv"
    manifest_df = pd.read_csv(manifest_path)
    report = generate_clinical_fold_report(manifest_df)

    assert "cohort_summary" in report
    assert "folds" in report
    cs = report["cohort_summary"]
    assert cs["total_patients"] == 743
    assert cs["hcc_patients"] == 421
    assert cs["hem_patients"] == 322

    # Verify demographic priors (HCC is older and male-predominant)
    assert cs["hcc_age_mean"] > cs["hem_age_mean"]
    assert cs["hcc_male_ratio"] > cs["hem_male_ratio"]

    # Verify each of the 5 folds exists
    for f in range(5):
        assert f"fold_{f}" in report["folds"]
        f_tr = report["folds"][f"fold_{f}"]["train"]
        f_val = report["folds"][f"fold_{f}"]["val"]
        assert f_tr["patients"] + f_val["patients"] == 743


def test_crop_ultrasound_margins():
    # Create image with black borders around a 100x100 bright square in a 200x200 canvas
    arr = np.zeros((200, 200), dtype=np.uint8)
    arr[50:150, 50:150] = 200  # Bright center
    img = Image.fromarray(arr)

    cropped, (left, top, right, bottom) = crop_ultrasound_margins(img, threshold=10)
    assert left == 50
    assert top == 50
    assert right == 150
    assert bottom == 150
    assert cropped.size == (100, 100)


def test_load_bmode_image_metadata(tmp_path):
    img_path = tmp_path / "sample_us.png"
    arr = np.ones((100, 120, 3), dtype=np.uint8) * 150
    Image.fromarray(arr).save(img_path)

    tensor, meta = load_bmode_image(str(img_path))
    assert tensor.shape == (3, 100, 120)
    assert meta["orig_size"] == (100, 120)
    assert "crop_box" in meta
