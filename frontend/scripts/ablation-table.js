/**
 * XMAI Presentation Frontend - Comprehensive Ablation Table Explorer.
 * Interactive table rendering 9-model ablation study with sorting, 95% CIs, and ECE diagnostics.
 */

let currentSortKey = "balanced_acc";
let currentSortAsc = false;
let currentFilter = "all"; // 'all', 'multimodal', 'baselines'
let selectedAblationModel = "A4";

function renderAblationView() {
    const container = document.getElementById('section-ablation');
    if (!container) return;

    container.innerHTML = `
        <div class="section-header">
            <span class="section-tag">Section 03 / Rigorous Benchmarking</span>
            <h2 class="section-title">Comprehensive 9-Model Multimodal Ablation Study</h2>
            <p class="section-desc">
                Patient-stratified 5-fold cross-validation comparison of visual, demographic, gated, modulated, 
                and evidential uncertainty fusion paradigms. All metrics report 95% bootstrap confidence intervals.
            </p>
        </div>

        <!-- Controls: Filter & Sort helper -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
            <div class="filter-group" style="display: flex; gap: 0.5rem;">
                <button class="btn btn-sm btn-outline filter-btn ${currentFilter === 'all' ? 'active' : ''}" data-filter="all">All 9 Models</button>
                <button class="btn btn-sm btn-outline filter-btn ${currentFilter === 'multimodal' ? 'active' : ''}" data-filter="multimodal">Multimodal Architectures</button>
                <button class="btn btn-sm btn-outline filter-btn ${currentFilter === 'baselines' ? 'active' : ''}" data-filter="baselines">Baselines & Controls</button>
            </div>
            <div class="text-sm text-muted">
                Click column headers to sort. Click any row to inspect clinical rationale.
            </div>
        </div>

        <!-- Interactive Table Container -->
        <div class="card" style="padding: 0; overflow: hidden;">
            <div style="overflow-x: auto;">
                <table class="academic-table" id="ablation-main-table">
                    <thead>
                        <tr>
                            <th data-sort="id" style="cursor: pointer;">Model <span class="sort-icon font-mono">↕</span></th>
                            <th>Paradigm & Inductive Bias</th>
                            <th>Modalities</th>
                            <th data-sort="balanced_acc" style="cursor: pointer; text-align: right;">Bal. Acc (95% CI) <span class="sort-icon font-mono">↕</span></th>
                            <th data-sort="sensitivity" style="cursor: pointer; text-align: right;">Sensitivity <span class="sort-icon font-mono">↕</span></th>
                            <th data-sort="specificity" style="cursor: pointer; text-align: right;">Specificity <span class="sort-icon font-mono">↕</span></th>
                            <th data-sort="auc" style="cursor: pointer; text-align: right;">AUROC <span class="sort-icon font-mono">↕</span></th>
                            <th data-sort="ece" style="cursor: pointer; text-align: right;">ECE (Calib) <span class="sort-icon font-mono">↕</span></th>
                            <th data-sort="log_loss" style="cursor: pointer; text-align: right;">Log-Loss <span class="sort-icon font-mono">↕</span></th>
                        </tr>
                    </thead>
                    <tbody id="ablation-table-body">
                        <!-- Rows rendered dynamically -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Selected Model Detail Card -->
        <div id="ablation-detail-card" class="card" style="margin-top: 1.25rem;">
            <!-- Dynamically populated -->
        </div>

        <!-- Reliability Diagram & Probability Calibration Panel -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Reliability Diagram & Temperature Scaling Calibration</h3>
                    <p class="text-sm text-muted">STARD-AI & CLAIM compliance: Ensuring predicted risks correspond to true observed patient outcomes.</p>
                </div>
                <span class="badge badge-success">ECE: 0.041 &rarr; 0.023 (-43.9%)</span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-top: 1rem; align-items: start;">
                <!-- SVG Reliability Diagram -->
                <div style="background: var(--surface-bg); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 1rem;">
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--navy-900);">Empirical Reliability Curve (10 Bins)</h4>
                    <svg viewBox="0 0 340 280" style="width: 100%; height: auto; display: block; font-family: 'Inter', sans-serif;">
                        <!-- Axes -->
                        <line x1="45" y1="225" x2="315" y2="225" stroke="#cbd5e1" stroke-width="1.5" />
                        <line x1="45" y1="25" x2="45" y2="225" stroke="#cbd5e1" stroke-width="1.5" />

                        <!-- Perfect Calibration Diagonal -->
                        <line x1="45" y1="225" x2="315" y2="25" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4,4" />

                        <!-- Grid lines -->
                        <line x1="45" y1="125" x2="315" y2="125" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="2,2" />
                        <line x1="180" y1="25" x2="180" y2="225" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="2,2" />

                        <!-- T=1.0 Raw Curve (Orange dashed) -->
                        <polyline points="45,225 72,218 99,195 126,168 153,138 180,110 207,80 234,52 261,30 288,25 315,25" 
                                  fill="none" stroke="#f97316" stroke-width="2" stroke-dasharray="3,3" />

                        <!-- T=1.35 Calibrated Curve (Royal Blue solid) -->
                        <polyline points="45,225 72,215 99,190 126,165 153,142 180,118 207,92 234,68 261,45 288,28 315,25" 
                                  fill="none" stroke="#1d4ed8" stroke-width="2.5" />

                        <!-- 10 Calibration Bin Bars (Calibrated) -->
                        <rect x="52" y="215" width="16" height="10" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="79" y="190" width="16" height="35" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="106" y="165" width="16" height="60" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="133" y="142" width="16" height="83" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="160" y="118" width="16" height="107" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="187" y="92" width="16" height="133" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="214" y="68" width="16" height="157" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="241" y="45" width="16" height="180" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="268" y="28" width="16" height="197" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />
                        <rect x="295" y="25" width="16" height="200" fill="rgba(29, 78, 216, 0.2)" stroke="#1d4ed8" stroke-width="1" />

                        <!-- Axis labels -->
                        <text x="45" y="240" font-size="9" text-anchor="middle" fill="#64748b">0.0</text>
                        <text x="180" y="240" font-size="9" text-anchor="middle" fill="#64748b">0.5</text>
                        <text x="315" y="240" font-size="9" text-anchor="middle" fill="#64748b">1.0</text>
                        <text x="180" y="258" font-size="10" text-anchor="middle" font-weight="600" fill="#0f172a">Mean Predicted Probability</text>

                        <text x="38" y="228" font-size="9" text-anchor="end" fill="#64748b">0.0</text>
                        <text x="38" y="128" font-size="9" text-anchor="end" fill="#64748b">0.5</text>
                        <text x="38" y="28" font-size="9" text-anchor="end" fill="#64748b">1.0</text>
                        <text x="18" y="125" font-size="10" text-anchor="middle" font-weight="600" fill="#0f172a" transform="rotate(-90 18 125)">Empirical Accuracy</text>
                    </svg>

                    <!-- Reliability Legend -->
                    <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 0.5rem; font-size: 0.78rem;">
                        <span style="color: #94a3b8;">-- Ideal (y = x)</span>
                        <span style="color: #f97316; font-weight: 600;">-- Raw (T=1.0, ECE=0.041)</span>
                        <span style="color: #1d4ed8; font-weight: 700;">— Scaled (T=1.35, ECE=0.023)</span>
                    </div>
                </div>

                <!-- Interactive Temperature Scaler & Explanation -->
                <div>
                    <h4 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--navy-900);">Interactive Temperature Scaling ($T$) Simulator</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 1rem 0;">
                        In deep neural networks trained with Cross-Entropy, overconfidence is widespread. 
                        Post-hoc temperature scaling maps raw validation logits $z$ to calibrated probabilities via 
                        $\\hat{p} = \\sigma(z / T)$ without modifying classification accuracy or AUROC ranking.
                    </p>

                    <div style="background: var(--surface-alt); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-light);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <label for="temp-slider" style="font-size: 0.85rem; font-weight: 600; color: var(--navy-900);">Scaling Factor Temperature (T):</label>
                            <span id="temp-display" class="font-mono badge badge-accent" style="font-size: 0.9rem;">T = 1.35</span>
                        </div>
                        <input type="range" id="temp-slider" min="0.5" max="2.5" step="0.05" value="1.35" style="width: 100%; cursor: pointer;" />
                        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                            <span>0.5 (Underconfident)</span>
                            <span>1.0 (Raw / Uncalibrated)</span>
                            <span>1.35 (Optimal)</span>
                            <span>2.5 (Diffused)</span>
                        </div>

                        <div style="margin-top: 1rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; border-top: 1px solid var(--border-light); padding-top: 0.75rem;">
                            <div>
                                <span class="text-xs text-muted">Simulated ECE:</span>
                                <div id="sim-ece-display" class="font-mono" style="font-size: 1.1rem; font-weight: 700; color: var(--color-success);">0.023</div>
                            </div>
                            <div>
                                <span class="text-xs text-muted">Calibration Status:</span>
                                <div id="sim-calib-status" style="font-size: 0.85rem; font-weight: 600; color: var(--navy-900);">Optimal Calibration</div>
                            </div>
                        </div>
                    </div>

                    <!-- Clinical Caution: Model A6 Late Fusion Note -->
                    <div style="margin-top: 1rem; background: rgba(225, 29, 72, 0.05); border: 1px solid rgba(225, 29, 72, 0.2); border-radius: var(--radius-sm); padding: 0.75rem 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.4rem; color: var(--color-danger); font-weight: 700; font-size: 0.85rem;">
                            <span>⚠️ Critical Methodological Finding: Model A6 Late Fusion Failure</span>
                        </div>
                        <p style="margin: 0.35rem 0 0 0; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45;">
                            Although naive late averaging (Model A6) attained 0.996 balanced accuracy, its ECE exploded to <strong>0.191</strong>. 
                            Unweighted probability averaging produces severely deformed confidence intervals unsuitable for clinical triage.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    `;

    bindAblationEvents(container);
    bindCalibrationEvents(container);
    updateAblationTable();
}

function bindCalibrationEvents(container) {
    const slider = container.querySelector('#temp-slider');
    const display = container.querySelector('#temp-display');
    const eceDisplay = container.querySelector('#sim-ece-display');
    const statusDisplay = container.querySelector('#sim-calib-status');
    if (!slider || !display || !eceDisplay || !statusDisplay) return;

    slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        display.textContent = `T = ${val.toFixed(2)}`;

        // Approximate ECE parabolic curve centered around optimal T=1.35
        const diff = Math.abs(val - 1.35);
        const simEce = 0.023 + diff * 0.045;
        eceDisplay.textContent = simEce.toFixed(3);

        if (val === 1.35) {
            eceDisplay.style.color = "var(--color-success)";
            statusDisplay.textContent = "Optimal Clinical Calibration";
            statusDisplay.style.color = "var(--color-success)";
        } else if (val < 1.0) {
            eceDisplay.style.color = "var(--color-warning)";
            statusDisplay.textContent = "Overconfident Risk Scores";
            statusDisplay.style.color = "var(--color-warning)";
        } else if (val > 1.6) {
            eceDisplay.style.color = "var(--color-warning)";
            statusDisplay.textContent = "Underconfident / Oversmoothed";
            statusDisplay.style.color = "var(--color-warning)";
        } else {
            eceDisplay.style.color = "var(--navy-900)";
            statusDisplay.textContent = "Suboptimal Calibration";
            statusDisplay.style.color = "var(--navy-900)";
        }
    });
}

function bindAblationEvents(container) {
    // Filter buttons
    const filterBtns = container.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.getAttribute('data-filter');
            updateAblationTable();
        });
    });

    // Sort headers
    const ths = container.querySelectorAll('th[data-sort]');
    ths.forEach(th => {
        th.addEventListener('click', () => {
            const key = th.getAttribute('data-sort');
            if (currentSortKey === key) {
                currentSortAsc = !currentSortAsc;
            } else {
                currentSortKey = key;
                currentSortAsc = (key === 'ece' || key === 'log_loss'); // Default ascending for error metrics
            }
            updateAblationTable();
        });
    });
}

function updateAblationTable() {
    const tbody = document.getElementById('ablation-table-body');
    if (!tbody) return;

    let list = [...XMAI_DATA.ablation_models];

    // Filter
    if (currentFilter === 'multimodal') {
        list = list.filter(m => m.id.match(/A[345689]/));
    } else if (currentFilter === 'baselines') {
        list = list.filter(m => m.id === 'A1' || m.id === 'A2' || m.id === 'A7');
    }

    // Sort
    list.sort((a, b) => {
        let valA = a[currentSortKey];
        let valB = b[currentSortKey];
        if (typeof valA === 'string') {
            return currentSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return currentSortAsc ? (valA - valB) : (valB - valA);
    });

    tbody.innerHTML = list.map(m => {
        const isSelected = (m.id === selectedAblationModel);
        const isProposed = (m.id === 'A4');
        const ciStr = `[${(m.bal_ci[0]*100).toFixed(1)}, ${(m.bal_ci[1]*100).toFixed(1)}]`;

        return `
            <tr class="ablation-row ${isSelected ? 'selected-row' : ''} ${isProposed ? 'proposed-row' : ''}" 
                data-model="${m.id}" 
                style="cursor: pointer; ${isProposed ? 'background: rgba(2, 132, 199, 0.04); font-weight: 500;' : ''}">
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span class="badge ${isProposed ? 'badge-accent' : (m.id === 'A1' || m.id === 'A2' ? 'badge-neutral' : 'badge-outline')}">${m.id}</span>
                        <strong>${m.name.split(':')[1].trim()}</strong>
                    </div>
                </td>
                <td style="font-size: 0.82rem; color: var(--text-secondary);">${m.paradigm}</td>
                <td>
                    <div style="display: flex; gap: 0.25rem; flex-wrap: wrap;">
                        ${m.modalities.map(mod => `<span class="badge badge-neutral" style="font-size: 0.72rem; padding: 0.1rem 0.4rem;">${mod}</span>`).join('')}
                    </div>
                </td>
                <td style="text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 600;">
                    ${(m.balanced_acc * 100).toFixed(1)}% <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 400;">${ciStr}</span>
                </td>
                <td style="text-align: right; font-family: 'JetBrains Mono', monospace; color: ${m.sensitivity === 1.0 ? 'var(--color-success)' : 'inherit'}; font-weight: ${m.sensitivity === 1.0 ? '700' : '400'};">
                    ${(m.sensitivity * 100).toFixed(1)}%
                </td>
                <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">
                    ${(m.specificity * 100).toFixed(1)}%
                </td>
                <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">
                    ${m.auc.toFixed(3)}
                </td>
                <td style="text-align: right; font-family: 'JetBrains Mono', monospace; color: ${m.ece > 0.1 ? 'var(--color-danger)' : (m.ece <= 0.025 ? 'var(--color-success)' : 'inherit')}; font-weight: ${m.ece > 0.1 ? '700' : '500'};">
                    ${m.ece.toFixed(3)}
                </td>
                <td style="text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-secondary);">
                    ${m.log_loss.toFixed(3)}
                </td>
            </tr>
        `;
    }).join('');

    // Attach click listeners to rows
    const rows = tbody.querySelectorAll('.ablation-row');
    rows.forEach(row => {
        row.addEventListener('click', () => {
            rows.forEach(r => r.classList.remove('selected-row'));
            row.classList.add('selected-row');
            selectedAblationModel = row.getAttribute('data-model');
            updateAblationDetail(selectedAblationModel);
        });
    });

    updateAblationDetail(selectedAblationModel);
}

function updateAblationDetail(modelId) {
    const detailCard = document.getElementById('ablation-detail-card');
    if (!detailCard) return;

    const m = XMAI_DATA.ablation_models.find(x => x.id === modelId) || XMAI_DATA.ablation_models[3];

    detailCard.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem;">
            <div>
                <span class="badge ${m.id === 'A4' ? 'badge-accent' : 'badge-neutral'}">${m.id} Evaluation Profile</span>
                <h3 style="margin: 0.35rem 0 0 0; font-size: 1.15rem; color: var(--navy-900); font-weight: 700;">
                    ${m.name} — ${m.paradigm}
                </h3>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <span class="text-sm text-muted">Optimal Temperature:</span>
                <span class="font-mono badge badge-neutral" style="font-weight: 600;">T = ${m.optimal_temp}</span>
            </div>
        </div>

        <p style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; margin: 0 0 1rem 0;">
            ${m.notes}
        </p>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; background: var(--surface-alt); padding: 0.85rem; border-radius: var(--radius-sm); border-left: 3px solid var(--accent);">
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Backbone / Operator</span>
                <div style="font-size: 0.85rem; font-weight: 600; color: var(--navy-900); margin-top: 0.15rem;">${m.backbone}</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Calibrated ECE vs Uncalibrated</span>
                <div style="font-size: 0.85rem; font-weight: 600; color: var(--navy-900); margin-top: 0.15rem;">${m.ece.toFixed(3)} (Raw: ${m.uncal_ece.toFixed(3)})</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Brier Score</span>
                <div style="font-size: 0.85rem; font-weight: 600; color: var(--navy-900); margin-top: 0.15rem;">${m.brier.toFixed(3)}</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Clinical Risk Interpretation</span>
                <div style="font-size: 0.85rem; font-weight: 600; color: ${m.sensitivity === 1.0 ? 'var(--color-success)' : 'var(--navy-900)'}; margin-top: 0.15rem;">
                    ${m.sensitivity === 1.0 ? 'Zero false negatives on HCC' : `${((1 - m.sensitivity) * 421).toFixed(0)} missed HCCs in 5-fold CV`}
                </div>
            </div>
        </div>
    `;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderAblationView);
} else {
    renderAblationView();
}
