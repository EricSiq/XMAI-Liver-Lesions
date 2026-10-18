"""
Visual QA Contact Sheet Generator for XMAI.
Produces auditable contact sheets for each cohort:
1. SMC-LUD: B-mode images with patient ID, label, age, and sex annotations.
2. TCIA: Dual-panel comparison (raw DICOM frame, B-mode panel, CEUS panel).
3. SYSU: Temporal cine sequence (T=16 frames with timestamps).
4. AUL: Original ultrasound with overlaid rasterized liver and mass segmentations.

Satisfies Phase 2 Exit Gate in tasks.md.
"""

from pathlib import Path
import json
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import torch
import torchvision.transforms.functional as TF

from xmai.data.datasets import SMCDataset, SYSUDataset, TCIADataset, AULDataset


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = WORKSPACE_ROOT / "artifacts" / "contact_sheets"


def render_smc_contact_sheet(n_samples: int = 8):
    """Renders contact sheet of SMC-LUD images with clinical annotations."""
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "smc_manifest_v1.csv"
    if not manifest_path.exists():
        print("[SKIP] SMC manifest not found.")
        return

    df = pd.read_csv(manifest_path)
    # Pick 4 HCC and 4 Hemangioma samples
    hcc_samples = df[df["label"] == "HCC"].head(n_samples // 2)
    hem_samples = df[df["label"] == "Hemangioma"].head(n_samples // 2)
    selected_df = pd.concat([hcc_samples, hem_samples]).reset_index(drop=True)

    dataset = SMCDataset(selected_df, workspace_root=WORKSPACE_ROOT)

    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    fig.suptitle("SMC-LUD Cohort Visual QA Contact Sheet (B-mode Images & Patient Context)", fontsize=16, fontweight="bold")

    for idx, ax in enumerate(axes.flat):
        if idx >= len(dataset):
            ax.axis("off")
            continue
        sample = dataset[idx]
        img = sample["img"].numpy().transpose(1, 2, 0)
        # Denormalize ImageNet
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img = np.clip(img * std + mean, 0.0, 1.0)

        label_name = "HCC" if sample["label"].item() == 1 else "Hemangioma"
        pid = sample["patient_id"]
        row = selected_df.iloc[idx]
        age_str = f"Age: {int(row['age'])}" if pd.notna(row['age']) else "Age: Missing"
        sex_str = f"Sex: {row['sex']}"

        ax.imshow(img)
        ax.set_title(f"{pid} | {label_name}\n{age_str}, {sex_str}", fontsize=11)
        ax.axis("off")

    plt.tight_layout()
    out_file = OUTPUT_DIR / "smc_qa_contact_sheet.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[OK] SMC contact sheet saved to {out_file}")


def render_tcia_contact_sheet():
    """Renders dual-panel split visual verification for TCIA DICOM series."""
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "tcia_manifest_v1.csv"
    if not manifest_path.exists():
        print("[SKIP] TCIA manifest not found.")
        return

    df = pd.read_csv(manifest_path)
    usable_df = df[df["usable_for_eval"] == True].head(3).reset_index(drop=True)
    dataset = TCIADataset(usable_df, workspace_root=WORKSPACE_ROOT, num_frames=4)

    fig, axes = plt.subplots(len(usable_df), 3, figsize=(15, 4 * len(usable_df)))
    fig.suptitle("TCIA Dual-Panel Ultrasound Split QA (Raw Multi-Frame -> B-mode & CEUS Panels)", fontsize=16, fontweight="bold")

    col_titles = ["Full DICOM Frame", "Separated B-mode Panel (Left)", "Separated CEUS Panel (Right)"]
    for col_idx, title in enumerate(col_titles):
        axes[0, col_idx].set_title(title, fontsize=12, fontweight="bold")

    for row_idx in range(len(usable_df)):
        sample = dataset[row_idx]
        row = usable_df.iloc[row_idx]
        dcm_dir = WORKSPACE_ROOT / row["relative_path"]
        dcm_files = sorted(list(dcm_dir.glob("*.dcm")))
        if not dcm_files:
            continue
        
        import pydicom
        ds = pydicom.dcmread(dcm_files[0])
        raw_pixels = ds.pixel_array
        if raw_pixels.ndim == 4:
            first_frame = raw_pixels[0]
        elif raw_pixels.ndim == 3 and raw_pixels.shape[-1] not in {1, 3}:
            first_frame = raw_pixels[0]
        else:
            first_frame = raw_pixels

        b_frame = sample["bmode_frames"][0].numpy().transpose(1, 2, 0)
        c_frame = sample["ceus_frames"][0].numpy().transpose(1, 2, 0)

        # Plot full
        ax_full = axes[row_idx, 0]
        if first_frame.ndim == 2:
            ax_full.imshow(first_frame, cmap="gray")
        else:
            ax_full.imshow(first_frame)
        ax_full.set_ylabel(f"{sample['patient_id']}\n{sample['harmonized_diagnosis']}", fontsize=11, fontweight="bold")
        ax_full.axis("on")
        ax_full.set_xticks([])
        ax_full.set_yticks([])

        # Plot B-mode
        ax_b = axes[row_idx, 1]
        ax_b.imshow(np.clip(b_frame, 0.0, 1.0))
        ax_b.axis("off")

        # Plot CEUS
        ax_c = axes[row_idx, 2]
        ax_c.imshow(np.clip(c_frame, 0.0, 1.0))
        ax_c.axis("off")

    plt.tight_layout()
    out_file = OUTPUT_DIR / "tcia_qa_contact_sheet.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[OK] TCIA contact sheet saved to {out_file}")


def render_sysu_contact_sheet():
    """Renders temporal sequence of 16 sampled frames from a SYSU CEUS cine."""
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "sysu_demo_manifest_v1.csv"
    if not manifest_path.exists():
        print("[SKIP] SYSU manifest not found.")
        return

    df = pd.read_csv(manifest_path)
    dataset = SYSUDataset(df.head(1), workspace_root=WORKSPACE_ROOT, num_frames=16)
    sample = dataset[0]

    video = sample["video"].numpy()  # [16, 3, 224, 224]
    timestamps = sample["timestamps"].numpy()

    fig, axes = plt.subplots(2, 8, figsize=(20, 6))
    fig.suptitle(f"SYSU-CEUS Video Cine Sequence QA ({sample['patient_id']} | {sample['label_name']} | T=16 Uniform Frames)", fontsize=16, fontweight="bold")

    mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)

    for idx, ax in enumerate(axes.flat):
        frame = video[idx] * std + mean
        frame = np.clip(frame.transpose(1, 2, 0), 0.0, 1.0)

        ax.imshow(frame)
        ax.set_title(f"t={timestamps[idx]:.2f}s", fontsize=10)
        ax.axis("off")

    plt.tight_layout()
    out_file = OUTPUT_DIR / "sysu_qa_contact_sheet.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[OK] SYSU contact sheet saved to {out_file}")


def render_aul_contact_sheet(n_samples: int = 4):
    """Renders AUL images with rasterized liver and mass segmentation mask overlays."""
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "aul_manifest_v1.csv"
    if not manifest_path.exists():
        print("[SKIP] AUL manifest not found.")
        return

    df = pd.read_csv(manifest_path)
    selected_df = df[df["has_mass_mask"] == True].head(n_samples).reset_index(drop=True)
    dataset = AULDataset(selected_df, workspace_root=WORKSPACE_ROOT, image_size=224)

    fig, axes = plt.subplots(n_samples, 3, figsize=(12, 4 * n_samples))
    fig.suptitle("AUL Ultrasound Segmentation QA (Raw Image vs. Liver & Mass Masks vs. Overlay)", fontsize=16, fontweight="bold")

    col_titles = ["Ultrasound Image", "Binary Masks (Liver=Green, Mass=Red)", "Combined Overlay"]
    for col_idx, title in enumerate(col_titles):
        axes[0, col_idx].set_title(title, fontsize=12, fontweight="bold")

    mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)

    for idx in range(n_samples):
        sample = dataset[idx]
        img_np = sample["img"].numpy() * std + mean
        img_np = np.clip(img_np.transpose(1, 2, 0), 0.0, 1.0)

        liver_m = sample["liver_mask"].squeeze(0).numpy()
        mass_m = sample["mass_mask"].squeeze(0).numpy()

        # 1. Raw Image
        axes[idx, 0].imshow(img_np)
        axes[idx, 0].set_ylabel(f"{sample['image_id']}\n({sample['class_name']})", fontsize=11, fontweight="bold")
        axes[idx, 0].axis("on")
        axes[idx, 0].set_xticks([])
        axes[idx, 0].set_yticks([])

        # 2. Binary mask RGB visualization (Liver = Green, Mass = Red)
        mask_rgb = np.zeros((*liver_m.shape, 3), dtype=np.float32)
        mask_rgb[:, :, 1] = liver_m * 0.7  # Green
        mask_rgb[:, :, 0] = mass_m * 0.9   # Red
        axes[idx, 1].imshow(mask_rgb)
        axes[idx, 1].axis("off")

        # 3. Blended Overlay
        overlay = img_np.copy()
        # Add red tint where mass is present
        overlay[:, :, 0] = np.where(mass_m > 0, np.clip(overlay[:, :, 0] + 0.4, 0, 1), overlay[:, :, 0])
        # Add green tint where liver is present (but not mass)
        overlay[:, :, 1] = np.where((liver_m > 0) & (mass_m == 0), np.clip(overlay[:, :, 1] + 0.3, 0, 1), overlay[:, :, 1])
        axes[idx, 2].imshow(overlay)
        axes[idx, 2].axis("off")

    plt.tight_layout()
    out_file = OUTPUT_DIR / "aul_qa_contact_sheet.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[OK] AUL contact sheet saved to {out_file}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("--- Rendering Visual QA Contact Sheets for Phase 2 Exit Gate ---")
    render_smc_contact_sheet()
    render_tcia_contact_sheet()
    render_sysu_contact_sheet()
    render_aul_contact_sheet()
    print("--- All Contact Sheets Rendered Successfully ---")


if __name__ == "__main__":
    main()
