"""
PyTorch Dataset implementations for XMAI:
- SMCDataset: Track A SMC-LUD B-mode ultrasound paired with patient clinical context.
- SYSUDataset: Track B SYSU-CEUS temporal cine clips (T=16 frames).
- TCIADataset: Track C TCIA DICOM B-mode and CEUS series evaluation.
- AULDataset: AUL ultrasound images paired with rasterized liver and mass segmentation masks.

Conforms strictly to XMAI Design Document Section 7.3 and tasks.md Section 2.4.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms.functional as TF

from xmai.data.clinical import ClinicalFeatureProcessor
from xmai.data.dicom_ceus import DICOMCEUSPipeline
from xmai.data.transforms import get_bmode_transforms, load_bmode_image


LABEL_TO_INT = {
    "Hemangioma": 0,
    "HCC": 1,
}

INT_TO_LABEL = {v: k for k, v in LABEL_TO_INT.items()}

SYSU_LABEL_TO_INT = {
    "Hemangioma": 0,
    "HCC": 1,
    "FNH": 2,
}

AUL_LABEL_TO_INT = {
    "Normal": 0,
    "Benign": 1,
    "Malignant": 2,
}


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
            self.clinical_processor = ClinicalFeatureProcessor().fit(self.df)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        row = self.df.iloc[idx]
        rel_path = row["relative_path"]
        abs_path = self.workspace_root / rel_path

        # 1. Load B-mode image with metadata
        img_tensor, img_meta = load_bmode_image(str(abs_path), transform=self.transform)

        # 2. Extract clinical features
        clin_feat, clin_miss = self.clinical_processor.transform_row(row)

        # 3. Modality mask: [M1: B-mode, M2: CEUS, M3: Context]
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
            "orig_size": img_meta["orig_size"],
            "crop_box": torch.tensor(img_meta["crop_box"], dtype=torch.long),
        }


class SYSUDataset(Dataset):
    """
    Dataset for Track B: SYSU-CEUS cine videos.
    Extracts T=16 frames uniformly across the video clip.
    Returns:
    - video: [T, 3, image_size, image_size] normalized tensor
    - timestamps: [T] in seconds
    - fps: float
    - label: int (0=Hemangioma, 1=HCC, 2=FNH)
    - patient_id: str
    - video_path: str
    """

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        workspace_root: Union[str, Path],
        num_frames: int = 16,
        image_size: int = 224,
    ):
        self.df = manifest_df.reset_index(drop=True)
        self.workspace_root = Path(workspace_root)
        self.num_frames = num_frames
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        row = self.df.iloc[idx]
        rel_path = row["relative_path"]
        abs_path = self.workspace_root / rel_path

        cap = cv2.VideoCapture(str(abs_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open SYSU video: {abs_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 15.0

        if total_frames <= 0:
            total_frames = self.num_frames

        # Sample frame indices uniformly
        frame_indices = np.linspace(0, max(0, total_frames - 1), self.num_frames, dtype=int)
        frames_list = []

        for target_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_idx))
            ret, frame = cap.read()
            if not ret or frame is None:
                if len(frames_list) > 0:
                    frames_list.append(frames_list[-1].clone())
                else:
                    blank = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
                    t = TF.to_tensor(Image.fromarray(blank))
                    frames_list.append(TF.normalize(t, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))
            else:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame).resize((self.image_size, self.image_size))
                t = TF.to_tensor(pil_img)
                frames_list.append(TF.normalize(t, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))

        cap.release()

        video_tensor = torch.stack(frames_list)
        timestamps = torch.tensor(frame_indices / fps, dtype=torch.float32)

        label_str = row["label"]
        label_int = SYSU_LABEL_TO_INT.get(label_str, -1)

        return {
            "video": video_tensor,
            "fps": fps,
            "timestamps": timestamps,
            "label": torch.tensor(label_int, dtype=torch.long),
            "label_name": label_str,
            "patient_id": row["patient_id"],
            "video_path": rel_path,
        }


class TCIADataset(Dataset):
    """
    Dataset for Track C: TCIA external multi-frame/single-frame DICOM series.
    Decodes DICOM files with dual-panel separation and content-addressed caching.
    Returns:
    - bmode_frames: [T, 3, image_size, image_size]
    - ceus_frames: [T, 3, image_size, image_size]
    - timestamps: [T]
    - label: int (1=HCC, 0=Definitive non-HCC, -1=Indeterminate/Exclude)
    - patient_id: str
    - series_uid: str
    - source_traceability: Dict
    """

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        workspace_root: Union[str, Path],
        num_frames: int = 16,
        image_size: int = 224,
        cache_dir: Optional[Union[str, Path]] = None,
    ):
        self.df = manifest_df.reset_index(drop=True)
        self.workspace_root = Path(workspace_root)
        self.num_frames = num_frames
        self.pipeline = DICOMCEUSPipeline(cache_dir=cache_dir, target_size=image_size)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        row = self.df.iloc[idx]
        rel_path = row["relative_path"]
        abs_path = self.workspace_root / rel_path

        if abs_path.is_dir():
            dcm_files = sorted(list(abs_path.glob("*.dcm")))
            if not dcm_files:
                raise FileNotFoundError(f"No .dcm files found in {abs_path}")
            dcm_target = dcm_files[0]
        else:
            dcm_target = abs_path

        decoded = self.pipeline.decode_series(dcm_target, target_t=self.num_frames)

        diag = row["harmonized_diagnosis"]
        if diag == "HCC":
            label_int = 1
        elif diag in {"ICC", "BENIGN_UNSPECIFIED", "BENIGN_ABSCESS"}:
            label_int = 0
        else:
            label_int = -1  # INDETERMINATE or MIXED_MULTI_LESION

        return {
            "bmode_frames": decoded["bmode_frames"],
            "ceus_frames": decoded["ceus_frames"],
            "timestamps": decoded["timestamps"],
            "is_phase_calibrated": decoded["is_phase_calibrated"],
            "is_dual_panel": decoded["is_dual_panel"],
            "label": torch.tensor(label_int, dtype=torch.long),
            "harmonized_diagnosis": diag,
            "patient_id": row["patient_id"],
            "series_uid": row.get("series_uid", ""),
            "source_traceability": {
                "relative_path": rel_path,
                "study_date": row.get("study_date", ""),
                "sop_class_uid": row.get("sop_class_uid", ""),
                "is_multiframe": row.get("is_multiframe", False),
            },
        }


def rasterize_polygon_mask(poly_coords: Optional[List[List[float]]], height: int, width: int) -> np.ndarray:
    """
    Rasterizes polygon coordinates into a binary mask of shape [height, width].
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    if poly_coords and len(poly_coords) >= 3:
        pts = np.array(poly_coords, dtype=np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [pts], color=1)
    return mask


class AULDataset(Dataset):
    """
    Dataset for AUL: ultrasound images paired with liver and mass segmentation masks.
    Enforces exact dimension alignment between images and polygon rasterizations.
    Returns:
    - img: [3, H, W]
    - liver_mask: [1, H, W]
    - mass_mask: [1, H, W]
    - class_name: str ('Benign', 'Malignant', 'Normal')
    - label: int (0=Normal, 1=Benign, 2=Malignant)
    - image_id: str
    - has_liver_mask: bool
    - has_mass_mask: bool
    """

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        workspace_root: Union[str, Path],
        image_size: Optional[int] = None,
    ):
        self.df = manifest_df.reset_index(drop=True)
        self.workspace_root = Path(workspace_root)
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        row = self.df.iloc[idx]
        img_path = self.workspace_root / row["relative_image_path"]

        pil_img = Image.open(img_path).convert("RGB")
        w, h = pil_img.size

        # Rasterize liver mask
        liver_rel = row.get("relative_liver_json")
        has_liver = False
        liver_mask_np = np.zeros((h, w), dtype=np.uint8)
        if pd.notna(liver_rel) and liver_rel:
            liver_abs = self.workspace_root / liver_rel
            if liver_abs.exists():
                with open(liver_abs, "r", encoding="utf-8") as f:
                    poly = json.load(f)
                liver_mask_np = rasterize_polygon_mask(poly, h, w)
                has_liver = True

        # Rasterize mass mask
        mass_rel = row.get("relative_mass_json")
        has_mass = False
        mass_mask_np = np.zeros((h, w), dtype=np.uint8)
        if pd.notna(mass_rel) and mass_rel:
            mass_abs = self.workspace_root / mass_rel
            if mass_abs.exists():
                with open(mass_abs, "r", encoding="utf-8") as f:
                    poly = json.load(f)
                mass_mask_np = rasterize_polygon_mask(poly, h, w)
                has_mass = True

        # Validate dimension alignment
        assert liver_mask_np.shape == (h, w), f"Liver mask dimension mismatch: {liver_mask_np.shape} vs {(h, w)}"
        assert mass_mask_np.shape == (h, w), f"Mass mask dimension mismatch: {mass_mask_np.shape} vs {(h, w)}"

        # Convert to tensors
        if self.image_size is not None:
            pil_img = pil_img.resize((self.image_size, self.image_size), Image.BILINEAR)
            liver_pil = Image.fromarray(liver_mask_np).resize((self.image_size, self.image_size), Image.NEAREST)
            mass_pil = Image.fromarray(mass_mask_np).resize((self.image_size, self.image_size), Image.NEAREST)
            img_tensor = TF.to_tensor(pil_img)
            liver_tensor = torch.from_numpy(np.array(liver_pil, dtype=np.float32)).unsqueeze(0)
            mass_tensor = torch.from_numpy(np.array(mass_pil, dtype=np.float32)).unsqueeze(0)
        else:
            img_tensor = TF.to_tensor(pil_img)
            liver_tensor = torch.from_numpy(liver_mask_np.astype(np.float32)).unsqueeze(0)
            mass_tensor = torch.from_numpy(mass_mask_np.astype(np.float32)).unsqueeze(0)

        # ImageNet normalization for image
        img_tensor = TF.normalize(img_tensor, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

        class_name = row["class_name"]
        label_int = AUL_LABEL_TO_INT.get(class_name, -1)

        return {
            "img": img_tensor,
            "liver_mask": liver_tensor,
            "mass_mask": mass_tensor,
            "class_name": class_name,
            "label": torch.tensor(label_int, dtype=torch.long),
            "image_id": row["image_id"],
            "has_liver_mask": has_liver,
            "has_mass_mask": has_mass,
            "orig_size": (w, h),
        }
