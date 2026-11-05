"""
Multimodal Fusion Family for XMAI:
- F1: Late Fusion (additive in probability space)
- F2: Early/Concatenation Fusion
- F3: Mask-Aware Gated Fusion (Primary model with modality dropout)
- F4: FiLM Feature-wise Linear Modulation
Conforms to XMAI Design Document Section 7.5 and 7.6.
"""

from typing import Any, Dict, List, Optional, Tuple
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


class CrossModalAttentionFusion(nn.Module):
    """
    F5 Cross-Modal Attention Fusion (CMAF).
    Employs bidirectional multi-head cross-attention between visual morphology
    and structured clinical context tokens with residual connections and layer normalization.
    Exposes cross-modal attention maps for explainability.
    """

    def __init__(
        self,
        dim_b: int = 256,
        dim_t: int = 64,
        embed_dim: int = 256,
        num_heads: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads

        # Project modalities to common attention embedding space
        self.proj_b = nn.Linear(dim_b, embed_dim)
        self.proj_t = nn.Linear(dim_t, embed_dim)

        # Bidirectional Multi-Head Attention: Visual attends to Clinical, Clinical attends to Visual
        self.attn_b_to_t = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.attn_t_to_b = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )

        # LayerNorm and FeedForward
        self.ln_b = nn.LayerNorm(embed_dim)
        self.ln_t = nn.LayerNorm(embed_dim)

        self.ffn = nn.Sequential(
            nn.Linear(embed_dim * 2, embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
        )

        # Store attention weights for explainability
        self.last_attn_weights: Optional[torch.Tensor] = None

    def forward(
        self,
        z_b: torch.Tensor,
        z_t: torch.Tensor,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Input:
            z_b: [B, dim_b] Visual embedding
            z_t: [B, dim_t] Clinical context embedding
            mod_mask: [B, 3] modality mask
        Output:
            z_fused: [B, embed_dim]
            attn_dict: Dictionary with attention matrices
        """
        B = z_b.shape[0]

        # Project to shared attention dimension and format as sequence [B, 1, embed_dim]
        h_b = self.proj_b(z_b).unsqueeze(1)
        h_t = self.proj_t(z_t).unsqueeze(1)

        # Cross attention: Visual queries Clinical keys/values
        out_b, weights_b_to_t = self.attn_b_to_t(query=h_b, key=h_t, value=h_t)
        # Cross attention: Clinical queries Visual keys/values
        out_t, weights_t_to_b = self.attn_t_to_b(query=h_t, key=h_b, value=h_b)

        # Residual + LayerNorm
        h_b_res = self.ln_b(h_b + out_b).squeeze(1)  # [B, embed_dim]
        h_t_res = self.ln_t(h_t + out_t).squeeze(1)  # [B, embed_dim]

        # Handle modality mask if provided
        if mod_mask is not None:
            m_b = mod_mask[:, 0:1]  # [B, 1]
            m_t = mod_mask[:, 2:3]  # [B, 1]
            h_b_res = h_b_res * m_b
            h_t_res = h_t_res * m_t

        combined = torch.cat([h_b_res, h_t_res], dim=1)  # [B, 2 * embed_dim]
        z_fused = self.ffn(combined)                     # [B, embed_dim]

        self.last_attn_weights = weights_b_to_t
        attn_dict = {
            "attn_b_to_t": weights_b_to_t,
            "attn_t_to_b": weights_t_to_b,
        }
        return z_fused, attn_dict


class EvidentialMultimodalFusion(nn.Module):
    """
    F6 Evidential Multimodal Fusion (Trusted Multi-View Fusion via Subjective Logic).
    Quantifies epistemic uncertainty per modality and fuses evidence via Dempster's Rule of Combination.
    Each modality parameterizes Dirichlet evidence:
        e_k = softplus(f(z)) >= 0
        alpha_k = e_k + 1
        S = sum(alpha_k)
        b_k = e_k / S  (belief mass)
        u = K / S      (uncertainty mass)
        sum(b_k) + u = 1.0
    Missing modalities are vacuous (b=0, u=1), cleanly ignored without heuristic masks.
    """

    def __init__(
        self,
        dim_b: int = 256,
        dim_t: int = 64,
        num_classes: int = 2,
    ):
        super().__init__()
        self.num_classes = num_classes

        # Modality Evidence Heads
        self.evidence_head_b = nn.Sequential(
            nn.Linear(dim_b, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes),
        )
        self.evidence_head_t = nn.Sequential(
            nn.Linear(dim_t, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def _evidence_to_belief(self, evidence: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Converts non-negative evidence to Dirichlet belief mass and uncertainty.
        Input: evidence [B, K] >= 0
        Output: belief [B, K], uncertainty [B, 1]
        """
        alpha = evidence + 1.0
        S = torch.sum(alpha, dim=1, keepdim=True)  # [B, 1]
        belief = evidence / S                     # [B, K]
        uncertainty = self.num_classes / S        # [B, 1]
        return belief, uncertainty

    @staticmethod
    def dempster_combination(
        b1: torch.Tensor, u1: torch.Tensor, b2: torch.Tensor, u2: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Fuses two subjective opinions using Dempster's rule of combination.
        b1, b2: [B, K] belief vectors
        u1, u2: [B, 1] epistemic uncertainty scalars
        """
        # Elementwise agreement
        diag_agree = b1 * b2  # [B, K]
        sum_agree = torch.sum(diag_agree, dim=1, keepdim=True)  # [B, 1]

        # Conflict C = (sum_k b1_k) * (sum_k b2_k) - sum_k (b1_k * b2_k)
        sum_b1 = torch.sum(b1, dim=1, keepdim=True)  # [B, 1]
        sum_b2 = torch.sum(b2, dim=1, keepdim=True)  # [B, 1]
        C = (sum_b1 * sum_b2) - sum_agree            # [B, 1]

        # Normalization scale factor: 1 - C (Dempster's normalization)
        scale = torch.clamp(1.0 - C, min=1e-6)       # [B, 1]

        # Fused belief mass: b_k = (b1_k * b2_k + b1_k * u2 + b2_k * u1) / (1 - C)
        b_fused = (diag_agree + b1 * u2 + b2 * u1) / scale  # [B, K]

        # Fused uncertainty: u = (u1 * u2) / (1 - C)
        u_fused = (u1 * u2) / scale                         # [B, 1]

        # Guarantee strict mathematical conservation: sum(b_k) + u == 1.0 to machine precision
        total_mass = torch.sum(b_fused, dim=1, keepdim=True) + u_fused
        total_clamped = torch.clamp(total_mass, min=1e-7)
        b_fused = b_fused / total_clamped
        u_fused = u_fused / total_clamped

        return b_fused, u_fused

    def forward(
        self,
        z_b: Optional[torch.Tensor] = None,
        z_t: Optional[torch.Tensor] = None,
        mod_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        Forward pass producing per-modality and fused Dirichlet distributions.
        """
        B = z_b.shape[0] if z_b is not None else z_t.shape[0]
        device = z_b.device if z_b is not None else z_t.device
        K = self.num_classes

        # Modality B: B-mode
        if z_b is not None:
            raw_ev_b = F.softplus(self.evidence_head_b(z_b))
            b_b, u_b = self._evidence_to_belief(raw_ev_b)
        else:
            b_b = torch.zeros(B, K, device=device)
            u_b = torch.ones(B, 1, device=device)

        # Modality T: Clinical context
        if z_t is not None:
            raw_ev_t = F.softplus(self.evidence_head_t(z_t))
            b_t, u_t = self._evidence_to_belief(raw_ev_t)
        else:
            b_t = torch.zeros(B, K, device=device)
            u_t = torch.ones(B, 1, device=device)

        # Apply modality mask if given (if absent, set to vacuous belief)
        if mod_mask is not None:
            m_b = mod_mask[:, 0:1]
            m_t = mod_mask[:, 2:3]
            b_b = b_b * m_b
            u_b = u_b * m_b + (1.0 - m_b)
            b_t = b_t * m_t
            u_t = u_t * m_t + (1.0 - m_t)

        # Fuse B-mode and Clinical context via Dempster's rule
        b_fused, u_fused = self.dempster_combination(b_b, u_b, b_t, u_t)

        # Reconstruct Dirichlet parameters and expected probability
        alpha_fused = (K * b_fused) / torch.clamp(u_fused, min=1e-6) + 1.0
        S_fused = torch.sum(alpha_fused, dim=1, keepdim=True)
        probs_fused = alpha_fused / S_fused

        return {
            "probs": probs_fused,
            "alpha_fused": alpha_fused,
            "b_fused": b_fused,
            "u_fused": u_fused,
            "b_b": b_b,
            "u_b": u_b,
            "b_t": b_t,
            "u_t": u_t,
        }

