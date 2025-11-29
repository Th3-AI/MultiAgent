// MultiAgent Platform - Enhanced JavaScript

let authToken = localStorage.getItem('authToken');
let currentUser = null;
const API_BASE = window.location.origin + '/api';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupMouseSpotlight();
    
    if (authToken) {
        document.getElementById('landingPage').classList.add('hidden');
        document.getElementById('mainDashboard').classList.remove('hidden');
        showSection('dashboard');
        loadDashboardData();
    }
});

// Mouse spotlight effect
function setupMouseSpotlight() {
    const spotlight = document.querySelector('.circle-3');
    const landingPage = document.querySelector('.landing-page');
    
    if (!spotlight || !landingPage) return;
    
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let currentX = mouseX;
    let currentY = mouseY;
    let isMouseMoving = false;
    let moveTimeout;
    
    // Track mouse movement
    landingPage.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        isMouseMoving = true;
        
        // Add glow effect when moving
        spotlight.style.opacity = '0.4';
        spotlight.style.filter = 'blur(100px)';
        
        // Reset timeout
        clearTimeout(moveTimeout);
        moveTimeout = setTimeout(() => {
            isMouseMoving = false;
            spotlight.style.opacity = '0.3';
            spotlight.style.filter = 'blur(80px)';
        }, 150);
    });
    
    // Smooth animation loop
    function animate() {
        // Smooth interpolation for fluid movement
        const speed = isMouseMoving ? 0.15 : 0.08;
        currentX += (mouseX - currentX) * speed;
        currentY += (mouseY - currentY) * speed;
        
        // Update spotlight position (offset by half the width/height for centering)
        spotlight.style.left = `${currentX - 300}px`;
        spotlight.style.top = `${currentY - 300}px`;
        
        requestAnimationFrame(animate);
    }
    
    animate();
}

function hideLanding() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('registerSection').classList.add('hidden');
}

function scrollToFeatures() {
    document.getElementById('features').scrollIntoView({ behavior: 'smooth' });
}

function setupEventListeners() {
    const forms = {
        loginForm: handleLogin,
        registerForm: handleRegister,
        transactionForm: handleTransaction,
        taskForm: handleTask,
        uploadForm: handleFileUpload
    };
    
    Object.entries(forms).forEach(([id, handler]) => {
        const form = document.getElementById(id);
        if (form) form.addEventListener('submit', handler);
    });
    
    // File input change handler
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const fileName = e.target.files[0]?.name || '';
            const fileNameSpan = document.getElementById('fileName');
            if (fileNameSpan) {
                fileNameSpan.textContent = fileName;
            }
        });
    }
}

// API Helper
async function apiCall(endpoint, options = {}) {
    showLoading();
    
    // Refresh token from localStorage
    authToken = localStorage.getItem('authToken');
    
    console.log('API Call:', endpoint, 'Token:', authToken ? 'Present' : 'Missing');
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
                ...options.headers
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    } finally {
        hideLoading();
    }
}

// Auth Functions
function showLogin() {
    document.getElementById('registerSection').classList.add('hidden');
    document.getElementById('loginSection').classList.remove('hidden');
}

function showRegister() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('registerSection').classList.remove('hidden');
}

function showDashboard() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('registerSection').classList.add('hidden');
    document.getElementById('mainDashboard').classList.remove('hidden');
    showSection('dashboard');
    loadDashboardData();
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Login failed');
        }
        
        // Set token IMMEDIATELY
        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('authToken', authToken);
        
        console.log('Token set:', authToken);
        
        hideLoading();
        showToast('Welcome back!', 'success');
        
        // Wait a bit then show dashboard
        await new Promise(resolve => setTimeout(resolve, 300));
        showDashboard();
        
    } catch (error) {
        hideLoading();
        showToast(error.message, 'error');
        console.error('Login failed:', error);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    try {
        const data = await apiCall('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                name: document.getElementById('regName').value,
                email: document.getElementById('regEmail').value,
                password: document.getElementById('regPassword').value
            })
        });
        
        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('authToken', authToken);
        showToast('Account created successfully!', 'success');
        
        // Small delay to ensure token is set
        setTimeout(() => showDashboard(), 100);
    } catch (error) {
        console.error('Registration failed:', error);
    }
}

function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showToast('Logged out successfully', 'info');
    showLogin();
}

// Navigation
function showSection(sectionName) {
    document.querySelectorAll('.dashboard-section').forEach(section => {
        section.classList.add('hidden');
    });
    
    const targetSection = document.getElementById(sectionName + 'Section');
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }
    
    document.querySelectorAll('.nav-link').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.querySelector(`[data-section="${sectionName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Load section data
    if (sectionName === 'dashboard') loadDashboardData();
    else if (sectionName === 'financial') loadFinancialData();
    else if (sectionName === 'tasks') loadTasks();
    else if (sectionName === 'agents') loadAgentPerformance();
}

// Dashboard Functions
async function loadDashboardData() {
    // Force refresh token from storage
    authToken = localStorage.getItem('authToken');
    
    if (!authToken) {
        console.log('No auth token, skipping dashboard load');
        return;
    }
    
    console.log('Loading dashboard with token:', authToken.substring(0, 20) + '...');
    
    // Add delay to ensure token is ready
    await new Promise(resolve => setTimeout(resolve, 200));
    
    try {
        const [spending, income, insights, transactions] = await Promise.all([
            apiCall('/analysis/spending-patterns').catch(err => {
                console.error('Spending error:', err);
                return { category_spending: {}, total_expenses: 0 };
            }),
            apiCall('/analysis/income-variability').catch(err => {
                console.error('Income error:', err);
                return { monthly_income: {}, average_income: 0 };
            }),
            apiCall('/insights').catch(err => {
                console.error('Insights error:', err);
                return [];
            }),
            apiCall('/transactions').catch(err => {
                console.error('Transactions error:', err);
                return [];
            })
        ]);
        
        updateDashboardStats(spending, income);
        createDashboardCharts(spending, income);
        displayDashboardInsights(insights);
        displayRecentTransactions(transactions);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateDashboardStats(spending, income) {
    const totalIncome = income.total_income || 0;
    const totalExpenses = spending.total_expenses || 0;
    const savingsRate = totalIncome > 0 ? ((totalIncome - totalExpenses) / totalIncome * 100) : 0;
    const healthScore = calculateHealthScore(savingsRate);
    
    updateElement('dashIncome', `$${totalIncome.toFixed(2)}`);
    updateElement('dashExpense', `$${totalExpenses.toFixed(2)}`);
    updateElement('dashSavings', `${savingsRate.toFixed(1)}%`);
    updateElement('dashHealth', Math.round(healthScore));
    updateElement('dashHealthRing', Math.round(healthScore));
    
    // Update health ring
    const ring = document.getElementById('healthRing');
    if (ring) {
        const roundedScore = Math.round(healthScore);
        ring.style.strokeDasharray = `${roundedScore}, 100`;
    }
}

function calculateHealthScore(savingsRate) {
    if (savingsRate >= 20) return 85 + Math.min(15, savingsRate - 20);
    if (savingsRate >= 10) return 70 + (savingsRate - 10);
    if (savingsRate >= 5) return 50 + (savingsRate - 5) * 4;
    return Math.max(0, 50 + savingsRate * 10);
}

function createDashboardCharts(spending, income) {
    // Spending Chart
    const spendingData = Object.entries(spending.category_spending || {});
    if (spendingData.length > 0) {
        const trace = {
            labels: spendingData.map(([cat]) => cat),
            values: spendingData.map(([, val]) => val),
            type: 'pie',
            hole: 0.4,
            marker: {
                colors: ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#14b8a6', '#f43f5e']
            },
            textinfo: 'label+percent',
            textposition: 'outside'
        };
        
        Plotly.newPlot('dashSpendingChart', [trace], {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: '#fff', family: 'Inter' },
            margin: { t: 20, b: 20, l: 20, r: 20 },
            showlegend: false
        }, { responsive: true, displayModeBar: false });
    } else {
        document.getElementById('dashSpendingChart').innerHTML = `
            <div class="empty-state">
                <i class="fas fa-chart-pie"></i>
                <p>No spending data</p>
            </div>
        `;
    }
    
    // Income Chart
    const incomeData = Object.entries(income.monthly_income || {});
    if (incomeData.length > 0) {
        const trace = {
            x: incomeData.map(([month]) => month),
            y: incomeData.map(([, val]) => val),
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#10b981', width: 3, shape: 'spline' },
            marker: { size: 10, color: '#10b981' },
            fill: 'tozeroy',
            fillcolor: 'rgba(16, 185, 129, 0.1)'
        };
        
        Plotly.newPlot('dashIncomeChart', [trace], {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: '#fff', family: 'Inter' },
            margin: { t: 20, b: 40, l: 50, r: 20 },
            xaxis: { 
                title: 'Month',
                gridcolor: 'rgba(255, 255, 255, 0.1)',
                color: '#fff'
            },
            yaxis: { 
                title: 'Income ($)',
                gridcolor: 'rgba(255, 255, 255, 0.1)',
                color: '#fff'
            }
        }, { responsive: true, displayModeBar: false });
    } else {
        document.getElementById('dashIncomeChart').innerHTML = `
            <div class="empty-state">
                <i class="fas fa-chart-line"></i>
                <p>No income data</p>
            </div>
        `;
    }
}

function displayDashboardInsights(insights) {
    const container = document.getElementById('dashInsights');
    if (!container) return;
    
    if (insights.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-lightbulb"></i>
                <p>No insights yet</p>
                <small>Add transactions to get AI-powered insights</small>
            </div>
        `;
        return;
    }
    
    container.innerHTML = insights.slice(0, 5).map(insight => `
        <div class="insight-item ${insight.priority}">
            <p style="margin-bottom:0.5rem;font-weight:600;">${insight.content}</p>
            <small style="color:rgba(255,255,255,0.5);">${formatDate(insight.created_at)}</small>
        </div>
    `).join('');
}

// Financial Functions
async function loadFinancialData() {
    try {
        const transactions = await apiCall('/transactions').catch(() => []);
        displayTransactions(transactions);
    } catch (error) {
        console.error('Error loading financial data:', error);
    }
}

async function handleTransaction(e) {
    e.preventDefault();
    try {
        await apiCall('/transactions', {
            method: 'POST',
            body: JSON.stringify({
                transaction_type: document.getElementById('transType').value,
                amount: parseFloat(document.getElementById('transAmount').value),
                category: document.getElementById('transCategory').value,
                description: document.getElementById('transDescription').value,
                date: new Date().toISOString()
            })
        });
        
        showToast('Transaction added successfully!', 'success');
        document.getElementById('transactionForm').reset();
        loadFinancialData();
        loadDashboardData();
    } catch (error) {
        console.error('Error adding transaction:', error);
    }
}

function displayTransactions(transactions) {
    const container = document.getElementById('transactionsList');
    if (!container) return;
    
    if (transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-receipt"></i>
                <p>No transactions yet</p>
                <small>Add your first transaction above to get started</small>
            </div>
        `;
        return;
    }
    
    container.innerHTML = transactions.slice(0, 20).map(t => `
        <div class="transaction-item">
            <div class="transaction-info">
                <div class="transaction-category">${t.category}</div>
                <div class="transaction-description">${t.description || 'No description'}</div>
                <small style="color:rgba(255,255,255,0.5);">${formatDate(t.date)}</small>
            </div>
            <div class="transaction-amount ${t.transaction_type}">
                ${t.transaction_type === 'income' ? '+' : '-'}$${Math.abs(t.amount).toFixed(2)}
            </div>
        </div>
    `).join('');
}

async function getAdvice() {
    const context = document.getElementById('adviceContext').value;
    if (!context.trim()) {
        showToast('Please enter a question', 'error');
        return;
    }
    
    try {
        const data = await apiCall('/coach/advice', {
            method: 'POST',
            body: JSON.stringify({ context })
        });
        
        const resultDiv = document.getElementById('adviceResult');
        resultDiv.innerHTML = `
            <h4 style="margin-bottom:1rem;">AI Financial Advice:</h4>
            <p style="white-space:pre-wrap;line-height:1.6;">${data.advice}</p>
        `;
        resultDiv.classList.remove('hidden');
    } catch (error) {
        console.error('Error getting advice:', error);
    }
}

async function getQuickAdvice() {
    document.getElementById('adviceContext').value = 'Based on my recent transactions, what financial advice do you have for me?';
    showSection('financial');
    setTimeout(() => getAdvice(), 500);
}

// Task Functions
async function loadTasks() {
    try {
        const tasks = await apiCall('/tasks').catch(() => []);
        displayTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

async function handleTask(e) {
    e.preventDefault();
    try {
        await apiCall('/tasks', {
            method: 'POST',
            body: JSON.stringify({
                title: document.getElementById('taskTitle').value,
                description: document.getElementById('taskDescription').value,
                agent_type: document.getElementById('taskAgent').value,
                priority: document.getElementById('taskPriority').value
            })
        });
        
        showToast('Task created successfully!', 'success');
        document.getElementById('taskForm').reset();
        loadTasks();
    } catch (error) {
        console.error('Error creating task:', error);
    }
}

function displayTasks(tasks) {
    const container = document.getElementById('tasksList');
    if (!container) return;
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-tasks"></i>
                <p>No tasks yet</p>
                <small>Create your first task to get started</small>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="task-item">
            <div style="flex:1;">
                <div class="task-title">${task.title}</div>
                <div class="task-description">${task.description || 'No description'}</div>
                <div class="task-meta">
                    <span class="task-badge priority-${task.priority}">${task.priority}</span>
                    <span class="task-badge">${task.agent_type}</span>
                    <span class="task-badge status-${task.status}">${task.status.replace('_', ' ')}</span>
                </div>
            </div>
            <div class="task-actions">
                <button class="btn-icon" onclick="deleteTask(${task.id})" title="Delete task">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

async function deleteTask(taskId) {
    if (!confirm('Delete this task?')) return;
    
    try {
        await apiCall(`/tasks/${taskId}`, { method: 'DELETE' });
        showToast('Task deleted', 'success');
        loadTasks();
    } catch (error) {
        console.error('Error deleting task:', error);
    }
}

// Agent Functions
async function loadAgentPerformance() {
    try {
        const performance = await apiCall('/agents/performance').catch(() => ({}));
        updateAgentStats(performance);
    } catch (error) {
        console.error('Error loading agent performance:', error);
    }
}

function updateAgentStats(performance) {
    Object.entries(performance).forEach(([agentType, data]) => {
        updateElement(`${agentType}Tasks`, data.task_count || 0);
        updateElement(`${agentType}Success`, `${((data.success_rate || 0) * 100).toFixed(0)}%`);
    });
}

async function testAgent(agentType) {
    showToast(`Testing ${agentType} agent...`, 'info');
    try {
        await apiCall('/tasks', {
            method: 'POST',
            body: JSON.stringify({
                title: `Test ${agentType} agent`,
                description: 'Automated test task',
                agent_type: agentType,
                priority: 'low'
            })
        });
        showToast(`${agentType} agent test completed!`, 'success');
        loadAgentPerformance();
    } catch (error) {
        console.error('Agent test failed:', error);
    }
}

async function runAnalysis() {
    showToast('Running comprehensive analysis...', 'info');
    try {
        // Generate insights
        await apiCall('/insights/generate', { method: 'POST' });
        
        // Run comprehensive analysis
        await apiCall('/analysis/comprehensive');
        
        showToast('Analysis complete! Check your insights.', 'success');
        
        // Reload dashboard to show new insights
        await loadDashboardData();
    } catch (error) {
        console.error('Analysis failed:', error);
    }
}

// UI Helpers
function showLoading() {
    document.getElementById('loadingOverlay')?.classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingOverlay')?.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div style="display:flex;align-items:center;gap:0.75rem;">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function refreshCharts() {
    loadDashboardData();
    showToast('Charts refreshed!', 'success');
}

function loadTransactions() {
    loadFinancialData();
    showToast('Transactions refreshed!', 'success');
}

let previewTransactions = [];

async function handleFileUpload(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading();
    
    try {
        authToken = localStorage.getItem('authToken');
        
        const response = await fetch(`${API_BASE}/upload-financial-data`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        
        // Check if it's a preview
        if (data.preview) {
            previewTransactions = data.transactions;
            showPreviewTable(data);
        } else {
            // Old flow (shouldn't happen now)
            showImportSuccess(data);
        }
        
    } catch (error) {
        const resultDiv = document.getElementById('uploadResult');
        resultDiv.innerHTML = `
            <div style="padding:1rem;background:#fee2e2;border-left:4px solid #ef4444;border-radius:0.5rem;">
                <h4 style="color:#991b1b;margin-bottom:0.5rem;">✗ Analysis Failed</h4>
                <p style="color:#991b1b;">${error.message}</p>
            </div>
        `;
        resultDiv.classList.remove('hidden');
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function showPreviewTable(data) {
    const resultDiv = document.getElementById('uploadResult');
    const summary = data.summary;
    
    resultDiv.innerHTML = `
        <div style="padding:1.5rem;background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);border-radius:1rem;">
            <h4 style="margin-bottom:1rem;font-size:1.25rem;">📊 Review Transactions</h4>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem;">
                <div style="padding:0.75rem;background:rgba(255,255,255,0.05);border-radius:0.5rem;">
                    <div style="font-size:0.875rem;color:rgba(255,255,255,0.6);">Total</div>
                    <div style="font-size:1.5rem;font-weight:700;" data-summary="total">${summary.total_transactions}</div>
                </div>
                <div style="padding:0.75rem;background:rgba(16,185,129,0.1);border-radius:0.5rem;">
                    <div style="font-size:0.875rem;color:rgba(255,255,255,0.6);">Income</div>
                    <div style="font-size:1.5rem;font-weight:700;color:#10b981;" data-summary="income">$${summary.total_income.toFixed(2)}</div>
                </div>
                <div style="padding:0.75rem;background:rgba(239,68,68,0.1);border-radius:0.5rem;">
                    <div style="font-size:0.875rem;color:rgba(255,255,255,0.6);">Expenses</div>
                    <div style="font-size:1.5rem;font-weight:700;color:#ef4444;" data-summary="expenses">$${summary.total_expenses.toFixed(2)}</div>
                </div>
                <div style="padding:0.75rem;background:rgba(139,92,246,0.1);border-radius:0.5rem;">
                    <div style="font-size:0.875rem;color:rgba(255,255,255,0.6);">Savings</div>
                    <div style="font-size:1.5rem;font-weight:700;color:#8b5cf6;" data-summary="savings">$${(summary.total_income - summary.total_expenses).toFixed(2)}</div>
                </div>
            </div>
            <div style="max-height:400px;overflow-y:auto;margin-bottom:1rem;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead style="position:sticky;top:0;background:rgba(30,41,59,0.95);backdrop-filter:blur(10px);">
                        <tr>
                            <th style="padding:0.75rem;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">Date</th>
                            <th style="padding:0.75rem;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">Description</th>
                            <th style="padding:0.75rem;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">Category</th>
                            <th style="padding:0.75rem;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">Type</th>
                            <th style="padding:0.75rem;text-align:right;border-bottom:1px solid rgba(255,255,255,0.1);">Amount</th>
                            <th style="padding:0.75rem;text-align:center;border-bottom:1px solid rgba(255,255,255,0.1);">Action</th>
                        </tr>
                    </thead>
                    <tbody id="previewTableBody">
                        ${data.transactions.map((t, idx) => `
                            <tr id="preview-row-${idx}" style="border-bottom:1px solid rgba(255,255,255,0.05);">
                                <td style="padding:0.75rem;">${t.date}</td>
                                <td style="padding:0.75rem;"><input type="text" value="${t.description}" onchange="updatePreviewTransaction(${idx}, 'description', this.value)" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:0.25rem;padding:0.25rem 0.5rem;color:#fff;width:100%;"></td>
                                <td style="padding:0.75rem;"><input type="text" value="${t.category}" onchange="updatePreviewTransaction(${idx}, 'category', this.value)" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:0.25rem;padding:0.25rem 0.5rem;color:#fff;width:100%;"></td>
                                <td style="padding:0.75rem;">
                                    <select onchange="updatePreviewTransaction(${idx}, 'type', this.value)" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:0.25rem;padding:0.25rem 0.5rem;color:#fff;">
                                        <option value="income" ${t.type === 'income' ? 'selected' : ''}>Income</option>
                                        <option value="expense" ${t.type === 'expense' ? 'selected' : ''}>Expense</option>
                                    </select>
                                </td>
                                <td style="padding:0.75rem;text-align:right;color:${t.type === 'income' ? '#10b981' : '#ef4444'};font-weight:600;">$${t.amount.toFixed(2)}</td>
                                <td style="padding:0.75rem;text-align:center;">
                                    <button onclick="removePreviewTransaction(${idx})" style="background:rgba(239,68,68,0.2);border:none;border-radius:0.25rem;padding:0.25rem 0.5rem;color:#ef4444;cursor:pointer;">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div style="display:flex;gap:1rem;justify-content:flex-end;">
                <button onclick="cancelImport()" style="padding:0.75rem 1.5rem;background:rgba(255,255,255,0.1);border:none;border-radius:0.5rem;color:#fff;cursor:pointer;">Cancel</button>
                <button onclick="confirmImport()" data-action="import" style="padding:0.75rem 1.5rem;background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;border-radius:0.5rem;color:#fff;cursor:pointer;font-weight:600;">Import ${summary.total_transactions} Transactions</button>
            </div>
        </div>
    `;
    resultDiv.classList.remove('hidden');
}

function updatePreviewTransaction(idx, field, value) {
    if (previewTransactions[idx]) {
        previewTransactions[idx][field] = value;
        
        // Update amount color if type changed
        if (field === 'type') {
            const row = document.getElementById(`preview-row-${idx}`);
            if (row) {
                const amountCell = row.querySelector('td:nth-child(5)');
                if (amountCell) {
                    amountCell.style.color = value === 'income' ? '#10b981' : '#ef4444';
                }
            }
            // Recalculate summary
            updatePreviewSummary();
        }
    }
}

function updatePreviewSummary() {
    const validTransactions = previewTransactions.filter(t => t !== null);
    const totalIncome = validTransactions.filter(t => t.type === 'income').reduce((sum, t) => sum + t.amount, 0);
    const totalExpenses = validTransactions.filter(t => t.type === 'expense').reduce((sum, t) => sum + t.amount, 0);
    const totalTransactions = validTransactions.length;
    
    // Update summary cards
    document.querySelector('[data-summary="total"]').textContent = totalTransactions;
    document.querySelector('[data-summary="income"]').textContent = `$${totalIncome.toFixed(2)}`;
    document.querySelector('[data-summary="expenses"]').textContent = `$${totalExpenses.toFixed(2)}`;
    document.querySelector('[data-summary="savings"]').textContent = `$${(totalIncome - totalExpenses).toFixed(2)}`;
    
    // Update import button text
    const importBtn = document.querySelector('[data-action="import"]');
    if (importBtn) {
        importBtn.textContent = `Import ${totalTransactions} Transactions`;
    }
}

function removePreviewTransaction(idx) {
    const row = document.getElementById(`preview-row-${idx}`);
    if (row) {
        row.remove();
        previewTransactions[idx] = null; // Mark as deleted
        updatePreviewSummary(); // Recalculate
    }
}

function cancelImport() {
    previewTransactions = [];
    document.getElementById('uploadResult').classList.add('hidden');
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
}

async function confirmImport() {
    // Filter out deleted transactions
    const transactionsToImport = previewTransactions.filter(t => t !== null);
    
    if (transactionsToImport.length === 0) {
        showToast('No transactions to import', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const data = await apiCall('/confirm-import', {
            method: 'POST',
            body: JSON.stringify({ transactions: transactionsToImport })
        });
        
        showToast(`Successfully imported ${data.transactions_added} transactions!`, 'success');
        
        // Reset
        cancelImport();
        
        // Generate insights for the new data
        try {
            await apiCall('/insights/generate', { method: 'POST' });
            showToast('AI insights generated!', 'success');
        } catch (err) {
            console.error('Failed to generate insights:', err);
        }
        
        // Reload data
        loadFinancialData();
        loadDashboardData();
        
    } catch (error) {
        showToast('Failed to import transactions: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function showImportSuccess(data) {
    const resultDiv = document.getElementById('uploadResult');
    resultDiv.innerHTML = `
        <div style="padding:1rem;background:#dcfce7;border-left:4px solid #10b981;border-radius:0.5rem;">
            <h4 style="color:#166534;margin-bottom:0.5rem;">✓ Import Successful!</h4>
            <p style="color:#166534;margin-bottom:0.5rem;">${data.message}</p>
            <p style="color:#166534;font-size:0.875rem;">Added ${data.transactions_added} transactions</p>
        </div>
    `;
    resultDiv.classList.remove('hidden');
    
    showToast(`Imported ${data.transactions_added} transactions!`, 'success');
    
    // Reset form
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    
    // Reload data
    loadFinancialData();
    loadDashboardData();
}


// Display recent transactions on dashboard
function displayRecentTransactions(transactions) {
    const container = document.getElementById('dashRecentTransactions');
    if (!container) return;
    
    if (transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-receipt"></i>
                <p>No transactions yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = transactions.slice(0, 5).map(t => `
        <div class="recent-transaction-item">
            <div class="rt-info">
                <div class="rt-category">${t.category}</div>
                <div class="rt-description">${t.description || 'No description'}</div>
            </div>
            <div class="rt-amount ${t.transaction_type}">
                ${t.transaction_type === 'income' ? '+' : '-'}$${Math.abs(t.amount).toFixed(2)}
            </div>
        </div>
    `).join('');
}


// ============================================================================
// PLAID BANKING INTEGRATION
// ============================================================================

async function connectBankAccount() {
    showLoading();
    
    try {
        // Get link token from backend
        const data = await apiCall('/plaid/create-link-token', { method: 'POST' });
        
        hideLoading();
        
        // Initialize Plaid Link
        const handler = Plaid.create({
            token: data.link_token,
            onSuccess: async (public_token, metadata) => {
                showLoading();
                
                try {
                    // Exchange public token for access token
                    await apiCall('/plaid/exchange-token', {
                        method: 'POST',
                        body: JSON.stringify({
                            public_token: public_token,
                            institution_name: metadata.institution.name,
                            institution_id: metadata.institution.institution_id
                        })
                    });
                    
                    showToast(`Connected to ${metadata.institution.name}!`, 'success');
                    
                    // Load connected accounts
                    await loadConnectedAccounts();
                    
                    // Ask to sync transactions
                    if (confirm('Bank connected! Sync transactions now?')) {
                        await syncBankTransactions();
                    }
                    
                } catch (error) {
                    showToast('Failed to save bank connection', 'error');
                } finally {
                    hideLoading();
                }
            },
            onExit: (err, metadata) => {
                if (err) {
                    console.error('Plaid Link error:', err);
                    showToast('Failed to connect bank', 'error');
                }
            },
            onEvent: (eventName, metadata) => {
                console.log('Plaid event:', eventName, metadata);
            }
        });
        
        handler.open();
        
    } catch (error) {
        hideLoading();
        showToast('Failed to initialize Plaid: ' + error.message, 'error');
        console.error('Plaid initialization error:', error);
    }
}

async function loadConnectedAccounts() {
    try {
        const accounts = await apiCall('/plaid/accounts');
        
        const container = document.getElementById('connectedAccounts');
        if (!container) return;
        
        if (accounts.length === 0) {
            container.innerHTML = '<p style="color:rgba(255,255,255,0.5);font-size:0.875rem;">No banks connected yet</p>';
            return;
        }
        
        container.innerHTML = accounts.map(acc => `
            <div style="padding:1rem;background:rgba(255,255,255,0.05);border-radius:0.75rem;margin-top:0.5rem;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:600;">${acc.institution_name}</div>
                    <div style="font-size:0.875rem;color:rgba(255,255,255,0.6);">
                        Last synced: ${acc.last_synced ? new Date(acc.last_synced).toLocaleString() : 'Never'}
                    </div>
                </div>
                <div style="display:flex;gap:0.5rem;">
                    <button onclick="syncSpecificAccount(${acc.id})" class="btn-icon" title="Sync transactions">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button onclick="disconnectBank(${acc.id})" class="btn-icon" title="Disconnect" style="background:rgba(239,68,68,0.2);color:#ef4444;">
                        <i class="fas fa-unlink"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load connected accounts:', error);
    }
}

async function syncBankTransactions(accountId = null) {
    showLoading();
    showToast('Syncing transactions from bank...', 'info');
    
    try {
        const data = await apiCall('/plaid/sync-transactions', {
            method: 'POST',
            body: JSON.stringify({ account_id: accountId })
        });
        
        showToast(data.message, 'success');
        
        // Generate insights
        try {
            await apiCall('/insights/generate', { method: 'POST' });
        } catch (err) {
            console.error('Failed to generate insights:', err);
        }
        
        // Reload data
        await loadConnectedAccounts();
        await loadFinancialData();
        await loadDashboardData();
        
    } catch (error) {
        showToast('Failed to sync transactions: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function syncSpecificAccount(accountId) {
    await syncBankTransactions(accountId);
}

async function disconnectBank(accountId) {
    if (!confirm('Disconnect this bank account? Transactions will remain.')) return;
    
    try {
        await apiCall(`/plaid/disconnect/${accountId}`, { method: 'DELETE' });
        showToast('Bank account disconnected', 'success');
        await loadConnectedAccounts();
    } catch (error) {
        showToast('Failed to disconnect bank', 'error');
    }
}

// Load connected accounts when financial section is shown
const originalShowSection = showSection;
showSection = function(sectionName) {
    originalShowSection(sectionName);
    if (sectionName === 'financial') {
        loadConnectedAccounts();
    }
};
