// FreEco.AI GUI - Complete Application Logic
const API_BASE = '/api';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    setupEventListeners();
    loadInitialData();
});

// ===== THEME =====
function initTheme() {
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-theme');
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
}

// ===== EVENT SETUP =====
function setupEventListeners() {
    // Theme
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    // Tabs
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => switchTab(e.target.dataset.tab));
    });

    // Chat
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('chatInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Tasks
    document.getElementById('newTaskBtn').addEventListener('click', () => openModal('taskModal'));
    document.getElementById('createTaskBtn').addEventListener('click', createTask);
    document.getElementById('cancelTaskBtn').addEventListener('click', () => closeModal('taskModal'));

    // Documents
    document.getElementById('addDocBtn').addEventListener('click', () => openModal('docModal'));
    document.getElementById('createDocBtn').addEventListener('click', createDocument);
    document.getElementById('cancelDocBtn').addEventListener('click', () => closeModal('docModal'));
    document.getElementById('searchInput').addEventListener('input', searchDocuments);

    // Settings
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    document.getElementById('resetSettingsBtn').addEventListener('click', resetSettings);
    document.getElementById('temperature').addEventListener('input', (e) => {
        document.getElementById('tempValue').textContent = e.target.value;
    });

    // Modal close buttons
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) closeModal(modal.id);
        });
    });

    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal(modal.id);
        });
    });
}

// ===== TABS =====
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    if (tabName === 'tasks') loadTasks();
    else if (tabName === 'knowledge') loadDocuments();
    else if (tabName === 'settings') {
        loadSettings();
        checkApiStatus();
    }
}

// ===== CHAT =====
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    input.value = '';

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await res.json();
        if (data.response) {
            addMessage(data.response, 'assistant');
        }
    } catch (error) {
        addMessage(`Error: ${error.message}`, 'error');
    }
}

function addMessage(text, sender) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${sender}`;
    messageDiv.textContent = text;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ===== TASKS =====
async function createTask() {
    const title = document.getElementById('taskTitle').value.trim();
    const desc = document.getElementById('taskDesc').value.trim();
    const priority = document.getElementById('taskPriority').value;

    if (!title) {
        alert('Enter task title');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description: desc, priority })
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        closeModal('taskModal');
        document.getElementById('taskTitle').value = '';
        document.getElementById('taskDesc').value = '';
        loadTasks();
    } catch (error) {
        alert(`Error creating task: ${error.message}`);
    }
}

async function loadTasks() {
    try {
        const res = await fetch(`${API_BASE}/tasks`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const tasks = await res.json();

        // Update statistics
        document.getElementById('totalTasks').textContent = tasks.length;
        document.getElementById('pendingTasks').textContent = tasks.filter(t => t.status === 'pending').length;
        document.getElementById('inProgressTasks').textContent = tasks.filter(t => t.status === 'in_progress').length;
        document.getElementById('completedTasks').textContent = tasks.filter(t => t.status === 'completed').length;

        // Render tasks
        const list = document.getElementById('taskList');
        if (tasks.length === 0) {
            list.innerHTML = '<div class="empty-state">No tasks yet. Create one to get started!</div>';
            return;
        }

        list.innerHTML = tasks.map(t => `
            <div class="task-item">
                <div class="task-item-content">
                    <div class="task-item-title">${escapeHtml(t.title)}</div>
                    <div class="task-item-meta">Priority: <strong>${t.priority}</strong> | Status: <strong>${t.status}</strong></div>
                    ${t.description ? `<div class="task-item-desc">${escapeHtml(t.description)}</div>` : ''}
                </div>
                <div class="task-item-actions">
                    <button class="btn-small" onclick="updateTask('${t.id}', 'in_progress')">Start</button>
                    <button class="btn-small" onclick="updateTask('${t.id}', 'completed')">Done</button>
                    <button class="btn-small btn-danger" onclick="deleteTask('${t.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Load tasks error:', error);
        document.getElementById('taskList').innerHTML = `<div class="error">Error loading tasks: ${error.message}</div>`;
    }
}

async function updateTask(id, status) {
    try {
        const res = await fetch(`${API_BASE}/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        loadTasks();
    } catch (error) {
        alert(`Error updating task: ${error.message}`);
    }
}

async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;

    try {
        const res = await fetch(`${API_BASE}/tasks/${id}`, {
            method: 'DELETE'
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        loadTasks();
    } catch (error) {
        alert(`Error deleting task: ${error.message}`);
    }
}

// ===== DOCUMENTS =====
async function createDocument() {
    const title = document.getElementById('docTitle').value.trim();
    const content = document.getElementById('docContent').value.trim();
    const category = document.getElementById('docCategory').value;

    if (!title || !content) {
        alert('Enter title and content');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/documents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content, category })
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        closeModal('docModal');
        document.getElementById('docTitle').value = '';
        document.getElementById('docContent').value = '';
        document.getElementById('docCategory').value = 'general';
        loadDocuments();
    } catch (error) {
        alert(`Error creating document: ${error.message}`);
    }
}

async function loadDocuments() {
    try {
        const res = await fetch(`${API_BASE}/documents`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const docs = await res.json();

        document.getElementById('totalDocs').textContent = docs.length;
        const size = (docs.reduce((s, d) => s + (d.size || 0), 0) / 1024 / 1024).toFixed(2);
        document.getElementById('totalSize').textContent = `${size} MB`;

        renderDocs(docs);
    } catch (error) {
        console.error('Load docs error:', error);
        document.getElementById('documentList').innerHTML = `<div class="error">Error loading documents: ${error.message}</div>`;
    }
}

function renderDocs(docs) {
    const list = document.getElementById('documentList');
    if (docs.length === 0) {
        list.innerHTML = '<div class="empty-state">No documents yet. Add one to get started!</div>';
        return;
    }

    list.innerHTML = docs.map(d => `
        <div class="document-item">
            <div class="document-item-content">
                <div class="document-item-title">${escapeHtml(d.title)}</div>
                <div class="document-item-meta">Category: <strong>${d.category}</strong> | Size: <strong>${(d.size / 1024).toFixed(2)} KB</strong></div>
            </div>
            <div class="document-item-actions">
                <button class="btn-small btn-danger" onclick="deleteDocument('${d.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

async function searchDocuments() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        loadDocuments();
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/documents/search?q=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const results = await res.json();
        renderDocs(results);
    } catch (error) {
        console.error('Search error:', error);
    }
}

async function deleteDocument(id) {
    if (!confirm('Delete this document?')) return;

    try {
        const res = await fetch(`${API_BASE}/documents/${id}`, {
            method: 'DELETE'
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        loadDocuments();
    } catch (error) {
        alert(`Error deleting document: ${error.message}`);
    }
}

// ===== SETTINGS =====
async function loadSettings() {
    try {
        const res = await fetch(`${API_BASE}/settings`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const settings = await res.json();
        document.getElementById('apiKey').value = settings.api_key || '';
        document.getElementById('model').value = settings.model || 'minimax-01';
        document.getElementById('temperature').value = settings.temperature || 0.7;
        document.getElementById('maxTokens').value = settings.max_tokens || 4096;
        document.getElementById('tempValue').textContent = settings.temperature || 0.7;
    } catch (error) {
        console.error('Load settings error:', error);
    }
}

async function saveSettings() {
    const settings = {
        api_key: document.getElementById('apiKey').value,
        model: document.getElementById('model').value,
        temperature: parseFloat(document.getElementById('temperature').value),
        max_tokens: parseInt(document.getElementById('maxTokens').value)
    };

    try {
        const res = await fetch(`${API_BASE}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        alert('Settings saved successfully!');
        checkApiStatus();
    } catch (error) {
        alert(`Error saving settings: ${error.message}`);
    }
}

function resetSettings() {
    if (confirm('Reset all settings to defaults?')) {
        localStorage.removeItem('freeco_settings');
        loadSettings();
    }
}

async function checkApiStatus() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        const status = document.getElementById('apiStatus');
        if (data.status === 'ok') {
            status.innerHTML = '✅ Connected - API is running and ready.';
            status.style.color = '#10b981';
        } else {
            status.innerHTML = '❌ Disconnected - Check your settings.';
            status.style.color = '#ef4444';
        }
    } catch (error) {
        const status = document.getElementById('apiStatus');
        status.innerHTML = '❌ Error - Cannot reach API.';
        status.style.color = '#ef4444';
    }
}

// ===== MODALS =====
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

// ===== UTILITIES =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadInitialData() {
    try {
        await fetch(`${API_BASE}/health`);
        switchTab('chat');
    } catch (error) {
        console.error('Initial load error:', error);
    }
}
