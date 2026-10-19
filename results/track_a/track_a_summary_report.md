# Track A Multimodal Baseline & Fusion Study Summary

**Cohort:** SMC-LUD Clean Cohort (743 patients: 421 HCC, 322 Hemangioma)
**Evaluation:** Repeated Patient-Stratified 5-Fold Cross-Validation
**Aggregation:** Arithmetic Mean of Calibrated Per-Image Class Probabilities

## Overall Model Comparison

| Model   | Accuracy (95% CI)    | Balanced Acc (95% CI)   |   Sensitivity |   Specificity | AUC (95% CI)         |   Log-Loss |   Brier |   ECE |
|:--------|:---------------------|:------------------------|--------------:|--------------:|:---------------------|-----------:|--------:|------:|
| A1      | 0.987 [0.966, 1.000] | 0.986 [0.963, 1.000]    |         0.988 |         0.984 | 1.000 [0.998, 1.000] |      0.043 |   0.009 | 0.03  |
| A2      | 0.785 [0.718, 0.846] | 0.787 [0.719, 0.850]    |         0.776 |         0.797 | 0.884 [0.830, 0.932] |      0.546 |   0.179 | 0.214 |
| A4      | 0.980 [0.953, 1.000] | 0.977 [0.947, 1.000]    |         1     |         0.953 | 0.999 [0.997, 1.000] |      0.172 |   0.033 | 0.139 |
| A6      | 0.987 [0.966, 1.000] | 0.986 [0.963, 1.000]    |         0.988 |         0.984 | 0.999 [0.997, 1.000] |      0.258 |   0.055 | 0.208 |

## Hypothesis H1 Evaluation: Gated Fusion (A4) vs. B-Mode Only (A1)

- **Rescue Count (A4 correct, A1 error):** 1 patients
- **Harm Count (A4 error, A1 correct):** 2 patients
- **Net Gain:** -1 patients
- **McNemar Discordance Test:** Discordant pairs = 3 (p-value: 1.0000)
- **Paired Balanced Accuracy Difference:** -0.0099 (95% CI: [-0.0360, +0.0118], p=0.4670)

### Low-Margin Decile Distribution (Hypothesis H1)
- **Low-Margin Decile Rescues:** 1 / 15 (Net Gain: +0)
- **High-Margin Rescues:** 0 / 134 (Net Gain: -1)
- **Concentration of Rescues in Low-Margin Decile:** 100.0%
