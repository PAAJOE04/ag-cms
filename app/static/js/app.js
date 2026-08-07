/* AG CMS JavaScript */

document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initSidebar();
    initAlerts();
    initMemberSearch();
});

function initTheme() {
    const saved = localStorage.getItem('ag-cms-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);

    document.querySelectorAll('.theme-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('ag-cms-theme', next);
            updateThemeIcon(next);
        });
    });
}

function updateThemeIcon(theme) {
    document.querySelectorAll('.theme-toggle i').forEach(icon => {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    });
}

function initSidebar() {
    const toggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => sidebar.classList.toggle('show'));
    }
}

function initAlerts() {
    setTimeout(() => {
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        });
    }, 5000);
}

function initMemberSearch() {
    const searchInput = document.getElementById('member-search');
    const resultsDiv = document.getElementById('search-results');
    const memberIdInput = document.getElementById('member_id');

    if (!searchInput) return;

    let debounceTimer;
    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const q = this.value.trim();
        if (q.length < 2) {
            resultsDiv && (resultsDiv.innerHTML = '');
            resultsDiv && (resultsDiv.style.display = 'none');
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const resp = await fetch(`/members/search?q=${encodeURIComponent(q)}`);
                const data = await resp.json();
                if (!resultsDiv) return;

                if (data.results.length === 0) {
                    resultsDiv.innerHTML = '<div class="p-3 text-muted">No members found</div>';
                } else {
                    resultsDiv.innerHTML = data.results.map(m => `
                        <div class="search-result-item" data-id="${m.id}" data-name="${m.name}">
                            <div class="member-avatar">${m.name.charAt(0)}</div>
                            <div>
                                <strong>${m.name}</strong><br>
                                <small class="text-muted">${m.membership_id}</small>
                            </div>
                        </div>
                    `).join('');

                    resultsDiv.querySelectorAll('.search-result-item').forEach(item => {
                        item.addEventListener('click', () => {
                            if (memberIdInput) memberIdInput.value = item.dataset.id;
                            searchInput.value = item.dataset.name;
                            resultsDiv.style.display = 'none';
                        });
                    });
                }
                resultsDiv.style.display = 'block';
            } catch (e) {
                console.error('Search error:', e);
            }
        }, 300);
    });

    document.addEventListener('click', (e) => {
        if (resultsDiv && !searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.style.display = 'none';
        }
    });
}

// AI Assistant
async function askAI(question) {
    const messagesDiv = document.getElementById('ai-messages');
    if (!messagesDiv) return;

    appendMessage('user', question);
    const loadingId = appendMessage('assistant', '<i class="fas fa-spinner fa-spin"></i> Thinking...');

    try {
        const formData = new FormData();
        formData.append('question', question);
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const resp = await fetch('/ai/ask', {
            method: 'POST',
            body: formData,
            headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
        });
        const data = await resp.json();
        document.getElementById(loadingId)?.remove();
        appendMessage('assistant', data.response.replace(/\n/g, '<br>'));
    } catch (e) {
        document.getElementById(loadingId)?.remove();
        appendMessage('assistant', 'Sorry, an error occurred. Please try again.');
    }
}

function appendMessage(role, content) {
    const messagesDiv = document.getElementById('ai-messages');
    const id = 'msg-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = `ai-message ${role} fade-in`;
    div.innerHTML = content;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return id;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(amount);
}

// Chart defaults
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = getComputedStyle(document.documentElement)
        .getPropertyValue('--text-secondary').trim() || '#6B7280';
    Chart.defaults.borderColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--border-color').trim() || '#E5E7EB';
}
