"""Tests for the Academic Presentation Frontend assets, data store integrity, and HTTP server."""

import json
from pathlib import Path
import re
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"


def test_frontend_structure_exists():
    """Verify that frontend core files exist."""
    assert FRONTEND_DIR.exists()
    assert (FRONTEND_DIR / "index.html").is_file()
    assert (FRONTEND_DIR / "styles" / "academic-theme.css").is_file()
    assert (FRONTEND_DIR / "styles" / "components.css").is_file()


def test_frontend_html_sections():
    """Verify that index.html contains all 9 required scholarly presentation sections."""
    html_content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    expected_sections = [
        "section-overview",
        "section-architecture",
        "section-ablation",
        "section-h1-rescue",
        "section-cases",
        "section-explainability",
        "section-selective",
        "section-external",
        "section-paper-artifacts",
    ]

    for section_id in expected_sections:
        assert f'id="{section_id}"' in html_content, f"Missing section #{section_id} in index.html"


def test_frontend_scripts_exist_and_linked():
    """Verify that all modular scripts exist and are referenced in index.html."""
    html_content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    expected_scripts = [
        "scripts/ml-client.js",
        "scripts/data-store.js",
        "scripts/overview-view.js",
        "scripts/architecture-diagram.js",
        "scripts/ablation-table.js",
        "scripts/h1-rescue-chart.js",
        "scripts/case-viewer.js",
        "scripts/explainability-view.js",
        "scripts/selective-triage.js",
        "scripts/tcia-benchmark.js",
        "scripts/manuscript-exporter.js",
        "scripts/app.js",
    ]

    for script_path in expected_scripts:
        file_path = FRONTEND_DIR / script_path
        assert file_path.is_file(), f"Missing script file: {file_path}"
        assert f'src="{script_path}"' in html_content, f"Script not linked in index.html: {script_path}"


def test_data_store_integrity():
    """Verify that data-store.js contains valid ground-truth scientific data."""
    data_store_content = (FRONTEND_DIR / "scripts" / "data-store.js").read_text(encoding="utf-8")

    # Check for all 9 model IDs
    for model_id in ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]:
        assert f'id: "{model_id}"' in data_store_content, f"Missing model {model_id} in data store"

    # Check for key real patient case IDs
    for patient_id in ["HCC_48", "Hem_5", "Hem_337", "HCC_10", "Hem_10"]:
        assert f'patient_id: "{patient_id}"' in data_store_content, f"Missing patient {patient_id} in data store"

    # Check for hypotheses H1 through H4
    for hyp in ["H1", "H2", "H3", "H4"]:
        assert f'id: "{hyp}"' in data_store_content, f"Missing hypothesis {hyp} in data store"


def test_serve_frontend_handler():
    """Verify that serve_frontend.py server module can be imported and initialized."""
    import sys
    sys.path.insert(0, str(WORKSPACE_ROOT))
    from scripts.serve_frontend import XMAIHTTPHandler, FRONTEND_DIR as S_FRONTEND_DIR
    assert S_FRONTEND_DIR.exists()
