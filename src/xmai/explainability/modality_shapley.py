"""
Exact Modality Shapley Value Computation.
Computes exact Shapley values across the 2^3 = 8 modality coalitions
by masking modality availability in the mask-aware fusion architecture.
Conforms to XMAI Design Document Section 8.1.
"""

from itertools import combinations
import math
from typing import Dict, List, Optional
import torch
import torch.nn as nn


MODALITY_NAMES = ["B-mode", "CEUS", "Context"]


def compute_exact_modality_shapley(
    model: nn.Module,
    img: Optional[torch.Tensor],
    clin: Optional[torch.Tensor],
    ceus: Optional[torch.Tensor] = None,
    target_class: int = 1,
) -> Dict[str, float]:
    """
    Computes exact Shapley attribution for each modality (B-mode, CEUS, Context)
    for predicting target_class probability.
    Uses exactly 2^3 = 8 forward evaluations.
    """
    model.eval()
    M = [0, 1, 2]  # Indices of modalities: 0=B-mode, 1=CEUS, 2=Context
    n = len(M)

    # 1. Evaluate value function v(S) for all 2^3 = 8 subsets
    v_cache: Dict[tuple, float] = {}

    with torch.no_grad():
        for k in range(n + 1):
            for subset in combinations(M, k):
                # Construct modality mask
                mask = [0.0, 0.0, 0.0]
                for idx in subset:
                    mask[idx] = 1.0

                mask_tensor = torch.tensor([mask], dtype=torch.float32)
                try:
                    device = next(model.parameters()).device
                except StopIteration:
                    if img is not None:
                        device = img.device
                    elif clin is not None:
                        device = clin.device
                    elif ceus is not None:
                        device = ceus.device
                    else:
                        device = torch.device("cpu")
                mask_tensor = mask_tensor.to(device)

                img_in = img.to(device) if (0 in subset and img is not None) else None
                ceus_in = ceus.to(device) if (1 in subset and ceus is not None) else None
                clin_in = clin.to(device) if (2 in subset and clin is not None) else None

                out = model(img=img_in, clin=clin_in, ceus=ceus_in, mod_mask=mask_tensor)
                prob = float(out["probs"][0, target_class].item())
                v_cache[subset] = prob

    # 2. Compute Shapley value for each modality m
    shapley_values: Dict[str, float] = {}

    for m in M:
        phi_m = 0.0
        rest = [x for x in M if x != m]

        for s_len in range(len(rest) + 1):
            for S in combinations(rest, s_len):
                S_with_m = tuple(sorted(list(S) + [m]))
                weight = (math.factorial(len(S)) * math.factorial(n - len(S) - 1)) / math.factorial(n)
                marginal_contribution = v_cache[S_with_m] - v_cache[S]
                phi_m += weight * marginal_contribution

        mod_name = MODALITY_NAMES[m]
        shapley_values[mod_name] = round(phi_m, 6)

    return shapley_values
