"""
Explanation Card Generation.
Synthesizes spatial (Grad-CAM), clinical, and cross-modal (Modality Shapley) attributions
into a structured clinical research explanation card.
Conforms to XMAI Design Document Section 8.2.
"""

from typing import Any, Dict, List, Optional


class ExplanationCard:
    """Standardized Explanation Card for a patient diagnostic output."""

    def __init__(
        self,
        patient_id: str,
        true_label: str,
        pred_label: str,
        probs: Dict[str, float],
        margin: float,
        gate_weights: Dict[str, float],
        shapley_values: Dict[str, float],
        flags: Optional[List[str]] = None,
    ):
        self.patient_id = patient_id
        self.true_label = true_label
        self.pred_label = pred_label
        self.probs = probs
        self.margin = margin
        self.gate_weights = gate_weights
        self.shapley_values = shapley_values
        self.flags = flags or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "true_label": self.true_label,
            "pred_label": self.pred_label,
            "calibrated_probabilities": self.probs,
            "top2_margin": self.margin,
            "fusion_gate_weights": self.gate_weights,
            "modality_shapley_attributions": self.shapley_values,
            "warning_flags": self.flags,
            "clinical_notice": (
                "Notice: Attributions describe model reliance on retrospective cohort statistics, "
                "not clinical etiology or diagnostic proof. Prototype research only."
            ),
        }

    def render_markdown(self) -> str:
        """Renders the explanation card as GitHub-style Markdown."""
        flags_text = ", ".join(self.flags) if self.flags else "None"
        md = f"""### XMAI Explanation Card: Patient {self.patient_id}

| Diagnostic Field | Result |
|---|---|
| **True Label** | `{self.true_label}` |
| **Predicted Label** | `{self.pred_label}` |
| **Margin (Top-2)** | `{self.margin:.4f}` |
| **Warning Flags** | `{flags_text}` |

#### 1. Calibrated Probabilities
- **HCC**: `{self.probs.get('HCC', 0.0):.4f}`
- **Hemangioma**: `{self.probs.get('Hemangioma', 0.0):.4f}`

#### 2. Modality Reliance & Contributions
- **Gate Weights (F3)**: B-mode: `{self.gate_weights.get('B-mode', 0.0):.3f}`, CEUS: `{self.gate_weights.get('CEUS', 0.0):.3f}`, Context: `{self.gate_weights.get('Context', 0.0):.3f}`
- **Exact Modality Shapley**:
  - B-mode: `{self.shapley_values.get('B-mode', 0.0):+.4f}`
  - CEUS: `{self.shapley_values.get('CEUS', 0.0):+.4f}`
  - Context: `{self.shapley_values.get('Context', 0.0):+.4f}`

> **Scientific Limit Notice**: Model explanations reflect retrospective cohort associations. Context features (age, sex) reflect institutional referral patterns and are not diagnostic evidence.
"""
        return md
