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

        <!-- Executive Stat Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-label">Primary Diagnostic Accuracy</span>
                <div class="stat-value text-accent">99.5%</div>
                <div class="stat-ci">95% CI: 98.9% – 100.0%</div>
                <div class="stat-desc">Mask-Aware Gated Fusion (Model A4) Balanced Accuracy over 5-fold CV.</div>
            </div>

            <div class="stat-card">
                <span class="stat-label">Malignancy Sensitivity</span>
                <div class="stat-value text-success">100.0%</div>
                <div class="stat-ci">HCC Sensitivity (0 False Negatives)</div>
                <div class="stat-desc">Complete avoidance of fatal missed malignancies on all 421 HCC cases.</div>
            </div>

            <div class="stat-card">
                <span class="stat-label">Probability Calibration (ECE)</span>
                <div class="stat-value">0.023</div>
                <div class="stat-ci">ECE Drop: 0.041 → 0.023 (-43.9%)</div>
                <div class="stat-desc">Post-hoc temperature scaling ($T=1.35$) delivers clinically calibrated risks.</div>
            </div>

            <div class="stat-card">
                <span class="stat-label">Validated Clinical Cohort</span>
                <div class="stat-value">743</div>
                <div class="stat-ci">2,651 B-mode Images + Demographics</div>
                <div class="stat-desc">Strict patient-level stratification preventing data leakage across folds.</div>
            </div>
        </div>

        <!-- Pre-Registered Hypotheses Review -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Pre-Registered Research Hypotheses & Trial Endpoints</h3>
                    <p class="text-sm text-muted">Evaluation against formal pre-registered decision rules and empirical thresholds.</p>
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
                                <strong style="color: var(--text-primary);">Empirical Evidence:</strong> 
                                <span style="color: var(--navy-900);">${h.evidence}</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
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
