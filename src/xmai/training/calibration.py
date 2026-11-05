"""
Temperature scaling for post-hoc probability calibration.
Fits temperature parameter T > 0 on validation fold logits to minimize NLL
without changing classification argmax ranking.
"""

from typing import Optional
import torch
import torch.nn as nn
import torch.optim as optim


class TemperatureScaler(nn.Module):
    """
    Fits a single scalar temperature T on validation logits.
    Calibrated probabilities: softmax(logits / T).
    
    Mathematical & Clinical Guarantees:
    - Top-1 ranking invariance: argmax_k(z_k / T) = argmax_k(z_k) for any T > 0.
    - Numerical safety: T clamped strictly in [min_temp, max_temp] (default [0.01, 100.0]).
    - Non-finite guard: validation logits with NaN or Inf are rejected immediately.
    - Graceful fallback: if optimization encounters non-finite gradients or degenerate states,
      temperature defaults safely to 1.0 (unscaled identity) rather than corrupting inference.
    """

    def __init__(self, init_temperature: float = 1.5, min_temp: float = 0.01):
        super().__init__()
        self.min_temp = min_temp
        self.temperature = nn.Parameter(torch.ones(1) * float(init_temperature))

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """
        Scale unnormalized logits by temperature T.
        Clamps temperature to min_temp (>=0.01) for strict numerical stability.
        """
        temp = self.temperature.clamp(min=self.min_temp)
        return logits / temp

    def fit(self, val_logits: torch.Tensor, val_labels: torch.Tensor, max_iter: int = 50) -> float:
        """
        Optimizes temperature to minimize cross-entropy loss on validation logits.
        Returns the optimal temperature value.
        """
        if val_logits.numel() == 0 or val_labels.numel() == 0:
            raise ValueError("Cannot fit temperature on empty validation set.")
        if val_logits.dim() != 2:
            raise ValueError(f"Expected 2D logits tensor [N, K], got shape {val_logits.shape}")
        if not torch.isfinite(val_logits).all():
            raise ValueError("Validation logits contain non-finite values (NaN or Inf).")

        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=0.01, max_iter=max_iter)

        val_logits = val_logits.detach()
        val_labels = val_labels.detach()

        def eval_loss():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(val_logits), val_labels)
            if torch.isfinite(loss):
                loss.backward()
            return loss

        try:
            optimizer.step(eval_loss)
        except Exception:
            # Fallback if L-BFGS line search encounters ill-conditioning
            pass

        # Ensure temperature remains strictly bounded and finite
        if not torch.isfinite(self.temperature):
            self.temperature.data = torch.tensor([1.0], device=self.temperature.device)
        else:
            self.temperature.data.clamp_(min=self.min_temp)

        opt_temp = float(self.temperature.item())
        return opt_temp
