# XMAI prerequisites and environment setup

## What must be true before implementation

XMAI is a research prototype, not a clinical device. Work must follow the scope and safeguards in `XMAI_Design_Document_v2.md`, `tasks.md`, and `decisions.md`.

### Data availability

| Dataset | Local status | Permitted use at project start |
|---|---|---|
| SMC-LUD | Present | Track A, clean no-caliper images only; patient metadata join required |
| TCIA B-mode-and-CEUS-Liver | Present | Track C DICOM/pipeline and external descriptive evaluation only |
| AUL | Present | Optional localisation/segmentation or pretraining; not subtype classification |
| SYSU-CEUS | 15-video sample present | Loader/visual QA only; full 353-case release is required for Track B metrics |
| MedPix | Present | Excluded from model development due to modality mix/licensing constraints |
| MultiCaRe | Not required | Deferred stretch source; do not block the MVP |

Before writing model code, verify that the raw data paths are configurable and readable, and that raw files will not be committed to source control.

### Data and licence controls

- Confirm the team is permitted to use every source under its stated licence/access terms.
- SMC-LUD is non-commercial research data. Do not redistribute raw images or derived resized/cropped image sets.
- Keep source attribution and licence notes with every released report.
- Patient-level predictions, decoded frames, checkpoints, and explanation cards are research artifacts. Store them in ignored directories and do not publish them without review.

## Recommended machine setup

### Minimum development machine

- 64-bit Windows, Linux, or macOS.
- Python **3.10 or 3.11** in a project-local virtual environment.
- 16 GB RAM minimum; 32 GB recommended for DICOM/video inspection.
- At least 350 GB free working storage in addition to the existing raw data, if decoded TCIA frames and run artifacts will be cached.

### Detected / Configured Training Machine
- **GPU**: NVIDIA GeForce RTX 5070 Ti Laptop GPU (12 GB VRAM, Compute Capability 12.0 / sm_120, Driver 592.01, CUDA 13.1 supported).
- **Python**: 3.11.15 managed via `uv`.
- **Environment**: Local `.venv` using `uv` with PyTorch CUDA 13.0 wheels (`cu130`) required for sm_120 Blackwell architecture.

## Create the environment

The project uses `uv` for fast, deterministic environment and dependency management.

```powershell
# 1. Create a virtual environment with Python 3.11
uv venv .venv --python 3.11

# 2. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install PyTorch and TorchVision with CUDA 13.0 (supports sm_120 Blackwell)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130

# 4. Install all dependencies and development tools in editable mode
uv pip install -e ".[dev]"
```

### Required packages

| Area | Packages / capabilities |
|---|---|
| Core | `numpy`, `pandas`, `pyyaml`, `pydantic` (or equivalent schema validation), `tqdm`, `rich` |
| Imaging | `Pillow`, `opencv-python-headless`, `scikit-image`, `pydicom`, `pylibjpeg` + appropriate pixel-data plugin |
| ML | `torch`, `torchvision`, `scikit-learn`, `scipy` |
| Metrics/reporting | `matplotlib`, `seaborn`, `statsmodels` or a tested Wilson-CI implementation |
| Explainability | `captum`; install `shap` only if the selected explanation implementation uses it |
| Testing/quality | `pytest`, `ruff`, `mypy` or `pyright`, formatter of choice |

Optional packages must not become implicit runtime dependencies. For example, experiment tracking (MLflow/W&B) and notebook support may be added only after a reviewer chooses them.

### Verify the environment

Run a small verification script that prints, at minimum:

- Python, PyTorch, torchvision, CUDA runtime, and GPU availability/version.
- Import success for `pydicom`, OpenCV, Pillow, NumPy, pandas, scikit-learn, Captum, and pytest.
- DICOM pixel decoding of one TCIA file.
- Video decoding of one SYSU sample AVI.
- Rasterisation of one AUL JSON annotation.

The verification output should be saved as a run artifact, not hand-written into a report.

## Required configuration

Use a local, uncommitted configuration file (for example `.env` or `configs/local.yaml`) containing only paths and machine-specific settings:

```yaml
workspace_root: C:/Users/erics/Downloads/XMAI Liver Lesions
raw_smc_root: ${workspace_root}/SMC-LUD Liver Ultrasound Dataset (HCC vs Hemangioma)
raw_tcia_root: ${workspace_root}/TCIA
raw_aul_root: ${workspace_root}/AUL
raw_sysu_root: ${workspace_root}/Focal-liver-lesions-dataset-in-CEUS-master
artifact_root: ${workspace_root}/artifacts
num_workers: 4
device: cuda
```

Never hard-code a developer-specific absolute path in package code, manifests committed to source control, or experiment configs intended for sharing.

## Required project choices before full training

The human reviewer must confirm the following in `decisions.md`:

1. The package/environment manager and target compute device.
2. The source-control and artifact-storage policy.
3. The reviewed SMC exact-join exception policy: `Hem_87` is excluded unless its metadata mapping is independently verified.
4. Whether/when full SYSU access is expected and who is responsible for obtaining it; until then, Track B is decoding-only.
5. Whether AUL is a pretraining/localisation deliverable or deferred.
6. The experiment-tracking choice, if any.

## Definition of “ready to start”

The project is ready for Phase 1 when all of the following are true:

- A clean Python environment passes the verification script.
- Raw datasets are read-only from the project’s perspective and excluded from Git.
- At least one reviewer has read the leakage rules in `tasks.md`.
- The team accepts that the current SYSU sample cannot support Track B performance claims.
- No historical or provisional results are carried forward without a reproducible manifest, configuration, and prediction file.
