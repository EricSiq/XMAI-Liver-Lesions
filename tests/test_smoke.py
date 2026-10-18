"""
Smoke test to ensure basic package imports and project integrity.
"""
import sys
from pathlib import Path

def test_python_version():
    assert sys.version_info >= (3, 11), "Python 3.11+ is required"

def test_project_structure():
    root = Path(__file__).parent.parent
    assert (root / "configs").is_dir()
    assert (root / "data" / "manifests").is_dir()
    assert (root / "src" / "xmai").is_dir()
    assert (root / "scripts").is_dir()
    assert (root / "artifacts").is_dir()

def test_package_import():
    import xmai
    assert xmai is not None
