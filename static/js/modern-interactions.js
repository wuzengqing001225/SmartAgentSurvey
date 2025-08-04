/**
 * Modern Interactions Enhancement
 * Adds ripple effects, smooth animations, and enhanced UX
 */

class ModernInteractions {
    constructor() {
        this.init();
    }

    init() {
        this.addRippleEffects();
        this.enhanceButtons();
        this.addKeyboardNavigation();
        this.addLoadingStates();
        this.enhanceFormInputs();
        this.addScrollAnimations();
    }

    /**
     * Add ripple effects to buttons
     */
    addRippleEffects() {
        document.addEventListener('click', (e) => {
            const button = e.target.closest('.btn, .method-card, .history-item');
            if (!button) return;

            const ripple = document.createElement('span');
            const rect = button.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
                z-index: 1;
            `;

            // Ensure button has relative positioning
            if (getComputedStyle(button).position === 'static') {
                button.style.position = 'relative';
            }

            button.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });

        // Add ripple animation keyframes
        if (!document.getElementById('ripple-styles')) {
            const style = document.createElement('style');
            style.id = 'ripple-styles';
            style.textContent = `
                @keyframes ripple {
                    to {
                        transform: scale(2);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Enhance button interactions
     */
    enhanceButtons() {
        document.querySelectorAll('.btn').forEach(button => {
            // Add loading state functionality
            const originalText = button.innerHTML;

            button.addEventListener('click', () => {
                if (button.classList.contains('loading')) return;

                // Add subtle feedback
                button.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    button.style.transform = '';
                }, 150);
            });
        });
    }

    /**
     * Enhanced keyboard navigation
     */
    addKeyboardNavigation() {
        // Focus management for modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    const closeBtn = openModal.querySelector('.close-modal');
                    if (closeBtn) closeBtn.click();
                }
            }

            // Tab trapping in modals
            if (e.key === 'Tab') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    const focusableElements = openModal.querySelectorAll(
                        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    );
                    const firstElement = focusableElements[0];
                    const lastElement = focusableElements[focusableElements.length - 1];

                    if (e.shiftKey && document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    } else if (!e.shiftKey && document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                }
            }
        });

        // Enhanced focus indicators
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    /**
     * Add loading states to buttons
     */
    addLoadingStates() {
        window.setButtonLoading = (button, loading = true) => {
            if (typeof button === 'string') {
                button = document.querySelector(button);
            }

            if (!button) return;

            if (loading) {
                button.classList.add('loading');
                button.disabled = true;
                button.setAttribute('aria-busy', 'true');
            } else {
                button.classList.remove('loading');
                button.disabled = false;
                button.removeAttribute('aria-busy');
            }
        };
    }

    /**
     * Enhance form inputs
     */
    enhanceFormInputs() {
        document.querySelectorAll('input, select, textarea').forEach(input => {
            // Add floating label effect
            const wrapper = input.closest('.setting-group, .form-group');
            if (wrapper) {
                input.addEventListener('focus', () => {
                    wrapper.classList.add('focused');
                });

                input.addEventListener('blur', () => {
                    if (!input.value) {
                        wrapper.classList.remove('focused');
                    }
                });

                // Check initial state
                if (input.value) {
                    wrapper.classList.add('focused');
                }
            }

            // Add validation feedback
            input.addEventListener('invalid', () => {
                input.classList.add('error');
                setTimeout(() => {
                    input.classList.remove('error');
                }, 3000);
            });
        });
    }

    /**
     * Add scroll-based animations
     */
    addScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        }, observerOptions);

        // Observe elements that should animate on scroll
        document.querySelectorAll('.card, .metric-card, .dimension-card, .profile-card').forEach(el => {
            observer.observe(el);
        });
    }

    /**
     * Add smooth page transitions
     */
    addPageTransitions() {
        // Add transition effects when switching views
        const originalShowView = window.showView || function () { };

        window.showView = function (viewId) {
            const currentView = document.querySelector('.view.active');
            const newView = document.getElementById(viewId);

            if (currentView && newView && currentView !== newView) {
                currentView.style.opacity = '0';
                currentView.style.transform = 'translateX(-20px)';

                setTimeout(() => {
                    currentView.classList.remove('active');
                    newView.classList.add('active');
                    newView.style.opacity = '0';
                    newView.style.transform = 'translateX(20px)';

                    requestAnimationFrame(() => {
                        newView.style.opacity = '1';
                        newView.style.transform = 'translateX(0)';
                    });
                }, 150);
            } else {
                originalShowView(viewId);
            }
        };
    }

    /**
     * Add enhanced tooltips
     */
    addTooltips() {
        document.querySelectorAll('[title]').forEach(element => {
            const title = element.getAttribute('title');
            element.removeAttribute('title');

            const tooltip = document.createElement('div');
            tooltip.className = 'modern-tooltip';
            tooltip.textContent = title;
            tooltip.style.cssText = `
                position: absolute;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 0.5rem 0.75rem;
                border-radius: 6px;
                font-size: 0.875rem;
                white-space: nowrap;
                z-index: 1000;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.2s ease;
                backdrop-filter: blur(8px);
            `;

            element.addEventListener('mouseenter', (e) => {
                document.body.appendChild(tooltip);
                const rect = element.getBoundingClientRect();
                tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
                tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
                tooltip.style.opacity = '1';
            });

            element.addEventListener('mouseleave', () => {
                tooltip.style.opacity = '0';
                setTimeout(() => {
                    if (tooltip.parentNode) {
                        tooltip.parentNode.removeChild(tooltip);
                    }
                }, 200);
            });
        });
    }

    /**
     * Add progress indicators for long operations
     */
    addProgressIndicators() {
        window.showProgress = (message = 'Processing...') => {
            const existing = document.getElementById('global-progress');
            if (existing) existing.remove();

            const progress = document.createElement('div');
            progress.id = 'global-progress';
            progress.innerHTML = `
                <div class="progress-overlay">
                    <div class="progress-content">
                        <div class="progress-spinner"></div>
                        <div class="progress-message">${message}</div>
                    </div>
                </div>
            `;
            progress.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
                z-index: 2500;
                display: flex;
                align-items: center;
                justify-content: center;
            `;

            document.body.appendChild(progress);
        };

        window.hideProgress = () => {
            const progress = document.getElementById('global-progress');
            if (progress) {
                progress.style.opacity = '0';
                setTimeout(() => progress.remove(), 300);
            }
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ModernInteractions();
});

// Export for use in other scripts
window.ModernInteractions = ModernInteractions;