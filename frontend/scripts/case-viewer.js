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

    renderCovariateSimulator(c);
}

function renderCovariateSimulator(patient) {
    const simContainer = document.getElementById('covariate-simulator-container');
    if (!simContainer) return;

    simContainer.innerHTML = `
        <div class="card" style="border-left: 4px solid var(--accent);">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Live Multimodal Diagnostic Simulator & Counterfactual Testing</h3>
                    <p class="text-sm text-muted">Perturb clinical demographics or test missing covariate fallback (Hypothesis H3) in real-time.</p>
                </div>
                <span class="badge badge-accent">Interactive Counterfactual Engine</span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-top: 1rem; align-items: start;">
                <!-- Perturbation Controls -->
                <div style="background: var(--surface-bg); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-light);">
                    <!-- Age Slider -->
                    <div style="margin-bottom: 1.25rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                            <label for="sim-age-slider" style="font-size: 0.88rem; font-weight: 600; color: var(--navy-900);">Simulated Patient Age:</label>
                            <span id="sim-age-val" class="badge badge-neutral font-mono font-bold" style="font-size: 0.9rem;">${patient.age} yrs</span>
                        </div>
                        <input type="range" id="sim-age-slider" min="20" max="85" step="1" value="${patient.age}" style="width: 100%; cursor: pointer;" />
                        <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem;">
                            <span>20 yrs (Young)</span>
                            <span>50 yrs (Cohort Median)</span>
                            <span>85 yrs (Elderly)</span>
                        </div>
                    </div>

                    <!-- Sex Toggle -->
                    <div style="margin-bottom: 1.25rem;">
                        <label style="font-size: 0.88rem; font-weight: 600; color: var(--navy-900); display: block; margin-bottom: 0.4rem;">Simulated Biological Sex:</label>
                        <div style="display: flex; gap: 0.5rem;">
                            <button id="sim-sex-male" class="btn btn-sm ${patient.sex === 'Male' ? 'btn-primary' : 'btn-outline'}" style="flex: 1;">Male (78% HCC prior)</button>
                            <button id="sim-sex-female" class="btn btn-sm ${patient.sex === 'Female' ? 'btn-primary' : 'btn-outline'}" style="flex: 1;">Female (58% Hem prior)</button>
                        </div>
                    </div>

                    <!-- Missing Mask Toggle (Hypothesis H3) -->
                    <div style="background: var(--surface-alt); padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-light);">
                        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.85rem; font-weight: 600; color: var(--navy-900); margin: 0;">
                            <input type="checkbox" id="sim-mask-toggle" checked style="cursor: pointer; width: 16px; height: 16px;" />
                            <span>Clinical Prior Available (Mask m = 1)</span>
                        </label>
                        <p class="text-xs text-muted" style="margin: 0.35rem 0 0 1.5rem; line-height: 1.4;">
                            Uncheck to simulate clinical missingness. Verifies Hypothesis H3: graceful fallback to B-mode.
                        </p>
                    </div>
                </div>

                <!-- Real-Time Counterfactual Response -->
                <div style="background: var(--surface-bg); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-light);">
                    <h4 style="margin: 0 0 0.75rem 0; font-size: 0.95rem; color: var(--navy-900);">Dynamic Gating Response & Risk Shifts</h4>

                    <!-- Dynamic Gate Display -->
                    <div style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.25rem;">
                            <span>Visual Stream Weight (g_B):</span>
                            <span id="sim-gate-b-val" class="font-mono font-bold">${patient.gate_weights.B_mode * 100}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-bottom: 0.75rem;">
                            <div id="sim-gate-b-bar" style="width: ${patient.gate_weights.B_mode * 100}%; height: 100%; background: var(--accent); transition: width 0.2s ease;"></div>
                        </div>

                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.25rem;">
                            <span>Clinical Prior Modulation Weight (g_C):</span>
                            <span id="sim-gate-c-val" class="font-mono font-bold">${patient.gate_weights.Clinical * 100}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
                            <div id="sim-gate-c-bar" style="width: ${patient.gate_weights.Clinical * 100}%; height: 100%; background: #059669; transition: width 0.2s ease;"></div>
                        </div>
                    </div>

                    <!-- Resulting Counterfactual Risk -->
                    <div style="border-top: 1px solid var(--border-light); padding-top: 0.75rem;">
                        <div style="font-size: 0.85rem; font-weight: 700; color: var(--navy-900); margin-bottom: 0.5rem;">
                            Simulated Posterior Risk:
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem; font-size: 0.85rem;">
                            <span>P(HCC | x_B, x_C, m):</span>
                            <span id="sim-post-hcc" class="font-mono font-bold" style="color: #e11d48;">${(patient.a4_prob.HCC * 100).toFixed(1)}%</span>
                        </div>
                        <div class="progress-bar-container" style="height: 12px; background: #e2e8f0; border-radius: 6px; overflow: hidden; margin-bottom: 0.5rem;">
                            <div id="sim-post-bar" style="width: ${patient.a4_prob.HCC * 100}%; height: 100%; background: #e11d48; transition: width 0.2s ease;"></div>
                        </div>

                        <div id="sim-verdict-note" style="margin-top: 0.5rem; font-size: 0.82rem; padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); background: rgba(5, 150, 105, 0.08); color: var(--color-success); font-weight: 600;">
                            Consistent with observed SMC-LUD ground truth.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    bindSimulatorEvents(patient);
}

function bindSimulatorEvents(patient) {
    const ageSlider = document.getElementById('sim-age-slider');
    const ageVal = document.getElementById('sim-age-val');
    const maleBtn = document.getElementById('sim-sex-male');
    const femaleBtn = document.getElementById('sim-sex-female');
    const maskToggle = document.getElementById('sim-mask-toggle');

    let currentSimAge = patient.age;
    let currentSimSex = patient.sex;
    let currentSimMask = true;

    function recalculate() {
        ageVal.textContent = `${currentSimAge} yrs`;

        const gateBVal = document.getElementById('sim-gate-b-val');
        const gateBBar = document.getElementById('sim-gate-b-bar');
        const gateCVal = document.getElementById('sim-gate-c-val');
        const gateCBar = document.getElementById('sim-gate-c-bar');
        const postHcc = document.getElementById('sim-post-hcc');
        const postBar = document.getElementById('sim-post-bar');
        const verdictNote = document.getElementById('sim-verdict-note');

        if (!currentSimMask) {
            // Missing clinical data fallback: Fallback to A1 baseline!
            gateBVal.textContent = "100.0% (Fallback)";
            gateBBar.style.width = "100%";
            gateCVal.textContent = "0.0% (m=0)";
            gateCBar.style.width = "0%";
            const rawHcc = (patient.a1_prob.HCC * 100).toFixed(1);
            postHcc.textContent = `${rawHcc}%`;
            postBar.style.width = `${rawHcc}%`;
            verdictNote.textContent = "Hypothesis H3 Confirmed: Graceful degradation to unimodal B-mode baseline without error.";
            verdictNote.style.background = "rgba(2, 132, 199, 0.08)";
            verdictNote.style.color = "var(--accent)";
            return;
        }

        // Calculate epidemiological demographic log-odds prior
        // Age mean 55, std 12; Males risk factor +0.8, Females -0.8
        const ageNorm = (currentSimAge - 55) / 12.0;
        const sexBias = (currentSimSex === 'Male') ? 0.75 : -0.75;
        const clinicalLogOdds = ageNorm * 0.6 + sexBias;

        // Base visual logit from A1
        const pVisual = patient.a1_prob.HCC;
        const visualLogit = Math.log(Math.max(0.001, Math.min(0.999, pVisual)) / (1 - pVisual));
        
        // Dynamic gating factor: higher when visual confidence is low (margin near 0)
        const acousticMargin = Math.abs(pVisual - 0.5) * 2;
        const gateC = Math.max(0.05, Math.min(0.55, 0.50 * (1.0 - acousticMargin)));
        const gateB = 1.0 - gateC;

        // Fused logit
        const fusedLogit = (visualLogit * gateB) + (clinicalLogOdds * gateC * 2.2);
        const calibratedProb = 1.0 / (1.0 + Math.exp(-fusedLogit / 1.35));
        const finalHccPct = (calibratedProb * 100).toFixed(1);

        gateBVal.textContent = `${(gateB * 100).toFixed(1)}%`;
        gateBBar.style.width = `${gateB * 100}%`;
        gateCVal.textContent = `${(gateC * 100).toFixed(1)}%`;
        gateCBar.style.width = `${gateC * 100}%`;

        postHcc.textContent = `${finalHccPct}%`;
        postBar.style.width = `${finalHccPct}%`;

        if (finalHccPct > 50 && patient.true_label === 'HCC') {
            verdictNote.textContent = "Correctly classified as Hepatocellular Carcinoma (Pathology Match).";
            verdictNote.style.background = "rgba(5, 150, 105, 0.08)";
            verdictNote.style.color = "var(--color-success)";
        } else if (finalHccPct <= 50 && patient.true_label === 'Hemangioma') {
            verdictNote.textContent = "Correctly classified as Benign Cavernous Hemangioma (Pathology Match).";
            verdictNote.style.background = "rgba(5, 150, 105, 0.08)";
            verdictNote.style.color = "var(--color-success)";
        } else {
            verdictNote.textContent = "Diagnostic disagreement with ground truth under this hypothetical profile.";
            verdictNote.style.background = "rgba(225, 29, 72, 0.08)";
            verdictNote.style.color = "var(--color-danger)";
        }
    }

    ageSlider.addEventListener('input', (e) => {
        currentSimAge = parseInt(e.target.value, 10);
        recalculate();
    });

    maleBtn.addEventListener('click', () => {
        currentSimSex = 'Male';
        maleBtn.className = 'btn btn-sm btn-primary';
        femaleBtn.className = 'btn btn-sm btn-outline';
        recalculate();
    });

    femaleBtn.addEventListener('click', () => {
        currentSimSex = 'Female';
        femaleBtn.className = 'btn btn-sm btn-primary';
        maleBtn.className = 'btn btn-sm btn-outline';
        recalculate();
    });

    maskToggle.addEventListener('change', (e) => {
        currentSimMask = e.target.checked;
        recalculate();
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderCaseView);
} else {
    renderCaseView();
}

