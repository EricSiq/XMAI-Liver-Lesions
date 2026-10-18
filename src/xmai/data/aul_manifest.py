"""
AUL Ultrasound Liver dataset manifest generation.
Catalogs images and matching liver and lesion/mass segmentation polygon JSONs.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd

from xmai.data.schemas import AULLabel, AULManifestRow


def generate_aul_manifest(
    workspace_root: Path,
    output_manifest_path: Path,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Scans AUL images and segmentation polygon JSON files,
    validates with AULManifestRow, and writes output manifest CSV.
    """
    aul_root = workspace_root / "AUL" / "7272660"
    if not aul_root.exists():
        raise FileNotFoundError(f"AUL dataset root not found at {aul_root}")

    classes: List[AULLabel] = ["Benign", "Malignant", "Normal"]
    records: List[Dict[str, Any]] = []

    for class_name in classes:
        base_dir = aul_root / class_name / class_name
        img_dir = base_dir / "image"
        seg_dir = base_dir / "segmentation"

        if not img_dir.exists():
            continue

        for img_file in sorted(img_dir.glob("*.*")):
            if img_file.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
                continue

            stem = img_file.stem
            liver_json = seg_dir / "liver" / f"{stem}.json"
            mass_json = seg_dir / "mass" / f"{stem}.json"

            rel_img = img_file.relative_to(workspace_root).as_posix()
            rel_liver = liver_json.relative_to(workspace_root).as_posix() if liver_json.exists() else None
            rel_mass = mass_json.relative_to(workspace_root).as_posix() if mass_json.exists() else None

            rec = {
                "image_id": f"AUL_{class_name}_{stem}",
                "relative_image_path": rel_img,
                "class_name": class_name,
                "relative_liver_json": rel_liver,
                "relative_mass_json": rel_mass,
                "has_mass_mask": rel_mass is not None,
            }

            row = AULManifestRow(**rec)
            records.append(row.model_dump())

    df = pd.DataFrame(records)
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_manifest_path, index=False)

    stats = {
        "total_images": len(df),
        "images_by_class": df["class_name"].value_counts().to_dict(),
        "images_with_mass_masks": int(df["has_mass_mask"].sum()),
    }

    return df, stats
