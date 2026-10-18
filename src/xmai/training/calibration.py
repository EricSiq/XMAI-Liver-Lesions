"""
Temperature scaling for post-hoc probability calibration.
Fits temperature parameter T > 0 on validation fold logits to minimize NLL
without changing classification argmax ranking.
"""

import torch
import torch.nn as nn
import torch.optim as optim


class TemperatureScaler(nn.Module):
    """
    Fits a single scalar temperature T on validation logits.
    Calibrated probabilities: softmax(logits / T).
    """

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        temp = self.temperature.clamp(min=0.01)
        return logits / temp

    def fit(self, val_logits: torch.Tensor, val_labels: torch.Tensor, max_iter: int = 50) -> float:
        """
        Optimizes temperature to minimize cross-entropy loss on validation logits.
        Returns the optimal temperature value.
        """
        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=0.01, max_iter=max_iter)

        val_logits = val_logits.detach()
        val_labels = val_labels.detach()

        def eval_loss():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(val_logits), val_labels)
            loss.backward()
            return loss

        optimizer.step(eval_loss)
        opt_temp = float(self.temperature.clamp(min=0.01).item())
        return opt_temp
