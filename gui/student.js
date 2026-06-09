const API_BASE = '/api';
let pollIntervals = {};
let currentQuizData = null;
let currentAnswers = {};

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

function getStudentId() {
    return document.getElementById('globalStudentId').value || 'student1';
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

    if(tabId === 'take-quiz') {
        document.getElementById('quizSelection').style.display = 'block';
        document.getElementById('quizTakingArea').style.display = 'none';
        loadAvailableQuizzes();
    }
    else if(tabId === 'results') loadMySubmissions();
    else if(tabId === 'notifications') loadNotifications();
}

async function loadAvailableQuizzes() {
    showLoading();
    try {
        const quizzes = await apiFetch('/quizzes');
        const container = document.getElementById('availableQuizzes');
        if(quizzes.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-clipboard-list"></i><p>No quizzes available</p></div>`;
        } else {
            container.innerHTML = `<div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));">
                ${quizzes.map(q => `
                    <div class="card" style="margin-bottom:0; cursor:pointer;" onclick="startQuiz(${q.id})">
                        <div class="card-body">
                            <h3 style="margin-bottom:10px; color:var(--primary)">${q.title}</h3>
                            <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:15px;">${q.description || 'No description'}</p>
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem;">
                                <span><i class="fas fa-clock"></i> ${q.time_limit_minutes} min</span>
                                <span class="badge badge-info" style="color:var(--text-main); background:var(--primary-gradient); border:none;">Take Quiz <i class="fas fa-arrow-right"></i></span>
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

async function loadMySubmissions() {
    showLoading();
    try {
        const studentId = getStudentId();
        const [subsData, notifsData] = await Promise.all([
            apiFetch('/submissions'),
            apiFetch('/notifications').catch(()=>[])
        ]);
        const subs = subsData.filter(s => s.student_name === studentId);
        const notifs = notifsData.filter(n => n.student_name === studentId);

        const container = document.getElementById('resultsList');
        if(subs.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-chart-pie"></i><p>You haven't submitted any quizzes yet</p></div>`;
        } else {
            container.innerHTML = `<table>
                <thead><tr><th>ID</th><th>Quiz ID</th><th>Status</th><th>Score</th><th>Date</th><th>Action</th></tr></thead>
                <tbody>
                    ${subs.map(s => {
                        const hasNotif = notifs.some(n => n.submission_id === s.id);
                        return `
                        <tr>
                            <td>#${s.id}</td>
                            <td>${s.quiz_id}</td>
                            <td><span class="badge badge-${s.status}">${s.status.toUpperCase()}</span></td>
                            <td>${(s.score !== null && hasNotif) ? `<strong>${s.score}</strong>` : (s.score !== null ? `<span style="font-size:0.8em; color:var(--text-muted)">Waiting for notification...</span>` : '-')}</td>
                            <td>${formatDate(s.submitted_at)}</td>
                            <td><button class="btn btn-sm btn-ghost" onclick="viewSubmissionDetail(${s.id}, ${hasNotif})"><i class="fas fa-eye"></i> View</button></td>
                        </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>`;
        }
    } finally { hideLoading(); }
}

async function viewSubmissionDetail(id, hasNotif = true) {
    showLoading();
    try {
        const sub = await apiFetch(`/submissions/${id}`);
        const card = document.getElementById('resultDetailCard');
        const detail = document.getElementById('resultDetail');
        detail.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
                <div>
                    <h3>Submission #${sub.id}</h3>
                    <p style="color:var(--text-muted)">Quiz ID: ${sub.quiz_id}</p>
                </div>
                <div style="text-align:right">
                    <span class="badge badge-${sub.status}">${sub.status}</span>
                    <h2 style="color:${(sub.score >= 60 && hasNotif) ? 'var(--success)' : ((sub.score !== null && hasNotif) ? 'var(--danger)' : 'var(--text-main)')}; margin-top:5px;">
                        ${(sub.score !== null && hasNotif) ? sub.score + '%' : (sub.score !== null ? 'Check Notifications' : 'Pending')}
                    </h2>
                </div>
            </div>
            ${sub.answers ? `
                <h4>Your Answers:</h4>
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
        const studentId = getStudentId();
        const notifsData = await apiFetch('/notifications');
        const notifs = notifsData.filter(n => n.student_name === studentId);

        const unreadCount = notifs.filter(n => !n.is_read).length;
        const badge = document.getElementById('notifBadge');
        if(unreadCount > 0) {
            badge.style.display = 'inline-block';
            badge.innerText = unreadCount;
        } else {
            badge.style.display = 'none';
        }

        const container = document.getElementById('notificationsList');
        if(notifs.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-bell-slash"></i><p>No notifications</p></div>`;
        } else {
            notifs.sort((a,b) => new Date(b.created_at) - new Date(a.created_at));
            container.innerHTML = notifs.map(n => `
                <div class="notification-item ${n.is_read ? '' : 'unread'}">
                    <div class="notification-content">
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:5px;">
                            <span class="badge badge-info">${n.notification_type}</span>
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

document.addEventListener('DOMContentLoaded', () => {
    switchTab('take-quiz');

    document.getElementById('globalStudentId').addEventListener('change', () => {
        showToast('Changed active student ID');
        if(document.getElementById('page-results').classList.contains('active')) loadMySubmissions();
        loadNotifications();
    });

    pollIntervals.notifications = setInterval(loadNotifications, 10000);

    document.getElementById('menuToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.add('open');
    });
    document.getElementById('sidebarClose').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('open');
    });
});
