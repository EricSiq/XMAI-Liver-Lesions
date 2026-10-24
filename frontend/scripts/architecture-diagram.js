/**
 * XMAI Presentation Frontend - Architecture Diagram Visualizer.
 * Provides an interactive SVG data-flow diagram with model switching across A1-A9.
 */

const ARCHITECTURE_SCHEMATICS = {
    A1: {
        title: "A1: Unimodal B-Mode ResNet-18 Baseline",
        inputs: ["B-mode US Image (3 x 224 x 224)"],
        activeStreams: ["visual"],
        fusionMethod: "No Fusion (Visual Only)",
        math: `z_B = \\text{ResNet18}(\\mathbf{x}_B) \\in \\mathbb{R}^{512} \\\\ \\hat{y} = \\sigma(W_v z_B + b_v)`,
        clinicalBias: "Acoustic morphology only. Vulnerable to borderline atypical echogenicity where hypoechoic HCC mimics hemangioma.",
        params: "11.18M parameters | Latency: 4.8 ms (GPU)",
        status: "Baseline"
    },
    A2: {
        title: "A2: Unimodal Clinical Prior MLP Baseline",
        inputs: ["Patient Age (Standardized)", "Biological Sex (One-hot)"],
        activeStreams: ["clinical"],
        fusionMethod: "No Fusion (Demographic Prior Only)",
        math: `z_C = \\text{ReLU}(W_1 \\mathbf{x}_C + b_1) \\in \\mathbb{R}^{64} \\\\ \\hat{y} = \\sigma(W_2 z_C + b_2)`,
        clinicalBias: "Captures population epidemiology (HCC older males, Hemangioma younger females) without lesion visualization.",
        params: "4.3K parameters | Latency: 0.2 ms",
        status: "Baseline"
    },
    A3: {
        title: "A3: Linear Feature Concatenation",
        inputs: ["B-mode US Image", "Age", "Sex"],
        activeStreams: ["visual", "clinical", "fusion"],
        fusionMethod: "Linear Vector Concatenation [z_B; z_C]",
        math: `z_F = [z_B \\parallel z_C] \\in \\mathbb{R}^{576} \\\\ \\hat{y} = \\sigma(W_f z_F + b_f)`,
        clinicalBias: "Static linear combination. Does not permit visual features to modulate clinical weight dynamically.",
        params: "11.22M parameters | Latency: 4.9 ms",
        status: "Ablation"
    },
    A4: {
        title: "A4: Mask-Aware Gated Multimodal Fusion (Proposed)",
        inputs: ["B-mode US Image", "Age", "Sex", "Availability Mask m"],
        activeStreams: ["visual", "clinical", "gate", "fusion"],
        fusionMethod: "Adaptive Sigmoidal Gating with Learned Fallback",
        math: `g = \\sigma(W_g [z_B \\parallel z_C \\parallel m] + b_g) \\in [0, 1]^{64} \\\\ z_F = [z_B \\parallel (g \\odot z_C)] \\in \\mathbb{R}^{576} \\\\ \\hat{y} = \\sigma(W_f z_F + b_f)`,
        clinicalBias: "Dynamically modulates clinical confidence when acoustic margin is low; drops cleanly to B-mode baseline when clinical covariates are missing (m=0).",
        params: "11.26M parameters | Latency: 5.1 ms",
        status: "Primary Proposed Architecture"
    },
    A5: {
        title: "A5: Feature-wise Linear Modulation (FiLM)",
        inputs: ["B-mode US Image", "Age", "Sex"],
        activeStreams: ["visual", "clinical", "film", "fusion"],
        fusionMethod: "Affine Feature Conditioning z_B' = gamma(z_C) * z_B + beta(z_C)",
        math: `[\\gamma; \\beta] = W_{\\text{film}} z_C + b_{\\text{film}} \\\\ z_B' = \\gamma \\odot z_B + \\beta \\\\ \\hat{y} = \\sigma(W_o z_B' + b_o)`,
        clinicalBias: "Demographics condition acoustic representations globally through channel-wise scaling and shifting.",
        params: "11.24M parameters | Latency: 5.0 ms",
        status: "Ablation"
    },
    A6: {
        title: "A6: Late Decision-Level Ensemble",
        inputs: ["B-mode US Image", "Age", "Sex"],
        activeStreams: ["visual", "clinical", "ensemble"],
        fusionMethod: "Logit / Probability Averaging 0.5 * P(A1) + 0.5 * P(A2)",
        math: `P_{\\text{final}} = 0.5 \\cdot \\sigma(f_B(\\mathbf{x}_B)) + 0.5 \\cdot \\sigma(f_C(\\mathbf{x}_C))`,
        clinicalBias: "Naive unweighted averaging. High accuracy on easy cases, but severely degrades probability calibration (ECE = 0.191).",
        params: "11.18M + 4.3K parameters | Latency: 5.0 ms",
        status: "Diagnostic Ablation"
    },
    A7: {
        title: "A7: Context-Shuffle Diagnostic Control",
        inputs: ["B-mode US Image", "Permuted Age/Sex (Cohort Shuffled)"],
        activeStreams: ["visual", "clinical_shuffled", "gate", "fusion"],
        fusionMethod: "Gated Fusion with Decoupled Demographics",
        math: `\\tilde{\\mathbf{x}}_C = \\pi(\\mathbf{x}_C), \\quad \\pi \\sim \\text{Permutation}(\\mathcal{D}) \\\\ z_F = [z_B \\parallel (g \\odot z_{\\tilde{C}})]`,
        clinicalBias: "Proves that clinical gain is genuine epidemiology rather than regularizing noise. Performance drops to 0.991 when shuffled.",
        params: "11.26M parameters | Latency: 5.1 ms",
        status: "Scientific Control"
    },
    A8: {
        title: "A8: Cross-Modal Attention Fusion (CMAF)",
        inputs: ["B-mode Spatial Feature Map (C x H x W)", "Clinical Vector z_C"],
        activeStreams: ["visual", "clinical", "attention", "fusion"],
        fusionMethod: "Multi-Head Cross-Attention (Q: Visual, K/V: Clinical)",
        math: `Q = W_q F_B(u, v), \\quad K = W_k z_C, \\quad V = W_v z_C \\\\ \\text{Attn}(u, v) = \\text{Softmax}\\left(\\frac{Q K^T}{\\sqrt{d}}\\right) V`,
        clinicalBias: "Allows demographic priors to selectively amplify relevant spatial acoustic regions in the ultrasound feature map.",
        params: "11.38M parameters | Latency: 5.8 ms",
        status: "Advanced Multimodal"
    },
    A9: {
        title: "A9: Evidential Uncertainty Fusion (EUF)",
        inputs: ["B-mode US Image", "Age", "Sex"],
        activeStreams: ["visual", "clinical", "evidential", "fusion"],
        fusionMethod: "Subjective Logic Dirichlet Heads + Dempster's Rule",
        math: `\\alpha_m = \\text{Softplus}(W_m z_m) + 1, \\quad b_{m, k} = \\frac{\\alpha_{m, k} - 1}{S_m}, \\quad u_m = \\frac{K}{S_m} \\\\ \\mathcal{M} = \\mathcal{M}_B \\oplus \\mathcal{M}_C`,
        clinicalBias: "Explicitly decomposes uncertainty into aleatoric belief mass and epistemic vacancy u for certified referral triage.",
        params: "11.28M parameters | Latency: 5.3 ms",
        status: "Uncertainty & Safety"
    }
};

let currentSelectedModel = "A4";

function renderArchitectureView() {
    const container = document.getElementById('section-architecture');
    if (!container) return;

    const models = XMAI_DATA.ablation_models;

    container.innerHTML = `
        <div class="section-header">
            <span class="section-tag">Section 02 / Inductive Biases</span>
            <h2 class="section-title">Multimodal Architecture & Data Flow Visualizer</h2>
            <p class="section-desc">
                Interactive schematic of the dual-stream feature extraction, dynamic gating mechanism, 
                and fallback path across all 9 evaluated ablation architectures.
            </p>
        </div>

        <!-- Model Switcher Selector Pills -->
        <div class="model-selector-bar" role="tablist" aria-label="Select Architecture Model">
            ${models.map(m => `
                <button class="model-pill ${m.id === currentSelectedModel ? 'active' : ''}" 
                        id="pill-${m.id}"
                        data-model="${m.id}" 
                        role="tab" 
                        aria-selected="${m.id === currentSelectedModel}">
                    <strong>${m.id}</strong>: ${m.name.split(':')[1].trim()}
                </button>
            `).join('')}
        </div>

        <!-- Interactive Diagram Box -->
        <div class="card" style="margin-top: 1.25rem;">
            <div id="arch-schematic-box" style="padding: 1rem 0;">
                <!-- SVG Diagram dynamically rendered -->
            </div>

            <!-- Mathematical Formalism Card -->
            <div id="arch-spec-box" style="margin-top: 1.25rem; border-top: 1px solid var(--border-light); padding-top: 1.25rem;">
                <!-- Spec details dynamically rendered -->
            </div>
        </div>

        <!-- Layer-by-Layer Architectural Breakdown (Multimodal AI & Medical Translation) -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Layer-by-Layer Computational Breakdown</h3>
                    <p class="text-sm text-muted">A step-by-step engineering walkthrough bridging medical ultrasound phenomenology and multimodal AI representation learning.</p>
                </div>
                <span class="badge badge-accent">Formal Pipeline Specification</span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1rem;">
                <!-- Layer 1: Visual Feature Extraction -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-top: 4px solid #0284c7; border-radius: var(--radius-md); padding: 1.1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Layer 1 &bull; Visual</span>
                        <span class="font-mono text-xs" style="color: #0284c7; font-weight: 700;">ℝ³ˣ²²⁴ˣ²²⁴ → ℝ⁵¹²</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--navy-900);">Visual Spatial Encoder</h4>
                    <div style="font-size: 0.82rem; line-height: 1.5; color: var(--text-secondary);">
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="color: var(--text-primary); display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">AI Architecture:</strong>
                            ResNet-18 backbone with conv1-layer4 residual hierarchy followed by AdaptiveAvgPool2d. Extracts dense spatial morphology $z_B$.
                        </div>
                        <div style="background: var(--surface-alt); padding: 0.5rem 0.65rem; border-radius: var(--radius-sm); border-left: 2px solid #0284c7;">
                            <strong style="color: var(--text-primary); font-size: 0.74rem;">Medical Translation:</strong>
                            <span style="color: var(--navy-900);">Speckle noise, hypoechoic cores, and acoustic shadow artifacts are modeled as low-SNR spatial textures and gradient dropouts.</span>
                        </div>
                    </div>
                </div>

                <!-- Layer 2: Contextual Representation -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-top: 4px solid #059669; border-radius: var(--radius-md); padding: 1.1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Layer 2 &bull; Tabular</span>
                        <span class="font-mono text-xs" style="color: #059669; font-weight: 700;">ℝ² → ℝ⁶⁴</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--navy-900);">Epidemiological Prior MLP</h4>
                    <div style="font-size: 0.82rem; line-height: 1.5; color: var(--text-secondary);">
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="color: var(--text-primary); display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">AI Architecture:</strong>
                            2-layer MLP (dim: $2 \to 64 \to 64$) with LayerNorm + ReLU. Zero-leakage fold-isolated standardizer maps age/sex to latent context $z_C$.
                        </div>
                        <div style="background: var(--surface-alt); padding: 0.5rem 0.65rem; border-radius: var(--radius-sm); border-left: 2px solid #059669;">
                            <strong style="color: var(--text-primary); font-size: 0.74rem;">Medical Translation:</strong>
                            <span style="color: var(--navy-900);">Patient age & biological sex encode population-level tumor incidence priors (e.g. elderly males face 4.2x higher HCC risk).</span>
                        </div>
                    </div>
                </div>

                <!-- Layer 3: Multimodal Fusion Core -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-top: 4px solid #d97706; border-radius: var(--radius-md); padding: 1.1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Layer 3 &bull; Fusion</span>
                        <span class="font-mono text-xs" style="color: #d97706; font-weight: 700;">[z_B; z_C; m] → ℝ⁵⁷⁶</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--navy-900);">Dynamic Gating & Modulation</h4>
                    <div style="font-size: 0.82rem; line-height: 1.5; color: var(--text-secondary);">
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="color: var(--text-primary); display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">AI Architecture:</strong>
                            Context-aware gating unit $g = \sigma(W_g [z_B; z_C; m])$ applies feature-wise modulation $z_F = [z_B; g \odot z_C]$, with automatic null-bypass if $m=0$.
                        </div>
                        <div style="background: var(--surface-alt); padding: 0.5rem 0.65rem; border-radius: var(--radius-sm); border-left: 2px solid #d97706;">
                            <strong style="color: var(--text-primary); font-size: 0.74rem;">Medical Translation:</strong>
                            <span style="color: var(--navy-900);">When an ultrasound view is ambiguous or shadowed, the network elevates clinical weighting to disambiguate the diagnosis.</span>
                        </div>
                    </div>
                </div>

                <!-- Layer 4: Decision & Calibration -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-top: 4px solid #7c3aed; border-radius: var(--radius-md); padding: 1.1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Layer 4 &bull; Decision</span>
                        <span class="font-mono text-xs" style="color: #7c3aed; font-weight: 700;">Logits / T → P(y | x)</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--navy-900);">Calibrated Decision Head</h4>
                    <div style="font-size: 0.82rem; line-height: 1.5; color: var(--text-secondary);">
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="color: var(--text-primary); display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">AI Architecture:</strong>
                            Linear projection followed by post-hoc temperature scaling ($T=1.35$), optimizing NLL on validation logits to guarantee reliable probabilities.
                        </div>
                        <div style="background: var(--surface-alt); padding: 0.5rem 0.65rem; border-radius: var(--radius-sm); border-left: 2px solid #7c3aed;">
                            <strong style="color: var(--text-primary); font-size: 0.74rem;">Medical Translation:</strong>
                            <span style="color: var(--navy-900);">Prevents overconfident false reassurances in borderline patients, enabling certified referral triage when confidence margin is low.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Bind event listeners to model pills
    const pills = container.querySelectorAll('.model-pill');
    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            pills.forEach(p => {
                p.classList.remove('active');
                p.setAttribute('aria-selected', 'false');
            });
            pill.classList.add('active');
            pill.setAttribute('aria-selected', 'true');
            currentSelectedModel = pill.getAttribute('data-model');
            updateArchitectureDiagram(currentSelectedModel);
        });
    });

    // Initial render
    updateArchitectureDiagram(currentSelectedModel);
}

function updateArchitectureDiagram(modelId) {
    const spec = ARCHITECTURE_SCHEMATICS[modelId] || ARCHITECTURE_SCHEMATICS.A4;
    const schematicBox = document.getElementById('arch-schematic-box');
    const specBox = document.getElementById('arch-spec-box');
    if (!schematicBox || !specBox) return;

    const isVisualActive = spec.activeStreams.includes('visual');
    const isClinicalActive = spec.activeStreams.includes('clinical') || spec.activeStreams.includes('clinical_shuffled');
    const isShuffle = spec.activeStreams.includes('clinical_shuffled');
    const isGateActive = spec.activeStreams.includes('gate');
    const isFilmActive = spec.activeStreams.includes('film');
    const isAttentionActive = spec.activeStreams.includes('attention');
    const isEvidentialActive = spec.activeStreams.includes('evidential');
    const isEnsembleActive = spec.activeStreams.includes('ensemble');

    // SVG colors
    const activeColor = "#1d4ed8"; // Royal blue
    const inactiveColor = "#cbd5e1"; // Light slate gray
    const accentColor = "#0284c7"; // Cyan blue
    const warningColor = "#e11d48"; // Rose red for shuffle

    schematicBox.innerHTML = `
        <div class="svg-diagram-wrapper" style="width: 100%; overflow-x: auto;">
            <svg viewBox="0 0 960 380" style="width: 100%; max-width: 960px; height: auto; display: block; margin: 0 auto; font-family: 'Inter', sans-serif;">
                <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 1 L 9 5 L 0 9 z" fill="#64748b" />
                    </marker>
                    <marker id="arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 1 L 9 5 L 0 9 z" fill="${activeColor}" />
                    </marker>
                    <linearGradient id="visGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#eff6ff" />
                        <stop offset="100%" stop-color="#dbeafe" />
                    </linearGradient>
                    <linearGradient id="clinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#f8fafc" />
                        <stop offset="100%" stop-color="#e2e8f0" />
                    </linearGradient>
                </defs>

                <!-- Background Frame -->
                <rect x="10" y="10" width="940" height="360" rx="8" fill="#fcfdfd" stroke="#e2e8f0" stroke-width="1.5" />

                <!-- 1. STREAM 1: VISUAL (Top Stream) -->
                <g opacity="${isVisualActive ? 1.0 : 0.35}">
                    <!-- Input US Image -->
                    <rect x="40" y="45" width="130" height="75" rx="6" fill="url(#visGrad)" stroke="${isVisualActive ? activeColor : inactiveColor}" stroke-width="2" />
                    <text x="105" y="75" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">B-Mode US</text>
                    <text x="105" y="95" text-anchor="middle" font-size="10" fill="#64748b" font-family="'JetBrains Mono', monospace">3 × 224 × 224</text>

                    <!-- Arrow 1 to Backbone -->
                    <line x1="170" y1="82" x2="225" y2="82" stroke="${isVisualActive ? activeColor : inactiveColor}" stroke-width="2" marker-end="url(#arrow-active)" />

                    <!-- Backbone: ResNet-18 -->
                    <rect x="230" y="40" width="160" height="85" rx="6" fill="#ffffff" stroke="${isVisualActive ? activeColor : inactiveColor}" stroke-width="2" />
                    <text x="310" y="70" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">ResNet-18 Backbone</text>
                    <text x="310" y="90" text-anchor="middle" font-size="10" fill="#64748b">conv1 → layer4 → GAP</text>
                    <text x="310" y="108" text-anchor="middle" font-size="10" font-weight="600" fill="${activeColor}" font-family="'JetBrains Mono', monospace">z_B ∈ ℝ⁵¹²</text>

                    <!-- Arrow to Fusion -->
                    <line x1="390" y1="82" x2="520" y2="82" stroke="${isVisualActive ? activeColor : inactiveColor}" stroke-width="2" marker-end="url(#arrow-active)" />
                </g>

                <!-- 2. STREAM 2: CLINICAL COVARIATES (Bottom Stream) -->
                <g opacity="${isClinicalActive ? 1.0 : 0.35}">
                    <!-- Input Clinical Box -->
                    <rect x="40" y="240" width="130" height="75" rx="6" fill="${isShuffle ? '#ffe4e6' : 'url(#clinGrad)'}" stroke="${isShuffle ? warningColor : (isClinicalActive ? '#059669' : inactiveColor)}" stroke-width="2" />
                    <text x="105" y="265" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">${isShuffle ? 'Shuffled Prior' : 'Clinical Priors'}</text>
                    <text x="105" y="285" text-anchor="middle" font-size="10" fill="#475569">Age, Sex</text>
                    <text x="105" y="302" text-anchor="middle" font-size="9" font-weight="600" fill="${isShuffle ? warningColor : '#059669'}" font-family="'JetBrains Mono', monospace">Mask m ∈ {0,1}²</text>

                    <!-- Arrow to Clinical MLP -->
                    <line x1="170" y1="277" x2="225" y2="277" stroke="${isShuffle ? warningColor : (isClinicalActive ? '#059669' : inactiveColor)}" stroke-width="2" marker-end="url(#arrow)" />

                    <!-- Clinical MLP Encoder -->
                    <rect x="230" y="235" width="160" height="85" rx="6" fill="#ffffff" stroke="${isShuffle ? warningColor : (isClinicalActive ? '#059669' : inactiveColor)}" stroke-width="2" />
                    <text x="310" y="265" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Clinical Encoder</text>
                    <text x="310" y="285" text-anchor="middle" font-size="10" fill="#64748b">Dense(64) + LayerNorm</text>
                    <text x="310" y="303" text-anchor="middle" font-size="10" font-weight="600" fill="${isShuffle ? warningColor : '#059669'}" font-family="'JetBrains Mono', monospace">z_C ∈ ℝ⁶⁴</text>

                    <!-- Arrow to Fusion -->
                    <line x1="390" y1="277" x2="520" y2="277" stroke="${isShuffle ? warningColor : (isClinicalActive ? '#059669' : inactiveColor)}" stroke-width="2" marker-end="url(#arrow)" />
                </g>

                <!-- 3. FUSION ENGINE (Middle Center) -->
                <g>
                    <!-- Center Fusion Box -->
                    <rect x="525" y="55" width="210" height="250" rx="8" fill="#ffffff" stroke="${activeColor}" stroke-width="2.5" />
                    <rect x="525" y="55" width="210" height="35" rx="6" fill="#eff6ff" />
                    <text x="630" y="78" text-anchor="middle" font-size="13" font-weight="800" fill="#1e3a8a">FUSION ENGINE</text>

                    <!-- Sub-block based on active paradigm -->
                    ${isGateActive ? `
                        <rect x="545" y="110" width="170" height="60" rx="6" fill="#f8fafc" stroke="${accentColor}" stroke-width="1.5" />
                        <text x="630" y="132" text-anchor="middle" font-size="11" font-weight="700" fill="#0f172a">Dynamic Gating Unit</text>
                        <text x="630" y="152" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="${accentColor}">g = σ(W_g [z_B; z_C; m])</text>
                        
                        <rect x="545" y="185" width="170" height="50" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="1.5" />
                        <text x="630" y="206" text-anchor="middle" font-size="11" font-weight="700" fill="#0f172a">Masked Modulation</text>
                        <text x="630" y="224" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="#475569">z_F = [z_B; g ⊙ z_C]</text>
                        <text x="630" y="285" text-anchor="middle" font-size="10" font-weight="700" fill="#059669">Fallback Path Active when m=0</text>
                    ` : ''}

                    ${isFilmActive ? `
                        <rect x="545" y="135" width="170" height="85" rx="6" fill="#f8fafc" stroke="${accentColor}" stroke-width="1.5" />
                        <text x="630" y="160" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">FiLM Generator</text>
                        <text x="630" y="180" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="${accentColor}">[γ; β] = W_film z_C</text>
                        <text x="630" y="200" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="#0f172a">z_B' = γ ⊙ z_B + β</text>
                    ` : ''}

                    ${isAttentionActive ? `
                        <rect x="545" y="135" width="170" height="85" rx="6" fill="#f8fafc" stroke="${accentColor}" stroke-width="1.5" />
                        <text x="630" y="160" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Cross-Modal Attn</text>
                        <text x="630" y="180" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="${accentColor}">Q = W_q F_B, K = W_k z_C</text>
                        <text x="630" y="200" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="#0f172a">Softmax(QKᵀ / √d) V</text>
                    ` : ''}

                    ${isEvidentialActive ? `
                        <rect x="545" y="135" width="170" height="85" rx="6" fill="#f8fafc" stroke="${accentColor}" stroke-width="1.5" />
                        <text x="630" y="160" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Dempster-Shafer Core</text>
                        <text x="630" y="180" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="${accentColor}">M = M_B ⊕ M_C</text>
                        <text x="630" y="200" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="#0f172a">Belief b_k, Vacancy u</text>
                    ` : ''}

                    ${isEnsembleActive ? `
                        <rect x="545" y="135" width="170" height="85" rx="6" fill="#f8fafc" stroke="${accentColor}" stroke-width="1.5" />
                        <text x="630" y="160" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Ensemble Averaging</text>
                        <text x="630" y="180" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="${accentColor}">P = 0.5 P_B + 0.5 P_C</text>
                        <text x="630" y="200" text-anchor="middle" font-size="9" fill="#e11d48">Miscalibrated (ECE 0.191)</text>
                    ` : ''}

                    ${(!isGateActive && !isFilmActive && !isAttentionActive && !isEvidentialActive && !isEnsembleActive) ? `
                        <rect x="545" y="135" width="170" height="85" rx="6" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.5" />
                        <text x="630" y="165" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">${spec.fusionMethod}</text>
                        <text x="630" y="190" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" fill="#64748b">${modelId === 'A1' ? 'Visual Only Bypass' : (modelId === 'A2' ? 'Clinical Only Bypass' : 'Concatenation [z_B; z_C]')}</text>
                    ` : ''}
                </g>

                <!-- Arrow from Fusion to Classification Head -->
                <line x1="735" y1="180" x2="790" y2="180" stroke="${activeColor}" stroke-width="2.5" marker-end="url(#arrow-active)" />

                <!-- 4. CLASSIFICATION & CALIBRATION HEAD -->
                <rect x="795" y="115" width="140" height="130" rx="8" fill="#ffffff" stroke="${activeColor}" stroke-width="2" />
                <text x="865" y="145" text-anchor="middle" font-size="12" font-weight="800" fill="#0f172a">Decision Head</text>
                <text x="865" y="165" text-anchor="middle" font-size="10" fill="#64748b">Logit z → Sigmoid</text>
                <line x1="810" y1="175" x2="920" y2="175" stroke="#e2e8f0" stroke-width="1" />
                <text x="865" y="195" text-anchor="middle" font-size="10" font-weight="700" fill="#0284c7">Temp Scaling T=1.35</text>
                <text x="865" y="215" text-anchor="middle" font-size="11" font-weight="800" fill="#059669">P(HCC | x)</text>
                <text x="865" y="232" text-anchor="middle" font-size="9" fill="#64748b">Risk Score & Margin</text>
            </svg>
        </div>
    `;

    specBox.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
            <div>
                <span class="badge ${spec.status.includes('Proposed') ? 'badge-accent' : 'badge-neutral'}">${spec.status}</span>
                <h4 style="margin: 0.5rem 0 0.25rem 0; font-size: 1.1rem; color: var(--navy-900);">${spec.title}</h4>
                <p style="margin: 0; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">${spec.clinicalBias}</p>
                <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">
                    ${spec.params}
                </div>
            </div>
            <div style="background: var(--surface-alt); border-radius: var(--radius-sm); padding: 0.85rem 1rem; border-left: 3px solid var(--accent);">
                <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: var(--text-secondary); letter-spacing: 0.05em; margin-bottom: 0.35rem;">
                    Mathematical Formalism
                </div>
                <div class="math-block" style="margin: 0.25rem 0 0 0; background: transparent; border: none; padding: 0;">
                    ${window.MathRenderer ? window.MathRenderer.render(spec.math, true) : spec.math}
                </div>
            </div>
        </div>
    `;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderArchitectureView);
} else {
    renderArchitectureView();
}
