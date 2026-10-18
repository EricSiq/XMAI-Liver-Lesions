"""
SYSU-CEUS dataset inspection and fixture manifest generation.
Records frame dimensions, fps, duration, and flags demo status.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import cv2
import pandas as pd

from xmai.data.schemas import SYSULabel, SYSUManifestRow


def generate_sysu_manifest(
    workspace_root: Path,
    output_manifest_path: Path,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Audits the local SYSU-CEUS video sample, records metadata,
    validates with SYSUManifestRow, and writes output manifest CSV.
    """
    sysu_root = workspace_root / "Focal-liver-lesions-dataset-in-CEUS-master" / "Focal-liver-lesions-dataset-in-CEUS-master" / "SYSU-CEUS"
    if not sysu_root.exists():
        raise FileNotFoundError(f"SYSU root not found at {sysu_root}")

    label_map: Dict[str, SYSULabel] = {
        "HCC": "HCC",
        "HEM": "Hemangioma",
        "FNH": "FNH",
    }

    records: List[Dict[str, Any]] = []

    for folder_name, standardized_label in label_map.items():
        class_dir = sysu_root / folder_name
        if not class_dir.exists():
            continue

        for avi_file in sorted(class_dir.glob("*.avi")):
            cap = cv2.VideoCapture(str(avi_file))
            if not cap.isOpened():
                continue

            fps = float(cap.get(cv2.CAP_PROP_FPS))
            num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            rel_path = avi_file.relative_to(workspace_root).as_posix()
            pat_id = f"SYSU_{folder_name}_{avi_file.stem}"

            rec = {
                "patient_id": pat_id,
                "relative_path": rel_path,
                "label": standardized_label,
                "num_frames": num_frames,
                "fps": fps if fps > 0 else 10.0,
                "width": width,
                "height": height,
                "is_fixture_sample": True,  # 15 demo videos are for integration testing only
            }

            row = SYSUManifestRow(**rec)
            records.append(row.model_dump())

    df = pd.DataFrame(records)
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_manifest_path, index=False)

    stats = {
        "total_videos": len(df),
        "videos_by_class": df["label"].value_counts().to_dict() if len(df) else {},
        "is_complete_cohort": False,
        "note": "Local repository contains 15 demonstration videos (5 per class). Full 353 cohort requires access grant.",
    }

    return df, stats
