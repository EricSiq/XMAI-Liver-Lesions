"""
Fold-isolated clinical feature processing.
Strictly ensures:
- Normalization (mean, std) is fitted on the training fold only.
- Imputation (median) is fitted on the training fold only.
- Encodes age, sex, and explicit missing indicators.
- Blocks any leakage fields via assert_no_leakage_fields.
"""

from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch

from xmai.data.schemas import assert_no_leakage_fields


class ClinicalFeatureProcessor:
    """
    Fits clinical transforms strictly inside training fold to prevent evaluation-fold leakage.
    Produces tensor [age_z, sex_binary, age_missing, sex_missing].
    """

    def __init__(self):
        self.age_mean: Optional[float] = None
        self.age_std: Optional[float] = None
        self.age_median: Optional[float] = None
        self.is_fitted: bool = False

    def fit(self, train_df: pd.DataFrame) -> "ClinicalFeatureProcessor":
        """Fits mean, std, and median on the training fold only."""
        # Leakage check: ensure only permitted columns are in candidate inputs
        for col in train_df.columns:
            if col in {"t_stage", "tumor_size", "tace_response"}:
                assert_no_leakage_fields({col: 1})

        valid_ages = train_df.loc[~train_df["age_missing"], "age"].dropna()
        if len(valid_ages) == 0:
            raise ValueError("Training fold contains no valid age values to fit scaler.")

        self.age_mean = float(valid_ages.mean())
        self.age_std = float(valid_ages.std()) if len(valid_ages) > 1 and valid_ages.std() > 0 else 1.0
        self.age_median = float(valid_ages.median())
        self.is_fitted = True
        return self

    def transform_row(self, row: Union[pd.Series, Dict]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Transforms a single patient row into (feature_vector, missing_mask).
        Features: [age_normalized, sex_binary] (dim=2)
        Missing mask: [age_missing, sex_missing] (dim=2)
        """
        if not self.is_fitted:
            raise RuntimeError("ClinicalFeatureProcessor must be fitted on training fold before transforming data.")

        age_missing = bool(row.get("age_missing", False) or pd.isna(row.get("age")))
        sex_missing = bool(row.get("sex_missing", False) or pd.isna(row.get("sex")))

        # Impute age if missing with training-fold median
        raw_age = row.get("age")
        age_val = self.age_median if (age_missing or raw_age is None) else float(raw_age)
        age_z = (age_val - self.age_mean) / self.age_std

        # Sex: M -> 1.0, F -> 0.0, Missing -> 0.5
        raw_sex = row.get("sex")
        if sex_missing or raw_sex is None:
            sex_val = 0.5
        elif str(raw_sex).strip().upper() == "M":
            sex_val = 1.0
        else:
            sex_val = 0.0

        feat = torch.tensor([age_z, sex_val], dtype=torch.float32)
        mask = torch.tensor([1.0 if age_missing else 0.0, 1.0 if sex_missing else 0.0], dtype=torch.float32)

        return feat, mask

    def transform_df(self, df: pd.DataFrame) -> Tuple[torch.Tensor, torch.Tensor]:
        """Batch transforms a dataframe into feature and missingness tensors."""
        feats = []
        masks = []
        for _, row in df.iterrows():
            f, m = self.transform_row(row)
            feats.append(f)
            masks.append(m)
        return torch.stack(feats), torch.stack(masks)


class MulticlassClinicalFeatureProcessor:
    """
    8-Variable Structured Clinical Feature Processor for Multiclass FLL Differential Diagnosis.
    Normalizes continuous markers (age, log(AFP), log(CA19-9)) and encodes binary clinical
    indicators (sex, cirrhosis, hepatitis, oral contraceptives, metabolic syndrome) with
    strict training-fold fitting and explicit missingness indicators.
    """

    def __init__(self):
        self.age_mean: Optional[float] = None
        self.age_std: Optional[float] = None
        self.age_median: Optional[float] = None
        self.afp_log_mean: Optional[float] = None
        self.afp_log_std: Optional[float] = None
        self.ca19_9_log_mean: Optional[float] = None
        self.ca19_9_log_std: Optional[float] = None
        self.is_fitted: bool = False

    def fit(self, train_df: pd.DataFrame) -> "MulticlassClinicalFeatureProcessor":
        """Fits normalization statistics on the training partition only."""
        # Check for leakage columns
        for col in train_df.columns:
            if col in {"t_stage", "tumor_size", "tace_response"}:
                assert_no_leakage_fields({col: 1})

        # Fit age
        valid_ages = train_df["age"].dropna()
        self.age_mean = float(valid_ages.mean()) if len(valid_ages) > 0 else 55.0
        self.age_std = float(valid_ages.std()) if len(valid_ages) > 1 and valid_ages.std() > 0 else 12.0
        self.age_median = float(valid_ages.median()) if len(valid_ages) > 0 else 55.0

        # Fit AFP (log1p)
        if "afp_level" in train_df.columns:
            valid_afp = np.log1p(train_df["afp_level"].dropna().clip(lower=0))
            self.afp_log_mean = float(valid_afp.mean()) if len(valid_afp) > 0 else 2.0
            self.afp_log_std = float(valid_afp.std()) if len(valid_afp) > 1 and valid_afp.std() > 0 else 1.5
        else:
            self.afp_log_mean, self.afp_log_std = 2.0, 1.5

        # Fit CA 19-9 (log1p)
        if "ca19_9_level" in train_df.columns:
            valid_ca = np.log1p(train_df["ca19_9_level"].dropna().clip(lower=0))
            self.ca19_9_log_mean = float(valid_ca.mean()) if len(valid_ca) > 0 else 2.5
            self.ca19_9_log_std = float(valid_ca.std()) if len(valid_ca) > 1 and valid_ca.std() > 0 else 1.2
        else:
            self.ca19_9_log_mean, self.ca19_9_log_std = 2.5, 1.2

        self.is_fitted = True
        return self

    def transform_row(self, row: Union[pd.Series, Dict]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Transforms row into 8-dimensional feature vector and 8-dimensional missingness mask.
        Features: [age_z, sex_binary, cirrhosis, hepatitis, oral_contraceptives, metabolic, afp_log_z, ca19_9_log_z]
        """
        if not self.is_fitted:
            raise RuntimeError("MulticlassClinicalFeatureProcessor must be fitted before transforming.")

        # 1. Age
        raw_age = row.get("age")
        age_missing = pd.isna(raw_age)
        age_val = self.age_median if age_missing else float(raw_age)
        age_z = (age_val - self.age_mean) / self.age_std

        # 2. Sex: M=1.0, F=0.0, Missing=0.5
        raw_sex = row.get("sex")
        sex_missing = pd.isna(raw_sex)
        if sex_missing:
            sex_val = 0.5
        elif str(raw_sex).strip().upper() == "M":
            sex_val = 1.0
        else:
            sex_val = 0.0

        # 3. Cirrhosis
        raw_cirr = row.get("cirrhosis")
        cirr_missing = pd.isna(raw_cirr)
        cirr_val = float(raw_cirr) if not cirr_missing else 0.0

        # 4. Hepatitis
        raw_hep = row.get("hepatitis")
        hep_missing = pd.isna(raw_hep)
        hep_val = float(raw_hep) if not hep_missing else 0.0

        # 5. Oral contraceptives
        raw_oc = row.get("oral_contraceptives")
        oc_missing = pd.isna(raw_oc)
        oc_val = float(raw_oc) if not oc_missing else 0.0

        # 6. Metabolic syndrome
        raw_met = row.get("metabolic_syndrome")
        met_missing = pd.isna(raw_met)
        met_val = float(raw_met) if not met_missing else 0.0

        # 7. AFP log z
        raw_afp = row.get("afp_level")
        afp_missing = pd.isna(raw_afp)
        afp_log = np.log1p(max(0.0, float(raw_afp))) if not afp_missing else self.afp_log_mean
        afp_z = (afp_log - self.afp_log_mean) / self.afp_log_std

        # 8. CA 19-9 log z
        raw_ca = row.get("ca19_9_level")
        ca_missing = pd.isna(raw_ca)
        ca_log = np.log1p(max(0.0, float(raw_ca))) if not ca_missing else self.ca19_9_log_mean
        ca_z = (ca_log - self.ca19_9_log_mean) / self.ca19_9_log_std

        feats = torch.tensor(
            [age_z, sex_val, cirr_val, hep_val, oc_val, met_val, afp_z, ca_z],
            dtype=torch.float32,
        )
        mask = torch.tensor(
            [
                1.0 if age_missing else 0.0,
                1.0 if sex_missing else 0.0,
                1.0 if cirr_missing else 0.0,
                1.0 if hep_missing else 0.0,
                1.0 if oc_missing else 0.0,
                1.0 if met_missing else 0.0,
                1.0 if afp_missing else 0.0,
                1.0 if ca_missing else 0.0,
            ],
            dtype=torch.float32,
        )
        return feats, mask

    def transform_df(self, df: pd.DataFrame) -> Tuple[torch.Tensor, torch.Tensor]:
        """Batch transforms a dataframe into feature and missingness tensors."""
        feats = []
        masks = []
        for _, row in df.iterrows():
            f, m = self.transform_row(row)
            feats.append(f)
            masks.append(m)
        return torch.stack(feats), torch.stack(masks)



def generate_clinical_fold_report(manifest_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Produces a detailed clinical feature report by fold, including
    demographics, class balance, and missingness.
    Conforms to tasks.md Section 2.2.
    """
    patient_df = manifest_df.drop_duplicates(subset=["patient_id"]).copy()
    folds = sorted(patient_df["fold"].unique())

    report: Dict[str, Any] = {
        "cohort_summary": {
            "total_patients": len(patient_df),
            "hcc_patients": int((patient_df["label"] == "HCC").sum()),
            "hem_patients": int((patient_df["label"] == "Hemangioma").sum()),
            "hcc_age_mean": float(patient_df.loc[patient_df["label"] == "HCC", "age"].dropna().mean()),
            "hem_age_mean": float(patient_df.loc[patient_df["label"] == "Hemangioma", "age"].dropna().mean()),
            "hcc_male_ratio": float((patient_df.loc[patient_df["label"] == "HCC", "sex"] == "M").mean()),
            "hem_male_ratio": float((patient_df.loc[patient_df["label"] == "Hemangioma", "sex"] == "M").mean()),
        },
        "folds": {},
    }

    for f in folds:
        train_p = patient_df[patient_df["fold"] != f]
        val_p = patient_df[patient_df["fold"] == f]

        report["folds"][f"fold_{f}"] = {
            "train": {
                "patients": len(train_p),
                "hcc": int((train_p["label"] == "HCC").sum()),
                "hem": int((train_p["label"] == "Hemangioma").sum()),
                "age_mean": float(train_p["age"].dropna().mean()),
                "age_std": float(train_p["age"].dropna().std()),
                "age_median": float(train_p["age"].dropna().median()),
                "missing_age": int(train_p["age_missing"].sum()),
                "male_ratio": float((train_p["sex"] == "M").mean()),
            },
            "val": {
                "patients": len(val_p),
                "hcc": int((val_p["label"] == "HCC").sum()),
                "hem": int((val_p["label"] == "Hemangioma").sum()),
                "age_mean": float(val_p["age"].dropna().mean()),
                "age_std": float(val_p["age"].dropna().std()),
                "age_median": float(val_p["age"].dropna().median()),
                "missing_age": int(val_p["age_missing"].sum()),
                "male_ratio": float((val_p["sex"] == "M").mean()),
            },
        }

    return report

