# Track A Multimodal Baseline & Fusion Study Summary

**Cohort:** SMC-LUD Clean Cohort (743 patients: 421 HCC, 322 Hemangioma)
**Evaluation:** Repeated Patient-Stratified 5-Fold Cross-Validation
**Aggregation:** Arithmetic Mean of Calibrated Per-Image Class Probabilities

## Overall Model Comparison

| Model   | Accuracy (95% CI)    | Balanced Acc (95% CI)   |   Sensitivity |   Specificity | AUC (95% CI)         |   Log-Loss |   Brier |   ECE |
|:--------|:---------------------|:------------------------|--------------:|--------------:|:---------------------|-----------:|--------:|------:|
| A3      | 0.993 [0.987, 0.999] | 0.993 [0.986, 0.998]    |         0.995 |         0.991 | 1.000 [0.999, 1.000] |      0.037 |   0.006 | 0.025 |
| A5      | 0.996 [0.991, 1.000] | 0.995 [0.989, 1.000]    |         1     |         0.991 | 1.000 [0.999, 1.000] |      0.033 |   0.005 | 0.023 |
