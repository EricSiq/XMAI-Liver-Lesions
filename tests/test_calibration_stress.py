"""Stress tests and mathematical invariant verification for Temperature Scaling and Calibration.

Academic Qualification Suite:
- Invariant: Temperature scaling strictly preserves argmax classification ranking (monotone bijection)
- Invariant: Clamping guards prevent divide-by-zero when T -> 0
- Invariant: As T -> inf, probability vector uniformly approaches 1/K simplex center
- Invariant: ECE bounded strictly in [0, 1] with zero-error on perfectly calibrated distributions
"""

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from xmai.training.calibration import TemperatureScaler
from xmai.evaluation.metrics import compute_ece


class TestTemperatureScalerStress:
    """Stress testing TemperatureScaler invariants."""

    def test_rank_preservation_invariant(self):
        """Temperature scaling must never alter the relative ordering of logits (top-1 argmax invariant)."""
        scaler = TemperatureScaler()
        scaler.temperature.data = torch.tensor([2.5])  # Artificially set high temperature

        logits = torch.randn(20, 5)
        scaled_logits = scaler(logits)

        orig_rank = torch.argsort(logits, dim=-1, descending=True)
        scaled_rank = torch.argsort(scaled_logits, dim=-1, descending=True)

        assert torch.equal(orig_rank, scaled_rank), "Temperature scaling must be a strictly monotonic order-preserving transform."

    def test_zero_and_negative_temperature_guard(self):
        """Temperatures <= 0 must be clamped to min=0.01 to prevent division by zero or negative inversions."""
        scaler = TemperatureScaler()
        scaler.temperature.data = torch.tensor([-1.5])  # Negative temperature

        logits = torch.tensor([[2.0, -1.0], [0.5, 1.2]])
        scaled = scaler(logits)

        assert torch.isfinite(scaled).all()
        # Clamped at 0.01, so scaling factor is 100x
        assert pytest.approx(scaled[0, 0].item(), rel=1e-3) == 200.0

    def test_high_temperature_uniform_limit(self):
        """As temperature approaches infinity, softmax probabilities must converge to 1/K uniform distribution."""
        scaler = TemperatureScaler()
        scaler.temperature.data = torch.tensor([1e5])

        logits = torch.tensor([[10.0, -5.0, 2.0], [1.0, 100.0, 0.0]])
        scaled = scaler(logits)
        probs = F.softmax(scaled, dim=-1)

        expected_uniform = 1.0 / 3.0
        assert torch.allclose(probs, torch.full_like(probs, expected_uniform), atol=1e-3)

    def test_optimization_convergence_on_overconfident_logits(self):
        """L-BFGS optimization must reduce negative log-likelihood on overconfident validation sets."""
        scaler = TemperatureScaler()

        # Create overconfident synthetic logits
        torch.manual_seed(42)
        val_labels = torch.randint(0, 2, (100,))
        # True class gets logit 5.0, false class gets -5.0, with some noise
        val_logits = torch.zeros(100, 2)
        for i, y in enumerate(val_labels):
            # Inject noise so true accuracy is 75%, but confidence is ~99%
            if torch.rand(1).item() < 0.75:
                val_logits[i, y] = 6.0
                val_logits[i, 1 - y] = -2.0
            else:
                val_logits[i, y] = -2.0
                val_logits[i, 1 - y] = 6.0

        initial_nll = F.cross_entropy(scaler(val_logits), val_labels).item()
        opt_t = scaler.fit(val_logits, val_labels, max_iter=30)
        calibrated_nll = F.cross_entropy(scaler(val_logits), val_labels).item()

        assert opt_t > 1.0, f"Overconfident predictions must drive temperature > 1.0, got {opt_t}"
        assert calibrated_nll <= initial_nll, "Calibrated NLL must be less than or equal to initial NLL"


class TestExpectedCalibrationErrorStress:
    """Stress testing Expected Calibration Error (ECE) metric."""

    def test_perfect_calibration_bounds(self):
        """Perfectly calibrated probabilities must yield ECE == 0.0."""
        # 100 samples with probability 0.8, exactly 80 are positive
        y_prob = np.full(100, 0.8)
        y_true = np.zeros(100)
        y_true[:80] = 1.0

        ece = compute_ece(y_true, y_prob, n_bins=10)
        assert pytest.approx(ece, abs=1e-5) == 0.0

    def test_complete_miscalibration_bounds(self):
        """Completely miscalibrated predictions (confident 1.0, all false) must yield ECE == 1.0."""
        y_prob = np.ones(50)
        y_true = np.zeros(50)

        ece = compute_ece(y_true, y_prob, n_bins=10)
        assert pytest.approx(ece, abs=1e-5) == 1.0

    def test_varying_bins_robustness(self):
        """ECE calculation must not fail or produce non-finite numbers across various bin configurations."""
        rng = np.random.RandomState(42)
        y_true = rng.randint(0, 2, size=150)
        y_prob = rng.uniform(0.0, 1.0, size=150)

        for n_bins in [5, 10, 15, 25, 50]:
            ece = compute_ece(y_true, y_prob, n_bins=n_bins)
            assert 0.0 <= ece <= 1.0, f"ECE must be bounded in [0, 1], got {ece} for {n_bins} bins"
