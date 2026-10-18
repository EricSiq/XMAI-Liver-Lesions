"""
TCIA B-mode and CEUS Liver manifest generation and metadata audit.
Records DICOM series, harmonized labels, and flags usable cohorts.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd
import pydicom

from xmai.data.schemas import TCIAManifestRow


def generate_tcia_manifest(
    workspace_root: Path,
    output_manifest_path: Path,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Audits TCIA subjects, links harmonized reference standards,
    and writes the Track C evaluation manifest.
    """
    tcia_root = workspace_root / "TCIA"
    labels_csv = tcia_root / "tcia_labels_harmonized.csv"
    dcm_dir = tcia_root / "b_mode_and_ceus_liver"

    if not labels_csv.exists() or not dcm_dir.exists():
        raise FileNotFoundError(f"TCIA files not found in {tcia_root}")

    labels_df = pd.read_csv(labels_csv)
    # Map by PatientID
    label_map = labels_df.set_index("PatientID").to_dict(orient="index")

    records: List[Dict[str, Any]] = []

    for pat_folder in sorted([p for p in dcm_dir.iterdir() if p.is_dir()]):
        pat_id = pat_folder.name
        meta = label_map.get(pat_id, {})

        dcm_files = sorted(list(pat_folder.glob("**/*.dcm")))
        if not dcm_files:
            continue

        # Group by series (parent directory of dcm)
        series_dirs = sorted(list({f.parent for f in dcm_files}))

        for s_dir in series_dirs:
            series_files = sorted(list(s_dir.glob("*.dcm")))
            if not series_files:
                continue

            sample_dcm = series_files[0]
            try:
                ds = pydicom.dcmread(sample_dcm, stop_before_pixels=True)
                sop_class = str(getattr(ds, "SOPClassUID", "Unknown"))
                series_uid = str(getattr(ds, "SeriesInstanceUID", s_dir.name))
                num_frames = int(getattr(ds, "NumberOfFrames", len(series_files)))
            except Exception:
                sop_class = "Unknown"
                series_uid = s_dir.name
                num_frames = len(series_files)

            is_multiframe = num_frames > 1
            rel_path = s_dir.relative_to(workspace_root).as_posix()

            rec = {
                "patient_id": pat_id,
                "study_date": str(meta.get("StudyDate", "")),
                "series_uid": series_uid,
                "relative_path": rel_path,
                "raw_diagnosis": str(meta.get("dx_raw", "Unknown")),
                "harmonized_diagnosis": str(meta.get("dx_harmonized", "Unknown")),
                "modality": "US",
                "sop_class_uid": sop_class,
                "is_multiframe": is_multiframe,
                "num_frames": num_frames,
                "usable_for_eval": bool(meta.get("usable_single_label", True)),
            }

            row = TCIAManifestRow(**rec)
            records.append(row.model_dump())

    df = pd.DataFrame(records)
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_manifest_path, index=False)

    stats = {
        "total_series": len(df),
        "total_patients": df["patient_id"].nunique(),
        "diagnoses_count": df.groupby("patient_id")["harmonized_diagnosis"].first().value_counts().to_dict(),
        "multiframe_series_count": int(df["is_multiframe"].sum()),
    }

    return df, stats
