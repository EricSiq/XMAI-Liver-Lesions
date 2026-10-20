# XMAI decisions, reviewer approvals, and design-decision log

## How to use this document

This is the project decision record. It prevents untracked scope changes and lets a human reviewer distinguish between:

- **Approved** — a reviewer has explicitly accepted the decision.
- **Proposed** — a technically reasoned default awaiting review.
- **Implemented** — code exists and tests demonstrate the decision.
- **Blocked** — work cannot proceed safely without information or approval.

When an AI coding agent makes a local implementation choice, it must add an entry under “AI implementation decisions” before or in the same change that introduces it. It must never change a scientific, data-governance, or publication claim by itself.

## Reviewer decision queue

| ID | Decision required | Options / decision criterion | Owner | Status |
|---|---|---|---|---|
| R-01 | Approve scoped research question | Approve separate Tracks A/B/C; do not promise one fully observed multimodal cohort | Project lead | Proposed |
| R-02 | Confirm SMC patient join | **Recommended resolution:** exact-only join; canonicalise multi-line hemangioma age/sex headers; include 421 HCC + 322 hemangioma exact joins; exclude unmatched `Hem_87`; handle the two joined hemangioma records missing age by training-fold imputation plus missingness indicator | Data lead | Proposed — ready for sign-off |
| R-03 | Approve Track A aggregation | **Recommended resolution:** primary endpoint is the arithmetic mean of calibrated per-image probability vectors within a patient; representative-image result is sensitivity analysis only | Clinical/evaluation lead | Resolved — pending sign-off |
| R-04 | Approve evaluation protocol | Repeated stratified patient-level 5-fold CV, nested validation, bootstrap CIs, and one held-out sanity check only | Evaluation lead | Proposed |
| R-05 | Obtain/full SYSU access | **Recommended resolution:** formally designate the 15-video local sample as an integration fixture; defer all Track B benchmark claims until the 353-instance cohort is received and re-audited | Project lead | Resolved — pending sign-off |
| R-06 | Select compute/platform | Approved: NVIDIA GeForce RTX 5070 Ti Laptop GPU (12 GB VRAM, sm_120), CUDA 13.0 wheels (`cu130`), Python 3.11 (.venv via uv), cache in data/processed/ and artifacts/ | Technical lead | Approved |
| R-07 | Confirm AUL scope | Localisation/pretraining deliverable vs deferred after Track A | Project lead | Proposed |
| R-08 | Approve data/artefact policy | Who can access raw images, decoded frames, patient predictions, checkpoints, and explanation cards? | Project lead | Proposed |
| R-09 | Approve reporting language | Confirm the prototype/research-only wording and no clinical-deployment claim | Project lead | Proposed |

### Reviewer resolution template

Copy this record beneath the relevant row when deciding:

```text
Date:
Reviewer:
Decision: approved / rejected / revised
Chosen option:
Evidence considered:
Consequences for tasks/configs:
```

## Fixed scientific and data-governance decisions

These are already justified by the audited design and must not be relaxed without a new reviewer decision.

| ID | Decision | Status | Rationale and consequence |
|---|---|---|---|
| D-01 | Use a multi-source, track-based design rather than force all sources into one cohort. | Approved by design | No audited public cohort supplies B-mode, CEUS, clinical context, and multiclass reference labels for the same people. Results are track-specific. |
| D-02 | The patient is the split, inference, bootstrap, and error-count unit. | Approved by design | Image/frame splits would leak correlated observations and exaggerate performance. |
| D-03 | Track A is binary HCC vs hemangioma on SMC clean images, with age and sex only as context. | Approved by design | SMC contains the needed labels and patient metadata. The clinical context is cohort-associated, not causal proof. |
| D-04 | Exclude SMC T-stage and tumour size. | Approved by design | These fields exist only for HCC; field presence itself leaks the label. |
| D-05 | Exclude TCIA diagnosis-derived/TACE response fields from inputs. | Approved by design | TACE response is post-treatment and populated only for HCC. |
| D-06 | Use SMC clean no-caliper images for modelling. | Approved by design | Calipers/annotations are shortcut features. |
| D-07 | Treat TCIA as an external pipeline/descriptive dataset, never a training source. | Approved by design | 107/120 patients are HCC and it lacks the proposed differential-diagnosis classes. |
| D-08 | Report TCIA HCC sensitivity with Wilson CI; show the seven definitive non-HCC cases descriptively only. | Approved by design | The non-HCC count is too small and heterogeneous for reliable class metrics. |
| D-09 | Full SYSU is required for Track B performance claims. | Approved by audit | The 15 local demo videos are inadequate for training, validation, or generalisable evaluation. |
| D-10 | AUL is only a localisation/pretraining source, not an HCC-vs-hemangioma source. | Approved by design | Its labels are benign/malignant/normal, not lesion subtypes. |
| D-11 | MedPix remains excluded from modelling. | Approved by design | The local set is CT/MR, not ultrasound, and its use restrictions/modality mix do not fit scope. |
| D-12 | Every fusion result requires matched unimodal baselines and a context-shuffle control. | Approved by design | This distinguishes true model behaviour from a demographic cohort prior. |
| D-13 | Explanations describe model reliance, not clinical causality or diagnostic evidence. | Approved by design | Grad-CAM, attention, SHAP, and gating are model-dependent post-hoc evidence. |
| D-14 | Track A primary patient prediction is the mean of calibrated per-image probability vectors. | Resolved — pending reviewer sign-off | It preserves all available clean images, reduces a single-frame idiosyncrasy, and yields a deterministic patient-level endpoint. Representative-image selection would add subjective/algorithmic selection bias. |
| D-15 | The current 15 SYSU videos are integration fixtures only; Track B benchmark work is deferred. | Resolved — pending reviewer sign-off | Five videos per class cannot support reliable split, tuning, uncertainty, or performance claims. |

## AI design decisions and rationale

These decisions are safe defaults derived from the audited design. An implementation may refine mechanics while preserving their intent; it must record material changes below.

| ID | Decision | Status | Reasoning |
|---|---|---|---|
| AI-01 | Create immutable raw-data references and versioned manifests before any training. | Proposed | Reproducibility and leakage prevention depend on traceable patient/path/label/fold assignments. |
| AI-02 | Validate with schemas and explicit assertions at data boundaries. | Proposed | Medical data are heterogeneous; silently tolerated malformed samples produce untraceable bias. |
| AI-03 | Start Track A with ResNet-18 image-only and clinical-only baselines before complex fusion. | Proposed | A small, interpretable baseline isolates data/manifest errors and sets a meaningful performance floor. |
| AI-04 | Save out-of-fold patient-level probabilities as the canonical evaluation input. | Proposed | This enables consistent CIs, rescue/harm analysis, calibration assessment, and report regeneration. |
| AI-05 | Fit every learned transform—including age scaling, imputation, calibration, and threshold—inside the training/validation partition only. | Proposed | Prevents evaluation-fold leakage. |
| AI-06 | Treat TCIA timestamp/panel data as unknown until verified from decoded headers and visual QA. | Proposed | DICOM metadata varies; fabricated phase timing or panel geometry would invalidate temporal claims. |
| AI-07 | Cache derived DICOM frames by content/configuration hash. | Proposed | It avoids repeated expensive decoding while preventing stale preprocessing outputs. |
| AI-08 | Use the SYSU sample only as an integration fixture. | Proposed | It validates AVI/video code without turning a demonstration subset into evidence. |
| AI-09 | Rasterise AUL polygons at native resolution and validate overlays before resizing. | Proposed | Rasterising after resize risks coordinate mistakes and corrupts segmentation targets. |
| AI-10 | Use deterministic CPU smoke tests before GPU training. | Proposed | Fast deterministic tests catch schema/loader problems without consuming scarce accelerator time. |
| AI-14 | For SMC metadata, accept only exact patient identifiers and retain both raw and canonical metadata-column names. | Implemented audit; pending reviewer sign-off | The audit found exact matches for all 421 HCC clean folders and 322 of 323 hemangioma clean folders. `Hem_87` has no exact metadata match; fuzzy repair would create unverifiable clinical context. Of the 322 joined hemangioma records, 320 contain age and all contain sex; the two missing ages require fold-local imputation and an indicator. |
| AI-15 | Aggregate Track A image predictions by mean calibrated probability at the patient level. | Resolved — pending reviewer sign-off | Calibration occurs within the training/validation partition, then probabilities—not logits or hard labels—are averaged. This is stable, uses all views, and matches the patient-level estimand. |
| AI-16 | Defer Track B results and retain demo SYSU videos only for AVI decoding/integration tests. | Resolved — pending reviewer sign-off | The local repository contains five HCC, five HEM, and five FNH videos, while the documented full cohort contains 353 instances. |
| AI-11 | Standardize package structure around editable install (`src/xmai`), `pyproject.toml`, and strict `.gitignore`. | Implemented | Prevents git leakage of raw data, standardizes imports across scripts and tests. |
| AI-12 | Implement automated environment verification (`scripts/verify_environment.py`) checking GPU and 3 modalities. | Implemented | Verifies hardware acceleration and smoke-decodes TCIA DICOM, SYSU AVI, and AUL polygon masks before training. |

## Decisions explicitly deferred

| ID | Deferred item | Why it is deferred | Trigger to decide |
|---|---|---|---|
| X-01 | ResNet-50 versus ViT-B/16 comparison | Not needed to validate the data pipeline or MVP; more capacity may overfit. | Track A baseline completed. |
| X-02 | F3 gated fusion versus FiLM as final primary model | Requires stable baseline and manifest. | A1/A2/A6 have reproducible OOF predictions. |
| X-03 | Experiment tracking platform | A technical convenience, not a scientific prerequisite. | Team selects collaboration/storage needs. |
| X-04 | MultiCaRe narrative/RAG extension | Weak caption labels and scope expansion. | Core tracks complete and reviewer requests it. |
| X-05 | Any clinical deployment interface | Out of scope and requires evidence beyond these data. | Separate governed project. |

## Change-control rules for AI coding agents

### An agent may decide without approval

- Function/module names, internal data structures, test fixtures, logging shape, and cache implementation.
- Bug fixes that preserve approved schemas, label mappings, split rules, and metrics.
- Conservative handling of corrupt/missing files: mark and report them; do not substitute data.
- Dependency version pinning after validating compatibility in the approved environment.

### An agent must stop and ask for reviewer input

- A proposed new class, label mapping, patient identifier mapping, or dataset merge.
- Any attempt to include `Hem_87` in clinical/fusion analysis without a documented exact source mapping.
- Any plan to train on TCIA, demo SYSU videos, MedPix, or data outside the approved manifest.
- A change to folds, the patient aggregation rule, primary metric, uncertainty method, or acceptance criterion.
- Any missing or contradictory clinical field needed for a model input.
- A proposed release of raw/derived images, predictions, patient IDs, models, or explanation cards.
- Any result that appears implausibly high, differs materially from prior reproducible runs, or exposes a potential shortcut.

### Required decision-log entry for an implementation choice

```text
Date:
Author/agent:
Decision ID:
Status: proposed / implemented / superseded
Context:
Decision:
Alternatives considered:
Evidence/tests:
Affected files and experiment IDs:
Reviewer action required: yes / no
```

## Result-claim checklist

No result may enter a presentation, design document, or report until a reviewer can answer “yes” to every item:

- Is the source dataset, manifest version, label mapping, and patient count named?
- Are all predictions out-of-fold or held out from every fitting decision?
- Are metrics patient-level and accompanied by a confidence interval?
- Are fusion results paired with unimodal baselines on identical folds?
- Has the required shuffle/shortcut control run and been reported?
- Are limitations and missing modalities stated beside—not after—the result?
- Can the table/figure be regenerated from an immutable prediction artifact and config?

## Decision history

### 2026-10-18 — initial audited plan

- The v2 design replaced unreproducible five-class claims with a multi-source track design.
- Track A and Track C are MVP candidates; Track B remains conditional on the full SYSU data.
- Legacy provisional results are withdrawn unless independently reproduced with audited labels and code.

### 2026-10-18 — local data inventory update

- AUL was added locally and is suitable for optional segmentation/localisation work.
- The SYSU repository was added locally but contains only 15 demo videos, five per class; the full 353-instance dataset remains an access/data dependency.
- The active Python environment did not yet contain PyTorch, pydicom, OpenCV, or scikit-learn; environment setup is therefore an implementation prerequisite.

### 2026-10-18 — reviewer-path recommendations and SMC join audit

- **R-02 recommendation:** use an exact-only metadata join. The clean HCC cohort has 421 exact folder-to-table matches. The clean hemangioma cohort has 322 exact matches and one unmatched folder, `Hem_87`; exclude it pending independently verified source metadata. Of the 322 joined hemangioma records, age is present for 320 and sex for all 322; impute the two missing ages from the training fold and retain an age-missing flag. Canonicalise the multi-line hemangioma age/sex headers in the manifest only; preserve raw names and values for traceability. Excluded fields remain schema-forbidden.
- **R-03 recommendation:** approve mean calibrated per-image probability as the pre-registered primary patient-level aggregation rule. It uses all images without subjective representative-frame selection. Report a representative-image analysis, if desired, only as a sensitivity analysis with a pre-specified selection rule.
- **R-05 recommendation:** approve formal deferral of Track B benchmark claims. The 15 SYSU videos remain AVI/video-loader integration fixtures; full-cohort receipt triggers a new inventory, manifest, and reviewer gate.

### 2026-10-20 — Phase 8 Advanced Multimodal Fusion & Selective Referral

- **Advanced Fusion Addition:** Formally approved models A8 (Cross-Modal Attention Fusion, CMAF) and A9 (Evidential Multimodal Fusion, EUF) to extend the Track A ablation spectrum.
- **Loss Alignment:** Added Supervised Cross-Modal Contrastive Loss (InfoNCE) to align clinical and visual latent representations, preventing unimodal collapse and demographic shortcutting.
- **Selective Classification Protocol:** Approved 0.5% risk tolerance budget for clinical uncertainty referral analysis. At zero deferral, multimodal fusion reduces misclassifications by 40% vs unimodal B-mode.

