/**
 * XMAI Presentation Frontend - Curated Patient Case Viewer.
 * Visualizes individual patient rescue cases (HCC_48, Hem_5, Hem_337) and controls with side-by-side model probabilities.
 */

let currentPatientId = "HCC_48";

function renderCaseView() {
    const container = document.getElementById('section-cases');
    if (!container) return;

    const cases = XMAI_DATA.curated_cases;

    container.innerHTML = `
        <div class="section-header">
            <span class="section-tag">Section 05 / Patient Verification</span>
            <h2 class="section-title">Curated Clinical Case Gallery & Diagnostic Comparison</h2>
            <p class="section-desc">
                In-depth audit of real patient cases from the SMC-LUD cohort, comparing unimodal B-mode ResNet-18 (A1) 
                predictions directly against Mask-Aware Gated Multimodal Fusion (A4).
            </p>
        </div>

        <!-- Case Selector Gallery Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
            ${cases.map(c => `
                <div class="case-card ${c.patient_id === currentPatientId ? 'active' : ''}" 
                     data-patient="${c.patient_id}"
                     style="cursor: pointer; padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1.5px solid ${c.patient_id === currentPatientId ? 'var(--accent)' : 'var(--border-light)'}; background: ${c.patient_id === currentPatientId ? '#ffffff' : 'var(--surface-bg)'}; transition: all 0.15s ease;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                        <span class="font-mono font-bold" style="color: var(--navy-900); font-size: 0.95rem;">${c.patient_id}</span>
                        <span class="badge ${c.is_rescue ? 'badge-success' : 'badge-neutral'}" style="font-size: 0.68rem; padding: 0.1rem 0.35rem;">
                            ${c.is_rescue ? 'RESCUE' : 'CONTROL'}
                        </span>
                    </div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: ${c.true_label === 'HCC' ? 'var(--color-danger)' : 'var(--navy-900)'};">
                        True: ${c.true_label}
                    </div>
                    <div class="text-xs text-muted" style="margin-top: 0.2rem;">
                        ${c.sex}, ${c.age} yrs
                    </div>
                </div>
            `).join('')}
        </div>

        <!-- Main Patient Inspector Box -->
        <div id="patient-inspector-box" class="card">
            <!-- Dynamically populated -->
        </div>

        <!-- Live Covariate Perturbation Simulator Container (Populated in next commit) -->
        <div id="covariate-simulator-container" style="margin-top: 1.5rem;">
            <!-- Populated by simulator module -->
        </div>
    `;

    bindCaseEvents(container);
    updatePatientInspector(currentPatientId);
}

function bindCaseEvents(container) {
    const cards = container.querySelectorAll('.case-card');
    cards.forEach(card => {
        card.addEventListener('click', () => {
            cards.forEach(c => {
                c.classList.remove('active');
                c.style.borderColor = 'var(--border-light)';
                c.style.background = 'var(--surface-bg)';
            });
            card.classList.add('active');
            card.style.borderColor = 'var(--accent)';
            card.style.background = '#ffffff';
            currentPatientId = card.getAttribute('data-patient');
            updatePatientInspector(currentPatientId);
            if (typeof updateCovariateSimulator === "function") {
                updateCovariateSimulator(currentPatientId);
            }
        });
    });
}

function updatePatientInspector(patientId) {
    const box = document.getElementById('patient-inspector-box');
    if (!box) return;

    const c = XMAI_DATA.curated_cases.find(x => x.patient_id === patientId) || XMAI_DATA.curated_cases[0];

    const a1HccProb = (c.a1_prob.HCC * 100).toFixed(1);
    const a1HemProb = (c.a1_prob.Hemangioma * 100).toFixed(1);
    const a4HccProb = (c.a4_prob.HCC * 100).toFixed(1);
    const a4HemProb = (c.a4_prob.Hemangioma * 100).toFixed(1);

    const a1IsCorrect = (c.true_label === 'HCC' && c.a1_prob.HCC > 0.5) || (c.true_label === 'Hemangioma' && c.a1_prob.Hemangioma > 0.5);
    const a4IsCorrect = (c.true_label === 'HCC' && c.a4_prob.HCC > 0.5) || (c.true_label === 'Hemangioma' && c.a4_prob.Hemangioma > 0.5);

    box.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem; border-bottom: 1px solid var(--border-light); padding-bottom: 1rem;">
            <div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.25rem; color: var(--navy-900); font-family: 'JetBrains Mono', monospace;">
                        Patient ID: ${c.patient_id}
                    </h3>
                    <span class="badge ${c.is_rescue ? 'badge-success' : 'badge-neutral'}">
                        ${c.is_rescue ? 'Multimodal Rescue Case' : 'Baseline Control Case'}
                    </span>
                    <span class="badge ${c.true_label === 'HCC' ? 'badge-danger' : 'badge-outline'}">
                        Histopathology Ground Truth: ${c.true_label}
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: var(--text-secondary); margin-top: 0.35rem;">
                    ${c.title} &bull; Clinical Profile: <strong>${c.sex}</strong>, <strong>${c.age} years old</strong>
                </div>
            </div>
            <div style="text-align: right;">
                <span class="text-xs text-muted">Acoustic Margin State:</span>
                <div class="font-mono font-bold" style="color: ${c.is_rescue ? 'var(--color-warning)' : 'var(--color-success)'}; font-size: 0.95rem;">
                    ${c.is_rescue ? 'Borderline / Ambiguous (Decile 1)' : 'Definitive Morphology (Decile > 4)'}
                </div>
            </div>
        </div>

        <!-- Clinical & Acoustic Findings -->
        <div style="margin-top: 1rem; background: var(--surface-alt); padding: 0.85rem 1rem; border-radius: var(--radius-sm); border-left: 3px solid var(--navy-800);">
            <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: var(--text-secondary); letter-spacing: 0.05em; margin-bottom: 0.25rem;">
                B-Mode Acoustic Appearance & Sonographic Findings
            </div>
            <p style="margin: 0; font-size: 0.88rem; color: var(--navy-900); line-height: 1.5;">
                ${c.bmode_findings}
            </p>
        </div>

        <!-- Comparative Model Predictions -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-top: 1.25rem;">
            <!-- Model A1 Prediction Box -->
            <div style="border: 1px solid ${a1IsCorrect ? 'var(--border-light)' : 'rgba(225, 29, 72, 0.4)'}; border-radius: var(--radius-md); padding: 1rem; background: ${a1IsCorrect ? 'var(--surface-bg)' : 'rgba(225, 29, 72, 0.02)'};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <strong style="color: var(--navy-900);">Model A1: B-Mode Only</strong>
                    <span class="badge ${a1IsCorrect ? 'badge-success' : 'badge-danger'}">
                        ${a1IsCorrect ? 'Correct' : 'Diagnostic Error'}
                    </span>
                </div>
                
                <!-- Probability Bars -->
                <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem;">
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem;">
                            <span>P(HCC):</span>
                            <span class="font-mono font-bold">${a1HccProb}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 10px; background: #e2e8f0; border-radius: 5px; overflow: hidden;">
                            <div style="width: ${a1HccProb}%; height: 100%; background: #e11d48; transition: width 0.3s ease;"></div>
                        </div>
                    </div>

                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem;">
                            <span>P(Hemangioma):</span>
                            <span class="font-mono font-bold">${a1HemProb}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 10px; background: #e2e8f0; border-radius: 5px; overflow: hidden;">
                            <div style="width: ${a1HemProb}%; height: 100%; background: #0284c7; transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-muted);">
                    Verdict: <strong style="color: ${a1IsCorrect ? 'var(--color-success)' : 'var(--color-danger)'};">${c.a1_pred}</strong>
                </div>
            </div>

            <!-- Model A4 (Gated Fusion) Prediction Box -->
            <div style="border: 2px solid ${a4IsCorrect ? 'var(--color-success)' : 'var(--border-light)'}; border-radius: var(--radius-md); padding: 1rem; background: rgba(5, 150, 105, 0.02);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div style="display: flex; align-items: center; gap: 0.4rem;">
                        <strong style="color: var(--navy-900);">Model A4: Gated Fusion</strong>
                        <span class="badge badge-accent" style="font-size: 0.7rem;">Proposed</span>
                    </div>
                    <span class="badge badge-success">
                        ${c.is_rescue ? 'Rescued to Truth' : 'Correct'}
                    </span>
                </div>
                
                <!-- Probability Bars -->
                <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem;">
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem;">
                            <span>P(HCC):</span>
                            <span class="font-mono font-bold" style="color: #e11d48;">${a4HccProb}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 10px; background: #e2e8f0; border-radius: 5px; overflow: hidden;">
                            <div style="width: ${a4HccProb}%; height: 100%; background: #e11d48; transition: width 0.3s ease;"></div>
                        </div>
                    </div>

                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem;">
                            <span>P(Hemangioma):</span>
                            <span class="font-mono font-bold" style="color: #0284c7;">${a4HemProb}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 10px; background: #e2e8f0; border-radius: 5px; overflow: hidden;">
                            <div style="width: ${a4HemProb}%; height: 100%; background: #0284c7; transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                    <span>Verdict: <strong style="color: var(--color-success);">${c.a4_pred}</strong></span>
                    <span class="text-xs font-mono" style="color: var(--accent);">Gate: B-mode ${c.gate_weights.B_mode * 100}% | Clin ${c.gate_weights.Clinical * 100}%</span>
                </div>
            </div>
        </div>

        <!-- Clinical Expert Narrative -->
        <div style="margin-top: 1.25rem; border-top: 1px solid var(--border-light); padding-top: 1rem;">
            <div style="font-size: 0.8rem; font-weight: 700; color: var(--navy-900); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;">
                Pathophysiological & Epidemiological Rationale
            </div>
            <p style="margin: 0; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
                ${c.clinical_narrative}
            </p>
        </div>
    `;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderCaseView);
} else {
    renderCaseView();
}
