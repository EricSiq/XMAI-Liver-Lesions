"""
Track B Temporal CEUS Model Family:
- B1: Shared frame encoder + mean pooling
- B2: Shared frame encoder + temporal attention pooling (primary temporal model)
- B3: Shared frame encoder + BiLSTM
- B4: Arterial-only / early phase comparison

Conforms to XMAI Design Document Section 8 and tasks.md Section 4.2.
"""

from typing import Any, Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from xmai.models.encoders import BModeEncoder, CEUSEncoder


class B1MeanPooling(nn.Module):
    """B1: Shared frame encoder + temporal mean pooling."""

    def __init__(self, num_classes: int = 3, embed_dim: int = 256, pretrained: bool = True):
        super().__init__()
        self.encoder = CEUSEncoder(pooling="mean", embed_dim=embed_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(embed_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(self, video: torch.Tensor) -> Dict[str, Any]:
        """
        Input video: [B, T, 3, 224, 224]
        """
        z_c = self.encoder(video)  # [B, embed_dim]
        logits = self.head(z_c)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": z_c,
            "temporal_weights": None,
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


class B2TemporalAttention(nn.Module):
    """B2: Shared frame encoder + temporal attention pooling (primary model)."""

    def __init__(self, num_classes: int = 3, embed_dim: int = 256, pretrained: bool = True):
        super().__init__()
        self.encoder = CEUSEncoder(pooling="attention", embed_dim=embed_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(embed_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(self, video: torch.Tensor) -> Dict[str, Any]:
        """
        Input video: [B, T, 3, 224, 224]
        """
        z_c = self.encoder(video)  # [B, embed_dim]
        logits = self.head(z_c)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": z_c,
            "temporal_weights": self.encoder.last_attn_weights,  # [B, T]
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


class B3BiLSTM(nn.Module):
    """B3: Shared frame encoder + Bidirectional LSTM."""

    def __init__(self, num_classes: int = 3, embed_dim: int = 256, pretrained: bool = True):
        super().__init__()
        self.encoder = CEUSEncoder(pooling="bilstm", embed_dim=embed_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(embed_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(self, video: torch.Tensor) -> Dict[str, Any]:
        """
        Input video: [B, T, 3, 224, 224]
        """
        z_c = self.encoder(video)  # [B, embed_dim]
        logits = self.head(z_c)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": z_c,
            "temporal_weights": None,
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


class B4ArterialOnly(nn.Module):
    """B4: Early arterial-phase only classifier (using first T_early frames)."""

    def __init__(self, num_classes: int = 3, embed_dim: int = 256, early_t: int = 4, pretrained: bool = True):
        super().__init__()
        self.early_t = early_t
        self.encoder = CEUSEncoder(pooling="mean", embed_dim=embed_dim)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(embed_dim, num_classes),
        )
        self.temperature = nn.Parameter(torch.ones(1), requires_grad=False)

    def forward(self, video: torch.Tensor) -> Dict[str, Any]:
        """
        Input video: [B, T, 3, 224, 224]
        Slices early arterial frames [B, :early_t, 3, 224, 224]
        """
        early_video = video[:, :self.early_t]
        z_c = self.encoder(early_video)
        logits = self.head(z_c)
        calibrated_logits = logits / self.temperature
        probs = F.softmax(calibrated_logits, dim=-1)

        return {
            "logits": logits,
            "calibrated_logits": calibrated_logits,
            "probs": probs,
            "embeddings": z_c,
            "temporal_weights": None,
        }

    def set_temperature(self, temp_val: float) -> None:
        if temp_val <= 0:
            raise ValueError(f"Temperature must be strictly positive, got {temp_val}")
        self.temperature.data.fill_(temp_val)


def create_track_b_model(model_id: str, num_classes: int = 3, pretrained: bool = True) -> nn.Module:
    """Factory function for Track B temporal model family."""
    if model_id in {"B1", "B1_mean"}:
        return B1MeanPooling(num_classes=num_classes, pretrained=pretrained)
    elif model_id in {"B2", "B2_attention"}:
        return B2TemporalAttention(num_classes=num_classes, pretrained=pretrained)
    elif model_id in {"B3", "B3_bilstm"}:
        return B3BiLSTM(num_classes=num_classes, pretrained=pretrained)
    elif model_id in {"B4", "B4_arterial"}:
        return B4ArterialOnly(num_classes=num_classes, pretrained=pretrained)
    else:
        raise ValueError(f"Unknown Track B model_id: {model_id}")
