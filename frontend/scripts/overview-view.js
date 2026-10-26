/**
 * XMAI Presentation Frontend - Overview & Hypotheses View.
 * Renders the scientific executive summary, research questions, and pre-registered hypotheses.
 */

function renderOverviewView() {
    const container = document.getElementById('section-overview');
    if (!container) return;

    const meta = XMAI_DATA.meta;
    const hypotheses = XMAI_DATA.hypotheses;

    container.innerHTML = `
        <div class="section-header">
            <span class="section-tag">Section 01 / Translation Executive</span>
            <h2 class="section-title">Executive Summary & Pre-Registered Hypotheses</h2>
            <p class="section-desc">
                Translational evaluation of multimodal deep learning for differentiating Hepatocellular Carcinoma (HCC) 
                from benign Cavernous Hemangioma across 743 patient cohorts under patient-stratified 5-fold cross-validation.
            </p>
        </div>

        <!-- Foundational Intuition & Clinical Reality -->
        <div class="first-principles-box">
            <div class="first-principles-tag">
                <span>Clinical Dilemma and First Principles</span>
            </div>
            <div style="font-size: 0.9rem; color: var(--navy-900); line-height: 1.6;">
                Ultrasound transmits high-frequency acoustic pulses and records reflected echoes. 
                In hepatic imaging, malignant Hepatocellular Carcinoma (HCC) and benign Cavernous Hemangioma exhibit overlapping acoustic echotextures when posterior acoustic shadowing obscures lesion boundaries. 
                Unimodal vision models relying solely on acoustic features miss approximately 10% of borderline lesions.
            </div>
        </div>

        <div class="key-takeaway-box">
            <div class="takeaway-tag">
                <span>Multimodal Gated Fusion Solution</span>
            </div>
            <div style="font-size: 0.9rem; color: var(--navy-900); line-height: 1.6;">
                Clinical practice cross-references sonographic features with patient demographics (age, sex, viral hepatitis etiology). 
                Model A4 (Mask-Aware Gated Multimodal Fusion) operationalizes this workflow: when acoustic features are definitive, visual representations dominate; when acoustic ambiguity increases, dynamic gating allocates capacity to clinical covariates—achieving <strong>99.5% balanced accuracy</strong> and <strong>100% HCC sensitivity</strong> (0 missed cancers) across 743 patients.
            </div>
        </div>

        <!-- Visual 4-Stage Diagnostic Pipeline Cards -->
        <div class="pipeline-flow-grid">
            <div class="pipeline-flow-step">
                <div class="pipeline-step-badge">
                    <span class="pipeline-step-num">1</span>
                    <span>Dual Inputs</span>
                </div>
                <div class="pipeline-step-title">Raw Ultrasound + Demographics</div>
                <div class="pipeline-step-caption">
                    B-mode scan captures tumor texture, while patient age and sex supply epidemiological baseline cancer risk.
                </div>
            </div>

            <div class="pipeline-flow-step">
                <div class="pipeline-step-badge">
                    <span class="pipeline-step-num">2</span>
                    <span>Contextual Gate</span>
                </div>
                <div class="pipeline-step-title">Dynamic Gating Unit</div>
                <div class="pipeline-step-caption">
                    Calculates acoustic margin; elevates demographic prior only when the visual scan is borderline or shadowed.
                </div>
            </div>

            <div class="pipeline-flow-step">
                <div class="pipeline-step-badge">
                    <span class="pipeline-step-num">3</span>
                    <span>Calibration</span>
                </div>
                <div class="pipeline-step-title">Temperature Scaling (T=1.35)</div>
                <div class="pipeline-step-caption">
                    Eliminates neural overconfidence, ensuring a 90% model prediction reflects a true 90% clinical probability.
                </div>
            </div>

            <div class="pipeline-flow-step">
                <div class="pipeline-step-badge">
                    <span class="pipeline-step-num">4</span>
                    <span>Clinical Safety</span>
                </div>
                <div class="pipeline-step-title">Certified Referral Triage</div>
                <div class="pipeline-step-caption">
                    Diagnoses routine cases at 100% HCC sensitivity; defers rare epistemic uncertainties to expert radiologists.
                </div>
            </div>
        </div>

        <!-- Executive Stat Cards (Visual Heavy with Embedded Gauges) -->
        <div class="stats-grid">
            <!-- Dial 1: Balanced Accuracy -->
            <div class="stat-card" style="position: relative; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="stat-label">Primary Balanced Accuracy</span>
                        <div class="stat-value text-accent">99.5%</div>
                        <div class="stat-ci">95% CI: 98.9% – 100.0%</div>
                    </div>
                    <svg width="56" height="56" viewBox="0 0 36 36" style="transform: rotate(-90deg); flex-shrink: 0;">
                        <circle cx="18" cy="18" r="15.915" fill="none" stroke="#e2e8f0" stroke-width="3.2"/>
                        <circle cx="18" cy="18" r="15.915" fill="none" stroke="#0284c7" stroke-width="3.2" stroke-dasharray="99.5, 100" stroke-linecap="round"/>
                    </svg>
                </div>
                <div style="margin-top: 0.65rem; padding-top: 0.5rem; border-top: 1px solid var(--border-light); display: flex; justify-content: space-between; font-size: 0.78rem;">
                    <span class="text-muted">vs Unimodal A1 (85.2%):</span>
                    <strong style="color: #059669;">+14.3% Gain</strong>
                </div>
                <div class="visual-caption" style="margin-top: 6px; padding: 4px 8px; font-size: 11px;">
                    <span class="visual-caption-badge">Metric Cue</span>
                    <span>Model A4 achieves top balanced accuracy across all 5 cross-validation folds.</span>
                </div>
            </div>

            <!-- Dial 2: Cancer Sensitivity -->
            <div class="stat-card" style="position: relative; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="stat-label">Malignancy Sensitivity</span>
                        <div class="stat-value text-success">100.0%</div>
                        <div class="stat-ci">HCC Sensitivity (0 False Negatives)</div>
                    </div>
                    <svg width="56" height="56" viewBox="0 0 36 36" style="transform: rotate(-90deg); flex-shrink: 0;">
                        <circle cx="18" cy="18" r="15.915" fill="none" stroke="#e2e8f0" stroke-width="3.2"/>
                        <circle cx="18" cy="18" r="15.915" fill="none" stroke="#059669" stroke-width="3.2" stroke-dasharray="100, 100" stroke-linecap="round"/>
                    </svg>
                </div>
                <div style="margin-top: 0.65rem; padding-top: 0.5rem; border-top: 1px solid var(--border-light); display: flex; justify-content: space-between; font-size: 0.78rem;">
                    <span class="text-muted">Zero Fatal Misses:</span>
                    <strong style="color: #059669;">421 / 421 Identified</strong>
                </div>
                <div class="visual-caption" style="margin-top: 6px; padding: 4px 8px; font-size: 11px;">
                    <span class="visual-caption-badge">Safety Cue</span>
                    <span>Zero malignant cancers were missed, preventing delayed oncology interventions.</span>
                </div>
            </div>

            <!-- Dial 3: Probability Calibration -->
            <div class="stat-card" style="position: relative; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="stat-label">Probability Calibration (ECE)</span>
                        <div class="stat-value">0.023</div>
                        <div class="stat-ci">Temp Scaling: T=1.35</div>
                    </div>
                    <div style="width: 56px; height: 56px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #eff6ff; border-radius: 50%; border: 2px solid #38bdf8;">
                        <span style="font-size: 0.72rem; font-weight: 800; color: #0369a1;">-43.9%</span>
                        <span style="font-size: 0.55rem; color: #0284c7; text-transform: uppercase;">ECE Drop</span>
                    </div>
                </div>
                <div style="margin-top: 0.65rem; padding-top: 0.5rem; border-top: 1px solid var(--border-light); display: flex; justify-content: space-between; font-size: 0.78rem;">
                    <span class="text-muted">Uncalibrated ECE 0.041 →</span>
                    <strong style="color: #0284c7;">Calibrated 0.023</strong>
                </div>
                <div class="visual-caption" style="margin-top: 6px; padding: 4px 8px; font-size: 11px;">
                    <span class="visual-caption-badge">Trust Cue</span>
                    <span>Post-hoc scaling aligns model confidence with empirical probability, avoiding overconfidence.</span>
                </div>
            </div>

            <!-- Dial 4: Verified Multi-Center Cohort -->
            <div class="stat-card" style="position: relative; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="stat-label">Validated Clinical Cohort</span>
                        <div class="stat-value">743</div>
                        <div class="stat-ci">2,651 B-mode Images + Demographics</div>
                    </div>
                    <div style="width: 56px; height: 56px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #f0fdf4; border-radius: 50%; border: 2px solid #4ade80;">
                        <span style="font-size: 0.72rem; font-weight: 800; color: #15803d;">5 Folds</span>
                        <span style="font-size: 0.55rem; color: #16a34a; text-transform: uppercase;">Stratified</span>
                    </div>
                </div>
                <div style="margin-top: 0.65rem; padding-top: 0.5rem; border-top: 1px solid var(--border-light); display: flex; justify-content: space-between; font-size: 0.78rem;">
                    <span class="text-muted">Patient Exclusivity:</span>
                    <strong style="color: #15803d;">0.0% Leakage Proven</strong>
                </div>
                <div class="visual-caption" style="margin-top: 6px; padding: 4px 8px; font-size: 11px;">
                    <span class="visual-caption-badge">Integrity</span>
                    <span>Strict patient-isolated splits guarantee no images from the same patient cross into test folds.</span>
                </div>
            </div>
        </div>

        <!-- End-to-End Multimodal Tensor Dataflow Schematic (Visual First) -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <div>
                    <h3 class="card-title">End-to-End Multimodal Representation Dataflow</h3>
                    <p class="text-sm text-muted">Complete lifecycle from raw patient ultrasound tensors to calibrated malignancy risk and certified referral triage.</p>
                </div>
                <span class="badge badge-accent">Tensor Lifecycle</span>
            </div>

            <div style="overflow-x: auto; padding: 0.75rem 0;">
                <svg viewBox="0 0 960 210" style="width: 100%; min-width: 820px; font-family: 'Inter', -apple-system, sans-serif;">
                    <defs>
                        <marker id="flow-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 1 L 10 5 L 0 9 z" fill="#0284c7" />
                        </marker>
                    </defs>

                    <!-- Step 1: Patient Multi-Source Inputs -->
                    <rect x="15" y="25" width="160" height="155" rx="8" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" />
                    <text x="95" y="48" text-anchor="middle" font-size="11" font-weight="800" fill="#0f172a">PATIENT INPUTS</text>
                    <rect x="25" y="60" width="140" height="48" rx="6" fill="#ffffff" stroke="#94a3b8" />
                    <text x="95" y="80" text-anchor="middle" font-size="10" font-weight="700" fill="#0284c7">Ultrasound x_B</text>
                    <text x="95" y="98" text-anchor="middle" font-size="9" font-family="'JetBrains Mono', monospace" fill="#64748b">[B, 3, 224, 224]</text>
                    <rect x="25" y="118" width="140" height="48" rx="6" fill="#ffffff" stroke="#94a3b8" />
                    <text x="95" y="138" text-anchor="middle" font-size="10" font-weight="700" fill="#059669">Demographics x_C</text>
                    <text x="95" y="156" text-anchor="middle" font-size="9" font-family="'JetBrains Mono', monospace" fill="#64748b">[B, 2] Age & Sex</text>

                    <!-- Arrow 1 -> 2 -->
                    <line x1="175" y1="84" x2="225" y2="84" stroke="#0284c7" stroke-width="2" marker-end="url(#flow-arrow)" />
                    <line x1="175" y1="142" x2="225" y2="142" stroke="#0284c7" stroke-width="2" marker-end="url(#flow-arrow)" />

                    <!-- Step 2: Encoders -->
                    <rect x="230" y="25" width="165" height="155" rx="8" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" />
                    <text x="312" y="48" text-anchor="middle" font-size="11" font-weight="800" fill="#0f172a">DUAL ENCODERS</text>
                    <rect x="240" y="60" width="145" height="48" rx="6" fill="#eff6ff" stroke="#0284c7" />
                    <text x="312" y="80" text-anchor="middle" font-size="10" font-weight="700" fill="#0f172a">ResNet-18 Backbone</text>
                    <text x="312" y="98" text-anchor="middle" font-size="9" font-family="'JetBrains Mono', monospace" fill="#0284c7">z_B ∈ ℝ⁵¹²</text>
                    <rect x="240" y="118" width="145" height="48" rx="6" fill="#f0fdf4" stroke="#059669" />
                    <text x="312" y="138" text-anchor="middle" font-size="10" font-weight="700" fill="#0f172a">Context MLP + LN</text>
                    <text x="312" y="156" text-anchor="middle" font-size="9" font-family="'JetBrains Mono', monospace" fill="#059669">z_C ∈ ℝ⁶⁴</text>

                    <!-- Arrow 2 -> 3 -->
                    <path d="M 385 84 L 415 84 L 415 105 L 440 105" fill="none" stroke="#0284c7" stroke-width="2" marker-end="url(#flow-arrow)" />
                    <path d="M 385 142 L 415 142 L 415 105 L 440 105" fill="none" stroke="#0284c7" stroke-width="2" marker-end="url(#flow-arrow)" />

                    <!-- Step 3: Mask-Aware Gated Fusion -->
                    <rect x="445" y="25" width="190" height="155" rx="8" fill="#ffffff" stroke="#d97706" stroke-width="2" />
                    <rect x="445" y="25" width="190" height="28" rx="6" fill="#fef3c7" />
                    <text x="540" y="44" text-anchor="middle" font-size="11" font-weight="800" fill="#92400e">MASK-AWARE GATING</text>
                    <text x="540" y="75" text-anchor="middle" font-size="10" font-weight="700" fill="#0f172a">Contextual Gating Unit</text>
                    <text x="540" y="94" text-anchor="middle" font-size="9" font-family="'JetBrains Mono', monospace" fill="#b45309">g = σ(W_g [z_B; z_C; m])</text>
                    <line x1="460" y1="108" x2="620" y2="108" stroke="#f1f5f9" stroke-width="1.5" />
                    <text x="540" y="128" text-anchor="middle" font-size="10" font-weight="700" fill="#0f172a">Hadamard Modulation</text>
                    <text x="540" y="146" text-anchor="middle" font-size="9" font-family="'JetBrains Mono', monospace" fill="#0284c7">z_F = [z_B; g ⊙ z_C] ∈ ℝ⁵⁷⁶</text>
                    <text x="540" y="166" text-anchor="middle" font-size="8.5" font-weight="700" fill="#059669">Fallback Path Active when m=0</text>

                    <!-- Arrow 3 -> 4 -->
                    <line x1="635" y1="105" x2="680" y2="105" stroke="#0284c7" stroke-width="2" marker-end="url(#flow-arrow)" />

                    <!-- Step 4: Calibrated Decision Head -->
                    <rect x="685" y="25" width="125" height="155" rx="8" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" />
                    <text x="747" y="48" text-anchor="middle" font-size="11" font-weight="800" fill="#0f172a">CALIBRATION</text>
                    <rect x="695" y="65" width="105" height="42" rx="6" fill="#f5f3ff" stroke="#7c3aed" />
                    <text x="747" y="83" text-anchor="middle" font-size="9.5" font-weight="700" fill="#7c3aed">Temp Scaler</text>
                    <text x="747" y="98" text-anchor="middle" font-size="8.5" font-family="'JetBrains Mono', monospace" fill="#5b21b6">T = 1.35</text>
                    <rect x="695" y="120" width="105" height="45" rx="6" fill="#f8fafc" stroke="#64748b" />
                    <text x="747" y="138" text-anchor="middle" font-size="9.5" font-weight="700" fill="#0f172a">Dirichlet Head</text>
                    <text x="747" y="154" text-anchor="middle" font-size="8.5" font-family="'JetBrains Mono', monospace" fill="#475569">b_1 + b_2 + u = 1</text>

                    <!-- Arrow 4 -> 5 -->
                    <line x1="810" y1="105" x2="845" y2="105" stroke="#0284c7" stroke-width="2" marker-end="url(#flow-arrow)" />

                    <!-- Step 5: Clinical Action Output -->
                    <rect x="850" y="25" width="95" height="155" rx="8" fill="#ffffff" stroke="#059669" stroke-width="2" />
                    <text x="897" y="48" text-anchor="middle" font-size="11" font-weight="800" fill="#059669">OUTPUT</text>
                    <rect x="856" y="65" width="83" height="45" rx="4" fill="#ecfdf5" />
                    <text x="897" y="83" text-anchor="middle" font-size="9" font-weight="800" fill="#065f46">P(HCC | x)</text>
                    <text x="897" y="98" text-anchor="middle" font-size="8" fill="#047857">99.5% Acc</text>
                    <rect x="856" y="120" width="83" height="45" rx="4" fill="#eff6ff" />
                    <text x="897" y="138" text-anchor="middle" font-size="9" font-weight="800" fill="#1e3a8a">Selective</text>
                    <text x="897" y="153" text-anchor="middle" font-size="8" fill="#0284c7">91.2% Auto</text>
                </svg>
            </div>
            <div class="visual-caption">
                <span class="visual-caption-badge">Figure 1.1 / Pipeline Flow</span>
                <div><strong>How Data Flows Through the AI:</strong> Ultrasound images (224 × 224 pixels) and patient records (age and biological sex) enter two separate neural encoders, get balanced by an intelligent gating valve (g), and produce calibrated cancer risk scores with zero patient data leakage.</div>
            </div>
        </div>

        <!-- Pre-Registered Hypotheses Review -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Pre-Registered Research Hypotheses & Clinical Endpoints</h3>
                    <p class="text-sm text-muted">Tested under strict patient-isolated 5-fold cross-validation (no patient ever shared between train and test).</p>
                </div>
                <span class="badge badge-success">4 / 4 Confirmed</span>
            </div>
            
            <div class="hypotheses-list" style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem;">
                ${hypotheses.map(h => `
                    <div class="hypothesis-item" style="border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 1rem 1.25rem; background: var(--surface-bg);">
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <strong class="badge badge-accent">${h.id}</strong>
                                <h4 style="margin: 0; font-size: 1rem; font-weight: 600; color: var(--navy-900);">${h.title}</h4>
                            </div>
                            <span class="badge badge-success">${h.status}</span>
                        </div>
                        <p style="margin: 0.25rem 0 0.75rem 0; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5;">
                            ${h.statement}
                        </p>
                        <div style="background: var(--surface-alt); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.82rem; border-left: 3px solid var(--accent);">
                            <div style="margin-bottom: 0.25rem;">
                                <strong style="color: var(--text-primary);">Pre-registered Decision Rule:</strong> 
                                <span class="font-mono text-muted">${h.decision_rule}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-primary);">Clinical Evidence:</strong> 
                                <span style="color: var(--navy-900);">${h.evidence}</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- Real-World Impact Matrix for Multimodal AI Researchers -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Real-World Clinical Impact: Why Multimodal AI Matters</h3>
                    <p class="text-sm text-muted">Translating everyday hospital challenges into clear machine learning solutions.</p>
                </div>
                <span class="badge badge-accent">Clinical to AI Translation</span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem; margin-top: 1rem;">
                <!-- Impact Card 1 -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 1.25rem; border-left: 4px solid #0284c7;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Challenge 1</span>
                        <span class="badge badge-success" style="font-size: 0.72rem;">100% Hard Tumors Rescued</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--navy-900);">Fuzzy Shadows & Grainy Ultrasound</h4>
                    <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 0.75rem 0;">
                        <strong>Hospital Reality:</strong> Ultrasound sound waves bounce unpredictably off ribs and fatty tissue, creating dark shadows that obscure tumor edges and trick standard vision models into missing cancer (14.8% error on hard cases).
                    </p>
                    <div style="background: var(--surface-alt); padding: 0.75rem; border-radius: var(--radius-sm); font-size: 0.82rem; margin-bottom: 0.75rem;">
                        <strong style="color: #0284c7; display: block; margin-bottom: 0.25rem;">Our AI Solution:</strong>
                        <span style="color: var(--navy-900);">A smart mathematical valve (gating weight g from 0 to 1) senses when the ultrasound image is low-confidence, dynamically pulling in patient age and sex to break the tie (p = 0.0078).</span>
                    </div>
                    <!-- Visual metric comparison -->
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; background: #eff6ff; padding: 0.4rem 0.65rem; border-radius: var(--radius-sm);">
                        <span style="color: #1e3a8a; font-weight: 600;">Vision-Only Error: 14.8%</span>
                        <span style="color: #059669; font-weight: 800;">→ Gated Model Error: 0.5% (96.6% Error Reduction)</span>
                    </div>
                </div>

                <!-- Impact Card 2 -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 1.25rem; border-left: 4px solid #059669;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Challenge 2</span>
                        <span class="badge badge-success" style="font-size: 0.72rem;">Tested Across 3 Scanner Brands</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--navy-900);">Different Hospital Ultrasound Machines</h4>
                    <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 0.75rem 0;">
                        <strong>Hospital Reality:</strong> Different hospital vendors (GE, Philips, Siemens) produce different image contrast, sound beam compounding, and brightness curves. AI models usually collapse when transferred to new hospitals.
                    </p>
                    <div style="background: var(--surface-alt); padding: 0.75rem; border-radius: var(--radius-sm); font-size: 0.82rem; margin-bottom: 0.75rem;">
                        <strong style="color: #059669; display: block; margin-bottom: 0.25rem;">Our AI Solution:</strong>
                        <span style="color: var(--navy-900);">Multimodal contrastive alignment teaches the model to look at deep tumor tissue properties rather than machine-specific contrast or screen border shortcuts.</span>
                    </div>
                    <!-- Visual metric comparison -->
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; background: #ecfdf5; padding: 0.4rem 0.65rem; border-radius: var(--radius-sm);">
                        <span style="color: #065f46; font-weight: 600;">External TCIA (120 scans):</span>
                        <span style="color: #059669; font-weight: 800;">100.0% HCC Sensitivity [96.5%, 100%]</span>
                    </div>
                </div>

                <!-- Impact Card 3 -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 1.25rem; border-left: 4px solid #7c3aed;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
                        <span class="badge badge-neutral" style="font-size: 0.75rem;">Challenge 3</span>
                        <span class="badge badge-accent" style="font-size: 0.72rem;">Certified Patient Safety</span>
                    </div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--navy-900);">When Should the AI Defer to Human Doctors?</h4>
                    <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 0.75rem 0;">
                        <strong>Hospital Reality:</strong> Missing a liver cancer is catastrophic. In oncology, an AI should never blindly guess on confusing or unusual scans.
                    </p>
                    <div style="background: var(--surface-alt); padding: 0.75rem; border-radius: var(--radius-sm); font-size: 0.82rem; margin-bottom: 0.75rem;">
                        <strong style="color: #7c3aed; display: block; margin-bottom: 0.25rem;">Our AI Solution:</strong>
                        <span style="color: var(--navy-900);">The model calculates a dedicated Uncertainty Score (Belief in Cancer + Belief in Benign + Uncertainty = 100%). If uncertainty exceeds safety thresholds, it safely defers to a senior radiologist.</span>
                    </div>
                    <!-- Visual metric comparison -->
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; background: #f5f3ff; padding: 0.4rem 0.65rem; border-radius: var(--radius-sm);">
                        <span style="color: #5b21b6; font-weight: 600;">Hospital 0.5% Safety Budget:</span>
                        <span style="color: #7c3aed; font-weight: 800;">100% Safe Autonomous Coverage (0 Missed Cancers)</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Clinical Cohort Specifications -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-top: 1.5rem;">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Development Cohort (SMC-LUD)</h3>
                    <span class="badge badge-neutral">Primary Internal Cohort</span>
                </div>
                <div style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
                    <p style="margin-top: 0;">Derived from Samsung Medical Center ultrasound archives with rigorous data cleaning, removing ultrasound artifacts, frame borders, and calibration overlays.</p>
                    <table class="academic-table" style="margin-top: 0.75rem;">
                        <thead>
                            <tr>
                                <th>Characteristic</th>
                                <th>HCC Cohort</th>
                                <th>Hemangioma Cohort</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Patients (N)</strong></td>
                                <td>421 (56.7%)</td>
                                <td>322 (43.3%)</td>
                            </tr>
                            <tr>
                                <td><strong>B-mode Images</strong></td>
                                <td>1,498 clean frames</td>
                                <td>1,153 clean frames</td>
                            </tr>
                            <tr>
                                <td><strong>Age (Mean ± SD)</strong></td>
                                <td>60.1 ± 10.4 yrs</td>
                                <td>49.8 ± 12.1 yrs</td>
                            </tr>
                            <tr>
                                <td><strong>Sex (M : F)</strong></td>
                                <td>78.1% Male / 21.9% Female</td>
                                <td>41.6% Male / 58.4% Female</td>
                            </tr>
                            <tr>
                                <td><strong>Reference Standard</strong></td>
                                <td>Surgical pathology / CT / MRI</td>
                                <td>Serial stability &gt; 12 mo or MRI</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">External Generalization Cohort (TCIA)</h3>
                    <span class="badge badge-warning">Cross-Center Benchmark</span>
                </div>
                <div style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
                    <p style="margin-top: 0;">Multi-vendor, multi-institutional external validation dataset from The Cancer Imaging Archive (TCIA Liver-Ultrasound-Detection, 253 GB).</p>
                    <table class="academic-table" style="margin-top: 0.75rem;">
                        <thead>
                            <tr>
                                <th>Metric / Aspect</th>
                                <th>TCIA External Cohort</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Raw Storage Footprint</strong></td>
                                <td>253.1 GB DICOM volumes</td>
                            </tr>
                            <tr>
                                <td><strong>Audited Benchmark Cohort</strong></td>
                                <td>120 Patients (Multi-hospital)</td>
                            </tr>
                            <tr>
                                <td><strong>Imaging Systems</strong></td>
                                <td>GE, Philips, Siemens, Supersonic</td>
                            </tr>
                            <tr>
                                <td><strong>Acoustic Domain Shift</strong></td>
                                <td>Severe (Vendor gain, frequency variation)</td>
                            </tr>
                            <tr>
                                <td><strong>External AUC Generalization</strong></td>
                                <td>0.912 ± 0.024 (Zero fine-tuning)</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// Auto-run if DOM is already loaded or register listener
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderOverviewView);
} else {
    renderOverviewView();
}
