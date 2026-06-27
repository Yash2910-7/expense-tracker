/**
 * Client-side Orchestrator for Smart Expense Tracker AI
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme State
    initializeTheme();

    // Setup Sidebar Toggle for Mobile Views
    setupMobileSidebar();

    // Setup Client-side Currency Switching
    setupCurrencySelector();

    // Trigger Skeleton Page Loading Clearances
    clearLoadingSkeletons();
});

/**
 * Toast Notification Dispatcher
 */
function showToast(message, type = 'info') {
    // Create toast container if missing
    let container = document.querySelector('.toast-container-custom');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container-custom';
        document.body.appendChild(container);
    }

    // Create Toast Item
    const toast = document.createElement('div');
    toast.className = `toast-custom toast-${type}`;
    
    // Choose icon depending on severity
    let icon = 'bi-info-circle';
    if (type === 'success') icon = 'bi-check-circle-fill';
    else if (type === 'warning') icon = 'bi-exclamation-triangle-fill';
    else if (type === 'danger') icon = 'bi-x-circle-fill';

    toast.innerHTML = `
        <i class="bi ${icon}"></i>
        <div>${message}</div>
    `;

    container.appendChild(toast);

    // Fade and delete toast
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s ease';
        setTimeout(() => {
            toast.remove();
        }, 500);
    }, 4000);
}

/**
 * Theme Manager & Sync
 */
function initializeTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (!themeToggleBtn) return;

    themeToggleBtn.addEventListener('click', () => {
        const body = document.body;
        const isLight = body.classList.contains('light-theme');
        
        // Toggle Local Classes
        if (isLight) {
            body.classList.remove('light-theme');
            localStorage.setItem('theme', 'dark');
            themeToggleBtn.innerHTML = '<i class="bi bi-sun-fill"></i>';
            syncThemeWithDatabase('dark');
        } else {
            body.classList.add('light-theme');
            localStorage.setItem('theme', 'light');
            themeToggleBtn.innerHTML = '<i class="bi bi-moon-stars-fill"></i>';
            syncThemeWithDatabase('light');
        }
        showToast("Theme configuration updated successfully.", "success");
    });
}

function syncThemeWithDatabase(themeName) {
    fetch('/api/theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ theme: themeName })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) console.error("Database theme sync failed:", data.message);
    })
    .catch(err => console.error("Theme sync network error:", err));
}

/**
 * Currency Manager & Reload
 */
function setupCurrencySelector() {
    const selector = document.getElementById('currency-selector');
    if (!selector) return;

    selector.addEventListener('change', (e) => {
        const selectedCurrency = e.target.value;
        
        fetch('/api/currency', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ currency: selectedCurrency })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast(`Currency changed to ${selectedCurrency}. Reloading...`, "success");
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast("Failed to switch currency.", "danger");
            }
        })
        .catch(err => {
            console.error("Currency update network error:", err);
            showToast("Failed to connect to servers.", "danger");
        });
    });
}

/**
 * Mobile Sidebar Controller
 */
function setupMobileSidebar() {
    const toggleBtn = document.getElementById('mobile-sidebar-toggle');
    const sidebar = document.querySelector('.app-sidebar');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('active');
        });

        // Close sidebar when clicking outside boundary on mobile
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('active') && !sidebar.contains(e.target) && e.target !== toggleBtn) {
                sidebar.classList.remove('active');
            }
        });
    }
}

/**
 * Skeleton Loader Clearances
 */
function clearLoadingSkeletons() {
    const skeletons = document.querySelectorAll('.skeleton');
    if (skeletons.length > 0) {
        setTimeout(() => {
            skeletons.forEach(s => {
                s.classList.remove('skeleton');
            });
        }, 600);
    }
}

/**
 * Password Strength Checker (Live UI feedback)
 */
function checkPasswordStrength(passwordInputId, feedbackContainerId) {
    const input = document.getElementById(passwordInputId);
    const feedback = document.getElementById(feedbackContainerId);
    
    if (!input || !feedback) return;
    
    input.addEventListener('input', (e) => {
        const pass = e.target.value;
        if (!pass) {
            feedback.innerHTML = '';
            return;
        }
        
        const checks = {
            length: pass.length >= 8,
            upper: /[A-Z]/.test(pass),
            lower: /[a-z]/.test(pass),
            number: /[0-9]/.test(pass),
            special: /[_@$!%*#?&+-]/.test(pass)
        };
        
        let passedCount = Object.values(checks).filter(Boolean).length;
        let color = 'danger';
        let text = 'Weak';
        
        if (passedCount === 5) {
            color = 'success';
            text = 'Strong (Excellent)';
        } else if (passedCount >= 3) {
            color = 'warning';
            text = 'Medium (Include numbers/symbols)';
        }
        
        feedback.innerHTML = `
            <div class="mt-2 text-${color} small">
                <strong>Password Strength: ${text}</strong>
                <ul class="ps-3 mt-1 mb-0">
                    <li style="color: ${checks.length ? 'green':'red'}">At least 8 characters</li>
                    <li style="color: ${checks.upper ? 'green':'red'}">At least one uppercase letter</li>
                    <li style="color: ${checks.lower ? 'green':'red'}">At least one lowercase letter</li>
                    <li style="color: ${checks.number ? 'green':'red'}">At least one number</li>
                    <li style="color: ${checks.special ? 'green':'red'}">At least one special character (_@$!%*#?&+-)</li>
                </ul>
            </div>
        `;
    });
}
