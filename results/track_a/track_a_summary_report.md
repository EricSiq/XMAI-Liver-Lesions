# Track A Multimodal Baseline & Fusion Study Summary

**Cohort:** SMC-LUD Clean Cohort (743 patients: 421 HCC, 322 Hemangioma)
**Evaluation:** Repeated Patient-Stratified 5-Fold Cross-Validation
**Aggregation:** Arithmetic Mean of Calibrated Per-Image Class Probabilities

## Overall Model Comparison

| Model   | Accuracy (95% CI)    | Balanced Acc (95% CI)   |   Sensitivity |   Specificity | AUC (95% CI)         |   Log-Loss |   Brier |   ECE |
|:--------|:---------------------|:------------------------|--------------:|--------------:|:---------------------|-----------:|--------:|------:|
| A8      | 0.995 [0.989, 0.999] | 0.995 [0.989, 0.999]    |         0.995 |         0.994 | 0.998 [0.995, 1.000] |      0.046 |   0.008 | 0.025 |
| A9      | 0.992 [0.984, 0.997] | 0.991 [0.983, 0.997]    |         0.998 |         0.984 | 0.998 [0.995, 1.000] |      0.17  |   0.027 | 0.141 |
