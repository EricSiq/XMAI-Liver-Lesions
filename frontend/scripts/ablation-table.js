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
    `;

    bindAblationEvents(container);
    updateAblationTable();
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
