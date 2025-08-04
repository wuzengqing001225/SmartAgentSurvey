/**
 * 🎊 Modern Toast Notification System
 * Provides elegant, accessible toast notifications with animations
 */

class ToastManager {
    constructor() {
        this.toasts = new Set();
        this.maxToasts = 5;
        this.defaultDuration = 4000;
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of toast (success, error, info, warning)
     * @param {number} duration - Duration in milliseconds (0 for persistent)
     * @param {Object} options - Additional options
     */
    show(message, type = 'info', duration = this.defaultDuration, options = {}) {
        // Remove oldest toast if we've reached the limit
        if (this.toasts.size >= this.maxToasts) {
            const oldestToast = this.toasts.values().next().value;
            this.remove(oldestToast);
        }

        const toast = this.createToast(message, type, options);
        this.toasts.add(toast);
        document.body.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Auto-remove after duration (if not persistent)
        if (duration > 0) {
            setTimeout(() => {
                this.remove(toast);
            }, duration);
        }

        return toast;
    }

    /**
     * Create toast element
     */
    createToast(message, type, options) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}-alert`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');

        // Add icon based on type
        const icon = this.getIcon(type);

        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-icon" aria-hidden="true">${icon}</div>
                <div class="toast-message">${message}</div>
                ${options.closable !== false ? '<button class="toast-close" aria-label="Close notification">&times;</button>' : ''}
            </div>
            <div class="toast-progress"></div>
        `;

        // Add close functionality
        if (options.closable !== false) {
            const closeBtn = toast.querySelector('.toast-close');
            closeBtn.addEventListener('click', () => this.remove(toast));
        }

        // Add click to dismiss (if enabled)
        if (options.clickToDismiss !== false) {
            toast.addEventListener('click', (e) => {
                if (!e.target.classList.contains('toast-close')) {
                    this.remove(toast);
                }
            });
        }

        return toast;
    }

    /**
     * Get icon for toast type
     */
    getIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }

    /**
     * Remove a toast
     */
    remove(toast) {
        if (!toast || !this.toasts.has(toast)) return;

        toast.classList.add('removing');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.toasts.delete(toast);
        }, 300);
    }

    /**
     * Clear all toasts
     */
    clear() {
        this.toasts.forEach(toast => this.remove(toast));
    }

    // Convenience methods
    success(message, duration, options) {
        return this.show(message, 'success', duration, options);
    }

    error(message, duration, options) {
        return this.show(message, 'error', duration, options);
    }

    warning(message, duration, options) {
        return this.show(message, 'warning', duration, options);
    }

    info(message, duration, options) {
        return this.show(message, 'info', duration, options);
    }
}

// Create global instance
window.toast = new ToastManager();

// Legacy compatibility functions
window.showError = (message) => toast.error(message);
window.showSuccess = (message) => toast.success(message);
window.showInfo = (message) => toast.info(message);