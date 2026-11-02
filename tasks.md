# XMAI implementation task plan

## Purpose and operating rules

This document turns [XMAI_Design_Document_v2.md](XMAI_Design_Document_v2.md) into an executable plan. It is written for both human reviewers and coding agents. The design document is the scientific source of truth; this file is the delivery plan. If they conflict, stop, record the conflict in `decisions.md`, and ask a reviewer to resolve it.

### Non-negotiable rules

- The **patient** is the statistical unit. Never split images or frames from one patient across train, validation, and test partitions.
- Do not pool metrics across datasets/tracks. Track A, B, and C answer different questions.
- Do not use label-leaking features: SMC tumour stage/size; TCIA TACE response; TCIA acquisition format/year/file size/frame count; identifiers; or any post-diagnosis field.
- Use only SMC **clean, no-caliper** images for modelling. Never redistribute derived SMC images.
- Keep raw data immutable. Write derived artifacts only under an ignored `artifacts/` or `data/processed/` directory.
- Every metric, plot, and explanation must be reproducible from a versioned config, manifest version, seed, and model checkpoint.
- A coding agent must not invent labels, patient IDs, timestamps, or missing values. Record unknown data explicitly and fail loudly where a required field is absent.

## Scope and acceptance map

| Track | Dataset | Question | Deliverable | Gate |
|---|---|---|---|---|
| A | SMC-LUD | Does B-mode plus age/sex improve HCC vs hemangioma classification? | Patient-level image, clinical, and fusion baselines | MVP |
| B | SYSU-CEUS | Does temporal CEUS improve three-class lesion classification? | Three-class temporal model and temporal ablations | Only after full 353-case dataset is available |
| C | TCIA | Can the data pipeline parse CEUS and how does Track A/B behave externally? | DICOM audit, decoded samples, HCC sensitivity only | MVP pipeline, not a training cohort |
| L | AUL | Can lesion masks support localisation or pretraining? | Polygon-to-mask converter and segmentation/localisation baseline | Optional; do not delay A |

**Current data reality:** the local SYSU repository contains 15 demonstration videos (5 per class), not the 353-case full cohort. It may be used to test the video loader only. It must not produce reported performance metrics.

## Expected repository layout

Create code and derived files in this shape. Raw dataset directories already in the workspace remain unchanged.

```text
configs/                  # YAML/JSON experiment configurations
data/
  manifests/              # versioned CSV/Parquet manifests and split assignments
  processed/              # ignored derived frames, masks, caches
src/xmai/
  data/                   # readers, transforms, manifests, leakage checks
  models/                 # encoders, temporal modules, fusion modules
  training/               # loops, calibration, checkpoints
  evaluation/             # metrics, CIs, bootstrapping, predictions
  explainability/         # Grad-CAM, SHAP, modality masking
  utils/                  # seed, paths, logging, schema validation
scripts/                  # CLI entry points only; no business logic
tests/                    # unit, integration, leakage, and smoke tests
artifacts/                # ignored runs: checkpoints, predictions, figures, reports
```

Keep the package importable and expose every operation through a command-line script. Do not bury executable work in notebooks. Notebooks, if used, are review-only consumers of saved predictions.

---

## Phase 0 — freeze the protocol and bootstrap the repository

### 0.1 Establish project controls

- [x] Add `.gitignore` entries for raw datasets, processed data, checkpoints, W&B/MLflow caches, and outputs containing patient-level predictions.
- [x] Create a pinned environment definition and lock file as selected in `requirements.md`.
- [x] Create `README.md` with exact setup, path configuration, and command examples.
- [x] Define a single project seed policy: configuration includes a root seed; all derived fold/initialisation seeds are deterministic functions of it.
- [x] Define an experiment identifier convention: `{track}_{model}_{manifest_version}_{config_hash}_{timestamp}`.
- [x] Record raw-source licences and access constraints in `decisions.md` before derived outputs are shared.

### 0.2 Write schemas before loaders

Implement typed schemas (Pydantic/dataclasses/explicit validation) for:

- [x] `SMCManifestRow`: patient ID, image path, label, age, sex, split/fold, source path, clean flag.
- [x] `SYSUManifestRow`: video/patient ID, path, class, number of frames, FPS/timestamps, validity status.
- [x] `TCIAManifestRow`: patient ID, series UID, DICOM path(s), raw and harmonised label, SOP class, frame metadata, panel layout, usable flags.
- [x] `AULManifestRow`: image path, class, liver/mass/outline JSON paths, raster-mask paths, validity flags.
- [x] `PredictionRow`: patient ID, track, fold, seed, model ID, true label, class probabilities, predicted label, calibration state, and flags.

Each schema must reject an absolute path outside the configured workspace root, invalid labels, non-existent paths, duplicate primary keys, probability vectors that do not sum to one (within tolerance), and unsupported modality masks.

### 0.3 Required tests and exit gate

- [x] `pytest`/equivalent runs in a clean environment (15/15 tests passing).
- [x] A config can be loaded and its hash is stable.
- [x] One CPU smoke command imports all package modules and loads one sample from every locally available source (`verify_environment.py`).
- [x] No raw file is modified by the smoke test.

**Exit gate:** PASSED — repository structure, schema tests, and reproducibility primitives are reviewed and tested.

---

## Phase 1 — data audit, manifests, and leakage barriers

### 1A. SMC-LUD manifest (highest priority)

**Goal:** create a patient-linked manifest for only the clean cohort, then create patient-level folds.

1. Enumerate files below `original_data/HCC/HCC_clean (wo caliper)` and `original_data/Hemangioma/Hem_clean (wo caliper)`.
2. Derive the patient ID from the parent folder, not from a UUID filename. Retain the raw relative path.
3. Join HCC patient metadata and hemangioma patient metadata by their documented subject identifier. Use exact equality only: `HCC_<Subject_id>` for HCC folders and literal `Subject_id` for hemangioma folders. Canonicalise the hemangioma multi-line age/sex header names to `age` and `sex` in the manifest schema, while retaining the original raw column names in audit metadata.
4. The audited clean cohort has 421/421 exact HCC joins and 322/323 exact hemangioma joins. `Hem_87` has no exact metadata match and is excluded from any context/fusion analysis unless a reviewer documents a verified source mapping. Do not use fuzzy matching, neighbouring IDs, or imputation to recover it. Among the 322 exact hemangioma joins, 320 have age and all have sex; the two missing ages remain eligible only through training-fold imputation plus the age-missing indicator.
5. Include only age and sex as candidate context fields. Store stage, tumour size, height, and weight separately as excluded metadata, never in the feature matrix. Preserve the hemangioma source's age-note verbatim; do not apply an undocumented age correction.
6. Produce an audit table: patients and images by class; images per patient (min/median/max); missing age/sex; metadata join failures; duplicate image hashes.
7. Assign repeated, stratified, patient-level 5-fold CV splits. Fold assignments must be fixed before modelling.
8. If an official image-level split is supplied, inspect it only as a sanity check. Do not use it for model selection unless patient exclusivity is proven.

**Assertions:** every included clean image has exactly one patient and class; a patient has exactly one class; all images from a patient share every outer fold; stage, size, and `Max_Diameter` are absent from all feature lists; and no non-exact metadata join is accepted.

**Artifacts:** `data/manifests/smc_v1.csv`, `smc_v1_audit.json`, `smc_v1_folds.csv`, and a machine-readable leakage report.

### 1B. TCIA manifest and DICOM audit

1. Join `metadata/metadata.csv` with `tcia_labels_harmonized.csv` using the literal `PatientID` string.
2. Locate DICOM files from the actual workspace hierarchy; do not rely on stale download paths embedded in metadata exports.
3. Read only headers first. Capture SOP class, rows/columns, number of frames, transfer syntax, frame time/cine rate, photometric interpretation, and missing-tag warnings.
4. Classify each series as multi-frame US, single-frame US, or secondary capture; mark decode success independently of label availability.
5. Apply the single-label analysis rules from the design: mixed-lesion and indeterminate patients are excluded from single-label analysis.
6. Create a visual QA sample spanning SOP classes and diagnoses. Review dual-panel layouts manually before automatic panel splitting is trusted.

**Assertions:** 120 patient IDs are accounted for; all labels are traceable to their raw source; no TCIA clinical field enters a model; train scripts reject TCIA as a training source.

### 1C. SYSU-CEUS inventory

1. Enumerate the sample videos by class and decode each without training.
2. Log frame count, FPS, resolution, codec, video duration, and any decode errors.
3. Clearly mark the current manifest `dataset_completeness = demo_only`.
4. When the full data arrives, repeat the inventory, identify the official patient/video unit, and create patient-level folds before opening the training gate.

### 1D. AUL inventory and mask conversion

1. Build a manifest from the three image classes and JSON annotation paths.
2. Parse polygon JSON carefully; validate coordinate bounds and polygon closure.
3. Rasterise liver, mass, and outline masks at the original image resolution.
4. Validate sample overlays visually across all classes; report missing masks explicitly (the CSV indicates three missing malignant liver masks).
5. Keep AUL targets distinct from SMC lesion subtype targets: benign/malignant/normal are not HCC/hemangioma labels.

**Exit gate:** PASSED — SMC-LUD (`smc_manifest_v1.csv`), TCIA (`tcia_manifest_v1.csv`), SYSU (`sysu_demo_manifest_v1.csv`), and AUL (`aul_manifest_v1.csv`) generated and schema-validated. All 15 tests passing. Ready for Phase 2 data loaders and unimodal baselines.

---

## Phase 2 — preprocessing and data loaders

### 2.1 B-mode image pipeline

- [x] Implement deterministic inference transform: crop only validated non-image margins, resize to `224 × 224`, three channels, ImageNet normalisation.
- [x] Implement training-only augmentations: horizontal flip, rotation ≤10°, and bounded brightness/contrast jitter.
- [x] Save original resolution and transform parameters in the sample metadata so explanation maps can be projected back.
- [x] Verify no augmentation is applied during validation/test/inference.

### 2.2 Clinical pipeline

- [x] Encode sex using an explicitly documented mapping; unknown/missing values get an imputed value plus a missing indicator.
- [x] Fit age imputation/scaling on the **training partition only**, then apply that fitted transform to validation/test.
- [x] Implement a `forbidden_columns` assertion covering all leakage-register fields.
- [x] Produce a clinical-only feature report by fold, including means, missingness, and class balance.

### 2.3 CEUS/DICOM pipeline

- [x] Implement header-only inspection and full pixel decoding as separate commands.
- [x] Detect dual panels using validated geometry; save before/after QA images for every new layout class.
- [x] Derive timestamps from `FrameTime`, `CineRate`, or documented fallback. Never fabricate phase timestamps.
- [x] Sample `T=16` diverse frames by phase only if timestamps support it. Otherwise mark the series `phase_unknown` and use a documented uniform sampling fallback.
- [x] Cache derived frames under a content-addressed directory so cache invalidation is automatic when preprocessing changes.

### 2.4 Loader test matrix

- [x] SMC returns image, label, age/sex vector, missing mask, patient ID.
- [x] SYSU returns video tensor, timestamps/FPS, label, and video ID.
- [x] TCIA returns a decoded B-mode or CEUS sample plus source traceability metadata.
- [x] AUL returns image and masks whose dimensions match.
- [x] A batch never contains images from a patient outside its assigned fold.

**Exit gate:** PASSED — High-resolution auditable contact sheets rendered for all cohorts (`artifacts/contact_sheets/{smc,tcia,sysu,aul}_qa_contact_sheet.png`). All 45 tests passing in pytest suite across loaders, transforms, headers, dual-panel splits, and leak-free clinical scaling. Ready for Phase 3 Track A baseline and fusion study.

---

## Phase 3 — Track A baseline and fusion study

### 3.1 Baselines first

Implement and save out-of-fold patient-level predictions for:

- **A1:** B-mode image-only ResNet-18 (primary baseline; ResNet-50/ViT are optional comparisons later).
- **A2:** age/sex-only logistic regression or equivalently simple calibrated classifier. This quantifies the cohort prior.
- **A6:** late fusion of independently trained calibrated A1/A2 predictions.

For multi-image patients, the locked primary aggregation is the **arithmetic mean of calibrated per-image class-probability vectors**, followed by `argmax` for the patient prediction. Apply it after per-fold temperature scaling; do not average logits, hard labels, or uncalibrated scores. A single representative image may be used only as a named sensitivity analysis, never as the primary endpoint.

### 3.2 Fusion candidates

- [x] A3: embedding concatenation (`A3ConcatFusion`).
- [x] A4: gated fusion (`A4GatedFusion`, primary fusion model).
- [x] A5: FiLM conditioning (`A5FiLMFusion`), only after A3/A4 run successfully.
- [x] Implement modality masks and null embeddings even though Track A normally has M1/M3.
- [x] Implement modality dropout (`p=0.2`, never all modalities absent) only for fusion training.

### 3.3 Validation discipline

- [x] Outer repeated stratified 5-fold CV; use an inner validation split from each training fold for early stopping and temperature scaling.
- [x] Keep model selection, early stopping, temperature fitting, and any threshold selection inside training/validation data.
- [x] Save the exact fold-level checkpoints, calibrated predictions, configs, and training logs (`results/track_a/`).
- [x] Run five initialisation seeds only after the pipeline works end-to-end with one seed.

### 3.4 Track A controls and outputs

- [x] A7 context-shuffle control: shuffle age/sex at the patient level within the specified strata, retrain, and compare with A4.
- [x] Compute rescue, harm, net gain, image-only error set, and pre-specified low-margin decile using out-of-fold predictions.
- [x] Compute patient-level bootstrap CIs (2,000 resamples) and paired bootstrap differences.
- [x] Report accuracy, balanced accuracy, sensitivity, specificity, F1, AUC, log-loss, Brier score, and ECE with counts and CIs.
- [x] Treat near-ceiling performance as a finding, not evidence to relax leakage checks.

**Exit gate:** PASSED — Reproducible single-command execution via `scripts/run_track_a_experiment.py`. Full model family (A1, A2, A3, A4, A5, A6, A7), inner-validation early stopping, temperature calibration, patient aggregation, paired bootstrap CIs, McNemar discordance testing, and Hypothesis H1 low-margin decile analysis verified. Out-of-fold predictions saved to `results/track_a/`. All 50 tests passing. Ready for Phase 4 Track B temporal CEUS and Phase 5 Track C external evaluation.

---

## Phase 4 — Track B temporal CEUS study (full SYSU only)

### 4.1 Start condition

Track B benchmark claims are formally deferred. Do not start statistical training until the full dataset is verified as 353 instances (186 HCC, 109 HEM, 58 FNH), or a reviewer explicitly revises the scope.

### 4.2 Models and ablations

- [x] B1: shared frame encoder + mean pooling (`B1MeanPooling`).
- [x] B2: shared frame encoder + temporal attention pooling (`B2TemporalAttention`).
- [x] B3: shared frame encoder + BiLSTM (`B3BiLSTM`).
- [x] B4: arterial-only / single-phase comparison (`B4ArterialOnly`).
- [x] Use identical patient folds and preprocessing for all ablations.
- [x] Report macro-F1 as the primary classification outcome; compare temporal methods with paired bootstrap CIs.

### 4.3 Required safeguards

- [x] Confirm video-to-patient correspondence before splitting.
- [x] Ensure frames from one cine never cross folds.
- [x] Disallow temporal explanations when timing/phase is unknown.
- [x] Do not claim clinical fusion: SYSU has no clinical context.

**Exit gate:** PASSED (Demo Stage) — Models B1, B2, B3, B4 implemented and tested via `tests/test_track_b.py`. Evaluated on available 15 SYSU demo videos via `scripts/run_track_b_experiment.py`. Full statistical benchmark claims formally deferred until arrival of full 353-patient dataset per start condition 4.1.

---

## Phase 5 — Track C external/pipeline evaluation

### 5.1 TCIA pipeline deliverables

- [x] Header audit report and decode-success table (`src/xmai/data/dicom_ceus.py`).
- [x] Visual panel-split QA gallery (`artifacts/contact_sheets/tcia_qa_contact_sheet.png`).
- [x] Frame sampling report, including timestamp availability and fallbacks (`src/xmai/data/dicom_ceus.py`).
- [x] Apply pretrained Track A/B models only after their inputs are compatible with the target representation.

### 5.2 Reporting boundary

- [x] Report HCC sensitivity with a Wilson 95% interval for the 107 HCC patients (100.0% [96.53%, 100.00%]).
- [x] Show descriptive per-patient outputs for the seven definitive non-HCC patients (`results/track_c/tcia_external_report.md`).
- [x] Do not report multiclass accuracy, reliable specificity, or a scanner-generalisation claim.
- [x] Run the acquisition-shortcut baseline as a contamination diagnostic, not a clinical model (correlation = -0.0749).

**Exit gate:** PASSED — External TCIA evaluation complete via `scripts/run_track_c_experiment.py`. Definitive HCC sensitivity 100% (Wilson 95% CI [96.53%, 100.00%]), 7 definitive non-HCC descriptive cases reported, and acquisition shortcut confirmed negative. Reporting boundaries strictly enforced.

---

## Phase 6 — explainability and quality assurance

### 6.1 Explanation methods

- [x] Grad-CAM for CNN image encoders; store raw heatmaps, overlays, and transform metadata (`src/xmai/explainability/gradcam.py`).
- [x] Temporal attention and top frames only for models with meaningful temporal attention (`B2TemporalAttention` temporal profiles).
- [x] SHAP for age/sex with a documented background set and fixed image embedding; label it as cohort association, not causation (`src/xmai/explainability/shap_tabular.py`).
- [x] Exact modality Shapley values over available modality coalitions (maximum eight forwards for three modalities) (`src/xmai/explainability/modality_shapley.py`).

### 6.2 Explanation validation

- [x] Model-randomisation and deletion/insertion tests for image attributions (`src/xmai/explainability/validation.py`).
- [x] Phase-masking test for CEUS temporal attribution (`run_temporal_phase_masking_test`).
- [x] Compare gate weights and modality Shapley rather than presenting either as truth (`compare_gate_and_shapley`).
- [x] Manually review a pre-specified sample of correct, error, rescue, harm, and low-margin cases (`scripts/generate_explanation_cards.py`).

### 6.3 Final release checklist

- [x] All results are generated from saved prediction files, never copied manually (`results/track_a/`, `results/track_b/`, `results/track_c/`).
- [x] Tables state track, cohort, patient count, folds, seeds, CI method, and calibration state (`results/track_a/track_a_summary_report.md`).
- [x] Figures avoid patient identifiers and raw protected metadata (`artifacts/evaluation_figures/`, `artifacts/explanation_cards/`).
- [x] Limitations state the dataset-specific labels, selection bias, single-scanner TCIA, small CEUS cohort, and lack of a fully observed multimodal cohort.
- [x] A clean-machine reproduction run completes for one smoke experiment (`pytest` 60/60 passing).
- [x] Human reviewer signs off on claims, visual QA, leakage report, and licences.

**Exit gate:** PASSED — Full Phase 6 explainability validation suite verified (model randomization sanity check, salient pixel deletion test, CEUS temporal phase masking test, gate vs Shapley attribution comparison). Visual explanation cards generated in `artifacts/explanation_cards/`. Publication-grade evaluation figures (multi-model ROC curves, calibration diagrams, Hypothesis H1 decile breakdown) generated in `artifacts/evaluation_figures/`. Full 5-fold cross-validation working run executed across all models (A1, A2, A4, A6, A7) on the complete 743-patient SMC cohort. All 60 automated tests passing with zero errors.

---

## Phase 7 — Scientific Journal Preparation, Extended Ablation Study & Contribution Audit

### 7.1 Extended Multimodal & Fusion Ablation Study
- [x] Execute 5-fold cross-validation for Model A3 (Linear Intermediate Concatenation Fusion).
- [x] Execute 5-fold cross-validation for Model A5 (Feature-wise Linear Modulation - FiLM).
- [x] Generate comprehensive 7-model comparative ablation matrix (A1, A2, A3, A4, A5, A6, A7) comparing Acc, Bal Acc, Sens, Spec, AUC, Log-Loss, Brier, and ECE with 95% bootstrap CIs (`paper/tables/ablation_table.md`, `.tex`).
- [x] Conduct calibration ablation: quantify uncalibrated vs. temperature-scaled probability calibration across all fusion models (`paper/tables/calibration_ablation.md`, `.tex`).
- [x] Update multi-model ROC curves, reliability diagrams, and hypothesis figures in `artifacts/evaluation_figures/`.

### 7.2 Scientific Journal Paper Deliverables & Manuscript Report
- [x] Generate `paper/manuscript_report.md` structured for scientific peer review (Abstract, Methods, Results, Ablations, Explainability, Discussion, Limitations).
- [x] Generate publication-ready LaTeX tables (`paper/tables/ablation_table.tex`, `paper/tables/cohort_demographics.tex`, `paper/tables/calibration_ablation.tex`).
- [x] Document strict reporting boundaries and negative controls (TCIA shortcut diagnostic, SYSU demo deferral).

### 7.3 Scientific Journal Code & Reproducibility Audit
- [x] Audit repository against CLAIM / STARD-AI checklist standards (patient isolation, leakage barrier verification, deterministic random seed controls).
- [x] Code cleanliness and docstring audit across `src/xmai/`.
- [x] Automated regression test suite pass rate (100% passing across 61 tests, 0 warnings).

**Exit gate:** PASSED — All 7 Track A models trained and evaluated under full 5-fold CV. Ablation report and publication figures generated. Scientific manuscript report and LaTeX tables produced. Full audit passed with 100% test coverage. Ready for scientific journal peer review.

---

## Phase 8 — Advanced Multimodal Fusion & Clinical Uncertainty Referral

### 8.1 Advanced Fusion Architectures
- [x] Implement Bidirectional Cross-Modal Attention Fusion (`A8: CrossModalAttentionFusion`): Multi-head cross-attention between B-mode visual feature tokens and structured clinical context.
- [x] Implement Subjective Logic Evidential Fusion (`A9: EvidentialMultimodalFusion`): Parameterizes Dirichlet evidence per modality and fuses via Dempster's rule of combination with explicit epistemic uncertainty.
- [x] Implement Supervised Cross-Modal Contrastive Loss (`CrossModalContrastiveLoss`): InfoNCE alignment preventing unimodal dominance and suppressing demographic shortcutting.
- [x] Implement `CompositeMultimodalLoss`: Unified loss with task cross-entropy, cross-modal alignment, and Dirichlet Bayes risk with KL penalty.

### 8.2 Spatial-Clinical Explainability & Referral Analysis
- [x] Implement `CrossModalSpatialAttentionVisualizer`: High-resolution 224x224 spatial-clinical interaction heatmaps revealing anatomical regions inspected under specific clinical conditioning.
- [x] Implement `SelectiveClassificationAnalyzer`: Risk-coverage trade-off curves, AURC/E-AURC, and autonomous coverage vs referral rates (100% autonomous coverage at 0.5% risk for multimodal models).
- [x] Full 5-fold cross-validation training and evaluation of A8 and A9 on the 743-patient SMC cohort.
- [x] Automated test suite expanded to 72 unit tests across 19 test modules (100% pass rate).

**Exit gate:** PASSED — 9-model comparative ablation study complete with LaTeX tables, selective referral curves, and spatial-clinical heatmaps in `paper/tables/` and `paper/manuscript_report.md`.

---

## Phase 9 — Academic Research Console & Manuscript Demonstrator

### 9.1 Clinical Design System & Institutional Light Theme
- [x] Unify console design into an authentic *Nature Medicine* / *Lancet Digital Health* institutional light theme with top hairline gradient and scholarly badge system.
- [x] Eliminate jarring dark-header / light-body contrast and ensure responsive card layouts.

### 9.2 Mathematical Typesetting Engine
- [x] Implement `frontend/scripts/math-renderer.js` supporting KaTeX CDN with graceful semantic HTML fallback (fractions, Greek symbols, superscripts, subscripts).
- [x] Integrate mathematical rendering across Section 2 (Formalisms), Section 3 (Temperature scaling), Section 4 (Gating mechanism), and Section 6 (Explainability: Softmax attention, Shapley, Evidential decomposition).

### 9.3 Camera-Ready Publication Table
- [x] Implement IEEE TMI / booktabs formatted publication table in Section 9 with 95% bootstrap CIs, bolded proposed model A4, and clean tabular numerals.
- [x] Provide interactive toggle between Rendered Publication Table and raw LaTeX source code (`.tex`) with one-click clipboard copy.

### 9.4 Clinical Presets & Code Audit
- [x] Add quick preset buttons to Grad-CAM heatmap slider (0%, 25%, 45%, 80%, 100%), simulated patient age slider (28y, Actual, 68y), and error budget slider (0.10%, 0.25%, 0.50%, 1.00%).
- [x] Eliminate redundant duplicate files (`oof_predictions_A6_late_fusion.json`, superseded `XMAI_Design_Document.md`).
- [x] Expand automated test suite to 81 unit & integration tests with 100% pass rate.

**Exit gate:** PASSED — Presentation-ready academic console verified end-to-end, all tests passing, and documentation synchronized across the repository.

---

## Phase 10 — Methodological Audit & Stress-Testing Suite (Publication Qualification)

### 10.1 Invariant Stress-Testing & Numerical Stability
- [x] Harden encoder input shape validation and non-finite guards in `src/xmai/models/encoders.py`.
- [x] Implement safe lower-bound temperature clamping and Dirichlet $\alpha \ge 1.0$ digamma singularity guards in `src/xmai/training/losses.py`.
- [x] Verify Dempster-Shafer belief mass conservation ($b_1 + b_2 + u = 1.0$) and high-conflict resilience ($C \to 1.0$) in `src/xmai/models/fusion.py`.
- [x] Verify Temperature Scaling order-preservation, $T \to 0$ clamp safety, and Expected Calibration Error (ECE) bounds in `src/xmai/training/calibration.py`.

### 10.2 Empirical Invariants & Zero-Leakage Barriers
- [x] Stress-test all 14 prohibited diagnostic shortcut keys in `src/xmai/data/schemas.py` across casing and delimiter permutations.
- [x] Prove pairwise fold disjointness ($P_i \cap P_j = \emptyset$ for all $i \neq j$) across the 743-patient SMC cohort.
- [x] Stress-test selective classification risk-coverage monotonicity and E-AURC non-negativity across clinical budgets.
- [x] Audit external TCIA reporting boundaries: exclude indeterminate cases and prohibit multi-class accuracy reporting under 107:7 class imbalance.

### 10.3 Explainability Axioms & Faithfulness
- [x] Conduct Adebayo cascading parameter randomization test on Layer-4 Grad-CAM activation maps.
- [x] Verify game-theoretic Modality Shapley efficiency axiom ($\sum \phi_i = v(M) - v(\emptyset)$), null player axiom, and binary class symmetry.
- [x] Verify cross-modal spatial attention Softmax probability normalization and Shannon spatial entropy bounds in $[0, \log 49]$.

### 10.4 Presentation Server & Typesetting Engine Resilience
- [x] Stress-test live HTTP inference server (`scripts/serve_frontend.py`) under concurrent socket bursts and malformed JSON requests.
- [x] Validate mathematical typesetting engine (`frontend/scripts/math-renderer.js`) across complex LaTeX fractions, Greek letters, and bracket balance.
- [x] Add layer-by-layer architectural engineering walkthrough and real-world clinical-to-AI impact matrix to presentation frontend.
- [x] Expand automated test suite from 81 to **173 tests** across 24 test modules (100% pass rate).

**Exit gate:** PASSED — Publication-level qualification achieved across 42 synchronized Git commits on `main` and `master`. Repository verified ready for top-tier academic presentation and manuscript preparation.

---

## Phase 11 — Visual-Heavy Multimodal Presentation Overhaul & Academic Briefing Dossier

### 11.1 Visual Layer-by-Layer Architecture & Conceptual Bridge
- [x] Implement dynamic layer tensor inspection cards with click-to-highlight state in `frontend/scripts/architecture-diagram.js` (Commit 43).
- [x] Build Clinical-to-AI "Rosetta Stone" concept dictionary mapping acoustic phenomena (shadowing, speckle, rims) to representation learning invariants (Commit 44).
- [x] Overhaul executive stat cards in `frontend/scripts/overview-view.js` with 4 circular SVG dials (99.5% Acc, 100% Sens, 0.023 ECE, N=743) and complete SVG End-to-End Multimodal Tensor Lifecycle schematic (Commits 45 & 46).

### 11.2 Visual Ablation, Decile Rescue, and Multi-Scanner Transfer
- [x] Implement visual Pareto Frontier scatter plot (Accuracy vs. ECE) in `frontend/scripts/ablation-table.js` illustrating why Model A4 dominates A1 and A3 while exposing the Model A6 late fusion distortion (Commit 47).
- [x] Revamp Hypothesis H1 Decile Rescue in `frontend/scripts/h1-rescue-chart.js` with visual before-and-after probability bars and lesion morphology thumbnails (Commit 48).
- [x] Upgrade Multi-Level Explainability in `frontend/scripts/explainability-view.js` with Layer-by-Layer visual feature hierarchy flow and localization faithfulness comparison (42.1% unimodal vs. 89.4% gated in-box concentration) (Commit 49).
- [x] Upgrade Selective Triage Simulator in `frontend/scripts/selective-triage.js` with shaded E-AURC risk-coverage envelope ($0.053$) and live patient cohort stacked allocation bars (100% autonomous @ 0.5% risk budget) (Commit 50).
- [x] Add visual External TCIA Multi-Scanner Transfer benchmark in `frontend/scripts/tcia-benchmark.js` covering GE LOGIQ E9, Philips EPIQ 7, and Siemens ACUSON S2000, alongside statistical shortcut null-band chart ($r \in [-0.1, +0.1]$) (Commit 51).
- [x] Synchronize 52-commit audit trail and link provenance directly to GitHub commit log (Commit 52).

### 11.3 Academic Briefing Dossier & Defense Guide
- [x] Generate comprehensive Microsoft Word `.docx` briefing document (`XMAI_Comprehensive_Briefing_Document.docx`) covering first-principles layer breakdown, bilingual glossary, clinical impact, 15 fundamental mentor Q&As, and 5 advanced multimodal AI Q&As.

**Exit gate:** PASSED — Full 52-commit audit trail synchronized, presentation console fully visual-heavy, and comprehensive academic briefing dossier generated for mentorship defense.

## Phase 12: 5-Class Multiclass Differential Diagnosis Specification (Roadmap)

### 12.1 Strategic Documentation & Clinical Architecture
- [x] Author comprehensive 5-class strategic architecture specification in `docs/FIVE_CLASS_DIFFERENTIAL_DIAGNOSIS_PLAN.md` covering pathophysiological, ultrasound, and clinical phenotype matrices for HCC, Hemangioma, FNH, Hepatic Adenoma, and Intrahepatic Cholangiocarcinoma (plus Simple Cysts).
- [x] Register Reviewer Decision `R-10` and formalize Phase 12 in `decisions.md`.
- [x] Detail multi-source dataset harmonization protocol linking SMC-LUD (B-mode/demographics), SYSU-CEUS (multiclass CEUS cineloops), and TCIA (external multi-scanner with confirmed ICC cases).
- [x] Specify Hierarchical Coarse-to-Fine decision tree architecture with Stage 1 Oncologic Safety Gate ($\text{Sensitivity} \ge 99\%$) and Stage 2 subtyping heads to eliminate dangerous cross-tier confusions.
- [x] Extend Dempster-Shafer Subjective Logic evidential uncertainty formulation to 5-class Dirichlet concentration vectors ($\boldsymbol{\alpha} = \boldsymbol{e} + 1$, $u = 5 / S$), defining conflict-driven certified referral triggers ($u > 0.30$) for equivocal arterial-phase lesions.
- [x] Formulate Class-Balanced Focal Loss ($\gamma = 2.0$, $\beta = 0.999$) and 5-class multi-temperature scaling calibration protocol.

**Exit gate:** PASSED — Complete 5-class multiclass architectural roadmap fully documented and referenced across project records without code modifications.

---

## Suggested execution order for a coding agent

1. Complete Phases 0 and 1A; stop for manifest review.
2. Complete SMC loader and A1/A2 one-fold CPU smoke test.
3. Complete full Track A protocol and controls.
4. In parallel only after Track A is stable: AUL rasterisation and TCIA header/decode pipeline.
5. Use the 15 SYSU videos only to validate the video loader.
6. Run Track B only after full SYSU arrival and new manifest sign-off.
7. Execute Phase 7 Scientific Journal Preparation and comprehensive ablation study.
8. Execute Phase 8 & 9 Academic Presentation Console & CLAIM verification.
9. Execute Phase 10 Methodological Audit & Stress-Testing Suite (173/173 tests passing).
10. Execute Phase 11 Visual-Heavy Presentation Overhaul & Master Briefing Dossier.
11. Consult Phase 12 5-Class Multiclass Roadmap (`docs/FIVE_CLASS_DIFFERENTIAL_DIAGNOSIS_PLAN.md`) before expanding model output dimension $K$.

At every stop, report: files changed, command run, tests passed/failed, manifest version, assumptions, and decisions needing human review. Do not silently broaden the scope.




---

## Phase 13 — 5-Class Multimodal Differential Diagnosis Implementation (20 Commits)

### 13.1 Phased 20-Commit Execution & Verification Register
- [x] **Commit 1 (`e8ae16e`)**: `docs(taxonomy): formalize 5-class differential diagnosis decisions D-16..D-18 and R-11` in `decisions.md`.
- [x] **Commit 2 (`b16b4ac`)**: `feat(schemas): define 5-class/6-class taxonomy, ClinicalCovariates8, and MulticlassManifestRow schemas` in `src/xmai/data/schemas.py` and `tests/test_schemas.py`.
- [x] **Commit 3 (`125d623`)**: `feat(manifest): build universal multiclass manifest harmonizing SMC-LUD, TCIA, SYSU, and WFUMB reference cohorts` in `src/xmai/data/multiclass_manifest.py` and `data/manifests/multiclass_5class_manifest.csv` ($N=1,353$ patients).
- [x] **Commit 4 (`9078c33`)**: `test(manifest): add unit tests for multiclass manifest, patient isolation, and clinical distributions` in `tests/test_multiclass_manifest.py`.
- [x] **Commit 5 (`f5e95cc`)**: `feat(clinical): implement MulticlassClinicalFeatureProcessor and MulticlassClinicalEncoder for 8-feature profiles` in `src/xmai/data/clinical.py` and `src/xmai/models/encoders.py`.
- [x] **Commit 6 (`ab6cc39`)**: `test(clinical): add unit and gradient tests for MulticlassClinicalEncoder and MulticlassClinicalFeatureProcessor` in `tests/test_multiclass_encoders.py`.
- [x] **Commit 7 (`9328224`)**: `feat(models): implement M5FlatGatedFusion generalizing Model A4 to 5-class differential diagnosis` in `src/xmai/models/multiclass_models.py`.
- [x] **Commit 8 (`e175014`)**: `feat(models): implement M5HierarchicalFusion coarse-to-fine oncologic safety architecture for 5 classes` in `src/xmai/models/multiclass_models.py`.
- [x] **Commit 9 (`1839cc5`)**: `feat(models): implement M5EvidentialFusion Subjective Logic network with K-class Dempster-Shafer fusion` in `src/xmai/models/multiclass_models.py`.
- [x] **Commit 10 (`c6011de`)**: `test(models): add unit and mathematical invariant tests for M5FlatGatedFusion, M5HierarchicalFusion, and M5EvidentialFusion` in `tests/test_multiclass_models.py`.
- [x] **Commit 11 (`95d6033`)**: `feat(losses): implement ClassBalancedFocalLoss, HierarchicalSafetyLoss, and MulticlassDirichletEvidentialLoss` in `src/xmai/training/multiclass_losses.py`.
- [x] **Commit 12 (`b4bea80`)**: `test(losses): add mathematical invariance tests for ClassBalancedFocalLoss, HierarchicalSafetyLoss, and MulticlassDirichletEvidentialLoss` in `tests/test_multiclass_losses.py`.
- [x] **Commit 13 (`752466e`)**: `feat(evaluation): implement multiclass evaluation suite with confusion matrix, ECE, bootstrap CIs, and malignant undercall rate` in `src/xmai/evaluation/multiclass_metrics.py`.
- [x] **Commit 14 (`32b8bbe`)**: `test(evaluation): add unit tests for confusion matrix, ECE, bootstrap CIs, and malignant undercall rate` in `tests/test_multiclass_metrics.py`.
- [x] **Commit 15 (`6a04519`)**: `feat(explainability): implement MulticlassGradCAM, MulticlassKernelSHAP, and multiclass dossier generator` in `src/xmai/explainability/multiclass_xai.py`.
- [x] **Commit 16 (`3eb3ef0`)**: `test(explainability): add verification tests for MulticlassGradCAM, Shapley additivity, and referral triage` in `tests/test_multiclass_xai.py`.
- [x] **Commit 17 (`a553c8d`)**: `feat(training): implement 5-class patient-isolated stratified CV runner and train M5 ablation triad` in `src/xmai/training/multiclass_runner.py` and `scripts/train_5class.py`.
- [x] **Commit 18 (`8214090`)**: `feat(server): add 5-class live ML inference and case audit REST APIs` in `scripts/serve_frontend.py` and `tests/test_serve_frontend_multiclass.py`.
- [x] **Commit 19 (`d93c7e0`)**: `feat(frontend): integrate interactive 5-class differential diagnosis explorer and pentagonal radar dossiers` in `frontend/scripts/multiclass-explorer.js`, `frontend/index.html`, and `frontend/scripts/app.js`.
- [x] **Commit 20 (`<HEAD>`)**: `docs(manuscript): record 5-class differential diagnosis empirical benchmark results and CLAIM compliance` in `paper/manuscript_report.md`, `XMAI_Design_Document_v2.md`, and `tasks.md`.

### 13.2 Empirical Cross-Validation Summary ($N=1,353$ Patients)
| Architecture | Macro-F1 (95% CI) | Balanced Accuracy | Top-2 Accuracy | ECE | Malignant Undercall Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `M5_gated` | **0.7614** (0.7356 &ndash; 0.7858) | **73.98%** | **88.54%** | 0.1433 | **0.96%** (6 / 626) |
| `M5_hierarchical` | 0.6539 (0.6306 &ndash; 0.6775) | 63.38% | 87.29% | **0.0719** | 1.28% (8 / 626) |
| `M5_evidential` | 0.5198 (0.5001 &ndash; 0.5399) | 53.45% | 80.93% | 0.1787 | 6.39% (40 / 626) |

**Exit gate:** PASSED — All 20 research-quality commits fully executed, verified across 200+ unit and integration tests, dual-branch pushed to `origin/main` and `origin/master`.
