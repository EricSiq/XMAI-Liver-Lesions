/**
 * XMAI Academic Research Console - Mathematical Typesetting Engine.
 * Supports KaTeX with seamless semantic HTML/CSS offline fallback for clean formula display.
 */

(function(window) {
    'use strict';

    const MathRenderer = {
        /**
         * Render a LaTeX expression into either KaTeX or formatted academic HTML fallback.
         * @param {string} latex - The LaTeX formula string.
         * @param {boolean} displayMode - True for display/block mode, false for inline.
         * @returns {string} Safe HTML string containing the rendered formula.
         */
        render(latex, displayMode = false) {
            if (!latex) return '';

            // Clean up surrounding math delimiters if present
            let expr = latex.trim();
            if (expr.startsWith('$$') && expr.endsWith('$$')) {
                expr = expr.substring(2, expr.length - 2).trim();
                displayMode = true;
            } else if (expr.startsWith('$') && expr.endsWith('$')) {
                expr = expr.substring(1, expr.length - 1).trim();
            }

            // If KaTeX is available in the global scope
            if (window.katex && typeof window.katex.renderToString === 'function') {
                try {
                    return window.katex.renderToString(expr, {
                        displayMode: displayMode,
                        throwOnError: false,
                        output: 'htmlAndMathml'
                    });
                } catch (err) {
                    console.warn('[MathRenderer] KaTeX render error, using fallback:', err);
                }
            }

            // High-fidelity semantic HTML fallback
            return this.renderFallback(expr, displayMode);
        },

        /**
         * Beautiful semantic HTML fallback when KaTeX CDN is offline.
         */
        renderFallback(expr, displayMode = false) {
            let out = expr;

            // Handle multiline equations (\\)
            out = out.replace(/\\\\/g, '<span class="math-break"></span>');

            // Common LaTeX functions and text
            out = out.replace(/\\text\{([^{}]+)\}/g, '<span class="math-roman">$1</span>');
            out = out.replace(/\\mathbf\{([^{}]+)\}/g, '<b>$1</b>');
            out = out.replace(/\\mathbb\{R\}/g, 'ℝ');
            out = out.replace(/\\mathcal\{D\}/g, '<span class="math-cal">𝒟</span>');
            out = out.replace(/\\mathcal\{M\}/g, '<span class="math-cal">ℳ</span>');

            // Fractions: \frac{num}{den}
            out = out.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '<span class="math-frac"><span class="math-num">$1</span><span class="math-denom">$2</span></span>');
            // Second pass for nested fractions
            out = out.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '<span class="math-frac"><span class="math-num">$1</span><span class="math-denom">$2</span></span>');

            // Square root: \sqrt{x}
            out = out.replace(/\\sqrt\{([^{}]+)\}/g, '√<span class="math-sqrt-radicand">$1</span>');

            // Accents: \hat{y}, \tilde{x}
            out = out.replace(/\\hat\{([^{}]+)\}/g, '<span class="math-hat">$1̂</span>');
            out = out.replace(/\\tilde\{([^{}]+)\}/g, '<span class="math-tilde">$1̃</span>');

            // Parentheses resizing
            out = out.replace(/\\left\(/g, '<span class="math-paren">(</span>');
            out = out.replace(/\\right\)/g, '<span class="math-paren">)</span>');

            // Greek symbols
            out = out.replace(/\\sigma/g, 'σ');
            out = out.replace(/\\alpha/g, 'α');
            out = out.replace(/\\beta/g, 'β');
            out = out.replace(/\\gamma/g, 'γ');
            out = out.replace(/\\phi/g, 'ϕ');
            out = out.replace(/\\pi/g, 'π');
            out = out.replace(/\\tau/g, 'τ');

            // Math operators & symbols
            out = out.replace(/\\in/g, ' ∈ ');
            out = out.replace(/\\odot/g, ' ⊙ ');
            out = out.replace(/\\oplus/g, ' ⊕ ');
            out = out.replace(/\\parallel/g, ' ∥ ');
            out = out.replace(/\\sim/g, ' ~ ');
            out = out.replace(/\\sum/g, '∑');
            out = out.replace(/\\cdot/g, ' · ');
            out = out.replace(/\\times/g, ' × ');
            out = out.replace(/\\quad/g, '&emsp;');
            out = out.replace(/\\,/g, ' ');
            out = out.replace(/\\;/g, ' ');
            out = out.replace(/\\%/g, '%');
            out = out.replace(/\\exp/g, '<span class="math-roman">exp</span>');
            out = out.replace(/\\log/g, '<span class="math-roman">log</span>');

            // Subscripts & Superscripts with braces: _{...} and ^{...}
            out = out.replace(/\^\{([^{}]+)\}/g, '<sup>$1</sup>');
            out = out.replace(/_\{([^{}]+)\}/g, '<sub>$1</sub>');

            // Single-char subscripts & superscripts: _x and ^x
            out = out.replace(/\^([a-zA-Z0-9])/g, '<sup>$1</sup>');
            out = out.replace(/_([a-zA-Z0-9])/g, '<sub>$1</sub>');

            const wrapperClass = displayMode ? 'math-block-display' : 'math-inline';
            return `<span class="${wrapperClass}">${out}</span>`;
        },

        /**
         * Scans an element (or document body) and renders any text nodes containing $...$ or $$...$$
         * or elements with class 'render-math'.
         */
        typeset(root = document) {
            // First render elements with explicit data-math attribute
            const mathElements = root.querySelectorAll('[data-math]');
            mathElements.forEach(el => {
                const latex = el.getAttribute('data-math');
                const isBlock = el.getAttribute('data-math-mode') === 'display';
                el.innerHTML = this.render(latex, isBlock);
            });

            // If KaTeX is loaded and has auto-render extension, call it
            if (window.renderMathInElement && typeof window.renderMathInElement === 'function') {
                try {
                    window.renderMathInElement(root, {
                        delimiters: [
                            { left: '$$', right: '$$', display: true },
                            { left: '$', right: '$', display: false }
                        ],
                        throwOnError: false
                    });
                } catch (e) {
                    console.warn('[MathRenderer] auto-render error:', e);
                }
            }
        }
    };

    window.MathRenderer = MathRenderer;

    // Run automatically on DOM load and when KaTeX loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => MathRenderer.typeset());
    } else {
        MathRenderer.typeset();
    }
})(window);
