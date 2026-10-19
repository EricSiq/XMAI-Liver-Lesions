# Track A Multimodal Baseline & Fusion Study Summary

**Cohort:** SMC-LUD Clean Cohort (743 patients: 421 HCC, 322 Hemangioma)
**Evaluation:** Repeated Patient-Stratified 5-Fold Cross-Validation
**Aggregation:** Arithmetic Mean of Calibrated Per-Image Class Probabilities

## Overall Model Comparison

| Model   | Accuracy (95% CI)    | Balanced Acc (95% CI)   |   Sensitivity |   Specificity | AUC (95% CI)         |   Log-Loss |   Brier |   ECE |
|:--------|:---------------------|:------------------------|--------------:|--------------:|:---------------------|-----------:|--------:|------:|
| A1      | 0.993 [0.987, 0.999] | 0.993 [0.986, 0.998]    |         0.998 |         0.988 | 1.000 [1.000, 1.000] |      0.032 |   0.005 | 0.025 |
| A2      | 0.766 [0.735, 0.795] | 0.761 [0.729, 0.791]    |         0.796 |         0.727 | 0.826 [0.794, 0.856] |      0.516 |   0.168 | 0.078 |
| A3      | 0.993 [0.987, 0.999] | 0.993 [0.986, 0.998]    |         0.995 |         0.991 | 1.000 [0.999, 1.000] |      0.037 |   0.006 | 0.026 |
| A4      | 0.996 [0.991, 1.000] | 0.995 [0.989, 1.000]    |         1     |         0.991 | 1.000 [1.000, 1.000] |      0.033 |   0.004 | 0.025 |
| A5      | 0.996 [0.991, 1.000] | 0.995 [0.989, 1.000]    |         1     |         0.991 | 1.000 [0.999, 1.000] |      0.033 |   0.005 | 0.023 |
| A7      | 0.992 [0.985, 0.997] | 0.991 [0.984, 0.997]    |         0.995 |         0.988 | 1.000 [1.000, 1.000] |      0.033 |   0.005 | 0.023 |
| A6      | 0.996 [0.991, 1.000] | 0.996 [0.990, 1.000]    |         0.998 |         0.994 | 0.999 [0.997, 1.000] |      0.228 |   0.049 | 0.191 |

## Hypothesis H1 Evaluation: Gated Fusion (A4) vs. B-Mode Only (A1)

- **Rescue Count (A4 correct, A1 error):** 3 patients
- **Harm Count (A4 error, A1 correct):** 1 patients
- **Net Gain:** +2 patients
- **McNemar Discordance Test:** Discordant pairs = 4 (p-value: 0.6250)
- **Paired Balanced Accuracy Difference:** +0.0027 (95% CI: [-0.0030, +0.0089], p=0.4230)

### Low-Margin Decile Distribution (Hypothesis H1)
- **Low-Margin Decile Rescues:** 3 / 75 (Net Gain: +2)
- **High-Margin Rescues:** 0 / 668 (Net Gain: +0)
- **Concentration of Rescues in Low-Margin Decile:** 100.0%
