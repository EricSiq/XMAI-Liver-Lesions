# Strategic Engineering & Clinical Plan: 5-Class Focal Liver Lesion Differential Diagnosis

**Document Status:** Architectural Specification & Roadmap  
**Target Milestone:** XMAI Phase III Clinical Multi-Classification Expansion  
**Compliance Standards:** CLAIM 2020, STARD-AI 2020, WFUMB/EFSUMB Clinical Guidelines  
**Scope:** Architectural, Clinical, Data-Governance, and Mathematical Specification (Documentation Only)

---

## 1. Executive Summary & Clinical Oncology Dilemma

In clinical hepatology, binary classification (**Hepatocellular Carcinoma [HCC]** vs. **Cavernous Hemangioma [Hem]**) represents only the initial triage step. In routine ultrasound screening and incidental liver lesion workups, sonographers encounter a heterogeneous spectrum of benign and malignant focal liver lesions (FLLs). 

Misclassifying an aggressive malignancy as benign leads to delayed surgical intervention and catastrophic oncologic outcomes. Conversely, misclassifying a benign lesion as malignant causes unnecessary patient anxiety, high-cost magnetic resonance imaging (MRI), and risky invasive percutaneous needle biopsies (with associated hemorrhage and tumor-tracking risks).

This specification details the end-to-end strategy to scale XMAI from binary triage to the definitive **5-Class Differential Diagnosis Benchmark**:

1. **Hepatocellular Carcinoma (HCC)** *(Primary Malignant - Hepatocellular origin)*
2. **Cavernous Hemangioma (Hem)** *(Benign - Mesenchymal / vascular origin)*
3. **Focal Nodular Hyperplasia (FNH)** *(Benign - Non-neoplastic hyperplastic response)*
4. **Hepatic Adenoma / Hepatocellular Adenoma (HCA)** *(Benign - Epithelial neoplasm with hemorrhage & malignant transformation risk)*
5. **Intrahepatic Cholangiocarcinoma (ICC)** *(Primary Malignant - Biliary epithelial origin)*  
*(Note: **Simple Hepatic Cyst** is incorporated as the fundamental non-neoplastic, anechoic benign reference benchmark).*

```
                              ┌────────────────────────────────────────┐
                              │  Focal Liver Lesion (FLL) Presentation │
                              └───────────────────┬────────────────────┘
                                                  │
                 ┌────────────────────────────────┴────────────────────────────────┐
                 ▼                                                                 ▼
    ┌──────────────────────────┐                                     ┌──────────────────────────┐
    │     Malignant Lesions    │                                     │      Benign Lesions      │
    └────────────┬─────────────┘                                     └────────────┬─────────────┘
          ┌──────┴──────┐                                           ┌─────────────┼─────────────┐
          ▼             ▼                                           ▼             ▼             ▼
   ┌─────────────┐┌─────────────┐                            ┌─────────────┐┌─────────────┐┌─────────────┐
   │     HCC     ││     ICC     │                            │ Hemangioma  ││     FNH     ││   Adenoma   │
   │ Hepatocell. ││ Cholangio. │                            │ Mesenchymal ││ Hyperplasia││ Premalignant│
   └─────────────┘└─────────────┘                            └─────────────┘└─────────────┘└─────────────┘
```

---

## 2. Pathophysiological, Ultrasound & Clinical Phenotype Matrix

Differentiating these 5 entities on single-frame B-mode ultrasound alone is notoriously difficult due to overlapping acoustic echogenicity. Differentiating them reliably requires **multimodal fusion** combining B-mode tissue acoustic texture, dynamic contrast-enhanced ultrasound (CEUS) wash-in/wash-out kinetics, and patient clinical-demographic risk covariates.

| Class | Pathophysiology & Etiology | B-Mode Ultrasound Morphology | CEUS Perfusion Dynamics (Arterial $\to$ Portal $\to$ Late) | Key Clinical Covariates | Diagnostic Pitfall |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. HCC** | Malignant transformation of hepatocytes, usually in cirrhotic or chronic hepatitis background. | Hypoechoic or mixed mosaic architecture, hypoechoic acoustic halo, lateral shadow. | **Early arterial hyperenhancement** (chaotic/diffuse) $\to$ **late mild washout** (>60s). | Age >50, Male (4:1), Cirrhosis, HBV/HCV (+), elevated serum AFP. | Atypical well-differentiated HCC can show delayed/slow washout, mimicking benign FNH. |
| **2. Hemangioma** | Congenital vascular malformation of ectatic blood-filled cavernous spaces. | Classic uniform hyperechoic mass, well-defined geographic margins, posterior enhancement. | **Peripheral nodular discontinuous puddle enhancement** $\to$ slow progressive centripetal fill-in $\to$ persistent iso-enhancement (no washout). | Age 30–60, Female predilection (3:1), non-cirrhotic, normal tumor markers. | Thrombosed, sclerosed, or rapid-filling (high-flow) hemangiomas show atypical mixed echogenicity. |
| **3. FNH** | Hyperplastic response to a pre-existing congenital arterial malformation. | Isoechoic to mildly hypoechoic, central stellate fibrous scar visible in ~30% of scans. | **Rapid arterial spoke-wheel / centrifugal filling** from center $\to$ sustained hyper/iso-enhancement across portal/late phases (**strictly NO washout**). | Young females (age 20–45), asymptomatic, non-cirrhotic, normal liver enzymes. | Central scar is often undetectable on small (<3cm) lesions, appearing identical to adenoma or well-diff HCC. |
| **4. Hepatic Adenoma (HCA)** | Monoclonal benign epithelial neoplasm; carries 10–30% rupture risk and 5% malignant transformation to HCC. | Isoechoic or mixed echogenicity with internal hemorrhage or fat vacuoles. | **Rapid, diffuse arterial hyperenhancement** $\to$ subtle or slow late washout in inflammatory/beta-catenin subtypes. | Females age 20–45, oral contraceptive use (>5 yrs), anabolic steroid use, metabolic syndrome (NAFLD/MASH). | Frequently mimics HCC or FNH due to arterial hypervascularity and equivocal late-phase washout. |
| **5. Cholangiocarcinoma (ICC)** | Highly aggressive primary biliary adenocarcinoma arising in intrahepatic bile ducts. | Lobulated hypoechoic mass, irregular indistinct margins, capsular retraction, satellite nodules. | **Peripheral rim-like arterial hyperenhancement** $\to$ **early and marked washout** (<60s) $\to$ marked hypoperfusion in late phase. | Older adults (age >60), non-cirrhotic or primary sclerosing cholangitis (PSC), elevated CA 19-9. | Peripheral rim enhancement can be mistaken for peripheral puddle enhancement of atypical hemangioma. |
| **Benchmark: Simple Cyst** | Congenital ductal malformation lined by cuboidal biliary epithelium. | Strictly anechoic (jet black), paper-thin imperceptible wall, sharp posterior acoustic enhancement. | **Completely non-enhancing** across all phases (arterial, portal, late) with zero microbubble transit. | Any age, benign, normal liver markers. | Complex hemorrhagic or infected cysts may develop internal septa/debris resembling necrotic cystic HCC. |

---

## 3. Multi-Source Dataset Harmonization Strategy

Because no single public medical institution provides all 5 classes simultaneously with multi-modal B-mode, CEUS cine, and clinical features, XMAI employs a **federated multi-source harmonization protocol**:

```
                                  DATASET INTEGRATION PIPELINE
 ┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
 │   SMC-LUD Repository    │   │     SYSU-CEUS Cohort    │   │     TCIA Public Cohort  │
 │  (n=743 Clean B-mode)   │   │   (n=353 Multiclass)    │   │   (n=120 CEUS & DICOM)  │
 └────────────┬────────────┘   └────────────┬────────────┘   └────────────┬────────────┘
              │                             │                             │
              ▼                             ▼                             ▼
   [HCC (421), Hem (322)]        [HCC, Hem, FNH, Adenoma]       [HCC (107), ICC, Cysts]
              │                             │                             │
              └─────────────────────────────┼─────────────────────────────┘
                                            ▼
                          ┌───────────────────────────────────┐
                          │ Universal Harmonization Manifest   │
                          │ - Strict Zero-Leakage Patient IDs │
                          │ - Caliper Removal & Noise Clean   │
                          │ - Standardized 5-Class Taxonomy   │
                          └───────────────────────────────────┘
```

### 3.1 Source Breakdown & Target Sample Size Targets
1. **SMC-LUD (Samsung Medical Center):**
   * Primary high-volume baseline for HCC ($n = 421$) and Hemangioma ($n = 322$).
   * Supplies paired age, sex, and clean ultrasound arrays.
2. **SYSU-CEUS (Sun Yat-sen University First Affiliated Hospital):**
   * Supplies verified CEUS video cineloops across benign and malignant categories: HCC, Hemangioma, and crucially **Focal Nodular Hyperplasia (FNH)** and **Hepatic Adenoma**.
   * Provides time-intensity contrast kinetics across Arterial, Portal, and Late phases.
3. **TCIA (The Cancer Imaging Archive - B-mode and CEUS Liver):**
   * Verified independent external test set containing 120 patients.
   * Manifest inspection confirms inclusion of confirmed **Intrahepatic Cholangiocarcinoma (`LiverUS-13`)**, non-enhancing simple cysts, and microwave-ablated indeterminate cases (`LiverUS-23`).
4. **Target Balanced Expansion Cohort:**
   * Target minimum cohort size: $N \ge 1,200$ patients across the 5 target classes.
   * Stratified patient-level partition: 70% Train ($n=840$), 15% Validation ($n=180$), 15% Test ($n=180$), with zero patient overlap across folds.

---

## 4. Multi-Modal Feature Representation Specifications

To support 5-class discrimination, the feature spaces must expand across all three input modalities:

### 4.1 Modality 1: B-Mode Acoustic Morphological Representation ($z_B \in \mathbb{R}^{256}$)
* **Backbone:** ResNet-18 or ConvNeXt-Femto initialized with ImageNet weights and fine-tuned with acoustic augmentation.
* **Morphological Feature Objectives:**
  * Acoustic margin contour: Smooth circumscription (Hemangioma/Cyst) vs. irregular infiltrating borders (HCC/ICC).
  * Acoustic enhancement artifacts: Posterior acoustic enhancement (Cyst/Hemangioma) vs. acoustic shadow/attenuation (HCC).
  * Internal echogenicity: Hyperechoic (Hemangioma), hypoechoic with peripheral halo (HCC), central stellate hypoechoic scar (FNH).

### 4.2 Modality 2: Spatiotemporal Contrast Dynamics ($z_C \in \mathbb{R}^{256}$)
* **Essential Role:** Distinguishing FNH, Adenoma, and ICC from HCC requires dynamic temporal microbubble transit.
* **Architecture:** 3D Convolutional Network (Conv3D) or Video Swin Transformer operating on 3 synchronized phase clips:
  * Phase 1: Arterial early influx ($t = 10\text{--}30\text{ s}$).
  * Phase 2: Portal venous distribution ($t = 30\text{--}120\text{ s}$).
  * Phase 3: Late parenchymal clearance ($t = 120\text{--}360\text{ s}$).
* **Temporal Attention Pooling:** Calculates temporal attention weights $\beta_t$ across the cineloop to pinpoint the exact second of vascular washout.

### 4.3 Modality 3: Expanded Clinical Covariate Vector ($z_T \in \mathbb{R}^{128}$)
The clinical input expands from 2 variables to an 8-variable structured oncology risk profile:
1. `Age` (Continuous, Z-score normalized)
2. `Sex` (Binary: Male / Female)
3. `Cirrhosis Background` (Binary: Present / Absent) — *Crucial: HCC develops in cirrhotic livers; FNH and Adenoma occur almost exclusively in non-cirrhotic parenchyma.*
4. `Hepatitis B / C Serology` (Categorical: Negative, Active HBV, Active HCV)
5. `Oral Contraceptive Use` (Continuous/Binary: Duration $\ge 5$ years) — *Specific strong prior for Hepatic Adenoma and FNH.*
6. `Metabolic Syndrome / NAFLD` (Binary: Present / Absent) — *Emerging driver for non-cirrhotic HCC and inflammatory Adenoma.*
7. `Serum Alpha-Fetoprotein (AFP)` (Continuous, log-transformed) — *Biomarker for HCC.*
8. `Serum CA 19-9` (Continuous, log-transformed) — *Biomarker for Cholangiocarcinoma.*

---

## 5. Architectural Designs for 5-Class Multimodal Fusion

### Approach A: Flat Gated Multimodal Fusion (Direct $K=5$ Softmax)
Direct generalization of Model A4:
1. Modality encoders generate representations: $z_B \in \mathbb{R}^{256}$, $z_C \in \mathbb{R}^{256}$, $z_T \in \mathbb{R}^{128}$.
2. Gating network computes tri-modal weights:
   $$[\alpha_B, \alpha_C, \alpha_T] = \text{Softmax}\left( W_g [z_B; z_C; z_T] + \text{mask\_penalty} \right)$$
3. Fused embedding $z_F = \alpha_B h_B + \alpha_C h_C + \alpha_T h_T \in \mathbb{R}^{256}$.
4. Classification head: $\text{Linear}(256 \to 5)$ with Temperature Scaling ($T$).

### Approach B (Recommended): Hierarchical Coarse-to-Fine Multimodal Decision Tree
Direct 5-class classification risks dangerous inter-tier confusions (e.g., misclassifying malignant Cholangiocarcinoma as benign FNH). A hierarchical architecture ensures patient safety:

```
                                  [ Fused Vector: z_F ]
                                            │
                                            ▼
                           ┌─────────────────────────────────┐
                           │   Stage 1: Safety Gate Head     │
                           │     Benign vs. Malignant        │
                           └────────────────┬────────────────┘
                                            │
                 ┌──────────────────────────┴──────────────────────────┐
                 ▼                                                     ▼
     ┌────────────────────────┐                           ┌────────────────────────┐
     │ Stage 2A: Benign Head  │                           │Stage 2B: Malignant Head│
     │ - Hemangioma           │                           │ - HCC                  │
     │ - FNH                  │                           │ - Cholangiocarcinoma   │
     │ - Hepatic Adenoma      │                           └────────────────────────┘
     │ - (Simple Cyst)        │
     └────────────────────────┘
```

* **Stage 1 (Oncologic Safety Gate):** Binary classifier maximizing Sensitivity for malignancy ($\text{Sensitivity} \ge 99.0\%$).
* **Stage 2A (Benign Subtyping Head):** Distinguishes among Hemangioma, FNH, and Hepatic Adenoma. Leverages oral contraceptive history and arterial spoke-wheel kinetics.
* **Stage 2B (Malignant Subtyping Head):** Differentiates HCC from Cholangiocarcinoma. Leverages AFP vs. CA 19-9, cirrhosis status, and washout speed (<60s ICC vs. >60s HCC).

### Loss Formulation for Long-Tail Multiclass Imbalance
Because FNH and Hepatic Adenoma have lower clinical prevalence than HCC or Hemangioma, standard cross-entropy causes minority class starvation. Training will utilize **Class-Balanced Focal Loss**:
$$\mathcal{L}_{\text{CB-Focal}}(p, y) = - \frac{1 - \beta}{1 - \beta^{N_y}} (1 - p_y)^\gamma \log(p_y)$$
Where $N_y$ is the number of patient cases for class $y$, $\beta = 0.999$, and focusing parameter $\gamma = 2.0$.

---

## 6. Evidential Uncertainty & 5-Class Dirichlet Belief Mass

Under Subjective Logic (Model A9), the output is parameterized by a 5-dimensional Dirichlet distribution:
$$\boldsymbol{\alpha} = (\alpha_1, \alpha_2, \alpha_3, \alpha_4, \alpha_5)^T = \boldsymbol{e} + 1, \quad \text{where } e_k \ge 0$$

* Total Dirichlet strength: $S = \sum_{k=1}^5 \alpha_k = \sum_{k=1}^5 e_k + 5$.
* Class belief mass: $b_k = \frac{e_k}{S}$ for $k \in \{\text{HCC}, \text{Hem}, \text{FNH}, \text{HCA}, \text{ICC}\}$.
* Vacuous epistemic uncertainty:
  $$u = \frac{K}{S} = \frac{5}{S}, \quad \text{such that } \sum_{k=1}^5 b_k + u = 1.0$$

### Dempster-Shafer Combination Across Modalities
When fusing B-mode belief $(b_B, u_B)$ and clinical-demographic belief $(b_T, u_T)$ across 5 classes:
1. Mutual agreement: $\text{Agree} = \sum_{k=1}^5 b_B(k) b_T(k)$.
2. Multi-class conflict:
   $$C = \sum_{i \ne j} b_B(i) b_T(j)$$
3. Fused belief mass:
   $$b_{\text{fused}}(k) = \frac{b_B(k) b_T(k) + b_B(k) u_T + b_T(k) u_B}{1 - C}$$
4. Fused epistemic uncertainty:
   $$u_{\text{fused}} = \frac{u_B \cdot u_T}{1 - C}$$

**Clinical Safety Significance:** When a young female patient presents with an ambiguous arterial-enhancing lesion, the B-mode image may be torn between FNH and Adenoma, while demographics support both. The mathematical conflict $C$ rises, pushing vacuous uncertainty $u > 0.30$. This automatically diverts the patient from an automated call to a **contrast-enhanced MRI with liver-specific contrast (Eovist/Primovist)** for definitive non-invasive subtyping.

---

## 7. Explainability Suite Extensions for 5 Classes

1. **Class-Discriminative Grad-CAM:**
   * Computes gradients with respect to each class logit: $A^k = \sum_c w_c^k A_c$.
   * Verifies that for FNH, gradients highlight the central star/scar; for Hemangioma, gradients highlight peripheral vascular puddles; for ICC, gradients highlight capsular retraction.
2. **5-Class Multi-Directional Kernel SHAP:**
   * Feature attribution breakdown decomposes the log-odds of each of the 5 classes:
     $$\text{Logit}_k(x) = \phi_0^k + \sum_{i=1}^M \phi_i^k$$
   * Proves that `Female` sex and `Oral Contraceptive` duration have strong positive $\phi$ for Adenoma and FNH, while `Cirrhosis` and `HBV` have strong positive $\phi$ for HCC.
3. **5-Spoke Pentagonal Radar Explanation Cards:**
   * Replaces binary bars with an interactive 5-spoke confidence polygon, displaying class probabilities alongside the exact Dirichlet uncertainty disk ($u$).

---

## 8. Clinical Evaluation Metrics & Regulatory Endpoints

To maintain CLAIM and STARD-AI compliance, the 5-class evaluation protocol adheres to the following certified endpoints:

| Metric | Target Acceptance Criteria | Clinical Rationale |
| :--- | :--- | :--- |
| **Malignant Under-Call Rate** | **$< 0.5\%$ (Zero-Tolerance)** | Fraction of true HCC or Cholangiocarcinomas falsely classified as benign Hemangioma, FNH, or Cyst. |
| **Macro-Averaged F1-Score** | $\ge 0.88$ across all 5 classes | Evaluates unweighted average performance, preventing dominance by high-volume HCC/Hemangioma. |
| **Per-Class Balanced Accuracy** | $\ge 85.0\%$ for minority classes (FNH, Adenoma) | Guarantees the network learns genuine physiological features for rare lesions. |
| **Expected Calibration Error (ECE)** | $\text{ECE} \le 0.035$ (5-class multi-temperature scaled) | Guarantees that confidence outputs represent true diagnostic reliability. |
| **Certified Safe Referral Coverage** | Coverage $\ge 85\%$ at $\text{Risk} < 1\%$ | At least 85% of standard cases are handled automatically, deferring only the ambiguous 15% to tumor boards. |

---

## 9. Phased Execution Roadmap

```
PHASE 1: Dataset Acquisition & Label Harmonization
  ├─ Audit SYSU-CEUS multiclass release (n=353)
  ├─ Extract confirmed ICC & simple cysts from TCIA (n=120)
  └─ Build universal manifest.csv with 5-class taxonomy

PHASE 2: Modality Encoders & Dynamic CEUS Pipeline
  ├─ Implement Conv3D temporal aggregator on dynamic cineloops
  ├─ Expand tabular clinical encoder from 2 to 8 covariates
  └─ Implement Hierarchical Coarse-to-Fine decision head

PHASE 3: 5-Class Gated Fusion & Evidential Training
  ├─ Train with Class-Balanced Focal Loss
  ├─ Fit 5-class Dirichlet evidential parameters (b_1..b_5, u)
  └─ Post-hoc multi-class temperature scaling calibration

PHASE 4: Interpretability Verification & Clinical Deployment
  ├─ Generate 5-class Grad-CAM localization audits
  ├─ Compute multi-class Kernel SHAP feature attribution matrices
  └─ Update Research Console frontend with 5-class interactive dossiers
```

---

*This specification serves as the formal design plan for XMAI Phase III. All implementations will follow patient-isolated cross-validation with certified zero-leakage constraints.*
