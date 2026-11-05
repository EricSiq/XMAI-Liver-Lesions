"""
Modality encoders for B-mode ultrasound, clinical context, and CEUS cine.
Conforms to XMAI Design Document Section 7.4.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn
from torchvision.models import resnet18, ResNet18_Weights


class BModeEncoder(nn.Module):
    """
    M1 B-mode ultrasound encoder using pretrained ResNet-18.
    Extracts features from layer4 and projects to embedding space z_B in R^256.
    Exposes layer4 feature maps for Grad-CAM visualization.
    """

    def __init__(self, pretrained: bool = True, embed_dim: int = 256):
        super().__init__()
        weights = ResNet18_Weights.DEFAULT if pretrained else None
        backbone = resnet18(weights=weights)

        # Retain feature extractor up to layer4
        self.conv1 = backbone.conv1
        self.bn1 = backbone.bn1
        self.relu = backbone.relu
        self.maxpool = backbone.maxpool
        self.layer1 = backbone.layer1
        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.layer4 = backbone.layer4
        self.avgpool = backbone.avgpool

        # Linear projection: 512 -> embed_dim (256)
        self.proj = nn.Sequential(
            nn.Linear(512, embed_dim),
            nn.LayerNorm(embed_dim),
        )

        self.last_features: Optional[torch.Tensor] = None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Input: [B, 3, 224, 224]
        Output: z_B in [B, embed_dim]
        """
        if x.ndim != 4:
            raise ValueError(f"Expected 4D image tensor [B, C, H, W], got shape {tuple(x.shape)}")
        if x.shape[1] != 3:
            raise ValueError(f"Expected 3 channels (RGB B-mode), got {x.shape[1]} channels in shape {tuple(x.shape)}")
        if torch.isnan(x).any() or torch.isinf(x).any():
            raise ValueError("BModeEncoder received tensor containing NaN or Inf values.")

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        # Store for Grad-CAM
        self.last_features = x

        x = self.avgpool(x)
        flat = torch.flatten(x, 1)
        z_B = self.proj(flat)
        return z_B


class ClinicalEncoder(nn.Module):
    """
    M3 Structured clinical context encoder for binary Track A (HCC vs. Hemangioma).
    
    Transforms 2-variable demographic profile (age_z, sex_binary) into
    a rich representation vector z_C in R^64 using a 2-layer MLP with LayerNorm.
    Supports optional modality masking for Hypothesis H3 graceful unimodal fallback.
    """

    def __init__(self, in_features: int = 2, hidden_dim: int = 64, out_dim: int = 64, dropout: float = 0.3):
        super().__init__()
        self.in_features = in_features
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_dim, out_dim),
            nn.LayerNorm(out_dim),
        )

    def forward(self, clin: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            clin: Clinical feature tensor [B, in_features].
            mask: Optional binary indicator [B] or [B, 1] (0 = missing modality, 1 = active).
            
        Returns:
            z_C representation in [B, out_dim].
        """
        if clin.ndim != 2:
            raise ValueError(f"Expected 2D clinical tensor [B, in_features], got shape {tuple(clin.shape)}")
        if clin.shape[1] != self.in_features:
            raise ValueError(f"Expected {self.in_features} features, got {clin.shape[1]}")
        if torch.isnan(clin).any() or torch.isinf(clin).any():
            raise ValueError("ClinicalEncoder received tensor containing NaN or Inf values.")
            
        z_C = self.net(clin)
        if mask is not None:
            z_C = z_C * mask.view(-1, 1)
        return z_C


class MulticlassClinicalEncoder(nn.Module):
    """
    M3 Expanded Structured Clinical Context Encoder for 5-Class / 6-Class Differential Diagnosis.
    
    Transforms 8-variable oncology profile into representation vector z_C in R^128:
    Features: [age_z, sex_val, cirrhosis, hepatitis, oral_contraceptives, metabolic, afp_z, ca19_9_z].
    Incorporates a linear residual connection, LayerNorm, and optional modality masking.
    """

    def __init__(
        self,
        in_features: int = 8,
        hidden_dim: int = 128,
        out_dim: int = 128,
        dropout: float = 0.25,
    ):
        super().__init__()
        self.in_features = in_features
        self.fc1 = nn.Linear(in_features, hidden_dim)
        self.relu = nn.ReLU()
        self.drop = nn.Dropout(p=dropout)
        self.fc2 = nn.Linear(hidden_dim, out_dim)
        self.ln = nn.LayerNorm(out_dim)
        self.res = nn.Linear(in_features, out_dim) if in_features != out_dim else nn.Identity()

    def forward(self, clin: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            clin: Clinical feature tensor [B, in_features].
            mask: Optional binary indicator [B] or [B, 1] (0 = missing modality, 1 = active).
            
        Returns:
            z_C in [B, out_dim].
        """
        if clin.ndim != 2:
            raise ValueError(f"Expected 2D clinical tensor [B, in_features], got shape {tuple(clin.shape)}")
        if clin.shape[1] != self.in_features:
            raise ValueError(f"Expected {self.in_features} features, got {clin.shape[1]}")
        if torch.isnan(clin).any() or torch.isinf(clin).any():
            raise ValueError("MulticlassClinicalEncoder received tensor containing NaN or Inf values.")

        residual = self.res(clin)
        x = self.fc1(clin)
        x = self.relu(x)
        x = self.drop(x)
        x = self.fc2(x)
        out = self.ln(x + residual)

        if mask is not None:
            out = out * mask.view(-1, 1)
        return out


class TemporalAttentionAggregator(nn.Module):
    """
    Temporal attention pooling over T video frames.
    Attention weights provide intrinsic temporal explanation ('when').
    """

    def __init__(self, in_features: int = 256):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(in_features, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Input: x in [B, T, D]
        Output: (pooled in [B, D], attn_weights in [B, T])
        """
        # Compute raw scores: [B, T, 1]
        scores = self.attn(x)
        weights = torch.softmax(scores, dim=1)  # [B, T, 1]
        pooled = torch.sum(x * weights, dim=1)  # [B, D]
        return pooled, weights.squeeze(-1)


class CEUSEncoder(nn.Module):
    """
    M2 CEUS Cine Sequence encoder.
    Applies shared frame encoder over T frames and pools across time.
    """

    def __init__(
        self,
        frame_encoder: Optional[BModeEncoder] = None,
        pooling: str = "attention",
        embed_dim: int = 256,
    ):
        super().__init__()
        self.frame_encoder = frame_encoder or BModeEncoder(pretrained=True, embed_dim=embed_dim)
        self.pooling = pooling

        if pooling == "attention":
            self.aggregator = TemporalAttentionAggregator(embed_dim)
        elif pooling == "mean":
            self.aggregator = None
        elif pooling == "bilstm":
            self.lstm = nn.LSTM(embed_dim, embed_dim // 2, batch_first=True, bidirectional=True)
            self.aggregator = None
        else:
            raise ValueError(f"Unsupported pooling mode: {pooling}")

        self.last_attn_weights: Optional[torch.Tensor] = None

    def forward(self, ceus_frames: torch.Tensor) -> torch.Tensor:
        """
        Input: [B, T, 3, 224, 224]
        Output: z_C in [B, embed_dim]
        """
        if ceus_frames.ndim != 5:
            raise ValueError(f"Expected 5D tensor [B, T, C, H, W], got shape {tuple(ceus_frames.shape)}")
        if ceus_frames.shape[2] != 3:
            raise ValueError(f"Expected 3 channels (RGB frames), got {ceus_frames.shape[2]} channels in shape {tuple(ceus_frames.shape)}")
        if torch.isnan(ceus_frames).any() or torch.isinf(ceus_frames).any():
            raise ValueError("CEUSEncoder received tensor containing NaN or Inf values.")

        B, T, C, H, W = ceus_frames.shape
        flat_frames = ceus_frames.reshape(B * T, C, H, W)
        frame_feats = self.frame_encoder(flat_frames)  # [B*T, embed_dim]
        seq_feats = frame_feats.reshape(B, T, -1)         # [B, T, embed_dim]

        if self.pooling == "attention":
            z_C, weights = self.aggregator(seq_feats)
            self.last_attn_weights = weights
        elif self.pooling == "mean":
            z_C = torch.mean(seq_feats, dim=1)
        elif self.pooling == "bilstm":
            out, _ = self.lstm(seq_feats)
            z_C = out[:, -1, :]

        return z_C
