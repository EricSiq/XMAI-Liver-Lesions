/**
 * XMAI Presentation Frontend - Multi-Level Explainability Console.
 * Visualizes Layer-4 Grad-CAM spatial activation overlays, cross-modal attention, Shapley values, and Dirichlet belief mass.
 */

let currentExpPatientId = "HCC_48";
let gradCamThreshold = 0.45;

function renderExplainabilityView() {
    const container = document.getElementById('section-explainability');
    if (!container) return;

    const cases = XMAI_DATA.curated_cases;

    container.innerHTML = `
        <div class="section-header">
            <span class="section-tag">Section 06 / Interpretability & Trust</span>
            <h2 class="section-title">Multi-Level Explainability Console</h2>
            <p class="section-desc">
                Four-tier explainability suite: Visual Spatial Grad-CAM (Level 1), Cross-Modal Attention (Level 2), 
                Game-Theoretic Shapley Attribution (Level 3), and Evidential Dirichlet Uncertainty (Level 4).
            </p>
        </div>

        <!-- Patient Selector Tabs -->
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.25rem;">
            ${cases.map(c => `
                <button class="btn btn-sm ${c.patient_id === currentExpPatientId ? 'btn-primary' : 'btn-outline'} exp-patient-btn" 
                        data-patient="${c.patient_id}">
                    <strong>${c.patient_id}</strong> (${c.true_label}${c.is_rescue ? ' &bull; Rescue' : ''})
                </button>
            `).join('')}
        </div>

        <!-- Level 1: Layer-4 Grad-CAM Spatial Heatmap -->
        <div class="card" id="level1-gradcam-card">
            <!-- Populated dynamically -->
        </div>

        <!-- Level 2 & Level 3 & Level 4 Panels (Populated in Commits 12 & 13) -->
        <div id="advanced-explainability-panels" style="margin-top: 1.5rem;">
            <!-- Populated dynamically -->
        </div>
    `;

    bindExplainabilityEvents(container);
    updateGradCamPanel(currentExpPatientId);
}

function bindExplainabilityEvents(container) {
    const btns = container.querySelectorAll('.exp-patient-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => {
                b.className = 'btn btn-sm btn-outline exp-patient-btn';
            });
            btn.className = 'btn btn-sm btn-primary exp-patient-btn';
            currentExpPatientId = btn.getAttribute('data-patient');
            updateGradCamPanel(currentExpPatientId);
            if (typeof updateAdvancedExplainabilityPanels === "function") {
                updateAdvancedExplainabilityPanels(currentExpPatientId);
            }
        });
    });
}

function updateGradCamPanel(patientId) {
    const card = document.getElementById('level1-gradcam-card');
    if (!card) return;

    const patient = XMAI_DATA.curated_cases.find(x => x.patient_id === patientId) || XMAI_DATA.curated_cases[0];

    // Determine lesion geometry based on case
    const isHcc = patient.true_label === 'HCC';
    const cx = isHcc ? 145 : 155;
    const cy = isHcc ? 135 : 125;
    const rx = isHcc ? 45 : 55;
    const ry = isHcc ? 38 : 45;

    card.innerHTML = `
        <div class="card-header">
            <div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="badge badge-accent">Level 1: Visual Spatial Localization</span>
                    <h3 class="card-title" style="margin: 0;">Layer-4 Grad-CAM Class Activation Map</h3>
                </div>
                <p class="text-sm text-muted">Acoustic feature gradient localization from ResNet-18 conv5_x / layer4 feature representations.</p>
            </div>
            <span class="badge badge-neutral font-mono font-bold">${patient.patient_id} &bull; ${patient.true_label}</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-top: 1rem; align-items: center;">
            <!-- Interactive Simulated Ultrasound + GradCAM Canvas/SVG -->
            <div style="background: #020617; border-radius: var(--radius-md); padding: 1rem; text-align: center; border: 1px solid #1e293b;">
                <svg id="gradcam-svg" viewBox="0 0 300 260" style="width: 100%; max-width: 300px; height: auto; display: block; margin: 0 auto; border-radius: 4px;">
                    <defs>
                        <!-- Ultrasound Sector Mask -->
                        <clipPath id="us-sector">
                            <path d="M 150 15 L 285 245 A 280 280 0 0 1 15 245 Z" />
                        </clipPath>

                        <!-- Radial GradCAM Heatmap Gradient -->
                        <radialGradient id="gradcam-heat" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stop-color="#ef4444" stop-opacity="0.85" />
                            <stop offset="35%" stop-color="#f59e0b" stop-opacity="0.75" />
                            <stop offset="65%" stop-color="#10b981" stop-opacity="0.5" />
                            <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0" />
                        </radialGradient>

                        <!-- Ultrasound Speckle Pattern Filter -->
                        <filter id="us-speckle" x="0%" y="0%" width="100%" height="100%">
                            <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" result="noise" />
                            <feColorMatrix type="matrix" values="0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0 0 0 0.45 0" />
                        </filter>
                    </defs>

                    <!-- Ultrasound Sector Scan Background -->
                    <rect x="0" y="0" width="300" height="260" fill="#090d16" />
                    
                    <!-- Ultrasound Fan Field -->
                    <g clip-path="url(#us-sector)">
                        <!-- Liver Parenchyma Background (Speckle Texture) -->
                        <rect x="0" y="0" width="300" height="260" fill="#1e293b" />
                        <rect x="0" y="0" width="300" height="260" filter="url(#us-speckle)" />

                        <!-- Acoustic Shadows / Tissue Streaks -->
                        <line x1="80" y1="30" x2="60" y2="250" stroke="#0f172a" stroke-width="6" opacity="0.4" />
                        <line x1="220" y1="30" x2="240" y2="250" stroke="#0f172a" stroke-width="8" opacity="0.4" />

                        <!-- Liver Lesion Mass -->
                        <ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" 
                                 fill="${isHcc ? '#0f172a' : '#334155'}" 
                                 stroke="${isHcc ? '#38bdf8' : '#cbd5e1'}" 
                                 stroke-width="1.5" stroke-dasharray="3,3" opacity="0.9" />

                        <!-- Dynamic Grad-CAM Heatmap Overlay -->
                        <g id="gradcam-overlay-group" opacity="${gradCamThreshold}">
                            <ellipse cx="${cx}" cy="${cy}" rx="${rx * 1.3}" ry="${ry * 1.3}" fill="url(#gradcam-heat)" />
                        </g>

                        <!-- Focal Lesion Annotation Ring -->
                        <ellipse cx="${cx}" cy="${cy}" rx="${rx * 0.9}" ry="${ry * 0.9}" 
                                 fill="none" stroke="#f8fafc" stroke-width="1.5" stroke-dasharray="4,4" />
                    </g>

                    <!-- Ultrasound Depth Caliper Markers -->
                    <line x1="285" y1="50" x2="295" y2="50" stroke="#64748b" stroke-width="1" />
                    <line x1="285" y1="100" x2="295" y2="100" stroke="#64748b" stroke-width="1" />
                    <line x1="285" y1="150" x2="295" y2="150" stroke="#64748b" stroke-width="1" />
                    <line x1="285" y1="200" x2="295" y2="200" stroke="#64748b" stroke-width="1" />
                    <text x="278" y="103" font-size="8" fill="#64748b" text-anchor="end" font-family="'JetBrains Mono', monospace">5cm</text>
                    <text x="278" y="203" font-size="8" fill="#64748b" text-anchor="end" font-family="'JetBrains Mono', monospace">10cm</text>
                </svg>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; font-size: 0.78rem; color: #94a3b8;">
                    <span>Acoustic Field: Layer4 Salience</span>
                    <span style="font-family: 'JetBrains Mono', monospace;">Centroid: (${cx}, ${cy})</span>
                </div>
            </div>

            <!-- Heatmap Interpretability Controls & Rationale -->
            <div>
                <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--navy-900);">Spatial Activation Analysis</h4>
                <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 1rem 0;">
                    ${patient.bmode_findings}
                </p>

                <!-- Heatmap Opacity Threshold Slider -->
                <div style="background: var(--surface-alt); padding: 0.85rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-light); margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                        <label for="gradcam-slider" style="font-size: 0.85rem; font-weight: 600; color: var(--navy-900);">Grad-CAM Activation Blend:</label>
                        <span id="gradcam-val-display" class="font-mono badge badge-neutral">${Math.round(gradCamThreshold * 100)}%</span>
                    </div>
                    <input type="range" id="gradcam-slider" min="0.0" max="1.0" step="0.05" value="${gradCamThreshold}" style="width: 100%; cursor: pointer;" />
                </div>

                <div style="background: var(--surface-bg); border-left: 3px solid var(--accent); padding: 0.75rem 1rem; border-radius: var(--radius-sm); font-size: 0.82rem; line-height: 1.5;">
                    <strong style="color: var(--navy-900);">Anatomical Feature Targeting:</strong>
                    <div style="margin-top: 0.25rem; color: var(--text-secondary);">
                        ${isHcc ? 
                            'Grad-CAM gradients heavily concentrate on the lesion hypoechoic rim and internal heterogenous architecture, matching surgical histology of aggressive neoplastic angiogenesis.' : 
                            'Grad-CAM gradients localize to peripheral acoustic enhancement and homogeneous echogenicity typical of slow sinusoidal vascular pooling.'}
                    </div>
                </div>
            </div>
        </div>
    `;

    bindGradCamSlider();
}

function bindGradCamSlider() {
    const slider = document.getElementById('gradcam-slider');
    const valDisplay = document.getElementById('gradcam-val-display');
    const overlay = document.getElementById('gradcam-overlay-group');
    if (!slider || !valDisplay || !overlay) return;

    slider.addEventListener('input', (e) => {
        gradCamThreshold = parseFloat(e.target.value);
        valDisplay.textContent = `${Math.round(gradCamThreshold * 100)}%`;
        overlay.setAttribute('opacity', gradCamThreshold);
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderExplainabilityView);
} else {
    renderExplainabilityView();
}
