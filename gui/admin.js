const API_BASE = '/api';
let pollIntervals = {};

function showLoading() { document.getElementById('loadingOverlay').classList.add('active'); }
function hideLoading() { document.getElementById('loadingOverlay').classList.remove('active'); }

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = type === 'success' ? 'check-circle' : (type === 'error' ? 'exclamation-circle' : 'info-circle');
    toast.innerHTML = `<i class="fas fa-${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatDate(dateStr) {
    if(!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
}

async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        const data = await response.json();
        if(!response.ok) throw new Error(data.message || data.error || 'API Error');
        return data;
    } catch (err) {
        console.error(err);
        showToast(err.message, 'error');
        throw err;
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(nav => nav.classList.remove('active'));
    document.getElementById(`page-${tabId}`).classList.add('active');
    const activeNav = document.querySelector(`.nav-link[data-tab="${tabId}"]`);
    if(activeNav) {
        activeNav.classList.add('active');
        document.getElementById('topbarTitle').innerText = activeNav.querySelector('span').innerText;
    }
    if(window.innerWidth <= 768) document.getElementById('sidebar').classList.remove('open');

    if(tabId === 'dashboard') loadDashboard();
    else if(tabId === 'quizzes') loadQuizzes();
    else if(tabId === 'results') loadSubmissions();
    else if(tabId === 'system') loadSystemStatus();
}

function openCreateQuizModal() {
    document.getElementById('createQuizForm').reset();
    document.getElementById('modalCreateQuiz').classList.add('active');
}
function openAddQuestionModal(quizId) {
    document.getElementById('addQuestionForm').reset();
    document.getElementById('questionQuizId').value = quizId;
    document.getElementById('modalAddQuestion').classList.add('active');
}
function closeModal(modalId) { document.getElementById(modalId).classList.remove('active'); }

async function loadDashboard() {
    try {
        const [quizzes, submissions, nodes] = await Promise.all([
            apiFetch('/quizzes').catch(() => []),
            apiFetch('/submissions').catch(() => []),
            apiFetch('/system/nodes').catch(() => ({nodes:[]}))
        ]);

        animateValue(document.querySelector('#statQuizzes .stat-number'), 0, quizzes.length || 0, 1000);
        animateValue(document.querySelector('#statSubmissions .stat-number'), 0, submissions.length || 0, 1000);

        let passRate = 0;
        const graded = submissions.filter(s => s.status === 'graded');
        if(graded.length > 0) {
            const passed = graded.filter(s => parseFloat(s.score) >= 60).length;
            passRate = Math.round((passed / graded.length) * 100);
        }
        document.querySelector('#statPassRate .stat-number').innerHTML = `${passRate}<span class="stat-unit">%</span>`;

        const recentDiv = document.getElementById('recentActivity');
        if(submissions.length === 0) {
            recentDiv.innerHTML = `<div class="empty-state"><i class="fas fa-inbox"></i><p>No recent activity</p></div>`;
        } else {
            recentDiv.innerHTML = submissions.slice(0, 5).map(s => `
                <div class="notification-item">
                    <div class="notification-content">
                        <p><strong>${s.student_name}</strong> submitted Quiz #${s.quiz_id}</p>
                        <span class="notification-time">${formatDate(s.submitted_at)}</span>
                    </div>
                    <span class="badge badge-${s.status}">${s.status}</span>
                </div>
            `).join('');
        }

        const clusterDiv = document.getElementById('clusterOverview');
        const totalNodes = nodes.nodes ? nodes.nodes.length : 0;
        const healthy = nodes.nodes ? nodes.nodes.filter(n => n.status === 'healthy').length : 0;
        clusterDiv.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <span>Total Nodes Configured</span>
                <strong>${totalNodes}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>Healthy Online Nodes</span>
                <strong style="color:var(--success)">${healthy}</strong>
            </div>
        `;
    } catch(e) {}
}

async function loadQuizzes() {
    showLoading();
    try {
        const quizzes = await apiFetch('/quizzes');
        const container = document.getElementById('quizzesList');
        if(quizzes.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-book-open"></i><p>No quizzes yet</p></div>`;
        } else {
            container.innerHTML = `<table>
                <thead><tr><th>ID</th><th>Title</th><th>Time Limit</th><th>Created</th><th>Actions</th></tr></thead>
                <tbody>
                    ${quizzes.map(q => `
                        <tr>
                            <td>${q.id}</td>
                            <td><strong>${q.title}</strong></td>
                            <td>${q.time_limit_minutes} min</td>
                            <td>${formatDate(q.created_at)}</td>
                            <td>
                                <button class="btn btn-sm btn-ghost" onclick="viewQuizQuestions(${q.id})"><i class="fas fa-list"></i> Questions</button>
                                <button class="btn btn-sm btn-ghost" onclick="openAddQuestionModal(${q.id})"><i class="fas fa-plus"></i> Add Q</button>
                                <button class="btn btn-sm btn-ghost" onclick="deleteQuiz(${q.id})" style="color:var(--danger)"><i class="fas fa-trash"></i></button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
        }
    } finally { hideLoading(); }
}

async function handleCreateQuiz(e) {
    e.preventDefault();
    const data = {
        title: document.getElementById('quizTitle').value,
        description: document.getElementById('quizDescription').value,
        time_limit_minutes: parseInt(document.getElementById('quizTimeLimit').value)
    };
    showLoading();
    try {
        await apiFetch('/quizzes', { method: 'POST', body: JSON.stringify(data) });
        showToast('Quiz created successfully!', 'success');
        closeModal('modalCreateQuiz');
        loadQuizzes();
    } finally { hideLoading(); }
}

async function deleteQuiz(id) {
    if(!confirm('Are you sure you want to delete this quiz?')) return;
    showLoading();
    try {
        await apiFetch(`/quizzes/${id}`, { method: 'DELETE' });
        showToast('Quiz deleted', 'success');
        loadQuizzes();
    } finally { hideLoading(); }
}

async function handleAddQuestion(e) {
    e.preventDefault();
    const quizId = document.getElementById('questionQuizId').value;
    const options = document.querySelectorAll('.option-input');
    const correctRadios = document.getElementsByName('correctOption');
    let correctLetter = 'a';
    for(let i=0; i<correctRadios.length; i++) {
        if(correctRadios[i].checked) { correctLetter = ['a','b','c','d'][i]; break; }
    }
    const data = {
        question_text: document.getElementById('questionText').value,
        option_a: options[0].value,
        option_b: options[1].value,
        option_c: options[2].value,
        option_d: options[3].value,
        correct_answer: correctLetter,
        points: parseInt(document.getElementById('questionPoints').value)
    };
    showLoading();
    try {
        await apiFetch(`/quizzes/${quizId}/questions`, { method: 'POST', body: JSON.stringify(data) });
        showToast('Question added successfully!', 'success');
        closeModal('modalAddQuestion');
    } finally { hideLoading(); }
}

async function viewQuizQuestions(id) {
    showLoading();
    try {
        const questions = await apiFetch(`/quizzes/${id}/questions`);
        const body = document.getElementById('viewQuestionsBody');
        if(questions.length === 0) {
            body.innerHTML = `<div class="empty-state"><p>No questions in this quiz.</p></div>`;
        } else {
            body.innerHTML = questions.map((q, idx) => `
                <div class="question-card" style="margin-bottom:15px; padding:15px;">
                    <h4>Q${idx+1}: ${q.question_text}</h4>
                    <ul style="list-style:none; padding-left:10px; margin-top:10px;">
                        <li style="${q.correct_answer==='a'?'color:var(--success);font-weight:bold;':''}"><i class="fas fa-${q.correct_answer==='a'?'check':'circle'}"></i> A) ${q.option_a}</li>
                        <li style="${q.correct_answer==='b'?'color:var(--success);font-weight:bold;':''}"><i class="fas fa-${q.correct_answer==='b'?'check':'circle'}"></i> B) ${q.option_b}</li>
                        <li style="${q.correct_answer==='c'?'color:var(--success);font-weight:bold;':''}"><i class="fas fa-${q.correct_answer==='c'?'check':'circle'}"></i> C) ${q.option_c}</li>
                        <li style="${q.correct_answer==='d'?'color:var(--success);font-weight:bold;':''}"><i class="fas fa-${q.correct_answer==='d'?'check':'circle'}"></i> D) ${q.option_d}</li>
                    </ul>
                    <div style="margin-top:10px; font-size:0.8rem; color:var(--text-muted)">Points: ${q.points}</div>
                </div>
            `).join('');
        }
        document.getElementById('modalViewQuestions').classList.add('active');
    } finally { hideLoading(); }
}

async function loadSubmissions() {
    showLoading();
    try {
        const subs = await apiFetch('/submissions');
        const container = document.getElementById('resultsList');
        if(subs.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-chart-pie"></i><p>No submissions yet</p></div>`;
        } else {
            container.innerHTML = `<table>
                <thead><tr><th>ID</th><th>Student</th><th>Quiz ID</th><th>Status</th><th>Score</th><th>Date</th><th>Action</th></tr></thead>
                <tbody>
                    ${subs.map(s => `
                        <tr>
                            <td>#${s.id}</td>
                            <td><strong>${s.student_name}</strong></td>
                            <td>${s.quiz_id}</td>
                            <td><span class="badge badge-${s.status}">${s.status.toUpperCase()}</span></td>
                            <td>${s.score !== null ? `<strong>${s.score}</strong>` : '-'}</td>
                            <td>${formatDate(s.submitted_at)}</td>
                            <td><button class="btn btn-sm btn-ghost" onclick="viewSubmissionDetail(${s.id})"><i class="fas fa-eye"></i> View</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
        }
    } finally { hideLoading(); }
}

async function viewSubmissionDetail(id) {
    showLoading();
    try {
        const sub = await apiFetch(`/submissions/${id}`);
        const card = document.getElementById('resultDetailCard');
        const detail = document.getElementById('resultDetail');
        detail.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
                <div>
                    <h3>Submission #${sub.id}</h3>
                    <p style="color:var(--text-muted)">Student: ${sub.student_name} | Quiz ID: ${sub.quiz_id}</p>
                </div>
                <div style="text-align:right">
                    <span class="badge badge-${sub.status}">${sub.status}</span>
                    <h2 style="color:${sub.score >= 60 ? 'var(--success)' : (sub.score !== null ? 'var(--danger)' : 'var(--text-main)')}; margin-top:5px;">
                        ${sub.score !== null ? sub.score + '%' : 'Pending'}
                    </h2>
                </div>
            </div>
            ${sub.answers ? `
                <h4>Answers Recorded:</h4>
                <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap:10px; margin-top:15px;">
                    ${sub.answers.map(a => `
                        <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:5px; border:1px solid var(--card-border)">
                            <div style="font-size:0.8rem; color:var(--text-muted)">Q ID: ${a.question_id}</div>
                            <div style="font-weight:bold; font-size:1.2rem; text-transform:uppercase;">${a.selected_answer}</div>
                        </div>
                    `).join('')}
                </div>
            ` : '<p>No answer details available.</p>'}
        `;
        card.style.display = 'block';
        card.scrollIntoView({behavior:'smooth'});
    } finally { hideLoading(); }
}

async function loadSystemStatus() {
    showLoading();
    try {
        try {
            const leaderData = await apiFetch('/leader');
            document.getElementById('leaderNodeId').innerText = leaderData.leader_id || 'Election...';
        } catch(e) { document.getElementById('leaderNodeId').innerText = 'Unknown'; }

        const nodesData = await apiFetch('/system/nodes');
        const nodes = nodesData.nodes || [];
        document.getElementById('totalNodes').innerText = nodes.length;
        document.getElementById('healthyNodes').innerText = nodes.filter(n => n.status === 'healthy').length;

        document.getElementById('nodeHealthList').innerHTML = `<table>
            <thead><tr><th>Node ID</th><th>Host</th><th>Port</th><th>Status</th></tr></thead>
            <tbody>
                ${nodes.map(n => `
                    <tr>
                        <td>Node <strong>${n.id}</strong></td>
                        <td>${n.host}</td>
                        <td>${n.port}</td>
                        <td>${n.status === 'healthy' ? `<span class="badge badge-graded"><i class="fas fa-check"></i> Online</span>` : `<span class="badge badge-pending" style="color:var(--danger); border-color:var(--danger)"><i class="fas fa-times"></i> Offline</span>`}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
    } finally { hideLoading(); }
}

async function triggerElection() {
    showLoading();
    try {
        await apiFetch('/leader/election', { method: 'POST' });
        showToast('Election triggered across the cluster', 'success');
        setTimeout(loadSystemStatus, 2000);
    } finally { hideLoading(); }
}

document.addEventListener('DOMContentLoaded', () => {
    switchTab('dashboard');
    pollIntervals.dashboard = setInterval(() => {
        if(document.getElementById('page-dashboard').classList.contains('active')) loadDashboard();
        if(document.getElementById('page-system').classList.contains('active')) loadSystemStatus();
    }, 10000);

    document.getElementById('menuToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.add('open');
    });
    document.getElementById('sidebarClose').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('open');
    });
});
