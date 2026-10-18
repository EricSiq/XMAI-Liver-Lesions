"""
SMC-LUD data audit, metadata join, and patient-stratified fold generation.
Strictly enforces:
- Clean no-caliper images only.
- Patient-level stratified 5-fold splitting (no patient in >1 fold).
- Exclusion of label-leaking fields (T-stage, tumor size, etc.).
- Image content hashing for duplicate detection.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from sklearn.model_selection import StratifiedKFold

from xmai.data.schemas import SMCManifestRow, assert_no_leakage_fields


def compute_file_sha256(filepath: Path) -> str:
    """Computes the SHA-256 hash of a file for exact duplicate auditing."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_and_clean_metadata(raw_smc_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parses and canonicalizes HCC and Hemangioma patient metadata tables.
    Returns mapping: patient_id -> {subject_id, age, age_missing, sex, sex_missing}
    """
    orig_root = raw_smc_root / "original_data"
    hcc_csv = orig_root / "HCC" / "HCC_patient_table.csv"
    hem_csv = orig_root / "Hemangioma" / "Hem_patient_table.csv"

    if not hcc_csv.exists() or not hem_csv.exists():
        raise FileNotFoundError(f"SMC patient tables not found in {orig_root}")

    patient_meta: Dict[str, Dict[str, Any]] = {}

    # 1. HCC Table
    hcc_df = pd.read_csv(hcc_csv)
    for _, row in hcc_df.iterrows():
        subj_val = row.get("Subject_id")
        if pd.isna(subj_val):
            continue
        subj_id = int(subj_val)
        pat_id = f"HCC_{subj_id}"

        age_val = row.get("age")
        age_missing = pd.isna(age_val)
        age = None if age_missing else float(age_val)

        sex_code = row.get("Sex")
        sex = "M" if sex_code == 1 else "F" if sex_code == 2 else None
        sex_missing = sex is None

        # Leakage barrier check on raw row
        assert_no_leakage_fields({"age": age, "sex": sex})

        patient_meta[pat_id] = {
            "subject_id": subj_id,
            "label": "HCC",
            "age": age,
            "age_missing": age_missing,
            "sex": sex,
            "sex_missing": sex_missing,
        }

    # 2. Hemangioma Table
    hem_df = pd.read_csv(hem_csv)
    # Detect age and sex columns due to multi-line header formatting in original CSV
    age_col = next(c for c in hem_df.columns if "age" in c.lower())
    sex_col = next(c for c in hem_df.columns if "sex" in c.lower())

    for _, row in hem_df.iterrows():
        subj_str = str(row.get("Subject_id", "")).strip()
        if not subj_str or pd.isna(row.get("Subject_id")):
            continue
        # subj_str is like "Hem_2", "Hem_4", etc.
        pat_id = subj_str
        try:
            subj_id = int(subj_str.split("_")[1])
        except (IndexError, ValueError):
            subj_id = -1

        age_val = row.get(age_col)
        age_missing = pd.isna(age_val)
        age = None if age_missing else float(age_val)

        sex_code = row.get(sex_col)
        sex = "M" if sex_code == 1 else "F" if sex_code == 2 else None
        sex_missing = sex is None

        assert_no_leakage_fields({"age": age, "sex": sex})

        patient_meta[pat_id] = {
            "subject_id": subj_id,
            "label": "Hemangioma",
            "age": age,
            "age_missing": age_missing,
            "sex": sex,
            "sex_missing": sex_missing,
        }

    return patient_meta


def generate_smc_manifest(
    workspace_root: Path,
    output_manifest_path: Path,
    seed: int = 42,
    exclude_unmatched: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Scans clean SMC images, joins metadata, generates patient-stratified folds,
    validates rows via SMCManifestRow, and writes output manifest CSV.
    """
    raw_smc_root = workspace_root / "SMC-LUD Liver Ultrasound Dataset (HCC vs Hemangioma)"
    orig_root = raw_smc_root / "original_data"

    patient_meta = load_and_clean_metadata(raw_smc_root)

    hcc_clean_dir = orig_root / "HCC" / "HCC_clean (wo caliper)"
    hem_clean_dir = orig_root / "Hemangioma" / "Hem_clean (wo caliper)"

    classes = [
        ("HCC", hcc_clean_dir),
        ("Hemangioma", hem_clean_dir),
    ]

    patient_records: List[Dict[str, Any]] = []
    image_records: List[Dict[str, Any]] = []
    unmatched_patients = []
    hash_to_images: Dict[str, List[str]] = {}

    for label, clean_dir in classes:
        if not clean_dir.exists():
            raise FileNotFoundError(f"Clean image directory not found: {clean_dir}")

        for pat_dir in sorted(clean_dir.iterdir()):
            if not pat_dir.is_dir():
                continue
            pat_id = pat_dir.name
            meta = patient_meta.get(pat_id)

            if meta is None:
                unmatched_patients.append(pat_id)
                if exclude_unmatched:
                    # In accordance with Decision AI-14: Hem_87 has no metadata match, exclude from manifest
                    continue
                else:
                    meta = {
                        "subject_id": -1,
                        "label": label,
                        "age": None,
                        "age_missing": True,
                        "sex": None,
                        "sex_missing": True,
                    }

            img_files = sorted([f for f in pat_dir.iterdir() if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg"}])
            if not img_files:
                continue

            patient_records.append({
                "patient_id": pat_id,
                "label": label,
                "image_count": len(img_files),
                "age": meta["age"],
                "age_missing": meta["age_missing"],
                "sex": meta["sex"],
                "sex_missing": meta["sex_missing"],
            })

            for img_file in img_files:
                rel_path = img_file.relative_to(workspace_root).as_posix()
                sha = compute_file_sha256(img_file)
                hash_to_images.setdefault(sha, []).append(rel_path)

                image_records.append({
                    "patient_id": pat_id,
                    "subject_id": meta["subject_id"],
                    "relative_path": rel_path,
                    "label": label,
                    "is_clean": True,
                    "age": meta["age"],
                    "age_missing": meta["age_missing"],
                    "sex": meta["sex"],
                    "sex_missing": meta["sex_missing"],
                    "image_sha256": sha,
                })

    # Stratified Patient-Level 5-Fold Splitting
    patient_df = pd.DataFrame(patient_records)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    patient_df["fold"] = -1

    for fold_idx, (_, val_indices) in enumerate(skf.split(patient_df["patient_id"], patient_df["label"])):
        patient_df.loc[val_indices, "fold"] = fold_idx

    pat_to_fold = dict(zip(patient_df["patient_id"], patient_df["fold"]))

    # Map fold assignments to each image row
    validated_rows = []
    for rec in image_records:
        rec["fold"] = pat_to_fold[rec["patient_id"]]
        # Validate schema
        row = SMCManifestRow(**rec)
        validated_rows.append(row.model_dump())

    manifest_df = pd.DataFrame(validated_rows)

    # Sort deterministically
    manifest_df = manifest_df.sort_values(by=["label", "patient_id", "relative_path"]).reset_index(drop=True)

    # Save to CSV
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_df.to_csv(output_manifest_path, index=False)

    # Duplicate hash audit
    duplicate_hashes = {h: paths for h, paths in hash_to_images.items() if len(paths) > 1}

    # Audit statistics
    audit_stats = {
        "manifest_file": str(output_manifest_path),
        "total_patients": len(patient_df),
        "total_images": len(manifest_df),
        "patients_by_class": patient_df["label"].value_counts().to_dict(),
        "images_by_class": manifest_df["label"].value_counts().to_dict(),
        "images_per_patient": {
            "min": int(patient_df["image_count"].min()),
            "median": float(patient_df["image_count"].median()),
            "max": int(patient_df["image_count"].max()),
        },
        "patients_missing_age": int(patient_df["age_missing"].sum()),
        "patients_missing_sex": int(patient_df["sex_missing"].sum()),
        "unmatched_folders": unmatched_patients,
        "duplicate_image_hashes_count": len(duplicate_hashes),
        "patients_per_fold": patient_df.groupby("fold")["label"].value_counts().unstack().to_dict(),
        "images_per_fold": manifest_df.groupby("fold")["label"].value_counts().unstack().to_dict(),
    }

    return manifest_df, audit_stats
