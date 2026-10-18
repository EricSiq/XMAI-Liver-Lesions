# XMAI: Explainable Multimodal AI for Differential Diagnosis of Focal Liver Lesions

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Research--Only-lightgrey.svg)](decisions.md)

XMAI investigates whether an explainable multimodal AI framework combining B-mode ultrasound morphology, contrast-enhanced ultrasound (CEUS) perfusion kinetics, and structured patient clinical context can support differential diagnosis of focal liver lesions (FLLs), and whether each modality's contribution can be explained to clinicians with faithful attributions.

> **Project Notice**: This is a research prototype developed for the Multimodal AI Lab at Symbiosis Institute of Technology (Pune, AY 2026-27). It is not approved or intended for clinical diagnosis or treatment planning.

---

## 1. Experimental Tracks

Because no open dataset provides B-mode, CEUS video, structured clinical context, and multiclass labels for the same cohort, XMAI employs a multi-source, track-based architecture:

| Track | Dataset | Primary Question | Inputs | Labels | Status |
|---|---|---|---|---|---|
| **Track A** | **SMC-LUD** (Samsung Medical Center) | Does patient context (age, sex) improve discrimination beyond B-mode alone? | M1: B-mode image<br>M3: Age, Sex | HCC vs Hemangioma (K=2) | **Primary MVP** |
| **Track B** | **SYSU-CEUS** (Sun Yat-sen Univ.) | Does temporal CEUS dynamics provide added signal over static frames? | M2: CEUS cine sequence<br>M1: B-mode | HCC, Hemangioma, FNH (K=3) | Conditional (Pending full 353-case cohort) |
| **Track C** | **TCIA** (B-mode and CEUS Liver) | External pipeline validation & single-scanner transfer behaviour | M1: B-mode<br>M2: CEUS DICOM | External HCC sensitivity (n=107) | **MVP Pipeline Testbed** (Not for training) |
| **Track L** | **AUL** (Ultrasound Liver) | Lesion localization & segmentation pretraining | M1: B-mode<br>Masks: Liver, Lesion | Benign / Malignant / Normal | Optional Auxiliary |

---

## 2. Repository Layout

```text
XMAI-Liver-Lesions/
├── configs/                  # Experiment configurations
│   ├── local.yaml.example    # Machine-specific configuration template
│   └── local.yaml            # Active local configuration (git-ignored)
├── data/
│   ├── manifests/            # Immutable, versioned train/val/test splits & manifests
│   └── processed/            # Derived frames, masks, and temporary caches (git-ignored)
├── src/xmai/                 # Core Python package
│   ├── data/                 # Readers, DICOM parsing, schemas, leakage assertions
│   ├── models/               # Encoders (M1/M2/M3), temporal pooling, fusion modules
│   ├── training/             # Stratified CV loops, early stopping, calibration
│   ├── evaluation/           # Patient-level metrics, bootstrap CIs, McNemar tests
│   ├── explainability/       # Grad-CAM, temporal attention, SHAP, Modality Shapley
│   └── utils/                # Seeds, path resolution, logging, schema validators
├── scripts/                  # CLI scripts (verify_environment.py, manifest_gen.py)
├── tests/                    # Unit, schema, leakage, and regression tests
├── artifacts/                # Run logs, model checkpoints, explanation cards (git-ignored)
├── XMAI_Design_Document_v2.md# Complete scientific specification & audit
├── decisions.md              # Project decision log & governance record
├── requirements.md           # Environment prerequisites & hardware guidelines
└── tasks.md                  # Executable step-by-step implementation plan
```

---

## 3. Getting Started

### 3.1 Prerequisites
- 64-bit Windows, Linux, or macOS
- Python **3.11**
- Recommended: [uv](https://github.com/astral-sh/uv) (fast Python package and project manager)
- GPU: NVIDIA RTX GPU with CUDA 12.4+ (or CPU mode for smoke tests)

### 3.2 Environment Setup with `uv`

```powershell
# 1. Create a virtual environment with Python 3.11
uv venv .venv --python 3.11

# 2. Activate the environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 3. Install PyTorch with CUDA 12.6 support (adjust if using CPU only)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# 4. Install the remaining dependencies in editable mode
uv pip install -e ".[dev]"
```

### 3.3 Configure Paths
Copy the local config template and adjust paths if your datasets are located elsewhere:
```powershell
cp configs/local.yaml.example configs/local.yaml
```

### 3.4 Verify Setup
Run the automated environment and decoding verification script:
```powershell
python scripts/verify_environment.py
```
This script validates:
- Python, PyTorch, and CUDA accelerator availability
- Core scientific and imaging libraries
- DICOM pixel decoding from TCIA
- Video decoding from SYSU sample AVIs
- Polygon mask rasterisation from AUL

---

## 4. Key Scientific Safeguards

1. **Patient-Level Splits Only**: Splits are strictly stratified by patient ID. No images or cine frames from the same patient are ever shared across train, validation, or test sets.
2. **Zero Leakage Barrier**: Features populated only for positive cases (e.g., SMC T-stage and tumor size for HCC) or post-treatment (e.g., TCIA TACE response) are strictly excluded via automated schema assertions.
3. **Clean-Only Imaging**: Uses SMC clean images without calipers to prevent models from learning measurement shortcuts.
4. **Context-Shuffle Controls**: Every multimodal gain must be verified against a context-shuffle control to ensure demographic priors are not masquerading as clinical features.

---

## 5. References and Documentation

- [XMAI Design Document v2.0](XMAI_Design_Document_v2.md)
- [Project Decisions & Change Control](decisions.md)
- [Requirements & Hardware Specs](requirements.md)
- [Task Implementation Checklist](tasks.md)
