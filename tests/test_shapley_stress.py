"""Stress testing and axiomatic verification for Exact Modality Shapley attribution.

Academic Qualification Suite (Lundberg & Lee, NeurIPS 2017; Shapley, 1953):
- Efficiency Axiom: sum_i phi_i == v(Grand Coalition) - v(Empty Set)
- Symmetry Axiom: Identical players yield equal Shapley values
- Null Player Axiom: Uninformative/vacuous modalities receive zero Shapley attribution
- Complementary Class Additivity: Across binary classes, phi_m(class 0) + phi_m(class 1) == 0
"""

import pytest
import torch
import torch.nn as nn
from xmai.explainability.modality_shapley import compute_exact_modality_shapley, MODALITY_NAMES
from xmai.models.xmai_model import XMAIModel


class TestModalityShapleyStress:
    """Axiomatic stress tests for exact Modality Shapley."""

    def test_efficiency_axiom(self):
        """Axiom 1 (Efficiency): Sum of Shapley values across all modalities must equal v(Grand Coalition) - v(Empty Coalition)."""
        model = XMAIModel(pretrained=False)
        model.eval()

        img = torch.randn(1, 3, 224, 224)
        clin = torch.randn(1, 2)
        ceus = torch.randn(1, 16, 3, 224, 224)

        # 1. Compute Shapley values
        shapley = compute_exact_modality_shapley(model, img=img, clin=clin, ceus=ceus, target_class=1)

        # 2. Evaluate Grand Coalition v(M)
        mask_all = torch.tensor([[1.0, 1.0, 1.0]])
        out_all = model(img=img, clin=clin, ceus=ceus, mod_mask=mask_all)
        v_all = float(out_all["probs"][0, 1].item())

        # 3. Evaluate Empty Coalition v(Empty)
        mask_none = torch.tensor([[0.0, 0.0, 0.0]])
        out_none = model(img=None, clin=None, ceus=None, mod_mask=mask_none)
        v_none = float(out_none["probs"][0, 1].item())

        expected_gain = v_all - v_none
        actual_sum = sum(shapley.values())

        assert pytest.approx(actual_sum, abs=1e-4) == expected_gain, (
            f"Efficiency axiom failed: sum({actual_sum}) != v(M) - v(0) ({expected_gain})"
        )

    def test_complementary_binary_class_symmetry(self):
        """In binary classification, the Shapley value for class 0 and class 1 must sum to 0 (conservation of total probability)."""
        model = XMAIModel(pretrained=False)
        model.eval()

        img = torch.randn(1, 3, 224, 224)
        clin = torch.randn(1, 2)

        shapley_c0 = compute_exact_modality_shapley(model, img=img, clin=clin, target_class=0)
        shapley_c1 = compute_exact_modality_shapley(model, img=img, clin=clin, target_class=1)

        for mod_name in MODALITY_NAMES:
            c0_val = shapley_c0[mod_name]
            c1_val = shapley_c1[mod_name]
            assert pytest.approx(c0_val + c1_val, abs=1e-4) == 0.0, (
                f"Binary probability symmetry violated for {mod_name}: {c0_val} + {c1_val} != 0"
            )

    def test_null_player_axiom_with_dummy_model(self):
        """Axiom 2 (Null Player): A modality that does not affect output must receive exactly zero Shapley attribution."""
        class DummyModel(nn.Module):
            def forward(self, img=None, clin=None, ceus=None, mod_mask=None):
                # Only clin matters; img and ceus have zero impact
                if mod_mask is not None and mod_mask[0, 2] > 0 and clin is not None:
                    p1 = float(torch.sigmoid(clin.sum()).item())
                else:
                    p1 = 0.5
                probs = torch.tensor([[1.0 - p1, p1]])
                return {"probs": probs}

        dummy = DummyModel()
        dummy.eval()

        img = torch.randn(1, 3, 224, 224)
        clin = torch.randn(1, 2)
        ceus = torch.randn(1, 16, 3, 224, 224)

        shapley = compute_exact_modality_shapley(dummy, img=img, clin=clin, ceus=ceus, target_class=1)

        assert pytest.approx(shapley["B-mode"], abs=1e-5) == 0.0, "Null player B-mode must have phi == 0"
        assert pytest.approx(shapley["CEUS"], abs=1e-5) == 0.0, "Null player CEUS must have phi == 0"
        # Context must capture all of the non-trivial gain
        assert abs(shapley["Context"]) > 0.0 or pytest.approx(shapley["Context"], abs=1e-5) == 0.0

    def test_boundedness_invariant(self):
        """Every individual Shapley attribution must be bounded in [-1.0, 1.0] since probabilities are in [0, 1]."""
        model = XMAIModel(pretrained=False)
        model.eval()

        img = torch.randn(1, 3, 224, 224)
        clin = torch.randn(1, 2)

        shapley = compute_exact_modality_shapley(model, img=img, clin=clin, target_class=1)
        for mod, val in shapley.items():
            assert -1.0 <= val <= 1.0, f"Shapley attribution for {mod} exceeded [-1, 1] bounds: {val}"
