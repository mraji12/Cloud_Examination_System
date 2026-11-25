// CloudExam Online Examination Interface JavaScript
(function () {
    'use strict';

    // DOM Elements
    const examDataEl = document.getElementById('examData');
    if (!examDataEl) return;

    const attemptId = parseInt(examDataEl.dataset.attemptId, 10);
    let remainingSeconds = parseInt(examDataEl.dataset.remainingSeconds, 10);
    const csrfToken = examDataEl.dataset.csrfToken;
    const saveUrl = examDataEl.dataset.saveUrl;
    const syncUrl = examDataEl.dataset.syncUrl;
    const submitUrl = examDataEl.dataset.submitUrl;

    const timerDisplay = document.getElementById('timerDisplay');
    const questionContainers = document.querySelectorAll('.question-block');
    const navButtons = document.querySelectorAll('.question-nav-btn');
    const prevBtn = document.getElementById('prevQuestionBtn');
    const nextBtn = document.getElementById('nextQuestionBtn');
    const answeredCountEl = document.getElementById('answeredCount');
    const unansweredCountEl = document.getElementById('unansweredCount');
    const submitBtn = document.getElementById('openSubmitModalBtn');
    const confirmSubmitForm = document.getElementById('confirmSubmitForm');

    let currentQuestionIndex = 0;
    const totalQuestions = questionContainers.length;

    // Track answers locally
    const answers = {};

    // Initialize answers from data attributes
    questionContainers.forEach((block, idx) => {
        const qId = block.dataset.questionId;
        const selected = block.dataset.selectedAnswer;
        if (selected && selected.trim() !== '') {
            answers[qId] = selected.trim();
        }
    });

    function updateQuestionView(index) {
        if (index < 0 || index >= totalQuestions) return;
        currentQuestionIndex = index;

        questionContainers.forEach((block, idx) => {
            if (idx === index) {
                block.classList.remove('d-none');
            } else {
                block.classList.add('d-none');
            }
        });

        navButtons.forEach((btn, idx) => {
            if (idx === index) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update Prev / Next button state
        if (prevBtn) prevBtn.disabled = (index === 0);
        if (nextBtn) {
            if (index === totalQuestions - 1) {
                nextBtn.innerHTML = 'Review All <i class="bi bi-check2-circle ms-1"></i>';
            } else {
                nextBtn.innerHTML = 'Next Question <i class="bi bi-arrow-right ms-1"></i>';
            }
        }
    }

    function updateNavButtonState(questionId, isAnswered) {
        const btn = document.querySelector(`.question-nav-btn[data-question-id="${questionId}"]`);
        if (btn) {
            if (isAnswered) {
                btn.classList.add('answered');
            } else {
                btn.classList.remove('answered');
            }
        }
        updateStats();
    }

    function updateStats() {
        let answered = 0;
        for (const qId in answers) {
            if (answers[qId] && answers[qId].trim() !== '') {
                answered++;
            }
        }
        const unanswered = totalQuestions - answered;

        if (answeredCountEl) answeredCountEl.textContent = answered;
        if (unansweredCountEl) unansweredCountEl.textContent = unanswered;

        // Modal counters
        const modalAnswered = document.getElementById('modalAnsweredCount');
        const modalUnanswered = document.getElementById('modalUnansweredCount');
        if (modalAnswered) modalAnswered.textContent = answered;
        if (modalUnanswered) modalUnanswered.textContent = unanswered;
    }

    // Handle Option Selection
    document.querySelectorAll('.option-card').forEach(card => {
        card.addEventListener('click', function () {
            const questionBlock = this.closest('.question-block');
            const questionId = questionBlock.dataset.questionId;
            const optionValue = this.dataset.option;

            // Deselect other options in this question
            questionBlock.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));

            // Toggle / Select this option
            this.classList.add('selected');
            answers[questionId] = optionValue;
            questionBlock.dataset.selectedAnswer = optionValue;

            updateNavButtonState(questionId, true);

            // Save to backend asynchronously
            saveAnswerToBackend(questionId, optionValue);
        });
    });

    // Handle Clear Option
    document.querySelectorAll('.clear-option-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const questionBlock = this.closest('.question-block');
            const questionId = questionBlock.dataset.questionId;

            questionBlock.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
            delete answers[questionId];
            questionBlock.dataset.selectedAnswer = '';

            updateNavButtonState(questionId, false);
            saveAnswerToBackend(questionId, null);
        });
    });

    function saveAnswerToBackend(questionId, selectedAnswer) {
        fetch(saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                question_id: questionId,
                selected_answer: selectedAnswer
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.expired) {
                alert('Time has expired! The examination is being submitted automatically.');
                window.location.href = data.redirect_url;
            }
        })
        .catch(err => {
            console.error('Error auto-saving answer:', err);
        });
    }

    // Navigation buttons
    navButtons.forEach((btn, idx) => {
        btn.addEventListener('click', function () {
            updateQuestionView(idx);
        });
    });

    if (prevBtn) {
        prevBtn.addEventListener('click', function () {
            if (currentQuestionIndex > 0) {
                updateQuestionView(currentQuestionIndex - 1);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', function () {
            if (currentQuestionIndex < totalQuestions - 1) {
                updateQuestionView(currentQuestionIndex + 1);
            } else {
                // At the last question, trigger modal confirmation
                const submitModal = new bootstrap.Modal(document.getElementById('submitConfirmModal'));
                submitModal.show();
            }
        });
    }

    // Countdown Timer
    function formatTime(totalSec) {
        const m = Math.floor(totalSec / 60);
        const s = totalSec % 60;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function tickTimer() {
        if (remainingSeconds <= 0) {
            timerDisplay.textContent = '00:00';
            timerDisplay.parentElement.classList.add('timer-warning');
            clearInterval(timerInterval);
            autoSubmitOnTimeout();
            return;
        }

        remainingSeconds--;
        timerDisplay.textContent = formatTime(remainingSeconds);

        if (remainingSeconds < 300) { // Less than 5 mins
            timerDisplay.parentElement.classList.add('timer-warning');
        }
    }

    function autoSubmitOnTimeout() {
        alert('Examination deadline reached. Automatically submitting your answers now.');
        if (confirmSubmitForm) {
            confirmSubmitForm.submit();
        }
    }

    const timerInterval = setInterval(tickTimer, 1000);
    tickTimer();

    // Server-Authoritative Sync every 30 seconds
    setInterval(() => {
        fetch(syncUrl, {
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.expired) {
                clearInterval(timerInterval);
                autoSubmitOnTimeout();
            } else if (typeof data.remaining_seconds === 'number') {
                remainingSeconds = data.remaining_seconds;
            }
        })
        .catch(err => console.warn('Sync ping failed:', err));
    }, 30000);

    // Initial setup
    updateQuestionView(0);
    updateStats();
})();
