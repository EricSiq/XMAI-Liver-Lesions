"""
Unit and integration tests for CEUS / DICOM processing pipeline.
"""

from pathlib import Path
import numpy as np
import pytest
import torch

from xmai.data.dicom_ceus import (
    DICOMCEUSPipeline,
    derive_frame_timestamps,
    inspect_dicom_header,
    sample_t16_frames,
    split_dual_panel,
)


@pytest.fixture
def workspace_root():
    return Path(__file__).parent.parent


@pytest.fixture
def sample_dcm_path(workspace_root):
    tcia_root = workspace_root / "TCIA/b_mode_and_ceus_liver"
    dcms = list(tcia_root.glob("**/*.dcm"))
    assert len(dcms) > 0, "No TCIA DICOM files found."
    return dcms[0]


def test_inspect_dicom_header(sample_dcm_path):
    info = inspect_dicom_header(sample_dcm_path)
    assert "rows" in info
    assert "cols" in info
    assert "num_frames" in info
    assert info["rows"] > 0
    assert info["cols"] > 0
    assert info["modality"] == "US"


def test_split_dual_panel():
    frame = np.ones((100, 200, 3), dtype=np.uint8)
    frame[:, :100] = 50   # Left = B-mode
    frame[:, 100:] = 150  # Right = CEUS

    left, right = split_dual_panel(frame)
    assert left.shape == (100, 100, 3)
    assert right.shape == (100, 100, 3)
    assert left.mean() == 50
    assert right.mean() == 150


def test_derive_frame_timestamps():
    # 1. Calibrated with frame_time_ms = 100 ms (10 fps)
    info_calibrated = {"frame_time_ms": 100.0, "cine_rate_fps": None}
    ts, is_calib = derive_frame_timestamps(info_calibrated, num_frames=10)
    assert is_calib is True
    assert len(ts) == 10
    assert ts[1] == pytest.approx(0.1)

    # 2. Uncalibrated fallback
    info_fallback = {"frame_time_ms": None, "cine_rate_fps": None}
    ts_f, is_calib_f = derive_frame_timestamps(info_fallback, num_frames=5)
    assert is_calib_f is False
    assert ts_f[0] == 0.0
    assert ts_f[-1] == 1.0


def test_sample_t16_frames():
    frames = np.zeros((100, 50, 50), dtype=np.uint8)
    timestamps = np.linspace(0, 10, 100)
    sampled_f, sampled_t = sample_t16_frames(frames, timestamps, target_t=16)

    assert len(sampled_f) == 16
    assert len(sampled_t) == 16


def test_dicom_pipeline_integration(sample_dcm_path, tmp_path):
    pipeline = DICOMCEUSPipeline(cache_dir=tmp_path / "cache", target_size=224)

    # First decode: parses and writes cache
    res1 = pipeline.decode_series(sample_dcm_path, target_t=16, use_cache=True)
    assert res1["bmode_frames"].shape == (16, 3, 224, 224)
    assert res1["ceus_frames"].shape == (16, 3, 224, 224)
    assert res1["timestamps"].shape == (16,)

    # Second decode: loads from cache
    res2 = pipeline.decode_series(sample_dcm_path, target_t=16, use_cache=True)
    assert torch.equal(res1["bmode_frames"], res2["bmode_frames"])
