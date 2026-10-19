"""
Pydantic schemas and leakage barriers for XMAI dataset manifests and predictions.
Strictly enforces patient-level tracking, valid label spaces, and blocks leakage fields.
"""

import math
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# Permitted class labels
SMCLabel = Literal["HCC", "Hemangioma"]
SYSULabel = Literal["HCC", "Hemangioma", "FNH"]
AULLabel = Literal["Benign", "Malignant", "Normal"]

# Prohibited leakage field names that must never enter feature dictionaries
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


class SMCManifestRow(BaseModel):
    """Schema for a single B-mode image entry in SMC-LUD."""
    patient_id: str = Field(..., description="Unique patient identifier, e.g. HCC_2 or Hem_10")
    subject_id: int = Field(..., description="Numeric subject ID from metadata table")
    relative_path: str = Field(..., description="Workspace-relative path to clean image")
    label: SMCLabel = Field(..., description="Ground truth diagnosis: HCC or Hemangioma")
    is_clean: bool = Field(True, description="Must be true (clean wo caliper only)")
    age: Optional[float] = Field(None, description="Patient age in years (cohort context)")
    age_missing: bool = Field(False, description="True if age was missing in metadata")
    sex: Optional[Literal["M", "F"]] = Field(None, description="Patient biological sex")
    sex_missing: bool = Field(False, description="True if sex was missing in metadata")
    fold: int = Field(..., ge=0, le=4, description="Stratified CV fold (0 to 4)")
    image_sha256: str = Field(..., description="SHA-256 hash of image bytes for deduplication")

    @field_validator("is_clean")
    @classmethod
    def validate_clean(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Only clean (without caliper) images are permitted for modelling.")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 120):
            raise ValueError(f"Invalid age value: {v}")
        return v


class SYSUManifestRow(BaseModel):
    """Schema for a CEUS video entry in SYSU-CEUS."""
    patient_id: str = Field(..., description="Video/Patient identifier")
    relative_path: str = Field(..., description="Workspace-relative path to AVI video")
    label: SYSULabel = Field(..., description="Ground truth diagnosis: HCC, Hemangioma, or FNH")
    num_frames: int = Field(..., gt=0, description="Total frame count in video")
    fps: float = Field(..., gt=0.0, description="Frames per second")
    width: int = Field(..., gt=0, description="Frame width")
    height: int = Field(..., gt=0, description="Frame height")
    is_fixture_sample: bool = Field(
        False, 
        description="True if part of 15-video demo fixture; demo videos cannot be used for benchmark claims"
    )


class TCIAManifestRow(BaseModel):
    """Schema for a TCIA DICOM series entry."""
    patient_id: str = Field(..., description="Patient ID e.g. LiverUS-01")
    study_date: Optional[str] = Field(None, description="Study acquisition date")
    series_uid: str = Field(..., description="DICOM SeriesInstanceUID")
    relative_path: str = Field(..., description="Workspace-relative path to DICOM file or directory")
    raw_diagnosis: str = Field(..., description="Original spreadsheet diagnosis")
    harmonized_diagnosis: str = Field(..., description="Harmonized diagnosis: HCC, ICC, Benign, Indeterminate")
    modality: str = Field("US", description="DICOM Modality, typically US")
    sop_class_uid: str = Field(..., description="SOP Class UID")
    is_multiframe: bool = Field(False, description="True if multi-frame cine series")
    num_frames: int = Field(1, ge=1, description="Number of frames in series")
    usable_for_eval: bool = Field(True, description="True if suitable for external HCC sensitivity check")


class AULManifestRow(BaseModel):
    """Schema for an AUL ultrasound image with optional segmentation masks."""
    image_id: str = Field(..., description="AUL image identifier")
    relative_image_path: str = Field(..., description="Workspace-relative path to image")
    class_name: AULLabel = Field(..., description="Benign, Malignant, or Normal")
    relative_liver_json: Optional[str] = Field(None, description="Path to liver outline polygon JSON")
    relative_mass_json: Optional[str] = Field(None, description="Path to mass/lesion polygon JSON")
    has_mass_mask: bool = Field(False, description="True if lesion polygon exists")


class PredictionRow(BaseModel):
    """Schema for standardized patient-level out-of-fold predictions."""
    patient_id: str = Field(..., description="Patient identifier")
    track: Literal["A", "B", "C"] = Field(..., description="Experimental track")
    fold: int = Field(..., ge=0, le=4, description="CV fold index")
    seed: int = Field(..., description="Evaluation seed")
    model_id: str = Field(..., description="Model identifier e.g. A1_image_only, A4_gated_fusion")
    true_label: str = Field(..., description="Ground truth label")
    pred_label: str = Field(..., description="Predicted label")
    prob_vector: Dict[str, float] = Field(..., description="Calibrated class probabilities summing to 1.0")
    margin: float = Field(..., description="Top-1 minus top-2 probability margin")
    is_calibrated: bool = Field(True, description="Whether temperature scaling was applied")
    is_low_margin: bool = Field(False, description="True if margin falls in lowest decile")
    is_error: bool = Field(False, description="True if pred_label != true_label")
    modality_mask: List[int] = Field(..., description="Binary indicator of modality presence [M1, M2, M3]")

    @model_validator(mode="after")
    def validate_probabilities(self) -> "PredictionRow":
        probs = list(self.prob_vector.values())
        if any(math.isnan(p) or math.isinf(p) for p in probs):
            raise ValueError(f"Probabilities must be finite numbers, got {probs}")
        total = sum(probs)
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Probability vector must sum to 1.0 within tolerance, got {total}")
        for p in probs:
            if p < 0.0 or p > 1.0:
                raise ValueError(f"Probabilities must be in [0, 1], got {p}")
        return self


def assert_no_leakage_fields(feature_dict: Dict[str, Union[float, int, str, None]]) -> None:
    """
    Automated leakage barrier: checks that no prohibited field enters a model feature dictionary.
    Raises ValueError immediately if any excluded feature is detected.
    """
    found_violations = set()
    for key in feature_dict.keys():
        normalized_key = key.strip().lower().replace(" ", "_").replace("-", "_")
        for prohibited in PROHIBITED_FEATURE_FIELDS:
            if prohibited in normalized_key:
                found_violations.add(key)
    
    if found_violations:
        raise ValueError(
            f"LEAKAGE ASSERTION FAILED: Prohibited diagnostic/shortcut fields detected in feature set: "
            f"{sorted(found_violations)}. See XMAI_Design_Document_v2 Section 5.6."
        )
