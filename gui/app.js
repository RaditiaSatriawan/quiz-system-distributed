const API_BASE = '/api';
let pollIntervals = {};
let currentQuizData = null;
let currentAnswers = {};

function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'info-circle';
    if(type === 'success') icon = 'check-circle';
    if(type === 'error') icon = 'exclamation-circle';

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
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function getStudentId() {
    return document.getElementById('globalStudentId').value || 'student1';
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

    if(window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }

    if(tabId === 'dashboard') loadDashboard();
    else if(tabId === 'quizzes') loadQuizzes();
    else if(tabId === 'take-quiz') {
        document.getElementById('quizSelection').style.display = 'block';
        document.getElementById('quizTakingArea').style.display = 'none';
        loadAvailableQuizzes();
    }
    else if(tabId === 'results') loadSubmissions();
    else if(tabId === 'notifications') loadNotifications();
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

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
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

async function loadDashboard() {
    try {
        const [quizzes, submissions, notifs, nodes] = await Promise.all([
            apiFetch('/quizzes').catch(() => []),
            apiFetch('/submissions').catch(() => []),
            apiFetch('/notifications').catch(() => []),
            apiFetch('/system/nodes').catch(() => ({nodes:[]}))
        ]);

        const qCount = document.querySelector('#statQuizzes .stat-number');
        animateValue(qCount, 0, quizzes.length || 0, 1000);

        const sCount = document.querySelector('#statSubmissions .stat-number');
        animateValue(sCount, 0, submissions.length || 0, 1000);

        let passRate = 0;
        const graded = submissions.filter(s => s.status === 'graded');
        if(graded.length > 0) {
            const passed = graded.filter(s => parseFloat(s.score) >= 60).length;
            passRate = Math.round((passed / graded.length) * 100);
        }
        document.querySelector('#statPassRate .stat-number').innerHTML = `${passRate}<span class="stat-unit">%</span>`;

        const unreadCount = notifs.filter(n => !n.is_read).length;
        document.querySelector('#statNotifications .stat-number').innerText = unreadCount;

        const badge = document.getElementById('notifBadge');
        if(unreadCount > 0) {
            badge.style.display = 'inline-block';
            badge.innerText = unreadCount;
        } else {
            badge.style.display = 'none';
        }

        const recentDiv = document.getElementById('recentActivity');
        if(submissions.length === 0) {
            recentDiv.innerHTML = `<div class="empty-state"><i class="fas fa-inbox"></i><p>No recent activity</p></div>`;
        } else {
            const recentHTML = submissions.slice(0, 5).map(s => `
                <div class="notification-item">
                    <div class="notification-content">
                        <p><strong>${s.student_name}</strong> submitted Quiz #${s.quiz_id}</p>
                        <span class="notification-time">${formatDate(s.submitted_at)}</span>
                    </div>
                    <span class="badge badge-${s.status}">${s.status}</span>
                </div>
            `).join('');
            recentDiv.innerHTML = recentHTML;
        }

        const clusterDiv = document.getElementById('clusterOverview');
        const totalNodes = nodes.nodes ? nodes.nodes.length : 0;
        const healthy = nodes.nodes ? nodes.nodes.filter(n => n.healthy).length : 0;
        clusterDiv.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <span>Total Nodes</span>
                <strong>${totalNodes}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>Healthy Nodes</span>
                <strong style="color:var(--success)">${healthy}</strong>
            </div>
        `;

    } catch(e) {

    }
}

async function loadQuizzes() {
    showLoading();
    try {
        const quizzes = await apiFetch('/quizzes');
        const container = document.getElementById('quizzesList');
        if(quizzes.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-book-open"></i><p>No quizzes yet</p></div>`;
        } else {
            container.innerHTML = `<table class="table">
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
    for(let i=0; i<correctRadios.length; i++){
        if(correctRadios[i].checked) {
            correctLetter = ['a','b','c','d'][i];
            break;
        }
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
    } catch(e) {
        showToast('Failed to load questions', 'error');
    } finally { hideLoading(); }
}

async function loadAvailableQuizzes() {
    showLoading();
    try {
        const quizzes = await apiFetch('/quizzes');
        const container = document.getElementById('availableQuizzes');
        if(quizzes.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-clipboard-list"></i><p>No quizzes available</p></div>`;
        } else {
            container.innerHTML = `<div class="stats-grid">
                ${quizzes.map(q => `
                    <div class="card" style="margin-bottom:0; cursor:pointer;" onclick="startQuiz(${q.id})">
                        <div class="card-body">
                            <h3 style="margin-bottom:10px; color:var(--primary)">${q.title}</h3>
                            <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:15px;">${q.description || 'No description'}</p>
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem;">
                                <span><i class="fas fa-clock"></i> ${q.time_limit_minutes} min</span>
                                <span class="badge badge-info">Take Quiz <i class="fas fa-arrow-right"></i></span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>`;
        }
    } finally { hideLoading(); }
}

async function startQuiz(id) {
    showLoading();
    try {
        const quiz = await apiFetch(`/quizzes/${id}`);
        if(!quiz.questions || quiz.questions.length === 0) {
            showToast('This quiz has no questions yet.', 'error');
            return;
        }
        currentQuizData = quiz;
        currentAnswers = {};

        document.getElementById('quizSelection').style.display = 'none';
        document.getElementById('quizTakingArea').style.display = 'block';
        document.getElementById('quizTakingTitle').innerText = quiz.title;
        document.getElementById('quizQuestionCount').innerText = `${quiz.questions.length} Questions`;

        renderQuizQuestions();
    } catch(e) {
    } finally { hideLoading(); }
}

function renderQuizQuestions() {
    const container = document.getElementById('quizQuestionsContainer');
    container.innerHTML = currentQuizData.questions.map((q, idx) => `
        <div class="question-card">
            <div class="question-text">
                <span style="color:var(--primary); margin-right:10px;">${idx+1}.</span> ${q.question_text}
                <span style="float:right; font-size:0.8rem; color:var(--text-muted)">${q.points} pts</span>
            </div>
            <div class="answers-grid">
                <label class="answer-option" onclick="selectAnswer(${q.id}, 'a', this)">
                    <input type="radio" name="q_${q.id}" value="a">
                    <span>${q.option_a}</span>
                </label>
                <label class="answer-option" onclick="selectAnswer(${q.id}, 'b', this)">
                    <input type="radio" name="q_${q.id}" value="b">
                    <span>${q.option_b}</span>
                </label>
                <label class="answer-option" onclick="selectAnswer(${q.id}, 'c', this)">
                    <input type="radio" name="q_${q.id}" value="c">
                    <span>${q.option_c}</span>
                </label>
                <label class="answer-option" onclick="selectAnswer(${q.id}, 'd', this)">
                    <input type="radio" name="q_${q.id}" value="d">
                    <span>${q.option_d}</span>
                </label>
            </div>
        </div>
    `).join('');
}

function selectAnswer(questionId, optionLetter, el) {

    currentAnswers[questionId] = optionLetter;

    const grid = el.parentElement;
    grid.querySelectorAll('.answer-option').forEach(opt => opt.classList.remove('selected'));
    el.classList.add('selected');
}

function cancelQuiz() {
    if(confirm('Abandon quiz? Your progress will be lost.')) {
        document.getElementById('quizSelection').style.display = 'block';
        document.getElementById('quizTakingArea').style.display = 'none';
    }
}

async function submitQuiz() {
    if(Object.keys(currentAnswers).length < currentQuizData.questions.length) {
        if(!confirm('You have unanswered questions. Submit anyway?')) return;
    }

    const payload = {
        student_name: getStudentId(),
        quiz_id: currentQuizData.id,
        answers: Object.keys(currentAnswers).map(qid => ({
            question_id: parseInt(qid),
            selected_answer: currentAnswers[qid]
        }))
    };

    showLoading();
    try {
        await apiFetch('/submissions', { method: 'POST', body: JSON.stringify(payload) });
        showToast('Quiz submitted for grading! You will receive a notification soon.', 'success');
        document.getElementById('quizSelection').style.display = 'block';
        document.getElementById('quizTakingArea').style.display = 'none';

        setTimeout(loadNotifications, 2000);
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
                            <td>
                                <button class="btn btn-sm btn-ghost" onclick="viewSubmissionDetail(${s.id})">
                                    <i class="fas fa-eye"></i> View
                                </button>
                            </td>
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

async function loadNotifications() {
    try {
        const notifs = await apiFetch('/notifications');
        const container = document.getElementById('notificationsList');

        const unreadCount = notifs.filter(n => !n.is_read).length;
        const badge = document.getElementById('notifBadge');
        if(unreadCount > 0) {
            badge.style.display = 'inline-block';
            badge.innerText = unreadCount;
        } else {
            badge.style.display = 'none';
        }

        if(notifs.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-bell-slash"></i><p>No notifications</p></div>`;
        } else {

            notifs.sort((a,b) => new Date(b.created_at) - new Date(a.created_at));
            container.innerHTML = notifs.map(n => `
                <div class="notification-item ${n.is_read ? '' : 'unread'}">
                    <div class="notification-content">
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:5px;">
                            <span class="badge badge-info">${n.notification_type}</span>
                            <strong>${n.student_name}</strong>
                        </div>
                        <p>${n.message}</p>
                        <span class="notification-time">${formatDate(n.created_at)}</span>
                    </div>
                    ${!n.is_read ? `<button class="btn btn-sm btn-ghost" onclick="markAsRead(${n.id})" title="Mark Read"><i class="fas fa-check"></i></button>` : ''}
                </div>
            `).join('');
        }
    } catch(e) {}
}

async function markAsRead(id) {
    try {
        await apiFetch(`/notifications/${id}/read`, { method: 'PUT' });
        loadNotifications();
        showToast('Marked as read', 'success');
    } catch(e) {}
}

async function loadSystemStatus() {
    showLoading();
    try {

        try {
            const leaderData = await apiFetch('/leader');
            document.getElementById('leaderNodeId').innerText = leaderData.leader_id || 'Election in progress';
        } catch(e) {
            document.getElementById('leaderNodeId').innerText = 'Unknown';
        }

        const nodesData = await apiFetch('/system/nodes');
        const nodes = nodesData.nodes || [];

        document.getElementById('totalNodes').innerText = nodes.length;
        document.getElementById('healthyNodes').innerText = nodes.filter(n => n.healthy).length;

        const container = document.getElementById('nodeHealthList');
        container.innerHTML = `<table>
            <thead><tr><th>Node ID</th><th>Host</th><th>Port</th><th>Status</th></tr></thead>
            <tbody>
                ${nodes.map(n => `
                    <tr>
                        <td>Node <strong>${n.id}</strong></td>
                        <td>${n.host}</td>
                        <td>${n.port}</td>
                        <td>
                            ${n.healthy 
                                ? `<span class="badge badge-graded"><i class="fas fa-check"></i> Online</span>` 
                                : `<span class="badge badge-pending" style="color:var(--danger); border-color:var(--danger)"><i class="fas fa-times"></i> Offline</span>`
                            }
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;

    } catch(e) {
        showToast('Failed to load system status', 'error');
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
        if(document.getElementById('page-dashboard').classList.contains('active')) {
            loadDashboard();
        }
    }, 10000);

    pollIntervals.notifications = setInterval(loadNotifications, 15000);

    document.getElementById('menuToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.add('open');
    });
    document.getElementById('sidebarClose').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('open');
    });
});
