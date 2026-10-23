"""
database.py - SQLite Local Persistence & Telemetry Layer for Cognify
Handles study sessions, interactive quiz attempts, flashcard reviews, and auto-seeding.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cognify.db"


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database with Row factory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initializes tables and seeds initial realistic telemetry data if empty."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Table 1: study_sessions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                topic_title TEXT NOT NULL,
                subject_category TEXT NOT NULL,
                difficulty_rating INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )

        # Table 2: quiz_attempts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                subject_category TEXT NOT NULL,
                score_pct REAL NOT NULL,
                time_spent_sec INTEGER NOT NULL,
                weak_subtopics_json TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE SET NULL
            );
            """
        )

        # Table 3: flashcard_reviews (Spaced Repetition Logging)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcard_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                card_index INTEGER NOT NULL,
                rating TEXT NOT NULL, -- 'again', 'hard', 'good', 'easy'
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE CASCADE
            );
            """
        )

        # Check if quiz_attempts is empty, if so auto-seed
        cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
        attempt_count = cursor.fetchone()[0]

        if attempt_count == 0:
            seed_initial_data(conn)

        conn.commit()


def seed_initial_data(conn: sqlite3.Connection) -> None:
    """
    Seeds initial realistic study sessions and 12 historical quiz attempts
    across subjects (Calculus, Biology, US History, Physics, Computer Science)
    distributed over the past 7 days.
    """
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)

    # Pre-seed realistic study sessions with enriched Flashcards, Formulas, and Misconceptions
    sample_sessions = [
        {
            "days_ago": 6.8,
            "topic_title": "Calculus: Fundamental Theorem & Integration Techniques",
            "subject_category": "STEM / Calculus",
            "difficulty_rating": 8,
            "executive_summary": "Core principles of differentiation and integration, focusing on substitution methods, integration by parts, accumulation functions, and curvature bounds.",
            "key_concepts": [
                {
                    "term": "Fundamental Theorem of Calculus (FTC)",
                    "definition": "Connects differentiation and integration: the derivative of an accumulation function recovers the integrand: d/dx [∫[a to x] f(t) dt] = f(x).",
                    "exam_tip": "Check continuity on closed intervals before applying FTC Part 1."
                },
                {
                    "term": "Integration by Parts",
                    "definition": "Technique derived from the product rule: ∫ u dv = uv - ∫ v du.",
                    "exam_tip": "Use the LIATE rule (Log, Inverse trig, Algebraic, Trig, Exponential) to select u."
                },
                {
                    "term": "Riemann Sum Limit",
                    "definition": "Definite integrals represent the infinite limit of partition rect sums as Δx approaches 0.",
                    "exam_tip": "Watch for midpoint vs trapezoidal error bounds on concavity."
                }
            ],
            "flashcards": [
                {
                    "front": "What is the formula for Integration by Parts?",
                    "back": "∫ u dv = uv - ∫ v du",
                    "mnemonic": "Ultra Violet Voodoo: UV - ∫ V dU"
                },
                {
                    "front": "What mnemonic determines the priority choice of 'u' in Integration by Parts?",
                    "back": "LIATE: Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential.",
                    "mnemonic": "L.I.A.T.E."
                },
                {
                    "front": "State Part 1 of the Fundamental Theorem of Calculus.",
                    "back": "If f is continuous on [a, b], then g(x) = ∫[a to x] f(t) dt is continuous on [a, b], differentiable on (a, b), and g'(x) = f(x).",
                    "mnemonic": "Derivative of accumulation = integrand"
                },
                {
                    "front": "If f''(x) > 0 (concave up), does the Trapezoidal Rule overestimate or underestimate?",
                    "back": "Overestimate. Because chords between points lie strictly above the curve.",
                    "mnemonic": "Cup up = Trapezoid overhang"
                }
            ],
            "formula_sheet": [
                {
                    "name": "Integration by Parts",
                    "formula_or_rule": "∫ u dv = uv - ∫ v du",
                    "application_notes": "Apply when integrand contains products of disparate function classes."
                },
                {
                    "name": "Mean Value Theorem for Integrals",
                    "formula_or_rule": "f(c) = 1/(b - a) ∫[a to b] f(x) dx",
                    "application_notes": "Guarantees at least one point c where instantaneous height equals average value."
                },
                {
                    "name": "Trapezoidal Error Bound",
                    "formula_or_rule": "|E_T| ≤ K(b - a)³ / (12n²), where |f''(x)| ≤ K",
                    "application_notes": "Use to bound maximum numerical integration approximation error."
                }
            ],
            "common_misconceptions": [
                {
                    "myth": "FTC Part 1 holds even if the integrand f(t) has a step discontinuity inside [a, b].",
                    "reality": "False. Continuity across the entire closed interval is a strict hypothesis for FTC.",
                    "why_it_matters": "AP and university exams test piecewise discontinuous integrals that violate FTC prerequisites."
                },
                {
                    "myth": "Integration by Parts can only be applied once per problem.",
                    "reality": "False. Repeated integration by parts or cyclic equations (e.g. ∫ e^x cos(x) dx) are standard exam patterns.",
                    "why_it_matters": "Recognizing cyclic algebraic loops saves minutes of wasted computation."
                }
            ],
            "quiz_questions": [
                {
                    "id": 1,
                    "question": "Which rule is best suited for prioritizing the choice of 'u' in integration by parts?",
                    "options": ["L'Hôpital's Rule", "LIATE Rule", "Chain Rule", "Ratio Test"],
                    "correct_index": 1,
                    "explanation": "The LIATE mnemonic (Logarithmic, Inverse trig, Algebraic, Trig, Exponential) helps optimize u selection.",
                    "subtopic_tag": "Integration by Parts"
                },
                {
                    "id": 2,
                    "question": "What is the derivative of g(x) = ∫[0 to x] sin(t²) dt with respect to x?",
                    "options": ["cos(x²)", "sin(x²)", "2x sin(x²)", "-cos(x²)"],
                    "correct_index": 1,
                    "explanation": "By FTC Part 1, d/dx [∫[0 to x] f(t) dt] = f(x), yielding sin(x²).",
                    "subtopic_tag": "FTC Part 1"
                },
                {
                    "id": 3,
                    "question": "When evaluates ∫ x e^x dx via integration by parts, what is the resulting expression?",
                    "options": ["x e^x - e^x + C", "x² e^x / 2 + C", "e^x - x e^x + C", "x e^x + e^x + C"],
                    "correct_index": 0,
                    "explanation": "With u=x, dv=e^x dx, du=dx, v=e^x, we get uv - ∫ v du = x e^x - e^x + C.",
                    "subtopic_tag": "Integration by Parts"
                },
                {
                    "id": 4,
                    "question": "Which condition is strictly required for the Mean Value Theorem for Integrals?",
                    "options": ["f must be differentiable on [a,b]", "f must be continuous on [a,b]", "f must be monotonic", "f(a) must equal f(b)"],
                    "correct_index": 1,
                    "explanation": "Continuity on [a,b] is sufficient to guarantee a point c where f(c) = (1/(b-a)) ∫[a to b] f(x) dx.",
                    "subtopic_tag": "MVT for Integrals"
                },
                {
                    "id": 5,
                    "question": "What error bound behavior occurs when approximating an upward concave function with trapezoids?",
                    "options": ["Underestimate", "Overestimate", "Exact result", "Zero error"],
                    "correct_index": 1,
                    "explanation": "Since chords lie above the curve for concave upward functions, trapezoidal sums overestimate.",
                    "subtopic_tag": "Riemann Approximations"
                }
            ],
            "study_roadmap": [
                {"step_title": "Master LIATE Selection Drills", "estimated_minutes": 25, "focus_area": "Integration by Parts"},
                {"step_title": "Review FTC Boundary Variable Chains", "estimated_minutes": 20, "focus_area": "FTC Part 1"},
                {"step_title": "Work Concavity Error Proofs", "estimated_minutes": 15, "focus_area": "Numerical Integration"}
            ]
        },
        {
            "days_ago": 4.5,
            "topic_title": "Biology: Cellular Respiration & ATP Chemiosmosis",
            "subject_category": "Biology",
            "difficulty_rating": 7,
            "executive_summary": "Comprehensive overview of glycolysis, the citric acid cycle, electron transport chain, and proton-motive phosphorylation.",
            "key_concepts": [
                {
                    "term": "Proton-Motive Force",
                    "definition": "Electrochemical gradient generated by pumping H+ across the inner mitochondrial membrane into the intermembrane space.",
                    "exam_tip": "High H+ in intermembrane space corresponds to low pH compared to the matrix."
                },
                {
                    "term": "ATP Synthase Rotary Motor",
                    "definition": "Enzyme complex that channels protons down their concentration gradient to phosphorylate ADP into ATP.",
                    "exam_tip": "Rotates mechanically as protons enter stator channels."
                },
                {
                    "term": "Final Electron Acceptor",
                    "definition": "Oxygen (O2) acts as the terminal electron acceptor in aerobic respiration, reducing to form water.",
                    "exam_tip": "Without O2, Complex IV halts, leading to backup of NADH."
                }
            ],
            "flashcards": [
                {
                    "front": "What serves as the terminal electron acceptor in mitochondrial oxidative phosphorylation?",
                    "back": "Molecular Oxygen (O₂), which combines with electrons and protons to form H₂O.",
                    "mnemonic": "O₂ drinks electrons to make water"
                },
                {
                    "front": "Where does glycolysis occur vs the citric acid cycle in eukaryotes?",
                    "back": "Glycolysis: Cytosol. Citric Acid Cycle: Mitochondrial Matrix.",
                    "mnemonic": "Cytosol splits, Matrix spins"
                },
                {
                    "front": "What is the net yield of ATP from 1 molecule of glucose in glycolysis alone?",
                    "back": "Net 2 ATP (consumes 2 ATP, produces 4 ATP).",
                    "mnemonic": "Invest 2, Harvest 4 = Net 2"
                }
            ],
            "formula_sheet": [
                {
                    "name": "Overall Cellular Respiration Equation",
                    "formula_or_rule": "C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O + ~30-32 ATP",
                    "application_notes": "Exergonic reaction with ΔG°' = -686 kcal/mol."
                },
                {
                    "name": "Proton Pumping Stoichiometry",
                    "formula_or_rule": "NADH → ~10 H⁺ pumped; FADH₂ → ~6 H⁺ pumped",
                    "application_notes": "Explains why NADH yields ~2.5 ATP whereas FADH₂ yields only ~1.5 ATP."
                }
            ],
            "common_misconceptions": [
                {
                    "myth": "Most ATP in cellular respiration is generated directly via substrate-level phosphorylation.",
                    "reality": "False. Oxidative phosphorylation via chemiosmosis accounts for ~90% of total ATP synthesis.",
                    "why_it_matters": "Understanding the efficiency distinction between glycolysis and the ETC is crucial."
                }
            ],
            "quiz_questions": [
                {
                    "id": 1,
                    "question": "What molecule serves as the terminal electron acceptor in oxidative phosphorylation?",
                    "options": ["NAD+", "Molecular Oxygen (O₂)", "Carbon Dioxide", "Pyruvate"],
                    "correct_index": 1,
                    "explanation": "Oxygen accepts electrons at Complex IV and binds protons to produce H₂O.",
                    "subtopic_tag": "Electron Transport Chain"
                },
                {
                    "id": 2,
                    "question": "Where does glycolysis occur in eukaryotic cells?",
                    "options": ["Mitochondrial Matrix", "Cytosol", "Inner Membrane Space", "Cristae"],
                    "correct_index": 1,
                    "explanation": "Glycolysis takes place in the cytoplasm/cytosol without requiring oxygen.",
                    "subtopic_tag": "Glycolysis"
                },
                {
                    "id": 3,
                    "question": "Which enzyme directly utilizes proton flow to synthesize ATP?",
                    "options": ["Phosphofructokinase", "ATP Synthase", "Citrate Synthase", "Cytochrome c Oxidase"],
                    "correct_index": 1,
                    "explanation": "ATP Synthase uses the flow of H+ down their gradient to rotate its catalytic subunit.",
                    "subtopic_tag": "Chemiosmosis"
                },
                {
                    "id": 4,
                    "question": "What is the net gain of ATP directly generated from 1 glucose molecule via glycolysis?",
                    "options": ["1 ATP", "2 ATP", "4 ATP", "32 ATP"],
                    "correct_index": 1,
                    "explanation": "Glycolysis consumes 2 ATP and produces 4 ATP, yielding a net of 2 ATP.",
                    "subtopic_tag": "Glycolysis"
                },
                {
                    "id": 5,
                    "question": "In the Krebs cycle, what 4-carbon compound binds with Acetyl-CoA to form citrate?",
                    "options": ["Malate", "Oxaloacetate", "Fumarate", "Succinate"],
                    "correct_index": 1,
                    "explanation": "Oxaloacetate (4C) combines with Acetyl-CoA (2C) to form Citrate (6C).",
                    "subtopic_tag": "Krebs Cycle"
                }
            ],
            "study_roadmap": [
                {"step_title": "Map Matrix vs Intermembrane pH Gradients", "estimated_minutes": 20, "focus_area": "Chemiosmosis"},
                {"step_title": "Trace Carbon Balance in Krebs Cycle", "estimated_minutes": 30, "focus_area": "Krebs Cycle"},
                {"step_title": "Memorize Electron Transport Complex Inhibitors", "estimated_minutes": 20, "focus_area": "Electron Transport Chain"}
            ]
        },
        {
            "days_ago": 2.2,
            "topic_title": "Computer Science: Distributed Consensus & Raft Protocol",
            "subject_category": "Computer Science",
            "difficulty_rating": 9,
            "executive_summary": "Architectural mechanics of distributed state machines, leader election, log replication, and split-brain resolution in the Raft consensus algorithm.",
            "key_concepts": [
                {
                    "term": "Leader Election & Heartbeats",
                    "definition": "Nodes start as followers; if no heartbeat is received within randomized timeout, candidate election begins.",
                    "exam_tip": "Randomized election timeouts prevent split-vote deadlocks."
                },
                {
                    "term": "Log Replication Safety",
                    "definition": "Leader appends entries locally, replicates to followers, and commits once a majority quorum acknowledges.",
                    "exam_tip": "A committed entry is guaranteed to be present in all future terms."
                },
                {
                    "term": "Quorum / Majority Rule",
                    "definition": "Agreement from floor(N/2) + 1 nodes ensures overlap across any two partitioned subsets.",
                    "exam_tip": "In a 5-node cluster, quorum requires at least 3 active nodes."
                }
            ],
            "flashcards": [
                {
                    "front": "How does Raft prevent persistent split votes during leader election?",
                    "back": "Randomized election timeouts (e.g., 150ms-300ms) ensure one candidate times out and requests votes first.",
                    "mnemonic": "Random jitter stops split ties"
                },
                {
                    "front": "What constitutes a quorum in an N-node distributed cluster?",
                    "back": "Strict majority: floor(N/2) + 1 nodes.",
                    "mnemonic": "Half plus one"
                },
                {
                    "front": "State the Raft Leader Completeness Property.",
                    "back": "If a log entry is committed in a given term, that entry will be present in the logs of the leaders for all higher-numbered terms.",
                    "mnemonic": "Committed logs survive forever"
                }
            ],
            "formula_sheet": [
                {
                    "name": "Cluster Quorum Formula",
                    "formula_or_rule": "Q = ⌊N / 2⌋ + 1",
                    "application_notes": "Determines minimum alive nodes needed for safety and liveness."
                },
                {
                    "name": "Fault Tolerance Bound",
                    "formula_or_rule": "F = ⌊(N - 1) / 2⌋",
                    "application_notes": "Max crash failures a cluster can tolerate without losing consensus."
                }
            ],
            "common_misconceptions": [
                {
                    "myth": "A Raft leader commits an entry as soon as it is written to its own local disk.",
                    "reality": "False. An entry is only committed once safely replicated to a majority of cluster nodes.",
                    "why_it_matters": "Writing to leader disk without quorum risks data loss during leader crashes."
                }
            ],
            "quiz_questions": [
                {
                    "id": 1,
                    "question": "What mechanism does Raft employ to avoid persistent split-vote scenarios during leader election?",
                    "options": ["Round-robin scheduling", "Randomized election timeouts", "Static priority IDs", "Vector clocks"],
                    "correct_index": 1,
                    "explanation": "Randomized timeouts (e.g. 150-300ms) stagger election starts, allowing one node to garner quorum.",
                    "subtopic_tag": "Leader Election"
                },
                {
                    "id": 2,
                    "question": "In a 5-node distributed cluster, what is the minimum quorum required to commit a log entry?",
                    "options": ["2 nodes", "3 nodes", "4 nodes", "5 nodes"],
                    "correct_index": 1,
                    "explanation": "Quorum is floor(5/2) + 1 = 3 nodes.",
                    "subtopic_tag": "Quorum Safety"
                },
                {
                    "id": 3,
                    "question": "When can a Raft leader safely commit an entry from its current term?",
                    "options": ["Immediately upon writing to disk", "Once replicated on a majority of nodes", "When all followers acknowledge", "At the end of the term"],
                    "correct_index": 1,
                    "explanation": "The leader commits an entry as soon as it is stored on a majority of nodes in the cluster.",
                    "subtopic_tag": "Log Replication"
                },
                {
                    "id": 4,
                    "question": "If a follower detects that an incoming leader has a lower Term number than its own, what does it do?",
                    "options": ["Accepts the leader", "Rejects the request with false", "Crashes the thread", "Triggers immediate election"],
                    "correct_index": 1,
                    "explanation": "Followers reject AppendEntries RPCs from stale terms to maintain state machine safety.",
                    "subtopic_tag": "Term Invariants"
                },
                {
                    "id": 5,
                    "question": "What property guarantees that if an entry is committed at index i in term t, all future leaders contain it?",
                    "options": ["State Machine Safety", "Election Safety & Leader Completeness", "Linearizability", "Eventual Consistency"],
                    "correct_index": 1,
                    "explanation": "The Leader Completeness property guarantees committed entries reside in all subsequent leaders.",
                    "subtopic_tag": "Leader Completeness"
                }
            ],
            "study_roadmap": [
                {"step_title": "Simulate Split-Vote Scenarios", "estimated_minutes": 25, "focus_area": "Leader Election"},
                {"step_title": "Analyze Log Matching Invariant Proofs", "estimated_minutes": 35, "focus_area": "Log Replication"},
                {"step_title": "Trace Network Partition Recovery in Raft", "estimated_minutes": 30, "focus_area": "Quorum Safety"}
            ]
        }
    ]

    session_ids = []
    for s in sample_sessions:
        created_time = (now - timedelta(days=s["days_ago"])).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO study_sessions (created_at, topic_title, subject_category, difficulty_rating, payload_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                created_time,
                s["topic_title"],
                s["subject_category"],
                s["difficulty_rating"],
                json.dumps(s)
            )
        )
        session_ids.append(cursor.lastrowid)

    # 12 historical realistic quiz attempts across 5 subjects over the past 7 days
    # (Calculus, Biology, US History, Physics, Computer Science)
    historical_attempts = [
        # (days_ago, session_index, subject, score_pct, time_spent_sec, weak_subtopics)
        (6.5, 0, "Calculus", 60.0, 195, ["Integration by Parts", "Taylor Series"]),
        (5.8, 1, "Biology", 80.0, 142, ["Glycolysis"]),
        (5.2, None, "Physics", 40.0, 210, ["Doppler Shift", "Lorentz Transformations"]),
        (4.7, None, "US History", 80.0, 115, ["Cold War Treaties"]),
        (4.1, 0, "Calculus", 80.0, 150, ["Riemann Approximations"]),
        (3.6, None, "Computer Science", 60.0, 185, ["Leader Election", "Quorum Safety"]),
        (3.0, 1, "Biology", 100.0, 95, []),
        (2.4, None, "US History", 100.0, 88, []),
        (1.9, 2, "Computer Science", 80.0, 130, ["Term Invariants"]),
        (1.4, None, "Physics", 60.0, 175, ["Wave-Particle Duality"]),
        (0.8, 0, "Calculus", 100.0, 110, []),
        (0.2, 2, "Computer Science", 100.0, 102, [])
    ]

    for days_ago, sess_idx, subject, score, duration, weak in historical_attempts:
        attempt_time = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        sess_id = session_ids[sess_idx] if sess_idx is not None and sess_idx < len(session_ids) else None
        cursor.execute(
            """
            INSERT INTO quiz_attempts (session_id, created_at, subject_category, score_pct, time_spent_sec, weak_subtopics_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                sess_id,
                attempt_time,
                subject,
                score,
                duration,
                json.dumps(weak)
            )
        )


def save_study_session(
    topic_title: str,
    subject_category: str,
    difficulty_rating: int,
    payload_json: str
) -> int:
    """Inserts a newly generated study session and returns its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO study_sessions (topic_title, subject_category, difficulty_rating, payload_json)
            VALUES (?, ?, ?, ?);
            """,
            (topic_title, subject_category, difficulty_rating, payload_json)
        )
        conn.commit()
        return cursor.lastrowid


def get_study_session(session_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single study session by its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM study_sessions WHERE id = ?;", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def delete_study_session(session_id: int) -> bool:
    """Deletes a study session by ID along with its associated records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM study_sessions WHERE id = ?;", (session_id,))
        cursor.execute("DELETE FROM quiz_attempts WHERE session_id = ?;", (session_id,))
        cursor.execute("DELETE FROM flashcard_reviews WHERE session_id = ?;", (session_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_all_study_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns the most recent study sessions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, topic_title, subject_category, difficulty_rating
            FROM study_sessions
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


def log_quiz_attempt(
    session_id: Optional[int],
    subject_category: str,
    score_pct: float,
    time_spent_sec: int,
    weak_subtopics: List[str]
) -> int:
    """Logs a quiz attempt and returns the attempt ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quiz_attempts (session_id, subject_category, score_pct, time_spent_sec, weak_subtopics_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                session_id,
                subject_category,
                float(score_pct),
                int(time_spent_sec),
                json.dumps(weak_subtopics or [])
            )
        )
        conn.commit()
        return cursor.lastrowid


def log_flashcard_review(session_id: Optional[int], card_index: int, rating: str) -> int:
    """Logs a flashcard review for Spaced Repetition analysis."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO flashcard_reviews (session_id, card_index, rating)
            VALUES (?, ?, ?);
            """,
            (session_id, card_index, rating)
        )
        conn.commit()
        return cursor.lastrowid


def get_all_quiz_attempts(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches quiz attempts ordered chronologically descending."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, session_id, created_at, subject_category, score_pct, time_spent_sec, weak_subtopics_json
            FROM quiz_attempts
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            try:
                item["weak_subtopics"] = json.loads(item.get("weak_subtopics_json") or "[]")
            except Exception:
                item["weak_subtopics"] = []
            results.append(item)
        return results


def get_dashboard_kpis() -> Dict[str, Any]:
    """
    Computes key performance indicators for the top-level dashboard:
    total_sessions, avg_mastery_pct, total_quizzes_taken, top_weak_spot, and subject breakdown.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Total sessions
        cursor.execute("SELECT COUNT(*) FROM study_sessions;")
        total_sessions = cursor.fetchone()[0]

        # Total quizzes & average mastery score
        cursor.execute("SELECT COUNT(*), AVG(score_pct) FROM quiz_attempts;")
        attempt_stats = cursor.fetchone()
        total_quizzes = attempt_stats[0] or 0
        avg_mastery = round(attempt_stats[1] or 0.0, 1)

        # Compute top weak spot from weak_subtopics_json
        cursor.execute("SELECT weak_subtopics_json FROM quiz_attempts;")
        rows = cursor.fetchall()
        subtopic_counts: Dict[str, int] = {}
        for row in rows:
            try:
                subtopics = json.loads(row[0] or "[]")
                for st in subtopics:
                    if st:
                        subtopic_counts[st] = subtopic_counts.get(st, 0) + 1
            except Exception:
                continue

        top_weak_spot = "None Detected"
        if subtopic_counts:
            top_weak_spot = max(subtopic_counts.items(), key=lambda x: x[1])[0]

        # Subject breakdown
        cursor.execute(
            """
            SELECT subject_category, COUNT(*) as count, AVG(score_pct) as avg_score
            FROM quiz_attempts
            GROUP BY subject_category
            ORDER BY avg_score DESC;
            """
        )
        subject_breakdown = [
            {
                "subject": r["subject_category"],
                "quiz_count": r["count"],
                "avg_score": round(r["avg_score"] or 0.0, 1)
            }
            for r in cursor.fetchall()
        ]

        # Total flashcard reviews
        cursor.execute("SELECT COUNT(*) FROM flashcard_reviews;")
        total_cards_reviewed = cursor.fetchone()[0]

        return {
            "total_sessions": total_sessions,
            "avg_mastery_pct": avg_mastery,
            "total_quizzes_taken": total_quizzes,
            "total_cards_reviewed": total_cards_reviewed,
            "top_weak_spot": top_weak_spot,
            "weak_spot_frequencies": sorted(subtopic_counts.items(), key=lambda x: x[1], reverse=True)[:6],
            "subject_breakdown": subject_breakdown
        }


def reset_and_seed_db() -> None:
    """Drops existing tables and resets the database with initial seed data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS flashcard_reviews;")
        cursor.execute("DROP TABLE IF EXISTS quiz_attempts;")
        cursor.execute("DROP TABLE IF EXISTS study_sessions;")
        conn.commit()
    init_db()


if __name__ == "__main__":
    init_db()
    kpis = get_dashboard_kpis()
    print("Database initialized successfully.")
    print(f"Total sessions: {kpis['total_sessions']}")
    print(f"Total quizzes: {kpis['total_quizzes_taken']}")
    print(f"Average mastery: {kpis['avg_mastery_pct']}%")
    print(f"Top weak spot: {kpis['top_weak_spot']}")
