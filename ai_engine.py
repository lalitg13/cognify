"""
ai_engine.py - Google Gemini Structured AI Engine with Zero-Config Offline Demo Fallback
Uses official `google-genai` SDK with strict Pydantic JSON schemas.
Includes Flashcards, Formula/Rule Sheets, Common Misconceptions, and Adaptive Synthesis.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()
logger = logging.getLogger("cognify.ai_engine")
logging.basicConfig(level=logging.INFO)


# -------------------------------------------------------------
# 1. Pydantic Structured JSON Schemas
# -------------------------------------------------------------
class KeyConcept(BaseModel):
    term: str = Field(description="Core academic or technical term")
    definition: str = Field(description="Rigorous, concise academic definition")
    exam_tip: str = Field(description="High-leverage exam warning, mnemonic, or pitfall to avoid")


class FlashcardItem(BaseModel):
    front: str = Field(description="Question, prompt, or technical term on the front of the flashcard")
    back: str = Field(description="Direct, high-yield answer or explanation on the back of the flashcard")
    mnemonic: Optional[str] = Field(default=None, description="Memory hook, formula abbreviation, or mnemonic anchor")


class FormulaRuleItem(BaseModel):
    name: str = Field(description="Name of the theorem, governing equation, or architectural invariant")
    formula_or_rule: str = Field(description="Mathematical expression, pseudo-code, or formal statement")
    application_notes: str = Field(description="Contextual guidance for when and how to apply this rule on exams")


class MisconceptionItem(BaseModel):
    myth: str = Field(description="Common student misconception, naive assumption, or exam trap")
    reality: str = Field(description="Rigorous academic correction of the error")
    why_it_matters: str = Field(description="Why examiners and test-makers frequently target this distinction")


class QuizQuestion(BaseModel):
    id: int = Field(description="Question identifier from 1 to 5")
    question: str = Field(description="Challenging active-recall multiple choice question")
    options: List[str] = Field(description="List of exactly 4 plausible answer choices")
    correct_index: int = Field(description="0-based index of the correct answer (0, 1, 2, or 3)")
    explanation: str = Field(description="In-depth conceptual justification explaining why the answer is correct")
    subtopic_tag: str = Field(description="Specific sub-discipline or mechanism tag tested by this question")


class RoadmapStep(BaseModel):
    step_title: str = Field(description="Action-oriented follow-up study task")
    estimated_minutes: int = Field(description="Realistic time estimate in minutes (10 to 60)")
    focus_area: str = Field(description="Specific academic focus area or technique")


class StudyPackSchema(BaseModel):
    topic_title: str = Field(description="Crisp, authoritative title for the study module")
    subject_category: str = Field(description="Broad academic discipline (e.g. STEM / Calculus, Biology, Computer Science, Physics, History)")
    difficulty_rating: int = Field(description="Integer difficulty rating from 1 (Introductory) to 10 (Advanced Graduate)")
    executive_summary: str = Field(description="High-density synthesis summarizing the primary principles and mental models")
    key_concepts: List[KeyConcept] = Field(description="List of 3 to 6 essential concept cards")
    flashcards: List[FlashcardItem] = Field(default_factory=list, description="List of 4 to 8 active recall flashcards")
    formula_sheet: List[FormulaRuleItem] = Field(default_factory=list, description="List of 2 to 4 core theorems or formulas")
    common_misconceptions: List[MisconceptionItem] = Field(default_factory=list, description="List of 2 to 3 common exam traps and pitfalls")
    quiz_questions: List[QuizQuestion] = Field(description="List of exactly 5 multiple choice questions")
    study_roadmap: List[RoadmapStep] = Field(description="List of exactly 3 sequential next-step study milestones")


# -------------------------------------------------------------
# 2. Curated Adaptive Demo Packs (Instant Zero-Config Experience)
# -------------------------------------------------------------
DEMO_TOPIC_BANKS = {
    "calculus": {
        "topic_title": "Multivariable Calculus: Gradient Descent & Directional Derivatives",
        "subject_category": "STEM / Calculus",
        "difficulty_rating": 8,
        "executive_summary": "Directional derivatives quantify instantaneous scalar field variation along arbitrary unit vectors. The gradient vector ∇f always points in the direction of maximal ascent with magnitude equal to that rate of increase, forming the mathematical bedrock for first-order gradient descent optimization.",
        "key_concepts": [
            {
                "term": "Gradient Vector (∇f)",
                "definition": "The vector composed of all first-order partial derivatives: ∇f = [∂f/∂x, ∂f/∂y, ∂f/∂z]. Points along the steepest rate of increase.",
                "exam_tip": "Always normalize the direction vector u into a unit vector before computing D_u f = ∇f · u."
            },
            {
                "term": "Directional Derivative (D_u f)",
                "definition": "The projection of the gradient onto unit vector u: D_u f = ∇f · u = |∇f| cos(θ).",
                "exam_tip": "Maximum value is |∇f| (when θ=0); minimum value is -|∇f| (when θ=π); zero along contour level curves."
            },
            {
                "term": "Hessian Matrix & Curvature",
                "definition": "Square matrix of second-order partial derivatives describing local quadratic curvature and concavity.",
                "exam_tip": "If det(H) < 0 at a critical point, the point is an immediate saddle point regardless of trace."
            },
            {
                "term": "Level Sets & Orthogonality",
                "definition": "The gradient vector at any point is strictly orthogonal (perpendicular) to the tangent plane of the level surface f(x,y,z) = c.",
                "exam_tip": "Use this orthogonality to quickly construct the normal vector for tangent planes."
            }
        ],
        "flashcards": [
            {
                "front": "What is the formula for the directional derivative D_u f?",
                "back": "D_u f = ∇f · u, where u is a normalized unit vector (|u| = 1).",
                "mnemonic": "Dot product of Gradient and Unit vector"
            },
            {
                "front": "In what direction does the gradient vector ∇f always point?",
                "back": "In the direction of steepest rate of ascent (maximal increase) of the scalar field.",
                "mnemonic": "Gradient climbs highest"
            },
            {
                "front": "What does a negative Hessian determinant (det(H) < 0) at a critical point signify?",
                "back": "It indicates a saddle point, meaning principal curvatures have opposite signs.",
                "mnemonic": "Negative Det = Saddle"
            },
            {
                "front": "What is the geometric relationship between ∇f and the level curves f(x, y) = c?",
                "back": "The gradient ∇f is strictly orthogonal (perpendicular) to the level curve's tangent at every point.",
                "mnemonic": "Perpendicular to contours"
            }
        ],
        "formula_sheet": [
            {
                "name": "Directional Derivative",
                "formula_or_rule": "D_u f = ∇f · u = |∇f| cos(θ)",
                "application_notes": "Requires |u| = 1. If given arbitrary vector v, divide by ||v|| first."
            },
            {
                "name": "Gradient Descent Parameter Update",
                "formula_or_rule": "θ_(t+1) = θ_t - α ∇f(θ_t)",
                "application_notes": "Negative sign moves in direction of steepest descent. α is the learning rate."
            },
            {
                "name": "2D Hessian Discriminant",
                "formula_or_rule": "D = f_xx f_yy - (f_xy)²",
                "application_notes": "If D > 0 and f_xx > 0: Min. If D > 0 and f_xx < 0: Max. If D < 0: Saddle."
            }
        ],
        "common_misconceptions": [
            {
                "myth": "You can calculate D_u f using any given direction vector directly without normalizing.",
                "reality": "False. If the direction vector is not of unit length, D_u f will be scaled incorrectly by the vector's magnitude.",
                "why_it_matters": "A common multiple-choice distractor provides the unnormalized dot product."
            },
            {
                "myth": "The gradient vector lies on the tangent plane of a level surface.",
                "reality": "False. The gradient vector is normal (perpendicular) to the tangent plane.",
                "why_it_matters": "Using the gradient as a tangent vector causes incorrect plane equations."
            }
        ],
        "quiz_questions": [
            {
                "id": 1,
                "question": "In which direction is the directional derivative D_u f(x, y) maximized?",
                "options": [
                    "Perpendicular to the gradient vector ∇f",
                    "Directly in the direction of the gradient vector ∇f",
                    "Opposite to the gradient vector (-∇f)",
                    "Along the tangent line of the level curve"
                ],
                "correct_index": 1,
                "explanation": "Because D_u f = |∇f| |u| cos(θ), the dot product is maximized when cos(θ) = 1, meaning u is parallel to ∇f.",
                "subtopic_tag": "Directional Derivatives"
            },
            {
                "id": 2,
                "question": "What is the value of the directional derivative along the tangent vector of a level curve f(x,y) = k?",
                "options": ["|∇f|", "0", "-|∇f|", "1"],
                "correct_index": 1,
                "explanation": "Along a level curve, f is constant, so df = 0. Therefore, the gradient is orthogonal to the tangent, making the dot product 0.",
                "subtopic_tag": "Level Curves"
            },
            {
                "id": 3,
                "question": "For f(x, y) = x² + 3y², what is the gradient ∇f at the coordinate point (2, 1)?",
                "options": ["[4, 6]", "[2, 3]", "[4, 3]", "[2, 6]"],
                "correct_index": 0,
                "explanation": "∂f/∂x = 2x = 4; ∂f/∂y = 6y = 6. Thus ∇f(2, 1) = [4, 6].",
                "subtopic_tag": "Gradient Calculation"
            },
            {
                "id": 4,
                "question": "If the Hessian determinant det(H) < 0 at critical point (x0, y0), what does the Second Derivative Test conclude?",
                "options": ["Local minimum", "Local maximum", "Saddle point", "Test is inconclusive"],
                "correct_index": 2,
                "explanation": "A negative Hessian determinant signifies principal curvatures of opposite sign, identifying a saddle point.",
                "subtopic_tag": "Second Derivative Test"
            },
            {
                "id": 5,
                "question": "In first-order Gradient Descent optimization, how is the parameter update step defined?",
                "options": [
                    "θ_new = θ_old + α ∇f(θ_old)",
                    "θ_new = θ_old - α ∇f(θ_old)",
                    "θ_new = θ_old / ∇f(θ_old)",
                    "θ_new = α ∇²f(θ_old)"
                ],
                "correct_index": 1,
                "explanation": "To minimize loss f, parameters step in the direction of steepest descent (-∇f) scaled by learning rate α.",
                "subtopic_tag": "Optimization Algorithms"
            }
        ],
        "study_roadmap": [
            {"step_title": "Unit Vector Normalization Drills", "estimated_minutes": 20, "focus_area": "Directional Derivatives"},
            {"step_title": "Construct 3D Tangent Planes via Level Gradients", "estimated_minutes": 25, "focus_area": "Level Sets"},
            {"step_title": "Implement Gradient Descent in Python with Learning Rate Decay", "estimated_minutes": 35, "focus_area": "Optimization Algorithms"}
        ]
    },
    "biology": {
        "topic_title": "Molecular Biology: CRISPR-Cas9 Gene Editing & DNA Repair",
        "subject_category": "Biology",
        "difficulty_rating": 7,
        "executive_summary": "CRISPR-Cas9 provides RNA-guided endonuclease targeting of genomic loci. Binding requires protospacer adjacent motif (PAM) recognition, followed by guide RNA hybridisation and double-strand break induction repaired via non-homologous end joining (NHEJ) or homology-directed repair (HDR).",
        "key_concepts": [
            {
                "term": "PAM (Protospacer Adjacent Motif)",
                "definition": "A 2-6 base pair DNA sequence immediately following the target sequence (e.g. 5'-NGG-3' for SpCas9) required for Cas9 binding.",
                "exam_tip": "Cas9 will NEVER cleave target DNA if the PAM sequence is absent, regardless of sgRNA homology."
            },
            {
                "term": "Single Guide RNA (sgRNA)",
                "definition": "A synthetic chimera combining crRNA (target complementarity) and tracrRNA (Cas9 structural scaffold).",
                "exam_tip": "The standard target-specific spacer length is 20 nucleotides."
            },
            {
                "term": "NHEJ vs HDR Repair Pathways",
                "definition": "NHEJ is an error-prone end-ligation causing frameshift knockouts; HDR utilizes a donor template for precise gene knock-ins.",
                "exam_tip": "HDR is active primarily during S and G2 phases when sister chromatids exist."
            }
        ],
        "flashcards": [
            {
                "front": "What PAM sequence is recognized by Streptococcus pyogenes Cas9 (SpCas9)?",
                "back": "5'-NGG-3' (where N is any nucleotide).",
                "mnemonic": "SpCas9 loves N-G-G"
            },
            {
                "front": "What are the two structural components engineered into a single guide RNA (sgRNA)?",
                "back": "crRNA (CRISPR RNA for target binding) and tracrRNA (trans-activating crRNA for Cas9 scaffold).",
                "mnemonic": "crRNA targets, tracrRNA docks"
            },
            {
                "front": "Which DNA repair mechanism introduces insertions and deletions (indels) causing gene knockout?",
                "back": "Non-Homologous End Joining (NHEJ).",
                "mnemonic": "NHEJ = No Homology, Error Jumble"
            }
        ],
        "formula_sheet": [
            {
                "name": "Cas9 Endonuclease Cleavage Site",
                "formula_or_rule": "Cuts 3 base pairs upstream of the PAM motif",
                "application_notes": "Blunt double-strand break positioned within the protospacer target sequence."
            },
            {
                "name": "HDR Timing Invariant",
                "formula_or_rule": "HDR activity restricted to late S / G2 phases",
                "application_notes": "Requires presence of homologous sister chromatids or synthetic donor DNA."
            }
        ],
        "common_misconceptions": [
            {
                "myth": "Cas9 will bind and cleave any DNA sequence that perfectly matches its 20nt guide RNA.",
                "reality": "False. Target binding strictly fails if the adjacent PAM sequence is mutated or missing.",
                "why_it_matters": "Design algorithms must anchor all guide RNA searches around valid PAM loci."
            }
        ],
        "quiz_questions": [
            {
                "id": 1,
                "question": "What sequence motif must immediately flank target DNA for Streptococcus pyogenes Cas9 binding?",
                "options": ["TATA Box", "5'-NGG-3' PAM", "Poly-A Tail", "Kozak Sequence"],
                "correct_index": 1,
                "explanation": "SpCas9 specifically interrogates for the 5'-NGG-3' PAM sequence before unwinding DNA.",
                "subtopic_tag": "PAM Recognition"
            },
            {
                "id": 2,
                "question": "Which cellular DNA repair mechanism typically leads to gene disruption/knockout via insertions or deletions (indels)?",
                "options": ["Homology-Directed Repair (HDR)", "Non-Homologous End Joining (NHEJ)", "Base Excision Repair", "Mismatch Repair"],
                "correct_index": 1,
                "explanation": "NHEJ directly ligates blunt DNA ends without a template, frequently introducing indel frameshifts.",
                "subtopic_tag": "NHEJ Pathway"
            },
            {
                "id": 3,
                "question": "During which cell cycle phases is Homology-Directed Repair (HDR) predominantly active?",
                "options": ["G0 and G1 phases", "S and G2 phases", "M phase only", "Quiescence"],
                "correct_index": 1,
                "explanation": "HDR requires homologous repair templates, naturally available in S and G2 after DNA replication.",
                "subtopic_tag": "HDR Dynamics"
            },
            {
                "id": 4,
                "question": "What is the typical length of the target-complementary spacer in a standard single-guide RNA (sgRNA)?",
                "options": ["10 nucleotides", "20 nucleotides", "50 nucleotides", "100 nucleotides"],
                "correct_index": 1,
                "explanation": "Standard Cas9 sgRNAs utilize a 20-nucleotide spacer complementary to the genomic protospacer.",
                "subtopic_tag": "sgRNA Architecture"
            },
            {
                "id": 5,
                "question": "Which domain of Cas9 cleaves the DNA strand complementary to the gRNA?",
                "options": ["HNH endonuclease domain", "RuvC endonuclease domain", "REC1 domain", "PI domain"],
                "correct_index": 0,
                "explanation": "The HNH domain cleaves the target strand, while the RuvC domain cleaves the non-target strand.",
                "subtopic_tag": "Cas9 Domains"
            }
        ],
        "study_roadmap": [
            {"step_title": "Diagram PAM Interrogation and Strand Unwinding", "estimated_minutes": 20, "focus_area": "PAM Recognition"},
            {"step_title": "Compare NHEJ indel frequency vs HDR precision", "estimated_minutes": 25, "focus_area": "Repair Pathways"},
            {"step_title": "Review Prime Editing & Base Editing Advances", "estimated_minutes": 30, "focus_area": "Next-Gen Editing"}
        ]
    },
    "cs": {
        "topic_title": "Computer Science: Transformer Attention Mechanisms & KV-Caching",
        "subject_category": "Computer Science",
        "difficulty_rating": 9,
        "executive_summary": "Transformers discard recurrent bottlenecks in favor of Scaled Dot-Product Attention: Attention(Q,K,V) = softmax(QKᵀ / √d_k)V. Autoregressive inference utilizes Key-Value caching to reduce decoding computational complexity from O(N²) to O(N) per generated token.",
        "key_concepts": [
            {
                "term": "Scaled Dot-Product Attention",
                "definition": "Softmax-normalized similarity between Query and Key matrices scaled by 1/√d_k to prevent gradient vanishing in large dimensions.",
                "exam_tip": "Without the √d_k division, large inner products push softmax into regions with near-zero gradients."
            },
            {
                "term": "Key-Value (KV) Cache",
                "definition": "Stores past Keys and Values across attention layers during autoregressive token generation, avoiding redundant re-computation.",
                "exam_tip": "During token decoding, Query is shape [1, d], while cached K and V are shape [seq_len, d]."
            },
            {
                "term": "Multi-Head Attention (MHA)",
                "definition": "Projects Q, K, V into h independent subspaces, allowing the model to jointly attend to information at different positions.",
                "exam_tip": "Total parameter count remains comparable because head dimension d_k = d_model / h."
            }
        ],
        "flashcards": [
            {
                "front": "Why is the dot product QKᵀ divided by √d_k in Transformer attention?",
                "back": "To scale variance back to 1.0, preventing dot products from growing excessively large and causing vanishing gradients in softmax.",
                "mnemonic": "Scale down to keep gradients alive"
            },
            {
                "front": "What is the per-step time complexity of generating token T with KV-cache vs without?",
                "back": "With KV-cache: O(T) (linear). Without KV-cache: O(T²) (quadratic re-computation).",
                "mnemonic": "KV Cache flattens O(T²) to O(T)"
            },
            {
                "front": "How does Grouped-Query Attention (GQA) optimize standard Multi-Head Attention?",
                "back": "Multiple query heads share a single Key-Value head, shrinking KV-cache memory bandwidth while retaining model quality.",
                "mnemonic": "Many Queries, One KV head"
            }
        ],
        "formula_sheet": [
            {
                "name": "Scaled Dot-Product Attention",
                "formula_or_rule": "Attention(Q, K, V) = softmax((Q Kᵀ) / √d_k) V",
                "application_notes": "Q is shape [batch, heads, seq_q, d_k]; K is [batch, heads, seq_k, d_k]."
            },
            {
                "name": "KV Cache Memory Footprint (FP16)",
                "formula_or_rule": "Bytes = 2 * 2 * n_layers * n_kv_heads * d_head * seq_len * batch",
                "application_notes": "First '2' accounts for K and V; second '2' accounts for 2 bytes per float16 parameter."
            }
        ],
        "common_misconceptions": [
            {
                "myth": "Multi-Head Attention (MHA) increases total model parameters by a factor of h heads.",
                "reality": "False. Each head dimension d_k = d_model / h, so the total projection parameter count is equivalent to a single full-rank projection.",
                "why_it_matters": "Frequently tested in system architecture and parameter calculation exams."
            }
        ],
        "quiz_questions": [
            {
                "id": 1,
                "question": "Why is the dot-product QKᵀ scaled by 1/√d_k in transformer self-attention?",
                "options": [
                    "To prevent numerical overflow and mitigate vanishing gradients in softmax",
                    "To invert matrix singular values",
                    "To reduce memory footprint from O(N²) to O(N)",
                    "To guarantee positive definiteness"
                ],
                "correct_index": 0,
                "explanation": "For large d_k, dot products grow large in magnitude, pushing softmax into flat regions with tiny gradients.",
                "subtopic_tag": "Attention Scaling"
            },
            {
                "id": 2,
                "question": "What is the computational complexity of standard self-attention with respect to sequence length N?",
                "options": ["O(N)", "O(N log N)", "O(N²)", "O(2ᴺ)"],
                "correct_index": 2,
                "explanation": "Computing the N x N attention matrix QKᵀ requires quadratic O(N²) operations and memory.",
                "subtopic_tag": "Complexity Analysis"
            },
            {
                "id": 3,
                "question": "In autoregressive LLM decoding, what is the primary benefit of the Key-Value (KV) cache?",
                "options": [
                    "Reduces training loss convergence epochs",
                    "Avoids recomputing previous tokens' K and V projections during generation",
                    "Eliminates the need for positional embeddings",
                    "Bypasses the feed-forward projection layers"
                ],
                "correct_index": 1,
                "explanation": "Past prompt and generated token representations are fixed, so caching K and V avoids redundant recalculation.",
                "subtopic_tag": "KV-Caching"
            },
            {
                "id": 4,
                "question": "What type of mask is applied to prevent attending to future tokens during decoder self-attention?",
                "options": ["Padding mask", "Causal / Upper-triangular mask", "Bidirectional mask", "Dropout mask"],
                "correct_index": 1,
                "explanation": "A causal mask sets attention logits for future positions (j > i) to -∞ so softmax assigns 0 probability.",
                "subtopic_tag": "Causal Masking"
            },
            {
                "id": 5,
                "question": "How does Grouped-Query Attention (GQA) reduce KV-cache memory bandwidth compared to standard MHA?",
                "options": [
                    "Multiple query heads share a single Key and Value head",
                    "Keys and Values are compressed with lossy PCA",
                    "Query vectors are quantized to 1-bit representations",
                    "Attention weights are replaced with state-space recurrence"
                ],
                "correct_index": 0,
                "explanation": "GQA partitions query heads into groups where each group shares one KV head, significantly shrinking KV cache size.",
                "subtopic_tag": "Grouped-Query Attention"
            }
        ],
        "study_roadmap": [
            {"step_title": "Derive Softmax Gradient under High Magnitude Inputs", "estimated_minutes": 25, "focus_area": "Attention Scaling"},
            {"step_title": "Profile KV-Cache GPU Memory Formula: 2 * 2 * n_layers * n_heads * d_head * seq_len", "estimated_minutes": 30, "focus_area": "KV-Caching"},
            {"step_title": "Implement FlashAttention Tiling Concept in PyTorch/NumPy", "estimated_minutes": 45, "focus_area": "Kernel Optimization"}
        ]
    }
}


def build_dynamic_demo_pack(notes: str, subject_hint: Optional[str] = None) -> StudyPackSchema:
    """
    Intelligently generates a realistic, domain-specific StudyPackSchema
    when running in offline Demo Mode or when API keys are not provided.
    """
    combined_text = f"{subject_hint or ''} {notes}".lower()

    if any(k in combined_text for k in ["calc", "deriv", "integr", "gradient", "math", "hessian"]):
        chosen = DEMO_TOPIC_BANKS["calculus"]
    elif any(k in combined_text for k in ["bio", "cell", "crispr", "gene", "dna", "protein", "mitochon", "atp"]):
        chosen = DEMO_TOPIC_BANKS["biology"]
    elif any(k in combined_text for k in ["transf", "attent", "llm", "neural", "comput", "softw", "code", "ai", "raft", "distrib"]):
        chosen = DEMO_TOPIC_BANKS["cs"]
    else:
        # Construct an adaptive pack using terms extracted from user input
        clean_lines = [line.strip() for line in notes.split("\n") if len(line.strip()) > 8]
        first_line = clean_lines[0] if clean_lines else "Academic Foundations & Systems Mastery"
        second_line = clean_lines[1] if len(clean_lines) > 1 else "Mechanistic models and empirical constraints"
        subject_title = (subject_hint or "Interdisciplinary Studies").strip()

        chosen = {
            "topic_title": f"{subject_title}: {first_line[:48]}",
            "subject_category": subject_title if len(subject_title) > 2 else "General Academic",
            "difficulty_rating": 7,
            "executive_summary": f"Comprehensive synthesis derived from raw study notes. Focuses on structural mechanisms, analytical rigor, and core heuristics needed for exam mastery and application: {first_line[:120]}.",
            "key_concepts": [
                {
                    "term": "First-Principles Conceptual Anchor",
                    "definition": f"Core conceptual basis extracted from notes: '{first_line[:80]}...'",
                    "exam_tip": "High frequency topic on technical exams; prioritize understanding the underlying mechanism."
                },
                {
                    "term": "Systemic Invariant Rule",
                    "definition": f"Governing boundary condition: {second_line[:80]}...",
                    "exam_tip": "Watch out for edge-case boundary conditions and constraint violations."
                },
                {
                    "term": "Operational Throughput & Tradeoffs",
                    "definition": "Analyzing efficiency, latency, accuracy, and degradation limits under elevated workload conditions.",
                    "exam_tip": "Clearly articulate trade-offs rather than proposing absolute unconstrained solutions."
                }
            ],
            "flashcards": [
                {
                    "front": f"What is the foundational premise of {first_line[:40]}?",
                    "back": f"Rooted in systematic decomposition: {second_line[:80]}",
                    "mnemonic": "Decompose before solving"
                },
                {
                    "front": "What happens when system boundary constraints are breached?",
                    "back": "Loss of convergence, non-deterministic state degradation, or cascading failure.",
                    "mnemonic": "Bounds guarantee stability"
                },
                {
                    "front": "What heuristic should guide diagnostic evaluation under edge-case stress?",
                    "back": "Isolate single variables and verify against verified baseline controls.",
                    "mnemonic": "Control vs Variable"
                }
            ],
            "formula_sheet": [
                {
                    "name": "System Governing Relationship",
                    "formula_or_rule": "System Efficiency η = Work_Output / Total_Resource_Input ≤ 1.0",
                    "application_notes": "Conservation boundary principle across closed physical or computational bounds."
                }
            ],
            "common_misconceptions": [
                {
                    "myth": "Superficial heuristic pattern matching is sufficient for advanced exam diagnostics.",
                    "reality": "Rigorous first-principles mechanistic decomposition is required to avoid edge-case traps.",
                    "why_it_matters": "Distinguishes high-scoring analytical mastery from rote memorization."
                }
            ],
            "quiz_questions": [
                {
                    "id": 1,
                    "question": f"Which foundational principle is most critical when evaluating {first_line[:30]}?",
                    "options": [
                        "Direct first-principles mechanistic decomposition",
                        "Superficial heuristic pattern matching",
                        "Ignoring secondary constraint boundaries",
                        "Relying exclusively on unverified assumptions"
                    ],
                    "correct_index": 0,
                    "explanation": "First-principles decomposition guarantees systematic isolation of core variables without compounding bias.",
                    "subtopic_tag": "Mechanistic Analysis"
                },
                {
                    "id": 2,
                    "question": "What is the primary operational consequence when an invariant constraint boundary is breached?",
                    "options": [
                        "Predictable linear acceleration",
                        "Cascading failure or non-convergent state",
                        "Guaranteed error-free output",
                        "Zero impact on system behavior"
                    ],
                    "correct_index": 1,
                    "explanation": "Violating system invariants destroys inductive stability and results in non-convergent states.",
                    "subtopic_tag": "Invariant Constraints"
                },
                {
                    "id": 3,
                    "question": "Under high-stress or edge-case conditions, what metric should be prioritized first?",
                    "options": [
                        "Aesthetic simplicity",
                        "Correctness and bounded failure modes",
                        "Premature optimization",
                        "Unmonitored execution speed"
                    ],
                    "correct_index": 1,
                    "explanation": "Correctness and predictable bounded failure prevent catastrophic cascading degradation.",
                    "subtopic_tag": "Failure Modes"
                },
                {
                    "id": 4,
                    "question": "How do verified empirical models differ from preliminary hypothetical conjectures?",
                    "options": [
                        "Empirical models demonstrate reproducible predictive accuracy across distinct trials",
                        "Empirical models require no evidentiary validation",
                        "Conjectures have higher statistical confidence",
                        "They are mathematically interchangeable"
                    ],
                    "correct_index": 0,
                    "explanation": "Empirical models are characterized by falsifiability, reproducibility, and verified predictive validity.",
                    "subtopic_tag": "Epistemological Validity"
                },
                {
                    "id": 5,
                    "question": "What is the recommended iterative protocol when encountering anomalous diagnostics?",
                    "options": [
                        "Immediately discard previous telemetry data",
                        "Formulate an isolated hypothesis and test against baseline controls",
                        "Accept the anomaly as standard baseline",
                        "Accelerate the workload to overwrite the error"
                    ],
                    "correct_index": 1,
                    "explanation": "Scientific troubleshooting requires isolating single variables and comparing responses against clean baselines.",
                    "subtopic_tag": "Diagnostic Methodology"
                }
            ],
            "study_roadmap": [
                {"step_title": "Synthesize Core Definitions into Anki Decks", "estimated_minutes": 20, "focus_area": "Active Recall"},
                {"step_title": "Work Through 5 Edge-Case Boundary Problems", "estimated_minutes": 35, "focus_area": "Problem Solving"},
                {"step_title": "Conduct Teach-Back Feynman Review", "estimated_minutes": 25, "focus_area": "Feynman Technique"}
            ]
        }

    return StudyPackSchema.model_validate(chosen)


# -------------------------------------------------------------
# 3. Main AI Orchestration Function
# -------------------------------------------------------------
def generate_study_pack(
    notes: str,
    subject_hint: Optional[str] = None,
    demo_mode: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transforms raw study notes into a structured StudyPackSchema.
    - If `demo_mode=True` or `GEMINI_API_KEY` is absent: Uses adaptive zero-config mock.
    - If `GEMINI_API_KEY` is present: Uses `gemini-2.5-flash` with structured Pydantic schema.
    Returns:
        dict: The serialized study pack + metadata ('ai_mode', 'status_note').
    """
    effective_api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()

    # Instant Zero-Config Fallback when requested or no key configured
    if demo_mode or not effective_api_key or effective_api_key.startswith("your_api_key"):
        logger.info("Executing Study Pack generation in Zero-Config Demo Mode.")
        pack = build_dynamic_demo_pack(notes, subject_hint)
        data = pack.model_dump()
        data["ai_mode"] = "demo"
        data["status_note"] = "Generated via Offline Academic Engine (Zero-Config Mode)."
        return data

    # Live Gemini 2.5 Flash API execution
    try:
        logger.info("Connecting to Google Gemini API using gemini-2.5-flash...")
        client = genai.Client(api_key=effective_api_key)

        system_instruction = (
            "You are Cognify, an elite Academic & Exam Architect. Your mission is to take raw study notes, "
            "lecture transcripts, or textbook excerpts and transform them into an authoritative, high-yield study pack.\n"
            "Requirements:\n"
            "1. Produce an authoritative topic title and categorize into a canonical academic subject.\n"
            "2. Assess difficulty from 1 (Introductory) to 10 (Graduate / Olympiad).\n"
            "3. Formulate an executive summary that synthesizes foundational mental models.\n"
            "4. Extract 3 to 6 key concepts with clear terms, rigorous definitions, and practical exam tips.\n"
            "5. Generate 4 to 8 active recall flashcards (front, back, and mnemonic).\n"
            "6. Formulate 2 to 4 core governing formulas or formal rules with application notes.\n"
            "7. Identify 2 to 3 common exam misconceptions/myths, the reality, and why test-makers target them.\n"
            "8. Generate exactly 5 challenging multiple-choice active recall questions (with 4 choices, 0-based correct index, "
            "deep pedagogical explanations, and specific subtopic tags).\n"
            "9. Formulate exactly 3 actionable, timed study roadmap tasks."
        )

        user_content = (
            f"Subject Context: {subject_hint or 'General Academic / Interdisciplinary'}\n\n"
            f"Raw Lecture Notes / Excerpt:\n\"\"\"\n{notes.strip()}\n\"\"\""
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[system_instruction, user_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StudyPackSchema,
                temperature=0.3,
            )
        )

        if not response.text:
            raise ValueError("Empty response received from Gemini API.")

        validated_pack = StudyPackSchema.model_validate_json(response.text)
        data = validated_pack.model_dump()
        data["ai_mode"] = "gemini"
        data["status_note"] = "Generated live via Google Gemini 2.5 Flash."
        return data

    except Exception as exc:
        logger.warning(f"Gemini API invocation encountered an issue ({exc}). Falling back gracefully to Demo Mode.")
        fallback_pack = build_dynamic_demo_pack(notes, subject_hint)
        data = fallback_pack.model_dump()
        data["ai_mode"] = "demo_fallback"
        data["status_note"] = f"Live API issue ({str(exc)[:60]}...). Gracefully activated Demo Mode."
        return data


if __name__ == "__main__":
    print("Testing ai_engine in Zero-Config Demo Mode...")
    sample_notes = "Gradient descent is an optimization algorithm used to minimize loss functions by stepping opposite the gradient."
    pack = generate_study_pack(sample_notes, subject_hint="Calculus", demo_mode=True)
    print("Study Pack Generated Successfully:")
    print(f"Title: {pack['topic_title']}")
    print(f"Subject: {pack['subject_category']}")
    print(f"Concepts: {len(pack['key_concepts'])}")
    print(f"Flashcards: {len(pack.get('flashcards', []))}")
    print(f"Formulas: {len(pack.get('formula_sheet', []))}")
    print(f"Misconceptions: {len(pack.get('common_misconceptions', []))}")
    print(f"Questions: {len(pack['quiz_questions'])}")
    print(f"Roadmap Steps: {len(pack['study_roadmap'])}")
    print(f"AI Mode: {pack['ai_mode']}")
