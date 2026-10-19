"""
Visual Explanation Card Generator for XMAI.
Produces comprehensive multimodal explanation cards:
- Ultrasound B-mode Image
- ResNet-18 Layer4 Grad-CAM Heatmap Overlay
- Intrinsic Gating Weights & Exact Modality Shapley Attributions
- Clinical Demographic Context (Age, Sex)
- Calibrated Diagnostic Confidence & Margin

Saves artifacts to artifacts/explanation_cards/.
Conforms to tasks.md Section 6.1.
"""

from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import torch
import torchvision.transforms.functional as TF

from xmai.data.clinical import ClinicalFeatureProcessor
from xmai.data.datasets import SMCDataset, INT_TO_LABEL
from xmai.explainability.card import ExplanationCard
from xmai.explainability.gradcam import GradCAM
from xmai.explainability.modality_shapley import compute_exact_modality_shapley
from xmai.models.track_a_models import create_track_a_model


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = WORKSPACE_ROOT / "artifacts" / "explanation_cards"


def render_visual_card(
    patient_id: str,
    img_tensor: torch.Tensor,
    clin_tensor: torch.Tensor,
    row: pd.Series,
    model: torch.nn.Module,
    cam: GradCAM,
    out_file: Path,
):
    """Renders a 4-panel visual explanation card."""
    model.eval()
    with torch.no_grad():
        out = model(img=img_tensor, clin=clin_tensor)
        probs = out["probs"][0].cpu().numpy()
        gates = out["gate_weights"][0].cpu().numpy()

    p_hem, p_hcc = float(probs[0]), float(probs[1])
    pred_label = "HCC" if p_hcc >= p_hem else "Hemangioma"
    true_label = row["label"]
    margin = abs(p_hcc - p_hem)

    target_class = 1 if pred_label == "HCC" else 0
    heatmap = cam.generate_heatmap(img_tensor, target_class=target_class, clin_tensor=clin_tensor)

    # Exact Modality Shapley
    shapley = compute_exact_modality_shapley(
        model=model,
        img=img_tensor,
        clin=clin_tensor,
        ceus=None,
        target_class=target_class,
    )

    # Denormalize ImageNet
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    raw_img = img_tensor[0].cpu().numpy().transpose(1, 2, 0)
    raw_img = np.clip(raw_img * std + mean, 0.0, 1.0)

    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    fig.suptitle(f"XMAI Clinical Explanation Card: Patient {patient_id} ({true_label})", fontsize=15, fontweight="bold")

    # Panel 1: Original B-mode image
    axes[0].imshow(raw_img)
    age_val = int(row['age']) if pd.notna(row['age']) else 'Missing'
    axes[0].set_title(f"B-mode Ultrasound\nAge: {age_val} | Sex: {row['sex']}", fontsize=11)
    axes[0].axis("off")

    # Panel 2: Grad-CAM Overlay
    axes[1].imshow(raw_img)
    axes[1].imshow(heatmap, cmap="jet", alpha=0.45)
    axes[1].set_title(f"Layer4 Grad-CAM Saliency\n(Target: {pred_label})", fontsize=11)
    axes[1].axis("off")

    # Panel 3: Calibrated Probabilities & Margin
    labels = ["Hemangioma", "HCC"]
    colors = ["#4A90E2", "#E94E77"]
    y_pos = np.arange(len(labels))
    axes[2].barh(y_pos, [p_hem, p_hcc], color=colors, height=0.5)
    axes[2].set_yticks(y_pos)
    axes[2].set_yticklabels(labels, fontsize=11)
    axes[2].set_xlim(0, 1.0)
    axes[2].set_title(f"Prediction: {pred_label}\nMargin: {margin:.3f}", fontsize=11)
    for i, v in enumerate([p_hem, p_hcc]):
        axes[2].text(v + 0.02, i, f"{v * 100:.1f}%", va="center", fontweight="bold")

    # Panel 4: Modality Shapley & Gate Weights
    mods = ["B-mode (M1)", "CEUS (M2)", "Context (M3)"]
    shap_vals = [shapley.get("B-mode", 0.0), shapley.get("CEUS", 0.0), shapley.get("Context", 0.0)]
    bar_colors = ["#2ECC71" if val >= 0 else "#E74C3C" for val in shap_vals]
    x_pos = np.arange(len(mods))
    axes[3].bar(x_pos, shap_vals, color=bar_colors, width=0.45)
    axes[3].axhline(0, color="gray", linestyle="--", linewidth=0.8)
    axes[3].set_xticks(x_pos)
    axes[3].set_xticklabels(mods, fontsize=10)
    axes[3].set_ylabel(f"Delta P({pred_label})", fontsize=10)
    axes[3].set_title(f"Exact Modality Shapley\nGates: B={gates[0]:.2f}, C={gates[1]:.2f}, T={gates[2]:.2f}", fontsize=10)

    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[OK] Visual explanation card saved to {out_file.name}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Generating Explanation Cards [Device: {device}] ===")

    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "smc_manifest_v1.csv"
    df = pd.read_csv(manifest_path)

    ckpt_path = WORKSPACE_ROOT / "results" / "track_a" / "checkpoint_A4_fold_0.pt"
    model = create_track_a_model("A4", pretrained=True).to(device)
    if ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state"] if "model_state" in ckpt else ckpt, strict=False)
        print(f"Loaded trained A4 checkpoint: {ckpt_path.name}")

    cam = GradCAM(model, model.encoder_b.layer4)

    # Select representative cases: 2 HCC and 2 Hemangioma
    sample_patients = [
        ("HCC_Case_1", df[df["label"] == "HCC"].iloc[0]),
        ("HCC_Case_2", df[df["label"] == "HCC"].iloc[5]),
        ("Hemangioma_Case_1", df[df["label"] == "Hemangioma"].iloc[0]),
        ("Hemangioma_Case_2", df[df["label"] == "Hemangioma"].iloc[5]),
    ]

    clin_proc = ClinicalFeatureProcessor().fit(df)

    for case_name, row in sample_patients:
        pid = row["patient_id"]
        rel_path = row["relative_path"]
        abs_path = WORKSPACE_ROOT / rel_path

        from xmai.data.transforms import load_bmode_image, get_bmode_transforms
        transform = get_bmode_transforms(is_train=False, image_size=224)
        img_tensor, _ = load_bmode_image(str(abs_path), transform=transform)
        img_tensor = img_tensor.unsqueeze(0).to(device)

        clin_feat, _ = clin_proc.transform_row(row)
        clin_tensor = clin_feat.unsqueeze(0).to(device)

        out_file = OUTPUT_DIR / f"explanation_card_{case_name}.png"
        render_visual_card(pid, img_tensor, clin_tensor, row, model, cam, out_file)

    print(f"\n[OK] All explanation cards generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
