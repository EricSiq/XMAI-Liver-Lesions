"""
PyTorch Dataset implementations for XMAI.
Supports Track A (SMC-LUD B-mode image + clinical context).
Conforms strictly to the multimodal tensor interface (XMAI Design Doc Section 7.3).
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import pandas as pd
import torch
from torch.utils.data import Dataset

from xmai.data.clinical import ClinicalFeatureProcessor
from xmai.data.transforms import get_bmode_transforms, load_bmode_image


LABEL_TO_INT = {
    "Hemangioma": 0,
    "HCC": 1,
}

INT_TO_LABEL = {v: k for k, v in LABEL_TO_INT.items()}


class SMCDataset(Dataset):
    """
    Dataset for Track A: SMC-LUD B-mode ultrasound images paired with patient context.
    Yields sample conforming to XMAI tensor specification:
    - img: [3, 224, 224]
    - clin: [2] (age_z, sex)
    - clin_miss: [2] (age_miss, sex_miss)
    - mod_mask: [3] ([1, 0, 1] -> M1=B-mode present, M2=CEUS absent, M3=context present)
    - label: int (0=Hemangioma, 1=HCC)
    - patient_id: str
    - metadata: Dict
    """

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        workspace_root: Union[str, Path],
        is_train: bool = False,
        clinical_processor: Optional[ClinicalFeatureProcessor] = None,
        image_size: int = 224,
    ):
        self.df = manifest_df.reset_index(drop=True)
        self.workspace_root = Path(workspace_root)
        self.is_train = is_train
        self.transform = get_bmode_transforms(is_train=is_train, image_size=image_size)
        self.clinical_processor = clinical_processor

        if self.clinical_processor is None:
            # If not provided, fit locally on the dataset
            self.clinical_processor = ClinicalFeatureProcessor().fit(self.df)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        row = self.df.iloc[idx]
        rel_path = row["relative_path"]
        abs_path = self.workspace_root / rel_path

        # 1. Load B-mode image
        img_tensor, orig_size = load_bmode_image(str(abs_path), transform=self.transform)

        # 2. Extract clinical features
        clin_feat, clin_miss = self.clinical_processor.transform_row(row)

        # 3. Modality mask: [M1: B-mode, M2: CEUS, M3: Context]
        # For Track A, M1 is always present (1.0), M2 is absent (0.0), M3 is present (1.0)
        mod_mask = torch.tensor([1.0, 0.0, 1.0], dtype=torch.float32)

        # 4. Target label
        label_str = row["label"]
        label_int = LABEL_TO_INT[label_str]

        return {
            "img": img_tensor,
            "clin": clin_feat,
            "clin_miss": clin_miss,
            "mod_mask": mod_mask,
            "label": torch.tensor(label_int, dtype=torch.long),
            "patient_id": row["patient_id"],
            "image_path": rel_path,
            "orig_size": orig_size,
        }
