"""
Multimodal Fusion Family for XMAI:
- F1: Late Fusion (additive in probability space)
- F2: Early/Concatenation Fusion
- F3: Mask-Aware Gated Fusion (Primary model with modality dropout)
- F4: FiLM Feature-wise Linear Modulation
Conforms to XMAI Design Document Section 7.5 and 7.6.
"""

from typing import Dict, List, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class MaskAwareGatedFusion(nn.Module):
    """
    F3 Primary Fusion: Mask-Aware Gated Fusion.
    Dynamic gating computes per-modality weights:
        g = softmax(W [z_B; z_C; z_T] + mask_penalty)
    Gating is re-normalized over available modalities.
    Modality dropout (p=0.2 per modality, never all dropped) trains robust partial-input operation.
    """

    def __init__(
        self,
        dim_b: int = 256,
        dim_c: int = 256,
        dim_t: int = 64,
        fused_dim: int = 256,
        dropout_p: float = 0.2,
    ):
        super().__init__()
        self.dim_b = dim_b
        self.dim_c = dim_c
        self.dim_t = dim_t
        self.fused_dim = fused_dim
        self.dropout_p = dropout_p

        # Learned null embeddings for missing modalities
        self.null_b = nn.Parameter(torch.zeros(dim_b))
        self.null_c = nn.Parameter(torch.zeros(dim_c))
        self.null_t = nn.Parameter(torch.zeros(dim_t))

        # Modality projection to shared dimension
        self.proj_b = nn.Linear(dim_b, fused_dim)
        self.proj_c = nn.Linear(dim_c, fused_dim)
        self.proj_t = nn.Linear(dim_t, fused_dim)

        # Gating network
        total_dim = dim_b + dim_c + dim_t
        self.gate_net = nn.Sequential(
            nn.Linear(total_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 3),  # 3 gate logits: [g_B, g_C, g_T]
        )

    def forward(
        self,
        z_b: Optional[torch.Tensor] = None,
        z_c: Optional[torch.Tensor] = None,
        z_t: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Input:
            z_b: [B, dim_b] or None
            z_c: [B, dim_c] or None
            z_t: [B, dim_t] or None
            mod_mask: [B, 3] binary mask (1 if present, 0 if absent)
        Output:
            z_f: [B, fused_dim]
            gate_weights: [B, 3] normalized modality weights
        """
        # Determine batch size and device from any available tensor
        if mod_mask is not None:
            device = mod_mask.device
            B = mod_mask.shape[0]
        elif z_b is not None:
            device = z_b.device
            B = z_b.shape[0]
        elif z_t is not None:
            device = z_t.device
            B = z_t.shape[0]
        elif z_c is not None:
            device = z_c.device
            B = z_c.shape[0]
        else:
            device = self.null_b.device
            B = 1

        if mod_mask is None:
            # Default: present if tensor is not None
            m1 = 1.0 if z_b is not None else 0.0
            m2 = 1.0 if z_c is not None else 0.0
            m3 = 1.0 if z_t is not None else 0.0
            mod_mask = torch.tensor([[m1, m2, m3]], device=device).expand(B, -1)
        else:
            mod_mask = mod_mask.to(device)

        # Apply Modality Dropout during training (never drop all present modalities)
        effective_mask = mod_mask.clone()
        if self.training and self.dropout_p > 0:
            rand_drop = torch.rand(B, 3, device=device) < self.dropout_p
            cand_mask = effective_mask * (~rand_drop).float()
            # If all dropped for a sample, restore original mask for that sample
            all_zero = (cand_mask.sum(dim=1, keepdim=True) == 0)
            effective_mask = torch.where(all_zero, effective_mask, cand_mask)

        # Substitute missing modalities with learned null vectors
        z_b_eff = z_b if z_b is not None else self.null_b.unsqueeze(0).expand(B, -1)
        z_c_eff = z_c if z_c is not None else self.null_c.unsqueeze(0).expand(B, -1)
        z_t_eff = z_t if z_t is not None else self.null_t.unsqueeze(0).expand(B, -1)

        # If masked out by effective_mask, zero out
        z_b_eff = z_b_eff * effective_mask[:, 0:1] + self.null_b.unsqueeze(0) * (1.0 - effective_mask[:, 0:1])
        z_c_eff = z_c_eff * effective_mask[:, 1:2] + self.null_c.unsqueeze(0) * (1.0 - effective_mask[:, 1:2])
        z_t_eff = z_t_eff * effective_mask[:, 2:3] + self.null_t.unsqueeze(0) * (1.0 - effective_mask[:, 2:3])

        # Compute Gate Logits
        concat_emb = torch.cat([z_b_eff, z_c_eff, z_t_eff], dim=1)  # [B, dim_b+dim_c+dim_t]
        raw_gate_logits = self.gate_net(concat_emb)                  # [B, 3]

        # Apply mask penalty (-1e9 for absent modalities)
        mask_penalty = (1.0 - effective_mask) * -1e9
        g_logits = raw_gate_logits + mask_penalty
        gate_weights = F.softmax(g_logits, dim=-1)                   # [B, 3]

        # Project modalities to shared fused dimension
        h_b = self.proj_b(z_b_eff)  # [B, fused_dim]
        h_c = self.proj_c(z_c_eff)  # [B, fused_dim]
        h_t = self.proj_t(z_t_eff)  # [B, fused_dim]

        # Dynamic weighted sum
        z_f = (
            gate_weights[:, 0:1] * h_b +
            gate_weights[:, 1:2] * h_c +
            gate_weights[:, 2:3] * h_t
        )

        return z_f, gate_weights


class ConcatenationFusion(nn.Module):
    """F2 Concatenation Fusion: [z_B; z_C; z_T] -> MLP."""

    def __init__(self, in_dim: int = 256 + 64, fused_dim: int = 256):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(in_dim, fused_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(fused_dim, fused_dim),
        )

    def forward(self, z_b: torch.Tensor, z_t: torch.Tensor) -> torch.Tensor:
        concat = torch.cat([z_b, z_t], dim=1)
        return self.fc(concat)


class FiLMFusion(nn.Module):
    """
    F4 Feature-wise Linear Modulation:
    Context z_T predicts scale gamma and shift beta to modulate image features:
        z_B' = gamma(z_T) * z_B + beta(z_T)
    """

    def __init__(self, dim_b: int = 256, dim_t: int = 64):
        super().__init__()
        self.gamma_net = nn.Linear(dim_t, dim_b)
        self.beta_net = nn.Linear(dim_t, dim_b)

    def forward(self, z_b: torch.Tensor, z_t: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        gamma = self.gamma_net(z_t)
        beta = self.beta_net(z_t)
        z_out = gamma * z_b + beta
        return z_out, gamma, beta
