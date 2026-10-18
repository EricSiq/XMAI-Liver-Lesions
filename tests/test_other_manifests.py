"""
Unit tests for TCIA, SYSU, and AUL manifest generators.
"""

from pathlib import Path
import pytest

from xmai.data.aul_manifest import generate_aul_manifest
from xmai.data.schemas import AULManifestRow, SYSUManifestRow, TCIAManifestRow
from xmai.data.sysu_manifest import generate_sysu_manifest
from xmai.data.tcia_manifest import generate_tcia_manifest


@pytest.fixture
def workspace_root():
    return Path(__file__).parent.parent


def test_tcia_manifest(workspace_root, tmp_path):
    out_csv = tmp_path / "test_tcia_manifest.csv"
    df, stats = generate_tcia_manifest(workspace_root, out_csv)

    assert out_csv.exists()
    assert stats["total_patients"] == 120
    assert stats["diagnoses_count"]["HCC"] >= 100

    # Validate each row against schema
    for _, row in df.iterrows():
        TCIAManifestRow(**row.to_dict())


def test_sysu_manifest(workspace_root, tmp_path):
    out_csv = tmp_path / "test_sysu_manifest.csv"
    df, stats = generate_sysu_manifest(workspace_root, out_csv)

    assert out_csv.exists()
    assert stats["total_videos"] == 15
    assert stats["is_complete_cohort"] is False

    # Validate each row against schema
    for _, row in df.iterrows():
        r = SYSUManifestRow(**row.to_dict())
        assert r.is_fixture_sample is True


def test_aul_manifest(workspace_root, tmp_path):
    out_csv = tmp_path / "test_aul_manifest.csv"
    df, stats = generate_aul_manifest(workspace_root, out_csv)

    assert out_csv.exists()
    assert stats["total_images"] == 735
    assert stats["images_by_class"]["Benign"] == 200
    assert stats["images_by_class"]["Malignant"] == 435
    assert stats["images_by_class"]["Normal"] == 100

    # Validate each row against schema
    for _, row in df.iterrows():
        AULManifestRow(**row.to_dict())
