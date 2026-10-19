# Track C External Validation: TCIA Liver Ultrasound Cohort

**Cohort Source:** The Cancer Imaging Archive (TCIA) Liver-Ultrasound-Detection
**Model Evaluated:** Pretrained B-mode Image-Only Model (ResNet-18)

## 1. Definitive HCC Sensitivity (Primary Endpoint)
- **Total HCC Patients Evaluated:** 107
- **HCC Detected by Model:** 107
- **HCC Sensitivity:** 100.00%
- **Wilson 95% Confidence Interval:** [96.53%, 100.00%]

## 2. Definitive Non-HCC Descriptive Evaluation (n=7)

| patient_id   | harmonized_diagnosis   |   prob_HCC | pred_label   | correct   |
|:-------------|:-----------------------|-----------:|:-------------|:----------|
| LiverUS-13   | ICC                    |     0.9765 | HCC          | False     |
| LiverUS-29   | BENIGN_UNSPECIFIED     |     0.9809 | HCC          | False     |
| LiverUS-34   | BENIGN_UNSPECIFIED     |     0.9499 | HCC          | False     |
| LiverUS-84   | ICC                    |     0.8999 | HCC          | False     |
| LiverUS-86   | BENIGN_UNSPECIFIED     |     0.9625 | HCC          | False     |
| LiverUS-91   | ICC                    |     0.9771 | HCC          | False     |
| LiverUS-92   | BENIGN_ABSCESS         |     0.985  | HCC          | False     |

## 3. Acquisition Shortcut Diagnostic
- **Correlation (Dual-Panel Layout vs. HCC Diagnosis):** -0.0749
- *Interpretation:* Minimal correlation indicates dual-panel layout does not function as an acquisition shortcut for malignancy.

## 4. Reporting Boundary Safeguards
> [!IMPORTANT]
> Multiclass accuracy, specificities, and scanner-generalisation claims are strictly disallowed due to cohort asymmetry (107 HCC vs 7 definitive non-HCC).
> - Excluded Indeterminate/Mixed-Lesion Cases: 0 patients.
