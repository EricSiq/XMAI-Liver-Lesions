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
    """Verify that index.html contains all 6 required scholarly presentation sections."""
    html_content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    expected_sections = [
        "section-overview",
        "section-architecture",
        "section-ablation",
        "section-cases",
        "section-explainability",
        "section-paper-artifacts",
    ]

    for section_id in expected_sections:
        assert f'id="{section_id}"' in html_content, f"Missing section #{section_id} in index.html"


def test_frontend_scripts_exist_and_linked():
    """Verify that all modular scripts exist and are referenced in index.html."""
    html_content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    expected_scripts = [
        "scripts/math-renderer.js",
        "scripts/ml-client.js",
        "scripts/data-store.js",
        "scripts/overview-view.js",
        "scripts/architecture-diagram.js",
        "scripts/ablation-table.js",
        "scripts/case-viewer.js",
        "scripts/explainability-view.js",
        "scripts/manuscript-exporter.js",
        "scripts/multiclass-explorer.js",
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


def test_latex_equations_balanced_braces_in_frontend():
    """Stress test that all LaTeX formulas in architecture-diagram.js and explainability-view.js have strictly balanced braces."""
    arch_content = (FRONTEND_DIR / "scripts" / "architecture-diagram.js").read_text(encoding="utf-8")
    xai_content = (FRONTEND_DIR / "scripts" / "explainability-view.js").read_text(encoding="utf-8")

    # Extract all math: `...` formulas from architecture diagram models A1-A9
    arch_matches = re.findall(r"math:\s*`([^`]+)`", arch_content)
    # Extract MathRenderer.render('...') formulas, properly handling escaped quotes like \'
    xai_matches = re.findall(r"MathRenderer\.render\('((?:[^'\\]|\\.)*)'", xai_content)

    all_formulas = arch_matches + xai_matches
    assert len(all_formulas) >= 9, f"Expected at least 9 mathematical model formulas, got {len(all_formulas)}"

    for formula in all_formulas:
        # Check balanced curly braces
        open_braces = formula.count("{")
        close_braces = formula.count("}")
        assert open_braces == close_braces, f"Unbalanced braces in LaTeX formula: {formula}"

        # Check balanced parentheses (excluding escaped \left( / \right))
        # Strip escaped \left( and \right) before checking raw paren counts
        clean_parens = formula.replace(r"\left(", "").replace(r"\right)", "")
        open_parens = clean_parens.count("(")
        close_parens = clean_parens.count(")")
        assert open_parens == close_parens, f"Unbalanced parentheses in LaTeX formula: {formula}"



def test_math_renderer_script_structure():
    """Stress test math-renderer.js for expected parsing tokens and fallbacks."""
    renderer_content = (FRONTEND_DIR / "scripts" / "math-renderer.js").read_text(encoding="utf-8")

    # Core required conversion tokens
    required_tokens = [
        "\\frac",
        "\\alpha",
        "\\beta",
        "\\sigma",
        "\\phi",
        "math-frac",
        "math-num",
        "math-denom",
        "renderFallback",
        "typeset",
        "window.katex",
    ]

    for tok in required_tokens:
        assert tok in renderer_content, f"Missing token {tok} in math-renderer.js"


def test_academic_theme_math_css_classes():
    """Verify that styles/academic-theme.css contains all styling classes required by math-renderer."""
    css_content = (FRONTEND_DIR / "styles" / "academic-theme.css").read_text(encoding="utf-8")

    required_classes = [
        ".math-frac",
        ".math-num",
        ".math-denom",
        ".math-inline",
        ".math-block-display",
    ]

    for cls in required_classes:
        assert cls in css_content, f"Missing CSS class {cls} in styles/academic-theme.css"

