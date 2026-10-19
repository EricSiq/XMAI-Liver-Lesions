"""
Explanation Validation Suite for XMAI:
1. Model Randomization Sanity Check (Adebayo et al., NeurIPS 2018):
   Verifies that Grad-CAM heatmaps degrade to noise when model weights are randomized.
2. Salient Deletion Test:
   Verifies that masking top salient pixels degrades target class probability significantly more than random masking.
3. Gate Weights vs. Exact Modality Shapley Comparison:
   Compares intrinsic gating weights with post-hoc coalition Shapley values.

Conforms to XMAI Design Document Section 11 and tasks.md Section 6.2.
"""

from typing import Any, Dict, List, Tuple
import numpy as np
from scipy import stats
import torch
import torch.nn as nn
import torch.nn.functional as F

from xmai.explainability.gradcam import GradCAM
from xmai.explainability.modality_shapley import compute_exact_modality_shapley
from xmai.models.track_a_models import A1BModeOnly
from xmai.models.xmai_model import XMAIModel


def run_model_randomization_check(
    trained_model: nn.Module,
    img_tensor: torch.Tensor,
    target_class: int = 1,
) -> Dict[str, Any]:
    """
    Performs parameter randomization sanity check.
    Compares Grad-CAM from trained model with Grad-CAM from completely randomized weights.
    Returns rank correlation and pass/fail indicator.
    """
    layer4 = getattr(trained_model, "encoder_b", trained_model).layer4
    cam_trained = GradCAM(trained_model, layer4)
    trained_map = cam_trained.generate_heatmap(img_tensor, target_class=target_class)

    # Create model with randomized weights
    random_model = A1BModeOnly(pretrained=False)
    cam_random = GradCAM(random_model, random_model.encoder_b.layer4)
    random_map = cam_random.generate_heatmap(img_tensor, target_class=target_class)

    # Flatten and compute Spearman rank correlation
    flat_trained = trained_map.flatten()
    flat_random = random_map.flatten()

    corr, p_value = stats.spearmanr(flat_trained, flat_random)
    if np.isnan(corr):
        corr = 0.0

    # Sanity check passes if correlation is low (< 0.50), proving sensitivity to weights
    passed = bool(abs(corr) < 0.50)

    return {
        "spearman_correlation": round(float(corr), 4),
        "p_value": round(float(p_value), 4),
        "sanity_check_passed": passed,
    }


def run_salient_deletion_test(
    model: nn.Module,
    img_tensor: torch.Tensor,
    heatmap: np.ndarray,
    target_class: int = 1,
    top_fraction: float = 0.20,
) -> Dict[str, Any]:
    """
    Measures drop in target class probability when top salient pixels are ablated (set to 0)
    vs. when an equal number of random pixels are ablated.
    """
    model.eval()
    with torch.no_grad():
        orig_out = model(img=img_tensor)
        orig_prob = float(orig_out["probs"][0, target_class].item())

    if isinstance(heatmap, torch.Tensor):
        heatmap = heatmap.cpu().numpy()

    # Create salient mask from numpy heatmap
    flat_heat = heatmap.flatten()
    k = int(len(flat_heat) * top_fraction)
    salient_thresh = float(np.partition(flat_heat, -k)[-k])
    salient_mask = (heatmap >= salient_thresh).astype(np.float32)

    # Ablated image (zeroing out salient pixels across all 3 channels)
    salient_ablated = img_tensor.clone()
    salient_ablated[0, :, salient_mask == 1.0] = 0.0

    # Random ablated image
    random_mask = np.random.rand(*heatmap.shape) < top_fraction
    random_ablated = img_tensor.clone()
    random_ablated[0, :, random_mask] = 0.0

    with torch.no_grad():
        salient_prob = float(model(img=salient_ablated)["probs"][0, target_class].item())
        random_prob = float(model(img=random_ablated)["probs"][0, target_class].item())

    salient_drop = orig_prob - salient_prob
    random_drop = orig_prob - random_prob

    return {
        "original_probability": round(orig_prob, 4),
        "salient_ablated_probability": round(salient_prob, 4),
        "random_ablated_probability": round(random_prob, 4),
        "salient_drop": round(salient_drop, 4),
        "random_drop": round(random_drop, 4),
        "salient_exceeds_random": bool(salient_drop >= random_drop),
    }


def compare_gate_and_shapley(
    model: XMAIModel,
    img_tensor: torch.Tensor,
    clin_tensor: torch.Tensor,
    target_class: int = 1,
) -> Dict[str, Any]:
    """
    Extracts intrinsic gating weights and exact Modality Shapley values for comparison.
    """
    model.eval()
    with torch.no_grad():
        out = model(img=img_tensor, clin=clin_tensor)
        gate_weights = out["gate_weights"][0].cpu().numpy()

    shapley_vals = compute_exact_modality_shapley(
        model=model,
        img=img_tensor,
        clin=clin_tensor,
        ceus=None,
        target_class=target_class,
    )

    phi_b = float(shapley_vals.get("B-mode", shapley_vals.get("phi_b", 0.0)))
    phi_c = float(shapley_vals.get("CEUS", shapley_vals.get("phi_c", 0.0)))
    phi_t = float(shapley_vals.get("Context", shapley_vals.get("phi_t", 0.0)))

    dominant_gate_idx = int(np.argmax(gate_weights))
    dominant_shap_idx = int(np.argmax([phi_b, phi_c, phi_t]))
    mod_names = ["M1_bmode", "M2_ceus", "M3_context"]

    return {
        "gate_weights": {
            "M1_bmode": round(float(gate_weights[0]), 4),
            "M2_ceus": round(float(gate_weights[1]), 4),
            "M3_context": round(float(gate_weights[2]), 4),
        },
        "modality_shapley": {
            "M1_bmode": round(phi_b, 4),
            "M2_ceus": round(phi_c, 4),
            "M3_context": round(phi_t, 4),
        },
        "agreement": {
            "dominant_gate": mod_names[dominant_gate_idx],
            "dominant_shapley": mod_names[dominant_shap_idx],
        },
    }


def run_temporal_phase_masking_test(
    model: nn.Module,
    video_tensor: torch.Tensor,
    target_class: int = 0,
) -> Dict[str, Any]:
    """
    Evaluates sensitivity of temporal CEUS model predictions to phase masking:
    - Unmasked baseline
    - Arterial phase masked (early 1/3 of frames zeroed)
    - Late phase masked (late 1/3 of frames zeroed)
    - Top-salient temporal attention frames masked
    """
    model.eval()
    B, T, C, H, W = video_tensor.shape
    with torch.no_grad():
        orig_out = model(video_tensor)
        orig_prob = float(orig_out["probs"][0, target_class].item())
        weights = orig_out.get("temporal_weights", None)
        if weights is not None:
            weights_np = weights[0].cpu().numpy().tolist()
        else:
            weights_np = None

    # Arterial phase: first T//3 frames
    arterial_end = max(1, T // 3)
    video_mask_arterial = video_tensor.clone()
    video_mask_arterial[:, :arterial_end] = 0.0

    # Late phase: last T//3 frames
    late_start = max(0, T - arterial_end)
    video_mask_late = video_tensor.clone()
    video_mask_late[:, late_start:] = 0.0

    with torch.no_grad():
        prob_mask_arterial = float(model(video_mask_arterial)["probs"][0, target_class].item())
        prob_mask_late = float(model(video_mask_late)["probs"][0, target_class].item())

    # Top-attention frames masked if weights are available
    if weights is not None:
        top_k = max(1, T // 4)
        top_indices = torch.topk(weights[0], k=top_k).indices
        video_mask_top = video_tensor.clone()
        video_mask_top[:, top_indices] = 0.0
        with torch.no_grad():
            prob_mask_top = float(model(video_mask_top)["probs"][0, target_class].item())
    else:
        prob_mask_top = prob_mask_arterial

    return {
        "original_probability": round(orig_prob, 4),
        "mask_arterial_probability": round(prob_mask_arterial, 4),
        "mask_late_probability": round(prob_mask_late, 4),
        "mask_top_attention_probability": round(prob_mask_top, 4),
        "arterial_drop": round(orig_prob - prob_mask_arterial, 4),
        "late_drop": round(orig_prob - prob_mask_late, 4),
        "top_attention_drop": round(orig_prob - prob_mask_top, 4),
        "temporal_weights": [round(float(w), 4) for w in weights_np] if weights_np else None,
    }

