/**
 * static/js/app.js - Full-Featured Decoupled State Manager & API Client for Cognify
 * Expo.dev / Vercel Ultra-Clean Editorial Dark Architecture
 * Orchestrates 3D Flashcards, Audio Tutor, Multi-View Telemetry, Anki/Markdown Exports,
 * Spaced Repetition, and Interactive Active-Recall Quizzing.
 */

// -------------------------------------------------------------
// 1. High-Yield Academic Presets
// -------------------------------------------------------------
const ACADEMIC_PRESETS = {
  calculus: {
    subject: "STEM / Calculus",
    notes: `Multivariable Calculus & Gradient Descent:
Directional derivatives quantify instantaneous scalar field variation along arbitrary unit vectors: D_u f = ∇f · u = |∇f| cos(θ).
The gradient vector ∇f always points in the direction of steepest rate of ascent, with magnitude equal to that rate of increase.
The Hessian matrix captures second-order partial derivatives and local curvature. A negative Hessian determinant signals a saddle point.
Level curves are strictly orthogonal to the gradient vector at every point.
Gradient descent updates parameters iteratively via: θ_new = θ_old - α ∇f(θ_old), scaling steps by the learning rate α to reach local minima.`
  },
  biology: {
    subject: "Molecular Biology",
    notes: `CRISPR-Cas9 Gene Editing Mechanisms:
CRISPR-Cas9 acts as an RNA-guided programmable endonuclease.
Binding strictly requires interrogating a 5'-NGG-3' Protospacer Adjacent Motif (PAM) sequence before strand unwinding.
Single guide RNA (sgRNA) contains a 20-nucleotide spacer complementary to the target sequence.
Cas9 creates double-strand breaks via HNH and RuvC endonuclease domains.
Cellular repair follows two primary pathways:
1. Non-Homologous End Joining (NHEJ): error-prone end ligation introducing insertion/deletion (indel) frameshifts.
2. Homology-Directed Repair (HDR): precise donor-template repair active during S and G2 phases.`
  },
  cs: {
    subject: "Computer Science",
    notes: `Transformer Attention & KV-Caching Architecture:
Transformers replace recurrence with Scaled Dot-Product Attention: Attention(Q,K,V) = softmax(QKᵀ / √d_k) V.
Scaling by √d_k mitigates extreme inner product magnitudes that push softmax into regions with vanishing gradients.
Standard self-attention incurs quadratic O(N²) computational complexity with sequence length N.
Autoregressive decoding maintains a Key-Value (KV) cache to avoid redundant re-computation of past token projections.
Grouped-Query Attention (GQA) groups query heads across shared KV heads, drastically lowering GPU memory bandwidth pressure during inference.`
  },
  history: {
    subject: "World History",
    notes: `Cold War Geopolitics & Nuclear Deterrence:
The post-WWII geopolitical landscape was defined by bipolar ideological rivalry between the United States and the Soviet Union.
George F. Kennan's Long Telegram formulated the Containment doctrine, executed through the Truman Doctrine and Marshall Plan.
The principle of Mutually Assured Destruction (MAD) underpinned strategic nuclear deterrence through a secure second-strike triad.
Key flashpoints included the Berlin Blockade (1948), the Cuban Missile Crisis (1962), and proxy wars in Korea and Vietnam.
Strategic Arms Limitation Talks (SALT I & II) and the INF Treaty marked pivotal de-escalation milestones.`
  }
};


// -------------------------------------------------------------
// 2. Centralized State Store
// -------------------------------------------------------------
const AppState = {
  currentSession: null,
  recentSessionsCache: [],
  activeTab: "tab-concepts",
  chartViewMode: "mastery", // 'mastery' or 'diagnostics'
  customApiKey: localStorage.getItem("cognify_api_key") || "",
  
  // Interactive Quiz State
  quiz: {
    questions: [],
    currentIndex: 0,
    selectedOption: null,
    isGraded: false,
    scoreCount: 0,
    answersLog: [],
    timerSeconds: 0,
    timerInterval: null
  },

  // 3D Flip Flashcards State
  flashcards: {
    cards: [],
    currentIndex: 0,
    isFlipped: false
  },

  // Audio Tutor Synthesizer
  speech: {
    isSpeaking: false,
    synth: window.speechSynthesis || null,
    currentUtterance: null
  }
};


// -------------------------------------------------------------
// 3. Decoupled REST API Client
// -------------------------------------------------------------
const ApiClient = {
  async getDashboard() {
    const res = await fetch("/api/dashboard");
    if (!res.ok) throw new Error("Failed to load dashboard data.");
    return await res.json();
  },

  async generateStudyPack(notes, subjectHint, demoMode = false) {
    const headers = { "Content-Type": "application/json" };
    if (AppState.customApiKey) {
      headers["X-Gemini-API-Key"] = AppState.customApiKey;
    }

    const payload = {
      notes,
      subject_hint: subjectHint,
      demo_mode: demoMode,
      api_key: AppState.customApiKey || undefined
    };

    const res = await fetch("/api/generate", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Failed to generate study pack.");
    return data;
  },

  async getSession(sessionId) {
    const res = await fetch(`/api/session/${sessionId}`);
    if (!res.ok) throw new Error(`Failed to load session #${sessionId}`);
    return await res.json();
  },

  async deleteSession(sessionId) {
    const res = await fetch(`/api/session/${sessionId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Failed to delete session.");
    return data;
  },

  async submitQuiz(sessionId, subjectCategory, scorePct, timeSpentSec, weakSubtopics) {
    const res = await fetch("/api/submit_quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        subject_category: subjectCategory,
        score_pct: scorePct,
        time_spent_sec: timeSpentSec,
        weak_subtopics: weakSubtopics
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Failed to submit quiz attempt.");
    return data;
  },

  async logFlashcardReview(sessionId, cardIndex, rating) {
    const res = await fetch("/api/flashcard/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        card_index: cardIndex,
        rating: rating
      })
    });
    return await res.json();
  },

  async resetDemo() {
    const res = await fetch("/api/reset_demo", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Failed to reset demo data.");
    return data;
  }
};


// -------------------------------------------------------------
// 4. UI View Controllers & Renderers
// -------------------------------------------------------------

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  
  let iconSvg = `
    <svg width="16" height="16" class="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>`;
  
  if (type === "success") {
    iconSvg = `
      <svg width="16" height="16" class="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
      </svg>`;
  } else if (type === "error") {
    iconSvg = `
      <svg width="16" height="16" class="w-4 h-4 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
      </svg>`;
  }

  toast.innerHTML = `${iconSvg}<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.2s ease";
    setTimeout(() => toast.remove(), 200);
  }, 3200);
}

function updateAIModeBadge(aiStatus) {
  const badgeText = document.getElementById("ai-mode-text");
  const badge = document.getElementById("ai-mode-badge");
  if (!badgeText || !badge) return;

  if (AppState.customApiKey) {
    badgeText.textContent = "Custom Gemini API Key Active";
    badge.className = "hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-cyan-950/70 border border-cyan-500/50 text-cyan-200 shadow-inner";
  } else if (aiStatus && aiStatus.has_api_key) {
    badgeText.textContent = aiStatus.badge_label;
    badge.className = "hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-emerald-950/70 border border-emerald-500/50 text-emerald-200 shadow-inner";
  } else {
    badgeText.textContent = "Zero-Config Mode";
    badge.className = "hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-zinc-950 border border-white/10 text-zinc-300";
  }
}

function renderDashboardKPIs(kpis) {
  if (!kpis) return;
  document.getElementById("kpi-total-sessions").textContent = kpis.total_sessions ?? 0;
  document.getElementById("kpi-avg-mastery").textContent = `${kpis.avg_mastery_pct ?? 0}%`;
  document.getElementById("kpi-total-quizzes").textContent = kpis.total_quizzes_taken ?? 0;
  document.getElementById("kpi-top-weak-spot").textContent = kpis.top_weak_spot ?? "None Detected";
}

function renderHistorySessions(sessions) {
  AppState.recentSessionsCache = sessions || [];
  filterHistorySessions("");
}

function filterHistorySessions(query) {
  const container = document.getElementById("sessions-history-list");
  const countTag = document.getElementById("session-count-tag");
  if (!container) return;

  const normalized = (query || "").toLowerCase().trim();
  const filtered = AppState.recentSessionsCache.filter(s => {
    if (!normalized) return true;
    return (s.topic_title || "").toLowerCase().includes(normalized) ||
           (s.subject_category || "").toLowerCase().includes(normalized);
  });

  countTag.textContent = `${filtered.length} Saved`;

  if (!filtered || filtered.length === 0) {
    container.innerHTML = `<div class="text-center py-6 text-xs text-slate-500 font-mono">No matching modules found.</div>`;
    return;
  }

  container.innerHTML = filtered.map(s => {
    const isActive = AppState.currentSession && AppState.currentSession.session_id === s.id;
    return `
      <div class="history-item history-session-item ${isActive ? 'active' : ''} group" data-session-id="${s.id}">
        <div class="flex items-center justify-between text-[11px] mb-1">
          <span class="font-mono text-cyan-400 font-semibold">${s.subject_category || 'General'}</span>
          <div class="flex items-center gap-2">
            <span class="font-mono text-slate-500">${s.created_at ? s.created_at.substring(5, 16) : ''}</span>
            <button class="delete-btn btn-delete-session p-1 text-slate-500 hover:text-rose-400 rounded transition" data-delete-id="${s.id}" title="Delete session">
              <svg width="14" height="14" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
        <div class="text-xs font-medium text-slate-200 truncate">${s.topic_title}</div>
      </div>
    `;
  }).join("");

  // Attach session load listeners
  container.querySelectorAll(".history-session-item, .history-item").forEach(item => {
    item.addEventListener("click", (e) => {
      if (e.target.closest(".btn-delete-session, .delete-btn")) return;
      const sid = parseInt(item.getAttribute("data-session-id"), 10);
      loadSessionById(sid);
    });
  });

  // Attach delete listeners
  container.querySelectorAll(".btn-delete-session, .delete-btn").forEach(delBtn => {
    delBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const sid = parseInt(delBtn.getAttribute("data-delete-id"), 10);
      if (confirm(`Delete study session #${sid}?`)) {
        try {
          await ApiClient.deleteSession(sid);
          showToast(`Session #${sid} deleted.`, "info");
          const dash = await ApiClient.getDashboard();
          renderHistorySessions(dash.recent_sessions || []);
          renderDashboardKPIs(dash.kpis);
        } catch (err) {
          showToast(err.message, "error");
        }
      }
    });
  });
}

function refreshTelemetryChart() {
  const chartImg = document.getElementById("telemetry-chart-img");
  const overlay = document.getElementById("chart-loading-overlay");
  if (!chartImg) return;

  if (overlay) overlay.classList.remove("hidden");
  
  const timestamp = new Date().getTime();
  const freshUrl = `/api/analytics.png?view=${AppState.chartViewMode}&t=${timestamp}`;
  
  const tempImg = new Image();
  tempImg.onload = () => {
    chartImg.src = freshUrl;
    if (overlay) overlay.classList.add("hidden");
  };
  tempImg.onerror = () => {
    if (overlay) overlay.classList.add("hidden");
  };
  tempImg.src = freshUrl;
}

function renderStudyPack(pack) {
  if (!pack) return;
  AppState.currentSession = pack;

  // Header Details
  document.getElementById("session-topic-title").textContent = pack.topic_title || "Untitled Topic";
  document.getElementById("session-subject-tag").textContent = pack.subject_category || "General Academic";
  document.getElementById("session-summary-text").textContent = pack.executive_summary || "";
  document.getElementById("session-difficulty-badge").textContent = `Diff: ${pack.difficulty_rating || 7}/10`;

  // Update Export Links
  if (pack.session_id) {
    document.getElementById("btn-export-markdown").href = `/api/export/${pack.session_id}/markdown`;
    document.getElementById("btn-export-anki").href = `/api/export/${pack.session_id}/anki`;
  }

  // Concepts, Formulas, Misconceptions
  renderConcepts(pack.key_concepts || []);
  renderFormulas(pack.formula_sheet || []);
  renderMisconceptions(pack.common_misconceptions || []);

  // Flashcards
  initFlashcards(pack.flashcards || []);

  // Roadmap
  renderRoadmap(pack.study_roadmap || []);

  // Initialize Quiz
  initQuiz(pack.quiz_questions || []);

  // Update history active highlights
  document.querySelectorAll(".history-session-item, .history-item").forEach(el => {
    const sid = parseInt(el.getAttribute("data-session-id"), 10);
    el.classList.toggle("active", sid === pack.session_id);
  });

  // Re-bind spotlight cursor and scroll animations for newly injected cards
  setTimeout(() => {
    initSpotlightCards();
    initScrollObserver();
  }, 50);
}

function renderConcepts(concepts) {
  const container = document.getElementById("concepts-container");
  if (!container) return;

  if (!concepts || concepts.length === 0) {
    container.innerHTML = `<div class="text-slate-500 text-xs py-4">No key concepts defined.</div>`;
    return;
  }

  container.innerHTML = concepts.map(c => `
    <div class="concept-item-card clean-card">
      <div class="flex items-center justify-between mb-1.5">
        <h4 class="text-sm font-spaceGrotesk font-bold text-white tracking-wide">${c.term}</h4>
      </div>
      <p class="text-xs text-slate-300 leading-relaxed font-sans">${c.definition}</p>
      ${c.exam_tip ? `
        <div class="tip-pill exam-tip-badge">
          <svg width="14" height="14" class="w-3.5 h-3.5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          </svg>
          <span><strong>Exam Tip:</strong> ${c.exam_tip}</span>
        </div>
      ` : ''}
    </div>
  `).join("");
}

function renderFormulas(formulas) {
  const section = document.getElementById("formula-section");
  const container = document.getElementById("formula-container");
  if (!container || !section) return;

  if (!formulas || formulas.length === 0) {
    section.classList.add("hidden");
    return;
  }

  section.classList.remove("hidden");
  container.innerHTML = formulas.map(f => `
    <div class="clean-card p-4 flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold text-white">${f.name}</span>
        <button class="text-[11px] font-mono text-slate-400 hover:text-cyan-300 transition btn-copy-formula" data-formula="${encodeURIComponent(f.formula_or_rule)}">
          Copy
        </button>
      </div>
      <div class="bg-black/60 border border-white/10 px-3.5 py-2 rounded-xl font-mono text-xs text-cyan-300">
        <code>${f.formula_or_rule}</code>
      </div>
      <p class="text-[11px] text-slate-400 font-sans italic">${f.application_notes}</p>
    </div>
  `).join("");

  container.querySelectorAll(".btn-copy-formula").forEach(btn => {
    btn.addEventListener("click", () => {
      const formula = decodeURIComponent(btn.getAttribute("data-formula"));
      navigator.clipboard.writeText(formula);
      showToast("Formula copied to clipboard!", "success");
    });
  });
}

function renderMisconceptions(misconceptions) {
  const section = document.getElementById("misconceptions-section");
  const container = document.getElementById("misconceptions-container");
  if (!container || !section) return;

  if (!misconceptions || misconceptions.length === 0) {
    section.classList.add("hidden");
    return;
  }

  section.classList.remove("hidden");
  container.innerHTML = misconceptions.map(m => `
    <div class="clean-card p-4 border-rose-500/20 bg-rose-500/[0.02] flex flex-col gap-2">
      <div class="text-xs text-rose-300 font-semibold flex items-center gap-1.5">
        <span>❌ Common Trap:</span>
        <span class="font-normal text-slate-300">${m.myth}</span>
      </div>
      <div class="text-xs text-emerald-300 font-semibold flex items-center gap-1.5 mt-0.5">
        <span>✅ Academic Reality:</span>
        <span class="font-normal text-slate-200">${m.reality}</span>
      </div>
      <p class="text-[11px] text-slate-400 mt-1"><em>Why it matters:</em> ${m.why_it_matters}</p>
    </div>
  `).join("");
}

function renderRoadmap(roadmap) {
  const container = document.getElementById("roadmap-container");
  if (!container) return;

  if (!roadmap || roadmap.length === 0) {
    container.innerHTML = `<div class="text-slate-500 text-xs py-4">No roadmap steps formulated.</div>`;
    return;
  }

  container.innerHTML = roadmap.map((step, idx) => `
    <div class="clean-card p-5 flex items-start gap-4">
      <div class="w-8 h-8 rounded-xl bg-white/[0.05] border border-white/10 flex items-center justify-center text-xs font-mono font-bold text-cyan-400 shrink-0">
        0${idx + 1}
      </div>
      <div class="flex-1">
        <div class="flex items-center justify-between mb-1">
          <h4 class="text-sm font-semibold text-white">${step.step_title}</h4>
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-white/[0.04] text-cyan-300 border border-white/10">
            ~${step.estimated_minutes || 20} min
          </span>
        </div>
        <p class="text-xs text-slate-400 font-sans">
          Primary Focus: <strong class="text-slate-300 font-medium">${step.focus_area || 'Core Fundamentals'}</strong>
        </p>
      </div>
    </div>
  `).join("");
}


// -------------------------------------------------------------
// 5. 3D Flip Flashcards Engine
// -------------------------------------------------------------

function initFlashcards(cards) {
  const fcState = AppState.flashcards;
  fcState.cards = cards || [];
  fcState.currentIndex = 0;
  fcState.isFlipped = false;

  const countBadge = document.getElementById("flashcard-badge-count");
  if (countBadge) countBadge.textContent = `${fcState.cards.length}`;

  const totalIdxEl = document.getElementById("fc-total-idx");
  if (totalIdxEl) totalIdxEl.textContent = `${fcState.cards.length}`;

  renderCurrentFlashcard();
}

function renderCurrentFlashcard() {
  const fcState = AppState.flashcards;
  const card = fcState.cards[fcState.currentIndex];
  const cardElem = document.getElementById("flashcard-element");

  if (!card) {
    document.getElementById("fc-front-text").textContent = "No flashcards generated for this pack.";
    document.getElementById("fc-back-text").textContent = "Add notes to generate cards.";
    return;
  }

  fcState.isFlipped = false;
  if (cardElem) cardElem.classList.remove("flipped");

  document.getElementById("fc-current-idx").textContent = `${fcState.currentIndex + 1}`;
  document.getElementById("fc-front-text").textContent = card.front;
  document.getElementById("fc-back-text").textContent = card.back;

  const mnemBox = document.getElementById("fc-mnemonic-box");
  if (card.mnemonic) {
    mnemBox.classList.remove("hidden");
    mnemBox.textContent = `Mnemonic Anchor: ${card.mnemonic}`;
  } else {
    mnemBox.classList.add("hidden");
  }
}

function flipFlashcard() {
  const fcState = AppState.flashcards;
  fcState.isFlipped = !fcState.isFlipped;
  const cardElem = document.getElementById("flashcard-element");
  if (cardElem) {
    cardElem.classList.toggle("flipped", fcState.isFlipped);
  }
}


// -------------------------------------------------------------
// 6. Interactive Active-Recall Quiz Arena
// -------------------------------------------------------------

function initQuiz(questions) {
  AppState.quiz.questions = questions || [];
  AppState.quiz.currentIndex = 0;
  AppState.quiz.selectedOption = null;
  AppState.quiz.isGraded = false;
  AppState.quiz.scoreCount = 0;
  AppState.quiz.answersLog = [];
  AppState.quiz.timerSeconds = 0;

  if (AppState.quiz.timerInterval) {
    clearInterval(AppState.quiz.timerInterval);
  }

  AppState.quiz.timerInterval = setInterval(() => {
    AppState.quiz.timerSeconds++;
    const mins = String(Math.floor(AppState.quiz.timerSeconds / 60)).padStart(2, "0");
    const secs = String(AppState.quiz.timerSeconds % 60).padStart(2, "0");
    const timerEl = document.getElementById("quiz-timer");
    if (timerEl) timerEl.textContent = `${mins}:${secs}`;
  }, 1000);

  document.getElementById("quiz-badge-count").textContent = `${questions.length} Qs`;
  document.getElementById("quiz-total-idx").textContent = questions.length;
  document.getElementById("quiz-question-box").classList.remove("hidden");
  document.getElementById("quiz-results-card").classList.add("hidden");

  renderCurrentQuizQuestion();
}

function renderCurrentQuizQuestion() {
  const qState = AppState.quiz;
  const question = qState.questions[qState.currentIndex];
  if (!question) return;

  qState.selectedOption = null;
  qState.isGraded = false;

  document.getElementById("quiz-current-idx").textContent = qState.currentIndex + 1;
  const progressPct = ((qState.currentIndex + 1) / qState.questions.length) * 100;
  document.getElementById("quiz-progress-fill").style.width = `${progressPct}%`;
  document.getElementById("quiz-subtopic-tag").textContent = question.subtopic_tag || "Core Theory";

  document.getElementById("quiz-question-prompt").textContent = question.question;

  const optionsContainer = document.getElementById("quiz-options-container");
  const optionLetters = ["A", "B", "C", "D"];

  optionsContainer.innerHTML = question.options.map((opt, idx) => `
    <div class="quiz-choice-card quiz-option" data-option-idx="${idx}">
      <span class="choice-badge option-badge">${optionLetters[idx]}</span>
      <span class="text-xs sm:text-sm font-medium text-slate-200 flex-1">${opt}</span>
    </div>
  `).join("");

  optionsContainer.querySelectorAll(".quiz-choice-card, .quiz-option").forEach(el => {
    el.addEventListener("click", () => {
      if (qState.isGraded) return;
      const optIdx = parseInt(el.getAttribute("data-option-idx"), 10);
      handleOptionSelect(optIdx);
    });
  });

  const explBox = document.getElementById("quiz-explanation-box");
  explBox.classList.add("hidden");
  explBox.className = "hidden p-4 rounded-xl border text-sm leading-relaxed";

  const btnNext = document.getElementById("btn-next-question");
  btnNext.textContent = "Submit Answer";
  btnNext.disabled = true;
}

function handleOptionSelect(optionIdx) {
  AppState.quiz.selectedOption = optionIdx;

  document.querySelectorAll(".quiz-choice-card, .quiz-option").forEach(el => {
    const idx = parseInt(el.getAttribute("data-option-idx"), 10);
    el.classList.toggle("selected", idx === optionIdx);
  });

  document.getElementById("btn-next-question").disabled = false;
}

function handleGradeOrNext() {
  const qState = AppState.quiz;
  const question = qState.questions[qState.currentIndex];
  if (!question) return;

  const btnNext = document.getElementById("btn-next-question");

  if (!qState.isGraded) {
    qState.isGraded = true;
    const isCorrect = qState.selectedOption === question.correct_index;
    if (isCorrect) qState.scoreCount++;

    qState.answersLog.push({
      questionId: question.id,
      selectedIndex: qState.selectedOption,
      correctIndex: question.correct_index,
      isCorrect: isCorrect,
      subtopic: question.subtopic_tag
    });

    document.querySelectorAll(".quiz-choice-card, .quiz-option").forEach(el => {
      el.classList.add("disabled");
      const idx = parseInt(el.getAttribute("data-option-idx"), 10);
      if (idx === question.correct_index) {
        el.classList.add("correct");
      } else if (idx === qState.selectedOption && !isCorrect) {
        el.classList.add("incorrect");
      }
    });

    const explBox = document.getElementById("quiz-explanation-box");
    const statusDiv = document.getElementById("quiz-grade-status");
    const textP = document.getElementById("quiz-grade-explanation");

    explBox.classList.remove("hidden");
    if (isCorrect) {
      explBox.className = "p-4 rounded-2xl border text-sm leading-relaxed bg-emerald-950/40 border-emerald-500/40 text-emerald-200";
      statusDiv.innerHTML = `
        <svg width="16" height="16" class="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span class="text-emerald-300 font-bold">Correct! High-Yield Concept Verified</span>`;
    } else {
      explBox.className = "p-4 rounded-2xl border text-sm leading-relaxed bg-rose-950/40 border-rose-500/40 text-rose-200";
      statusDiv.innerHTML = `
        <svg width="16" height="16" class="w-4 h-4 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        <span class="text-rose-300 font-bold">Incorrect — Review Conceptual Trap</span>`;
    }

    textP.textContent = question.explanation;

    if (qState.currentIndex + 1 < qState.questions.length) {
      btnNext.textContent = "Next Question →";
    } else {
      btnNext.textContent = "Complete Diagnostics →";
    }

  } else {
    if (qState.currentIndex + 1 < qState.questions.length) {
      qState.currentIndex++;
      renderCurrentQuizQuestion();
    } else {
      finishQuizAndSubmit();
    }
  }
}

async function finishQuizAndSubmit() {
  const qState = AppState.quiz;
  clearInterval(qState.timerInterval);

  const total = qState.questions.length;
  const scorePct = total > 0 ? (qState.scoreCount / total) * 100 : 0.0;
  const timeSpentSec = qState.timerSeconds;

  const weakSubtopics = qState.answersLog
    .filter(a => !a.isCorrect && a.subtopic)
    .map(a => a.subtopic);

  document.getElementById("quiz-question-box").classList.add("hidden");
  const resultsCard = document.getElementById("quiz-results-card");
  resultsCard.classList.remove("hidden");

  document.getElementById("result-score-pct").textContent = `${scorePct.toFixed(1)}%`;
  const mins = Math.floor(timeSpentSec / 60);
  const secs = timeSpentSec % 60;
  document.getElementById("result-time-spent").textContent = `${mins}m ${secs}s`;

  const tierLabel = document.getElementById("result-tier-label");
  if (scorePct >= 80) {
    tierLabel.textContent = "Mastery Achieved (≥80%)";
    tierLabel.className = "text-sm font-semibold text-emerald-400 mt-2";
  } else if (scorePct >= 65) {
    tierLabel.textContent = "Proficient Competence (65-79%)";
    tierLabel.className = "text-sm font-semibold text-cyan-400 mt-2";
  } else {
    tierLabel.textContent = "At-Risk Focus Area (<65%)";
    tierLabel.className = "text-sm font-semibold text-rose-400 mt-2";
  }

  const weakTagsList = document.getElementById("result-weak-tags-list");
  const weakPanel = document.getElementById("result-weak-subtopics-panel");

  if (weakSubtopics.length > 0) {
    weakPanel.classList.remove("hidden");
    const uniqueWeak = [...new Set(weakSubtopics)];
    weakTagsList.innerHTML = uniqueWeak.map(st => `
      <span class="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/30 font-medium">
        ${st}
      </span>
    `).join("");
  } else {
    weakPanel.classList.remove("hidden");
    weakTagsList.innerHTML = `<span class="text-xs text-emerald-400 font-medium">Perfect retention! Zero weak spots detected in this trial.</span>`;
  }

  try {
    const sessionId = AppState.currentSession ? AppState.currentSession.session_id : null;
    const subjectCategory = AppState.currentSession ? AppState.currentSession.subject_category : "General Academic";

    const submitRes = await ApiClient.submitQuiz(
      sessionId,
      subjectCategory,
      scorePct,
      timeSpentSec,
      weakSubtopics
    );

    showToast(`Quiz logged (${scorePct.toFixed(0)}%). Telemetry updated!`, "success");

    if (submitRes.updated_kpis) {
      renderDashboardKPIs(submitRes.updated_kpis);
    }
    refreshTelemetryChart();

  } catch (err) {
    console.error("Submission error:", err);
    showToast("Quiz logged locally.", "info");
  }
}


// -------------------------------------------------------------
// 7. Speech Audio Tutor Engine
// -------------------------------------------------------------

function toggleAudioTutor() {
  const synth = AppState.speech.synth;
  if (!synth) {
    showToast("Text-to-speech is not supported by your browser.", "error");
    return;
  }

  if (AppState.speech.isSpeaking) {
    synth.cancel();
    AppState.speech.isSpeaking = false;
    document.getElementById("audio-btn-label").textContent = "Audio Tutor";
    return;
  }

  const summary = document.getElementById("session-summary-text").textContent;
  const title = document.getElementById("session-topic-title").textContent;
  const textToRead = `${title}. Executive summary: ${summary}`;

  const utterance = new SpeechSynthesisUtterance(textToRead);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  utterance.onend = () => {
    AppState.speech.isSpeaking = false;
    document.getElementById("audio-btn-label").textContent = "Audio Tutor";
  };
  utterance.onerror = () => {
    AppState.speech.isSpeaking = false;
    document.getElementById("audio-btn-label").textContent = "Audio Tutor";
  };

  AppState.speech.isSpeaking = true;
  document.getElementById("audio-btn-label").textContent = "Stop Audio";
  synth.speak(utterance);
}


// -------------------------------------------------------------
// 8. Event Listeners & Bootstrapper
// -------------------------------------------------------------

async function loadSessionById(sessionId) {
  try {
    showToast(`Loading study session #${sessionId}...`, "info");
    const res = await ApiClient.getSession(sessionId);
    renderStudyPack(res.session);
    showToast(`Loaded: ${res.session.topic_title}`, "success");
  } catch (err) {
    console.error("Error loading session:", err);
    showToast(err.message, "error");
  }
}

async function handleGenerateClick() {
  const notes = document.getElementById("notes-input").value.trim();
  const subjectHint = document.getElementById("subject-hint").value.trim();
  const btn = document.getElementById("btn-generate");
  const spinner = document.getElementById("generate-spinner");
  const btnText = document.getElementById("generate-btn-text");

  if (!notes) {
    showToast("Please enter notes or choose a preset.", "error");
    document.getElementById("notes-input").focus();
    return;
  }

  try {
    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Deconstructing...";

    const res = await ApiClient.generateStudyPack(notes, subjectHint);
    renderStudyPack(res.study_pack);

    const dash = await ApiClient.getDashboard();
    renderHistorySessions(dash.recent_sessions || []);
    renderDashboardKPIs(dash.kpis);

    showToast("Study Pack architected successfully!", "success");

  } catch (err) {
    console.error("Generation error:", err);
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
    btnText.textContent = "Architect Study Pack";
  }
}

function setupEventListeners() {
  // Tabs navigation
  document.querySelectorAll(".tab-pill, .tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-pill, .tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));

      btn.classList.add("active");
      const targetPanel = document.getElementById(tabId);
      if (targetPanel) targetPanel.classList.remove("hidden");
      AppState.activeTab = tabId;
    });
  });

  // 3D Isometric Layer Jumps
  document.querySelectorAll(".iso-layer").forEach(layer => {
    layer.addEventListener("click", () => {
      const target = layer.getAttribute("data-jump");
      if (target) {
        const el = document.querySelector(target);
        if (el) el.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // Hero Explore Demo Button
  const heroDemoBtn = document.getElementById("btn-hero-demo-calculus");
  if (heroDemoBtn) {
    heroDemoBtn.addEventListener("click", () => {
      const preset = ACADEMIC_PRESETS.calculus;
      document.getElementById("subject-hint").value = preset.subject;
      const notesEl = document.getElementById("notes-input");
      notesEl.value = preset.notes;
      document.getElementById("char-counter").textContent = `${preset.notes.length} characters`;
      document.querySelector("#studio-section").scrollIntoView({ behavior: "smooth" });
      showToast("Loaded Calculus Preset into Studio!", "info");
    });
  }

  // Notes Character Counter
  const notesTextarea = document.getElementById("notes-input");
  const charCounter = document.getElementById("char-counter");
  if (notesTextarea && charCounter) {
    notesTextarea.addEventListener("input", () => {
      charCounter.textContent = `${notesTextarea.value.length} characters`;
    });
  }

  // Clear Input Button
  document.getElementById("btn-clear-input").addEventListener("click", () => {
    notesTextarea.value = "";
    document.getElementById("subject-hint").value = "";
    charCounter.textContent = "0 characters";
    notesTextarea.focus();
  });

  // Generate Button & Shortcut (Cmd/Ctrl + Enter)
  document.getElementById("btn-generate").addEventListener("click", handleGenerateClick);
  notesTextarea.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleGenerateClick();
    }
  });

  // Presets Buttons
  document.querySelectorAll(".preset-tag, .preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const presetKey = btn.getAttribute("data-preset");
      const preset = ACADEMIC_PRESETS[presetKey];
      if (preset) {
        document.getElementById("subject-hint").value = preset.subject;
        notesTextarea.value = preset.notes;
        charCounter.textContent = `${preset.notes.length} characters`;
        showToast(`Loaded ${preset.subject} preset`, "info");
      }
    });
  });

  // 3D Flip Flashcards Scene Flip
  const scene = document.getElementById("flashcard-scene");
  if (scene) {
    scene.addEventListener("click", flipFlashcard);
  }

  // Flashcards Prev / Next
  document.getElementById("btn-fc-prev").addEventListener("click", () => {
    const fc = AppState.flashcards;
    if (fc.cards.length === 0) return;
    fc.currentIndex = (fc.currentIndex - 1 + fc.cards.length) % fc.cards.length;
    renderCurrentFlashcard();
  });

  document.getElementById("btn-fc-next").addEventListener("click", () => {
    const fc = AppState.flashcards;
    if (fc.cards.length === 0) return;
    fc.currentIndex = (fc.currentIndex + 1) % fc.cards.length;
    renderCurrentFlashcard();
  });

  // Leitner Spaced-Repetition Review Buttons
  document.querySelectorAll(".rate-pill, .fc-rate-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const rating = btn.getAttribute("data-rating");
      const fc = AppState.flashcards;
      const sessionId = AppState.currentSession ? AppState.currentSession.session_id : null;

      try {
        await ApiClient.logFlashcardReview(sessionId, fc.currentIndex, rating);
        showToast(`Card marked '${rating}'. Advancing...`, "info");
      } catch (err) {
        console.error("Flashcard review logging error:", err);
      }

      if (fc.cards.length > 0) {
        fc.currentIndex = (fc.currentIndex + 1) % fc.cards.length;
        renderCurrentFlashcard();
      }
    });
  });

  // Audio Tutor Button
  document.getElementById("btn-read-aloud").addEventListener("click", toggleAudioTutor);

  // Quiz Question Speech Button
  document.getElementById("btn-quiz-speech").addEventListener("click", () => {
    const qState = AppState.quiz;
    const question = qState.questions[qState.currentIndex];
    if (question && AppState.speech.synth) {
      const utt = new SpeechSynthesisUtterance(question.question);
      AppState.speech.synth.speak(utt);
    }
  });

  // Quiz Submit/Next Button & Retake
  document.getElementById("btn-next-question").addEventListener("click", handleGradeOrNext);
  document.getElementById("btn-retake-quiz").addEventListener("click", () => {
    if (AppState.currentSession && AppState.currentSession.quiz_questions) {
      initQuiz(AppState.currentSession.quiz_questions);
    }
  });

  // Global Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    if (AppState.activeTab === "tab-flashcards" && e.code === "Space") {
      if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
      e.preventDefault();
      flipFlashcard();
      return;
    }

    if (AppState.activeTab === "tab-quiz") {
      if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;

      if (["1", "2", "3", "4"].includes(e.key)) {
        const optIdx = parseInt(e.key, 10) - 1;
        if (!AppState.quiz.isGraded) {
          handleOptionSelect(optIdx);
        }
      } else if (e.key === "Enter") {
        const nextBtn = document.getElementById("btn-next-question");
        if (nextBtn && !nextBtn.disabled && !document.getElementById("quiz-question-box").classList.contains("hidden")) {
          handleGradeOrNext();
        }
      }
    }
  });

  // Chart Telemetry View Toggles
  const btnChartMastery = document.getElementById("btn-chart-mastery");
  const btnChartDiag = document.getElementById("btn-chart-diag");

  if (btnChartMastery && btnChartDiag) {
    btnChartMastery.addEventListener("click", () => {
      AppState.chartViewMode = "mastery";
      btnChartMastery.className = "px-3.5 py-1.5 rounded-full text-white bg-white/10 transition";
      btnChartDiag.className = "px-3.5 py-1.5 rounded-full text-slate-400 hover:text-white transition";
      refreshTelemetryChart();
    });

    btnChartDiag.addEventListener("click", () => {
      AppState.chartViewMode = "diagnostics";
      btnChartDiag.className = "px-3.5 py-1.5 rounded-full text-white bg-white/10 transition";
      btnChartMastery.className = "px-3.5 py-1.5 rounded-full text-slate-400 hover:text-white transition";
      refreshTelemetryChart();
    });
  }

  document.getElementById("btn-refresh-chart").addEventListener("click", () => {
    refreshTelemetryChart();
    showToast("Telemetry figure refreshed.", "info");
  });

  // History Search Input
  document.getElementById("history-search-input").addEventListener("input", (e) => {
    filterHistorySessions(e.target.value);
  });

  // Export Menu Dropdown Toggle
  const exportBtn = document.getElementById("btn-export-menu");
  const exportMenu = document.getElementById("export-dropdown-menu");
  if (exportBtn && exportMenu) {
    exportBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      exportMenu.classList.toggle("hidden");
    });
    window.addEventListener("click", () => {
      if (exportMenu) exportMenu.classList.add("hidden");
    });
  }

  // Copy Study Guide to Clipboard
  document.getElementById("btn-copy-guide").addEventListener("click", () => {
    if (!AppState.currentSession) return;
    const s = AppState.currentSession;
    let guideText = `# ${s.topic_title}\n\n${s.executive_summary}\n\n## Key Concepts\n`;
    (s.key_concepts || []).forEach(c => {
      guideText += `- ${c.term}: ${c.definition} (Exam Tip: ${c.exam_tip || 'N/A'})\n`;
    });
    navigator.clipboard.writeText(guideText);
    showToast("Study guide copied to clipboard!", "success");
  });

  // Print Guide (Save to PDF)
  document.getElementById("btn-print-guide").addEventListener("click", () => {
    window.print();
  });

  // API Key Modal Controls
  const modal = document.getElementById("api-key-modal");
  const modalInput = document.getElementById("custom-api-key-input");

  document.getElementById("btn-api-key-modal").addEventListener("click", () => {
    modalInput.value = AppState.customApiKey;
    modal.classList.remove("hidden");
    modalInput.focus();
  });

  document.getElementById("btn-close-modal").addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  document.getElementById("btn-clear-key").addEventListener("click", () => {
    AppState.customApiKey = "";
    localStorage.removeItem("cognify_api_key");
    modal.classList.add("hidden");
    updateAIModeBadge(null);
    showToast("Switched to Zero-Config Mode.", "info");
  });

  document.getElementById("btn-save-key").addEventListener("click", () => {
    const key = modalInput.value.trim();
    if (key) {
      AppState.customApiKey = key;
      localStorage.setItem("cognify_api_key", key);
      updateAIModeBadge({ has_api_key: true });
      showToast("Gemini API key saved.", "success");
    } else {
      AppState.customApiKey = "";
      localStorage.removeItem("cognify_api_key");
      updateAIModeBadge(null);
    }
    modal.classList.add("hidden");
  });

  // Initialize Scroll & Interactive Animations
  initScrollObserver();
  initCountersObserver();
  initParallaxHero();
  initFaqAccordion();
  initSpotlightCards();
}

// -------------------------------------------------------------
// 8B. Advanced Scroll & Interaction Animation Engine
// -------------------------------------------------------------
function initSpotlightCards() {
  const cards = document.querySelectorAll(".spotlight-card");
  cards.forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty("--mouse-x", `${x}px`);
      card.style.setProperty("--mouse-y", `${y}px`);
    });
  });
}

function initScrollObserver() {
  const elements = document.querySelectorAll(".scroll-reveal");
  if (!elements.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    },
    {
      threshold: 0.05,
      rootMargin: "60px 0px 60px 0px"
    }
  );

  elements.forEach((el) => {
    observer.observe(el);
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight + 200) {
      el.classList.add("is-visible");
    }
  });
}

function initCountersObserver() {
  const strip = document.getElementById("metrics-strip");
  if (!strip) return;

  let hasAnimated = false;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !hasAnimated) {
          hasAnimated = true;
          const counters = strip.querySelectorAll(".counter-number");
          counters.forEach((counter) => {
            const rawTarget = counter.getAttribute("data-target") || counter.textContent;
            const target = parseInt(rawTarget, 10);
            if (isNaN(target)) return;

            const duration = 1400;
            const startTime = performance.now();

            function tick(currentTime) {
              const elapsed = currentTime - startTime;
              const progress = Math.min(elapsed / duration, 1);
              // Smooth easeOutCubic
              const ease = 1 - Math.pow(1 - progress, 3);
              const val = Math.floor(ease * target);
              counter.textContent = val;

              if (progress < 1) {
                requestAnimationFrame(tick);
              } else {
                counter.textContent = target;
              }
            }
            requestAnimationFrame(tick);
          });
        }
      });
    },
    { threshold: 0.25 }
  );

  observer.observe(strip);
}

function initParallaxHero() {
  const stage = document.getElementById("isometric-hero-stage");
  const container = document.getElementById("isometric-hero-container");
  const backdrop = document.getElementById("ambient-backdrop");

  if (stage && container) {
    stage.addEventListener("mousemove", (e) => {
      const rect = stage.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      const rotX = 60 - y * 14;
      const rotZ = -32 + x * 18;
      container.style.transform = `rotateX(${rotX}deg) rotateZ(${rotZ}deg) translateY(-26px)`;
    });

    stage.addEventListener("mouseleave", () => {
      container.style.transform = "rotateX(60deg) rotateZ(-32deg) translateY(-20px)";
    });
  }

  // Scroll Parallax
  window.addEventListener("scroll", () => {
    const scrollY = window.scrollY;
    if (backdrop) {
      backdrop.style.transform = `translateY(${scrollY * 0.12}px)`;
    }
  }, { passive: true });
}

function initFaqAccordion() {
  const items = document.querySelectorAll(".faq-item");
  items.forEach((item) => {
    const trigger = item.querySelector(".faq-trigger");
    if (trigger) {
      trigger.addEventListener("click", () => {
        const isOpen = item.classList.contains("open");
        items.forEach((i) => i.classList.remove("open"));
        if (!isOpen) {
          item.classList.add("open");
        }
      });
    }
  });
}


// -------------------------------------------------------------
// 9. Initial Application Bootstrapper
// -------------------------------------------------------------
async function initializeApp() {
  try {
    const dashboard = await ApiClient.getDashboard();
    
    updateAIModeBadge(dashboard.ai_mode_status);
    renderDashboardKPIs(dashboard.kpis);
    renderHistorySessions(dashboard.recent_sessions || []);

    if (dashboard.recent_sessions && dashboard.recent_sessions.length > 0) {
      const firstSessionId = dashboard.recent_sessions[0].id;
      const sessionData = await ApiClient.getSession(firstSessionId);
      renderStudyPack(sessionData.session);
    }

  } catch (err) {
    console.error("Bootstrapping error:", err);
    showToast("Failed to initialize telemetry.", "error");
  }
}

// Bootstrap on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  initializeApp();
});
