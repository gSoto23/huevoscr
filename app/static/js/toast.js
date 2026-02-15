// Toast Notification System
// Requires style.css (toast styles)

// 1. Initialize Container
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('toast-container')) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    if (!document.getElementById('confirm-modal-overlay')) {
        const modal = document.createElement('div');
        modal.id = 'confirm-modal-overlay';
        modal.innerHTML = `
            <div class="confirm-card">
                <div class="confirm-title">Confirmación</div>
                <div class="confirm-message" id="confirm-msg-text"></div>
                <div class="confirm-actions">
                    <button class="btn-secondary" id="confirm-btn-cancel">Cancelar</button>
                    <button class="btn-primary" id="confirm-btn-ok">Aceptar</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
});

// 2. showToast Function
window.showToast = function (message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return; // Should be there

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';

    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s forwards';
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    }, 3000);
};

// 3. showConfirm Function (Promise based)
window.showConfirm = function (message) {
    return new Promise((resolve) => {
        const overlay = document.getElementById('confirm-modal-overlay');
        const msgText = document.getElementById('confirm-msg-text');
        const btnOk = document.getElementById('confirm-btn-ok');
        const btnCancel = document.getElementById('confirm-btn-cancel');

        if (!overlay) {
            // Fallback if DOM not ready or error
            resolve(confirm(message));
            return;
        }

        msgText.textContent = message;
        overlay.classList.add('active');

        // Handlers
        const handleOk = () => {
            cleanup();
            resolve(true);
        };

        const handleCancel = () => {
            cleanup();
            resolve(false);
        };

        const cleanup = () => {
            overlay.classList.remove('active');
            btnOk.removeEventListener('click', handleOk);
            btnCancel.removeEventListener('click', handleCancel);
        };

        btnOk.addEventListener('click', handleOk);
        btnCancel.addEventListener('click', handleCancel);
    });
};
