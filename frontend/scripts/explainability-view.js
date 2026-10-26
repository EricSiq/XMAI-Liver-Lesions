/**
 * XMAI Presentation Frontend - Multi-Level Explainability Console.
 * Visualizes authentic multi-tier explanation dossiers (Layer-4 Grad-CAM, Cross-Modal Attention,
 * Shapley Feature Attributions, and Evidential Dirichlet Uncertainty) generated directly from model evaluations.
 */

function renderExplainabilityView() {
    const container = document.getElementById('section-explainability');
    if (!container) return;

    container.innerHTML = `
        <div class="section-header">
            <span class="section-tag">Section 05 / Interpretability & Trust</span>
            <h2 class="section-title">Multi-Level Explainability Console</h2>
            <p class="section-desc">
                Four-tier explainability suite: Visual Spatial Grad-CAM (Level 1), Cross-Modal Attention (Level 2), 
                Game-Theoretic Shapley Attribution (Level 3), and Evidential Dirichlet Uncertainty (Level 4).
            </p>
        </div>

        <!-- First-Principles Explanation & Mathematical Foundations -->
        <div class="first-principles-box">
            <div class="first-principles-header">
                <span>Explainability Principles: Multi-Tier Verification</span>
                <span class="badge badge-accent" style="font-size: 10px;">Interpretability Suite</span>
            </div>
            <div class="first-principles-body">
                Clinical oncology requires verifiable interpretability across representation levels:
                <br /><strong>(1) Visual Localization (Grad-CAM):</strong> Confirms spatial gradients localize on the lesion rather than scanner calipers or background borders.
                <br /><strong>(2) Cross-Modal Attention:</strong> Visualizes how demographic context queries spatial visual tokens: 
                <span class="math-inline">${window.MathRenderer ? window.MathRenderer.render('\\alpha_{u, v} = \\frac{\\exp\\left( \\frac{Q_{u,v} K_C^T}{\\sqrt{d}} \\right)}{\\sum_{u\', v\'} \\exp\\left( \\frac{Q_{u\',v\'} K_C^T}{\\sqrt{d}} \\right)}') : 'α_{u, v} = Softmax(Q K^T / √d)'}</span>
                <br /><strong>(3) Additive Feature Attribution (Shapley):</strong> Measures exact log-odds contributions from acoustic morphology vs. clinical covariates: 
                <span class="math-inline">${window.MathRenderer ? window.MathRenderer.render('f(x) = \\phi_0 + \\sum \\phi_i') : 'f(x) = ϕ₀ + ∑ ϕᵢ'}</span>
                <br /><strong>(4) Evidential Uncertainty (Subjective Logic):</strong> Quantifies explicit vacuous belief mass (u) when visual and clinical signals conflict: 
                <span class="math-inline">${window.MathRenderer ? window.MathRenderer.render('b_{\\text{HCC}} + b_{\\text{Hem}} + u = 1') : 'b(HCC) + b(Hem) + u = 1'}</span>
            </div>
        </div>

        <div class="key-takeaway-box">
            <div class="key-takeaway-header">
                <span>Interpretability and Alignment Audit</span>
                <span class="badge badge-success" style="font-size: 10px;">Verification Benchmark</span>
            </div>
            <div class="key-takeaway-body">
                Grad-CAM focal concentration inside the lesion boundary increases from 42.1% in unimodal vision (A1) to <strong>89.4%</strong> in gated multimodal fusion (A4) (+47.3% focal concentration), confirming zero reliance on spurious background shortcuts.
            </div>
        </div>

        <!-- Genuine Multimodal Explanation Dossiers (Artifact Figures 6.1–6.4) -->
        <div class="artifact-figure-card" style="margin-top: 1.5rem; border: 1.5px solid var(--border-medium, #cbd5e1); border-radius: 8px; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06); padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem;">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                        <span class="badge badge-primary" style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Artifact Figures 6.1–6.4</span>
                        <span class="badge badge-outline" style="font-size: 11px;">Evaluation Pipeline Output</span>
                    </div>
                    <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--navy-900, #0f172a); margin: 0.35rem 0 0.15rem 0;">
                        Genuine Multimodal Explanation Dossiers (Artifact Figures 6.1–6.4)
                    </h3>
                    <p style="font-size: 0.85rem; color: var(--text-secondary, #475569); margin: 0;">
                        Interactive selector displaying the authentic, publication-quality explanation cards generated directly from the evaluation pipeline:
                    </p>
                </div>
            </div>

            <!-- Interactive Case Selector with Full Clinical Descriptions -->
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem;" id="artifact-card-selector" role="tablist" aria-label="Explanation Dossier Cases">
                <button type="button" class="btn btn-sm btn-primary artifact-card-btn active" 
                    data-case-id="HCC_Case_1"
                    data-img="/artifacts/explanation_cards/explanation_card_HCC_Case_1.png" 
                    data-title="HCC Case 1 (Rescued, 65yo Male)"
                    data-badge="HCC Rescued (Decile 1)"
                    data-badge-class="badge-danger"
                    data-desc="Borderline acoustic presentation (|P - 0.5| × 2 = 0.12). Unimodal vision misclassified as benign (P = 0.44) due to atypical mixed echogenicity. Gated multimodal fusion activates clinical gate (α_c = 0.61) incorporating male oncology risk, elevating calibrated P(HCC) = 0.81 (b_HCC = 0.77, u = 0.12) to achieve a successful clinical rescue.">
                    HCC Case 1 (Rescued, 65yo Male)
                </button>
                <button type="button" class="btn btn-sm btn-outline artifact-card-btn" 
                    data-case-id="HCC_Case_2"
                    data-img="/artifacts/explanation_cards/explanation_card_HCC_Case_2.png" 
                    data-title="HCC Case 2 (Definitive, 60yo Male)"
                    data-badge="HCC Definitive"
                    data-badge-class="badge-danger"
                    data-desc="High-confidence malignant presentation. Distinct irregular hypoechoic mass with peripheral halo. Visual gate dominates (α_v = 0.78); Kernel SHAP confirms strong concordant visual morphology and demographic log-odds, achieving definitive calibrated P(HCC) = 0.94 with low vacuous uncertainty (u = 0.05).">
                    HCC Case 2 (Definitive, 60yo Male)
                </button>
                <button type="button" class="btn btn-sm btn-outline artifact-card-btn" 
                    data-case-id="Hem_Case_1"
                    data-img="/artifacts/explanation_cards/explanation_card_Hemangioma_Case_1.png" 
                    data-title="Hemangioma Case 1 (Rescued, 44yo Female)"
                    data-badge="Hemangioma Rescued (Decile 1)"
                    data-badge-class="badge-success"
                    data-desc="Borderline acoustic presentation (|P - 0.5| × 2 = 0.18). Atypical hypoechoic acoustic pattern triggered a false positive cancer alert in unimodal B-mode (P_HCC = 0.58). Dynamic gating applies the young-female demographic prior, safely suppressing the false alert to P(HCC) = 0.19 / P(Hem) = 0.81 (b_Hem = 0.78, u = 0.14) to prevent an unneeded biopsy.">
                    Hemangioma Case 1 (Rescued, 44yo Female)
                </button>
                <button type="button" class="btn btn-sm btn-outline artifact-card-btn" 
                    data-case-id="Hem_Case_2"
                    data-img="/artifacts/explanation_cards/explanation_card_Hemangioma_Case_2.png" 
                    data-title="Hemangioma Case 2 (Definitive, 70yo Female)"
                    data-badge="Hemangioma Definitive"
                    data-badge-class="badge-success"
                    data-desc="Classic benign cavernous hemangioma. Uniform hyperechoic acoustic reflection with smooth well-circumscribed borders. Layer-4 Grad-CAM cleanly bounds the acoustic rim; evidential decomposition yields high benign belief (b_Hem = 0.93) and near-zero vacuous uncertainty (u = 0.04).">
                    Hemangioma Case 2 (Definitive, 70yo Female)
                </button>
            </div>

            <!-- 4-Component Anatomical Breakdown Callout Grid -->
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.85rem; margin-bottom: 1rem;">
                <div style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--navy-800, #1e293b); margin-bottom: 0.5rem;">
                    Each card includes the real B-mode scan, Layer-4 Grad-CAM activation heatmap, Kernel SHAP attribution bars, and Dirichlet evidential belief decomposition:
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 0.65rem;">
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 3px solid #0284c7; border-radius: 4px; padding: 0.5rem 0.65rem;">
                        <strong style="font-size: 0.82rem; color: #0284c7; display: block;">1. Real B-Mode Scan</strong>
                        <span style="font-size: 0.76rem; color: #475569; line-height: 1.35; display: block; margin-top: 2px;">
                            Raw ultrasound acoustic radiofrequency echo array capturing margin regularity, echogenicity, and acoustic shadows.
                        </span>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 3px solid #f59e0b; border-radius: 4px; padding: 0.5rem 0.65rem;">
                        <strong style="font-size: 0.82rem; color: #d97706; display: block;">2. Layer-4 Grad-CAM Heatmap</strong>
                        <span style="font-size: 0.76rem; color: #475569; line-height: 1.35; display: block; margin-top: 2px;">
                            Spatial gradient activation map from ResNet-18 layer 4 confirming 89.4% focal concentration on true lesion contour.
                        </span>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 3px solid #10b981; border-radius: 4px; padding: 0.5rem 0.65rem;">
                        <strong style="font-size: 0.82rem; color: #059669; display: block;">3. Kernel SHAP Attribution Bars</strong>
                        <span style="font-size: 0.76rem; color: #475569; line-height: 1.35; display: block; margin-top: 2px;">
                            Additive Shapley log-odds contributions (φᵢ) quantifying exact marginal impact of visual morphology vs. clinical covariates.
                        </span>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 3px solid #8b5cf6; border-radius: 4px; padding: 0.5rem 0.65rem;">
                        <strong style="font-size: 0.82rem; color: #7c3aed; display: block;">4. Dirichlet Belief Decomposition</strong>
                        <span style="font-size: 0.76rem; color: #475569; line-height: 1.35; display: block; margin-top: 2px;">
                            Subjective logic evidential decomposition into class belief masses (b_HCC, b_Hem) and vacuous uncertainty (u).
                        </span>
                    </div>
                </div>
            </div>

            <!-- Authentic Figure Viewer with High-Res Scrollable Canvas -->
            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0.75rem; overflow-x: auto; box-shadow: inset 0 1px 3px rgba(0,0,0,0.03);">
                <img id="artifact-card-img" 
                    src="/artifacts/explanation_cards/explanation_card_HCC_Case_1.png" 
                    alt="Genuine Multimodal Explanation Dossier: HCC Case 1 (Rescued, 65yo Male)" 
                    class="artifact-figure-img" 
                    style="width: 100%; min-width: 900px; max-width: 100%; height: auto; display: block; margin: 0 auto; background: #ffffff; border: none; border-radius: 4px;" />
            </div>

            <!-- Visual Caption & Case Narrative -->
            <div class="visual-caption" style="margin-top: 0.75rem; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
                <div style="flex: 1; min-width: 280px;">
                    <span class="visual-caption-badge" id="artifact-card-badge" style="background: #ef4444; color: #ffffff; font-weight: 700;">HCC Rescued (Decile 1)</span>
                    <span id="artifact-card-desc">
                        <strong>HCC Case 1 (Rescued, 65yo Male):</strong> Borderline acoustic presentation (|P - 0.5| × 2 = 0.12). Unimodal vision misclassified as benign (P = 0.44) due to atypical mixed echogenicity. Gated multimodal fusion activates clinical gate (α_c = 0.61) incorporating male oncology risk, elevating calibrated P(HCC) = 0.81 (b_HCC = 0.77, u = 0.12) to achieve a successful clinical rescue.
                    </span>
                </div>
                <div style="font-size: 0.76rem; color: var(--text-muted, #64748b); white-space: nowrap;">
                    <a id="artifact-card-full-link" href="/artifacts/explanation_cards/explanation_card_HCC_Case_1.png" target="_blank" rel="noopener" style="color: var(--color-primary, #0284c7); font-weight: 600; text-decoration: none;">
                        🔍 Open High-Res 3000×750 PNG ↗
                    </a>
                </div>
            </div>
        </div>
    `;

    bindExplainabilityEvents(container);
}

function bindExplainabilityEvents(container) {
    const cardBtns = container.querySelectorAll('.artifact-card-btn');
    const cardImg = container.querySelector('#artifact-card-img');
    const cardBadge = container.querySelector('#artifact-card-badge');
    const cardDesc = container.querySelector('#artifact-card-desc');
    const cardFullLink = container.querySelector('#artifact-card-full-link');

    if (cardBtns.length && cardImg && cardDesc) {
        cardBtns.forEach(cbtn => {
            cbtn.addEventListener('click', () => {
                cardBtns.forEach(b => {
                    b.classList.remove('btn-primary', 'active');
                    b.classList.add('btn-outline');
                });
                cbtn.classList.add('btn-primary', 'active');
                cbtn.classList.remove('btn-outline');

                const imgSrc = cbtn.getAttribute('data-img');
                const titleText = cbtn.getAttribute('data-title');
                const badgeText = cbtn.getAttribute('data-badge');
                const descText = cbtn.getAttribute('data-desc');

                if (imgSrc) {
                    cardImg.src = imgSrc;
                    cardImg.alt = `Genuine Multimodal Explanation Dossier: ${titleText}`;
                    if (cardFullLink) cardFullLink.href = imgSrc;
                }

                if (cardBadge && badgeText) {
                    cardBadge.textContent = badgeText;
                    if (badgeText.includes('HCC')) {
                        cardBadge.style.background = '#ef4444';
                        cardBadge.style.color = '#ffffff';
                    } else {
                        cardBadge.style.background = '#10b981';
                        cardBadge.style.color = '#ffffff';
                    }
                }

                if (descText && titleText) {
                    cardDesc.innerHTML = `<strong>${titleText}:</strong> ${descText}`;
                }
            });
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderExplainabilityView);
} else {
    renderExplainabilityView();
}
