"""
Fold-isolated clinical feature processing.
Strictly ensures:
- Normalization (mean, std) is fitted on the training fold only.
- Imputation (median) is fitted on the training fold only.
- Encodes age, sex, and explicit missing indicators.
- Blocks any leakage fields via assert_no_leakage_fields.
"""

from typing import Dict, Optional, Tuple, Union
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
