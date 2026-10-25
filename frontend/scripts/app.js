/**
 * XMAI Presentation Frontend - Main Application Orchestrator.
 * Coordinates views, scroll-spy navigation, keyboard presentation shortcuts, and responsive UI.
 */

(function () {
    const SECTIONS = [
        "section-overview",
        "section-architecture",
        "section-ablation",
        "section-h1-rescue",
        "section-cases",
        "section-explainability",
        "section-selective",
        "section-external",
        "section-paper-artifacts"
    ];

    let currentSectionIdx = 0;
    let isPresentationMode = false;

    function initApp() {
        console.log("XMAI Academic Presentation Frontend Initializing...");

        setupNavigationScrollSpy();
        setupKeyboardShortcuts();
        setupPresentationModeToggle();
        setupSmoothScroll();
    }

    // Scroll-Spy to highlight current navigation item
    function setupNavigationScrollSpy() {
        const navLinks = document.querySelectorAll('.nav-link');
        const sectionElements = SECTIONS.map(id => document.getElementById(id)).filter(Boolean);

        const observerOptions = {
            root: null,
            rootMargin: "-20% 0px -70% 0px",
            threshold: 0
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const sectionId = entry.target.id;
                    const idx = SECTIONS.indexOf(sectionId);
                    if (idx !== -1) {
                        currentSectionIdx = idx;
                    }

                    navLinks.forEach(link => {
                        if (link.getAttribute('href') === `#${sectionId}`) {
                            link.classList.add('active');
                            // Ensure visible in horizontal scroll on mobile
                            link.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
                        } else {
                            link.classList.remove('active');
                        }
                    });

                    updatePresentationPill(currentSectionIdx);
                }
            });
        }, observerOptions);

        sectionElements.forEach(el => observer.observe(el));
    }

    // Smooth scroll for nav links
    function setupSmoothScroll() {
        const links = document.querySelectorAll('.nav-link, a[href^="#"]');
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href').replace('#', '');
                const targetEl = document.getElementById(targetId);
                if (targetEl) {
                    e.preventDefault();
                    const headerHeight = document.getElementById('site-header')?.offsetHeight || 100;
                    const topPos = targetEl.getBoundingClientRect().top + window.pageYOffset - headerHeight - 16;
                    window.scrollTo({
                        top: topPos,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    // Keyboard shortcuts for mentors during presentations
    function setupKeyboardShortcuts() {
        window.addEventListener('keydown', (e) => {
            // Ignore if active in input or slider
            if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
                return;
            }

            if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === 'j') {
                e.preventDefault();
                navigateSection(currentSectionIdx + 1);
            } else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'k') {
                e.preventDefault();
                navigateSection(currentSectionIdx - 1);
            } else if (e.key === 'p' || e.key === 'P') {
                togglePresentationMode();
            } else if (e.key === 'Home') {
                e.preventDefault();
                navigateSection(0);
            } else if (e.key === 'End') {
                e.preventDefault();
                navigateSection(SECTIONS.length - 1);
            }
        });
    }

    function navigateSection(index) {
        if (index < 0 || index >= SECTIONS.length) return;
        currentSectionIdx = index;
        const targetId = SECTIONS[currentSectionIdx];
        const el = document.getElementById(targetId);
        if (el) {
            const headerHeight = document.getElementById('site-header')?.offsetHeight || 100;
            const topPos = el.getBoundingClientRect().top + window.pageYOffset - headerHeight - 16;
            window.scrollTo({ top: topPos, behavior: 'smooth' });
        }
    }

    // Floating presentation pill at the bottom & Header Toggle Sync
    function setupPresentationModeToggle() {
        const toggleCheckbox = document.getElementById('toggle-presenter-mode');
        // Default to presenter mode active so judges immediately see speaking cues & takeaways
        const savedMode = localStorage.getItem('xmai_presenter_mode');
        isPresentationMode = savedMode !== null ? savedMode === 'true' : true;

        if (toggleCheckbox) {
            toggleCheckbox.checked = isPresentationMode;
            toggleCheckbox.addEventListener('change', (e) => {
                isPresentationMode = e.target.checked;
                applyPresentationMode(isPresentationMode);
            });
        }
        applyPresentationMode(isPresentationMode);

        const pill = document.createElement('div');
        pill.id = 'presentation-control-bar';
        pill.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(15, 23, 42, 0.94);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #ffffff;
            padding: 8px 14px;
            border-radius: 9999px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.8rem;
            z-index: 999;
            font-family: 'Inter', sans-serif;
            transition: all 0.2s ease;
        `;

        pill.innerHTML = `
            <span id="pres-section-indicator" style="font-weight: 600; color: #38bdf8;">Section 1 of 9</span>
            <span style="opacity: 0.3;">|</span>
            <button id="pres-prev-btn" style="background: none; border: none; color: #ffffff; cursor: pointer; padding: 2px 6px; border-radius: 4px;" title="Previous Section (Left Arrow)">◀</button>
            <button id="pres-next-btn" style="background: none; border: none; color: #ffffff; cursor: pointer; padding: 2px 6px; border-radius: 4px;" title="Next Section (Right Arrow)">▶</button>
            <span style="opacity: 0.3;">|</span>
            <span class="text-xs text-muted" style="color: #94a3b8;">Key: ◀ / ▶ | [P] Mode</span>
        `;

        document.body.appendChild(pill);

        pill.querySelector('#pres-prev-btn').addEventListener('click', () => navigateSection(currentSectionIdx - 1));
        pill.querySelector('#pres-next-btn').addEventListener('click', () => navigateSection(currentSectionIdx + 1));
    }

    function updatePresentationPill(idx) {
        const indicator = document.getElementById('pres-section-indicator');
        if (indicator) {
            indicator.textContent = `Section ${idx + 1} of ${SECTIONS.length}`;
        }
    }

    function applyPresentationMode(active) {
        document.body.classList.toggle('presenter-mode-active', active);
        const toggleCheckbox = document.getElementById('toggle-presenter-mode');
        if (toggleCheckbox && toggleCheckbox.checked !== active) {
            toggleCheckbox.checked = active;
        }
        try {
            localStorage.setItem('xmai_presenter_mode', active ? 'true' : 'false');
        } catch (e) {}
        console.log(`Presenter mode set to: ${active ? 'ACTIVE' : 'INACTIVE'}`);
    }

    function togglePresentationMode() {
        isPresentationMode = !isPresentationMode;
        applyPresentationMode(isPresentationMode);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApp);
    } else {
        initApp();
    }
})();
