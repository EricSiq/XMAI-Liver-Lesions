"""
Pydantic schemas, type contracts, and clinical leakage barriers for XMAI.

This module formalizes:
1. Patient-level tracking contracts ensuring zero-leakage cross-validation.
2. Label taxonomy spaces for Track A (Binary HCC vs. Hemangioma) and Multiclass (5-class & 6-class FLL spectrum).
3. Automated leakage barrier preventing post-diagnostic or outcome-related features
   (e.g., T-stage, tumor size, TACE response) from contaminating the multimodal feature set.
4. Standardized prediction schemas enforcing probability normalization and margin bounds.

Conforms strictly to:
- CLAIM (Checklist for AI in Medical Imaging) Items 1, 2, and 7.
- STARD-AI 2020 Reporting Guidelines for diagnostic test accuracy.
- XMAI Design Document v2 Section 5.6 and Section 7.
"""

import math
import re
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# Clinical Taxonomy and Label Space Contracts
# ==============================================================================

# Permitted class labels across experimental tracks
SMCLabel = Literal["HCC", "Hemangioma"]
SYSULabel = Literal["HCC", "Hemangioma", "FNH"]
AULLabel = Literal["Benign", "Malignant", "Normal"]

# 5-Class and 6-Class Focal Liver Lesion Differential Diagnosis Taxonomy
FLL5ClassLabel = Literal["HCC", "Hemangioma", "FNH", "Adenoma", "Cholangiocarcinoma"]
FLL6ClassLabel = Literal["HCC", "Hemangioma", "FNH", "Adenoma", "Cholangiocarcinoma", "Cyst"]

TAXONOMY_5CLASS: List[str] = ["HCC", "Hemangioma", "FNH", "Adenoma", "Cholangiocarcinoma"]
TAXONOMY_5CLASS_WITH_CYST: List[str] = ["HCC", "Hemangioma", "FNH", "Cholangiocarcinoma", "Cyst"]
TAXONOMY_6CLASS: List[str] = ["HCC", "Hemangioma", "FNH", "Adenoma", "Cholangiocarcinoma", "Cyst"]

# Oncologic safety tier mapping (Malignant vs. Benign)
CLASS_TIER_MAPPING: Dict[str, Literal["Malignant", "Benign"]] = {
    "HCC": "Malignant",
    "Cholangiocarcinoma": "Malignant",
    "Hemangioma": "Benign",
    "FNH": "Benign",
    "Adenoma": "Benign",
    "Cyst": "Benign",
}

# Prohibited leakage field names that must NEVER enter model feature dictionaries.
# Sourced from post-diagnosis histology, surgical staging, or therapeutic interventions.
PROHIBITED_FEATURE_FIELDS = {
    "t_stage",
    "tumor_size",
    "tumor_size_cm",
    "max_diameter",
    "pathologic_t_stage",
    "tace_response",
    "complete_response_to_tace",
    "year",
    "acquisition_format",
    "file_size",
    "frame_count",
}


# ==============================================================================
# Manifest Row Schemas
# ==============================================================================

class SMCManifestRow(BaseModel):
    """
    Schema for a single B-mode image entry in the SMC-LUD primary cohort.
    
    Attributes:
        patient_id: Unique patient identifier (e.g. 'HCC_2' or 'Hem_10').
        subject_id: Numeric subject ID extracted from hospital metadata.
        relative_path: Workspace-relative POSIX path to verified clean image.
        label: Ground-truth pathology or imaging consensus ('HCC' or 'Hemangioma').
        is_clean: Boolean flag enforcing exclusion of caliper/text-annotated scans.
        age: Patient biological age in years (cohort context).
        age_missing: True if age was missing in metadata (handled via imputation).
        sex: Biological sex ('M' or 'F').
        sex_missing: True if sex was missing in metadata.
        fold: Stratified CV fold index (0 to 4).
        image_sha256: 64-character SHA-256 hash of image bytes for deduplication.
    """
    patient_id: str = Field(..., min_length=1, description="Unique patient identifier, e.g. HCC_2 or Hem_10")
    subject_id: int = Field(..., description="Numeric subject ID from metadata table")
    relative_path: str = Field(..., min_length=1, description="Workspace-relative path to clean image")
    label: SMCLabel = Field(..., description="Ground truth diagnosis: HCC or Hemangioma")
    is_clean: bool = Field(True, description="Must be true (clean wo caliper only)")
    age: Optional[float] = Field(None, description="Patient age in years (cohort context)")
    age_missing: bool = Field(False, description="True if age was missing in metadata")
    sex: Optional[Literal["M", "F"]] = Field(None, description="Patient biological sex")
    sex_missing: bool = Field(False, description="True if sex was missing in metadata")
    fold: int = Field(..., ge=0, le=4, description="Stratified CV fold (0 to 4)")
    image_sha256: str = Field(..., min_length=16, max_length=64, description="SHA-256 (or truncated) hash of image bytes for deduplication")

    @field_validator("is_clean")
    @classmethod
    def validate_clean(cls, v: bool) -> bool:
        if not v:
            raise ValueError("CLAIM Principle 3 Violation: Only clean (without caliper) images are permitted for modelling.")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 120):
            raise ValueError(f"Physiologically invalid age value: {v}. Must be in [0, 120] years.")
        return v

    @field_validator("relative_path")
    @classmethod
    def validate_path_safety(cls, v: str) -> str:
        if ".." in v or v.startswith("/") or v.startswith("\\"):
            raise ValueError(f"Path traversal or absolute path violation: '{v}'. Must be a workspace-relative path.")
        return v


class SYSUManifestRow(BaseModel):
    """Schema for a CEUS video entry in SYSU-CEUS."""
    patient_id: str = Field(..., min_length=1, description="Video/Patient identifier")
    relative_path: str = Field(..., min_length=1, description="Workspace-relative path to AVI video")
    label: SYSULabel = Field(..., description="Ground truth diagnosis: HCC, Hemangioma, or FNH")
    num_frames: int = Field(..., gt=0, description="Total frame count in video")
    fps: float = Field(..., gt=0.0, description="Frames per second")
    width: int = Field(..., gt=0, description="Frame width in pixels")
    height: int = Field(..., gt=0, description="Frame height in pixels")
    is_fixture_sample: bool = Field(
        False, 
        description="True if part of 15-video demo fixture; demo videos cannot be used for benchmark claims"
    )

    @field_validator("relative_path")
    @classmethod
    def validate_path_safety(cls, v: str) -> str:
        if ".." in v:
            raise ValueError(f"Path traversal detected in relative_path: '{v}'.")
        return v


class TCIAManifestRow(BaseModel):
    """Schema for a TCIA DICOM series entry."""
    patient_id: str = Field(..., min_length=1, description="Patient ID e.g. LiverUS-01")
    study_date: Optional[str] = Field(None, description="Study acquisition date")
    series_uid: str = Field(..., min_length=1, description="DICOM SeriesInstanceUID")
    relative_path: str = Field(..., min_length=1, description="Workspace-relative path to DICOM file or directory")
    raw_diagnosis: str = Field(..., description="Original spreadsheet diagnosis")
    harmonized_diagnosis: str = Field(..., description="Harmonized diagnosis: HCC, ICC, Benign, Indeterminate")
    modality: str = Field("US", description="DICOM Modality, typically US")
    sop_class_uid: str = Field(..., min_length=1, description="SOP Class UID")
    is_multiframe: bool = Field(False, description="True if multi-frame cine series")
    num_frames: int = Field(1, ge=1, description="Number of frames in series")
    usable_for_eval: bool = Field(True, description="True if suitable for external HCC sensitivity check")


class AULManifestRow(BaseModel):
    """Schema for an AUL ultrasound image with optional segmentation masks."""
    image_id: str = Field(..., min_length=1, description="AUL image identifier")
    relative_image_path: str = Field(..., min_length=1, description="Workspace-relative path to image")
    class_name: AULLabel = Field(..., description="Benign, Malignant, or Normal")
    relative_liver_json: Optional[str] = Field(None, description="Path to liver outline polygon JSON")
    relative_mass_json: Optional[str] = Field(None, description="Path to mass/lesion polygon JSON")
    has_mass_mask: bool = Field(False, description="True if lesion polygon exists")


class ClinicalCovariates8(BaseModel):
    """
    Structured 8-variable clinical oncology covariate profile for FLL differential diagnosis.
    All laboratory values and comorbidities are bounded within established clinical ranges.
    """
    age: Optional[float] = Field(None, ge=0.0, le=120.0, description="Patient age in years")
    sex: Optional[Literal["M", "F"]] = Field(None, description="Biological sex")
    cirrhosis: Optional[Literal[0, 1]] = Field(None, description="Parenchymal cirrhosis (0: Absent, 1: Present)")
    hepatitis: Optional[Literal[0, 1]] = Field(None, description="Viral hepatitis serology HBV/HCV (0: Neg, 1: Pos)")
    oral_contraceptives: Optional[Literal[0, 1]] = Field(None, description="Oral contraceptive history >= 5 yrs")
    metabolic_syndrome: Optional[Literal[0, 1]] = Field(None, description="Metabolic syndrome / NAFLD (0: No, 1: Yes)")
    afp_level: Optional[float] = Field(None, ge=0.0, le=500000.0, description="Serum Alpha-Fetoprotein in ng/mL")
    ca19_9_level: Optional[float] = Field(None, ge=0.0, le=500000.0, description="Serum CA 19-9 in U/mL")


class MulticlassManifestRow(BaseModel):
    """
    Schema for a unified multiclass focal liver lesion patient entry.
    Ensures that every record aligns with the approved taxonomy, clinical tier, and fold bounds.
    """
    patient_id: str = Field(..., min_length=1, description="Unique patient identifier")
    relative_path: str = Field(..., min_length=1, description="Workspace-relative path to primary clean image or DICOM")
    label: str = Field(..., description="Lesion diagnostic label in 5-class or 6-class taxonomy")
    tier: Literal["Malignant", "Benign"] = Field(..., description="Oncologic safety tier")
    fold: int = Field(..., ge=0, le=4, description="Stratified CV fold (0 to 4)")
    data_source: str = Field(..., description="Originating repository: SMC-LUD, TCIA, SYSU-CEUS, WFUMB-Acoustic")
    is_synthetic: bool = Field(False, description="True if generated as clinical acoustic reference fixture")
    verification_status: Literal[
        "VERIFIED_HISTOPATHOLOGY",
        "VERIFIED_IMAGING_CONSENSUS",
        "VALIDATED_REFERENCE_COHORT",
    ] = Field(..., description="Diagnostic ground-truth verification standard")
    clinical: ClinicalCovariates8 = Field(default_factory=ClinicalCovariates8)

    @model_validator(mode="after")
    def validate_tier_alignment(self) -> "MulticlassManifestRow":
        if self.label not in TAXONOMY_6CLASS:
            raise ValueError(f"Label '{self.label}' is not in valid taxonomy {TAXONOMY_6CLASS}")
        expected_tier = CLASS_TIER_MAPPING.get(self.label)
        if expected_tier and self.tier != expected_tier:
            raise ValueError(f"Label '{self.label}' tier mismatch: expected {expected_tier}, got {self.tier}")
        return self


class PredictionRow(BaseModel):
    """
    Schema for standardized patient-level out-of-fold predictions.
    Enforces mathematical consistency across probability distributions.
    """
    patient_id: str = Field(..., min_length=1, description="Patient identifier")
    track: Literal["A", "B", "C"] = Field(..., description="Experimental track")
    fold: int = Field(..., ge=0, le=4, description="CV fold index")
    seed: int = Field(..., description="Evaluation seed")
    model_id: str = Field(..., min_length=1, description="Model identifier e.g. A1_image_only, A4_gated_fusion")
    true_label: str = Field(..., description="Ground truth label")
    pred_label: str = Field(..., description="Predicted label")
    prob_vector: Dict[str, float] = Field(..., description="Calibrated class probabilities summing to 1.0")
    margin: float = Field(..., ge=0.0, description="Top-1 minus top-2 probability margin in [0, 1]")
    is_calibrated: bool = Field(True, description="Whether temperature scaling was applied")
    is_low_margin: bool = Field(False, description="True if margin falls in lowest decile")
    is_error: bool = Field(False, description="True if pred_label != true_label")
    modality_mask: List[int] = Field(..., description="Binary indicator of modality presence [M1, M2, M3]")

    @model_validator(mode="after")
    def validate_probabilities(self) -> "PredictionRow":
        probs = list(self.prob_vector.values())
        if len(probs) < 2:
            raise ValueError(f"prob_vector must contain at least 2 classes for differential evaluation, got {len(probs)}")
        if any(math.isnan(p) or math.isinf(p) for p in probs):
            raise ValueError(f"Probabilities must be finite numbers, got {probs}")
        total = sum(probs)
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Probability vector must sum to 1.0 within tolerance, got {total}")
        for p in probs:
            if p < 0.0 or p > 1.0:
                raise ValueError(f"Probabilities must be in [0, 1], got {p}")
        return self

    @field_validator("modality_mask")
    @classmethod
    def validate_modality_mask(cls, v: List[int]) -> List[int]:
        if len(v) not in (2, 3):
            raise ValueError(f"modality_mask must contain 2 or 3 binary indicators, got length {len(v)}")
        if any(m not in (0, 1) for m in v):
            raise ValueError(f"modality_mask elements must be strictly 0 or 1, got {v}")
        return v


# ==============================================================================
# Automated Zero-Leakage Barrier Assertion
# ==============================================================================

def assert_no_leakage_fields(feature_dict: Dict[str, Union[float, int, str, None]]) -> None:
    """
    Automated clinical leakage barrier (CLAIM Checklist Item 2).
    
    Verifies that no prohibited post-diagnostic, surgical, or format-shortcut field
    enters a model feature dictionary. Normalizes feature names across camelCase,
    delimiters, whitespace, dots, and slashes to prevent delimiter-based evasion.
    
    Raises:
        ValueError: Immediately if any prohibited variable name is detected.
    """
    found_violations = set()
    for key in feature_dict.keys():
        # 1. Normalize with standard delimiters replaced by underscores
        normalized_key = key.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
        # 2. Fully stripped representation (e.g. 'tumorsize', 'tstage') to catch camelCase
        stripped_key = re.sub(r"[^a-z0-9]", "", key.lower())

        for prohibited in PROHIBITED_FEATURE_FIELDS:
            prohibited_stripped = prohibited.replace("_", "")
            if prohibited in normalized_key or prohibited_stripped == stripped_key or prohibited_stripped in stripped_key:
                found_violations.add(key)
    
    if found_violations:
        raise ValueError(
            f"LEAKAGE ASSERTION FAILED: Prohibited diagnostic/shortcut fields detected in feature set: "
            f"{sorted(found_violations)}. Sourced from post-diagnosis histology or surgical staging. "
            f"See XMAI_Design_Document_v2 Section 5.6."
        )
