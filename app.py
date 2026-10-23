"""
app.py - Cognify Flask REST API Server & View Controller
Serves the decoupled dashboard, runs the AI engine, coordinates SQLite, analytics,
and exports study packs into Markdown and Anki deck formats.
Runs on port 5001.
"""

import io
import json
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file

import ai_engine
import analytics
import database

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger("cognify.app")

# Initialize Flask application
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static"
)
app.config["JSON_SORT_KEYS"] = False

# Ensure database exists and is seeded on startup
database.init_db()


# -------------------------------------------------------------
# Web Page Route
# -------------------------------------------------------------
@app.route("/")
def index():
    """Renders the main Cognify workspace interface."""
    return render_template("index.html")


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    """
    Returns high-level telemetry KPIs, system AI mode status,
    recent study sessions, and recent quiz attempts.
    """
    try:
        kpis = database.get_dashboard_kpis()
        recent_sessions = database.get_all_study_sessions(limit=25)
        recent_attempts = database.get_all_quiz_attempts(limit=15)

        # Detect active Gemini API configuration
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        has_api_key = bool(env_key and not env_key.startswith("your_api_key"))

        ai_status = {
            "has_api_key": has_api_key,
            "mode": "gemini" if has_api_key else "demo",
            "model_name": "gemini-2.5-flash" if has_api_key else "Zero-Config Academic Engine",
            "badge_label": "Gemini 2.5 Flash Active" if has_api_key else "Zero-Config Offline Mode"
        }

        return jsonify({
            "status": "success",
            "kpis": kpis,
            "ai_mode_status": ai_status,
            "recent_sessions": recent_sessions,
            "recent_attempts": recent_attempts
        })
    except Exception as exc:
        logger.error(f"Error fetching dashboard metrics: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_study_pack():
    """
    Transforms raw study notes into structured concept breakdowns,
    flashcards, formula sheets, a 5-question active recall quiz, and a study roadmap.
    Persists the result to SQLite and returns the session payload.
    """
    try:
        data = request.get_json(silent=True) or {}
        notes = data.get("notes", "").strip()
        subject_hint = data.get("subject_hint", "").strip()
        demo_mode = bool(data.get("demo_mode", False))
        request_api_key = data.get("api_key") or request.headers.get("X-Gemini-API-Key")

        if not notes:
            return jsonify({
                "status": "error",
                "message": "Study notes or textbook excerpts cannot be empty."
            }), 400

        # Run structured AI generation pipeline
        pack_data = ai_engine.generate_study_pack(
            notes=notes,
            subject_hint=subject_hint,
            demo_mode=demo_mode,
            api_key=request_api_key
        )

        # Persist session to SQLite
        session_id = database.save_study_session(
            topic_title=pack_data["topic_title"],
            subject_category=pack_data["subject_category"],
            difficulty_rating=pack_data["difficulty_rating"],
            payload_json=json.dumps(pack_data)
        )

        pack_data["session_id"] = session_id

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "study_pack": pack_data
        }), 201

    except Exception as exc:
        logger.error(f"Error generating study pack: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/session/<int:session_id>", methods=["GET"])
def get_session(session_id: int):
    """Retrieves a previously saved study session by ID."""
    try:
        record = database.get_study_session(session_id)
        if not record:
            return jsonify({"status": "error", "message": f"Session #{session_id} not found."}), 404

        pack_data = json.loads(record["payload_json"])
        pack_data["session_id"] = record["id"]
        pack_data["created_at"] = record["created_at"]

        return jsonify({
            "status": "success",
            "session": pack_data
        })
    except Exception as exc:
        logger.error(f"Error fetching session #{session_id}: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/session/<int:session_id>", methods=["DELETE"])
def delete_session(session_id: int):
    """Deletes a saved study session and associated records."""
    try:
        success = database.delete_study_session(session_id)
        if not success:
            return jsonify({"status": "error", "message": f"Session #{session_id} not found."}), 404

        return jsonify({
            "status": "success",
            "message": f"Study session #{session_id} deleted successfully."
        })
    except Exception as exc:
        logger.error(f"Error deleting session #{session_id}: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/submit_quiz", methods=["POST"])
def submit_quiz():
    """
    Submits a completed quiz attempt, logs telemetry to SQLite,
    and returns updated KPIs to dynamically trigger chart refreshes.
    """
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        subject_category = (data.get("subject_category") or "General Academic").strip()
        score_pct = float(data.get("score_pct", 0.0))
        time_spent_sec = int(data.get("time_spent_sec", 0))
        weak_subtopics = data.get("weak_subtopics", [])

        attempt_id = database.log_quiz_attempt(
            session_id=session_id,
            subject_category=subject_category,
            score_pct=score_pct,
            time_spent_sec=time_spent_sec,
            weak_subtopics=weak_subtopics
        )

        updated_kpis = database.get_dashboard_kpis()

        return jsonify({
            "status": "success",
            "attempt_id": attempt_id,
            "score_pct": score_pct,
            "updated_kpis": updated_kpis
        }), 201

    except Exception as exc:
        logger.error(f"Error submitting quiz attempt: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/flashcard/review", methods=["POST"])
def review_flashcard():
    """Logs a flashcard spaced-repetition rating ('again', 'hard', 'good', 'easy')."""
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        card_index = int(data.get("card_index", 0))
        rating = str(data.get("rating", "good")).lower()

        review_id = database.log_flashcard_review(session_id, card_index, rating)
        return jsonify({"status": "success", "review_id": review_id, "rating": rating})
    except Exception as exc:
        logger.error(f"Error logging flashcard review: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/analytics.png", methods=["GET"])
def get_analytics_chart():
    """
    Renders and streams the live Matplotlib telemetry figure.
    Query param 'view': 'mastery' (default) or 'diagnostics'.
    Includes cache-busting headers to ensure immediate browser rendering updates.
    """
    try:
        view_mode = request.args.get("view", "mastery")
        png_bytes = analytics.generate_telemetry_chart(view_mode=view_mode)
        response = Response(png_bytes, mimetype="image/png")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as exc:
        logger.error(f"Error rendering analytics chart: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to generate analytics image."}), 500


# -------------------------------------------------------------
# Export Endpoints (Markdown & Anki TSV)
# -------------------------------------------------------------
@app.route("/api/export/<int:session_id>/markdown", methods=["GET"])
def export_markdown(session_id: int):
    """Generates and downloads a clean, publication-ready Markdown study guide."""
    try:
        record = database.get_study_session(session_id)
        if not record:
            return jsonify({"status": "error", "message": "Session not found."}), 404

        pack = json.loads(record["payload_json"])
        
        md_lines = [
            f"# {pack.get('topic_title', 'Study Guide')}",
            f"**Discipline:** {pack.get('subject_category', 'General')} | **Difficulty:** {pack.get('difficulty_rating', 7)}/10",
            f"*Generated by Cognify AI Academic Architect*\n",
            "## Executive Summary",
            f"{pack.get('executive_summary', '')}\n",
            "## Key Concepts",
        ]

        for c in pack.get("key_concepts", []):
            md_lines.append(f"### {c.get('term', '')}")
            md_lines.append(f"- **Definition:** {c.get('definition', '')}")
            if c.get("exam_tip"):
                md_lines.append(f"- **Exam Tip:** {c.get('exam_tip', '')}")
            md_lines.append("")

        if pack.get("formula_sheet"):
            md_lines.append("## Core Formulas & Rules")
            for f in pack.get("formula_sheet", []):
                md_lines.append(f"- **{f.get('name', '')}:** `{f.get('formula_or_rule', '')}`")
                md_lines.append(f"  *Application:* {f.get('application_notes', '')}")
            md_lines.append("")

        if pack.get("common_misconceptions"):
            md_lines.append("## Common Exam Traps & Misconceptions")
            for m in pack.get("common_misconceptions", []):
                md_lines.append(f"- ❌ **Trap/Myth:** {m.get('myth', '')}")
                md_lines.append(f"  ✅ **Academic Reality:** {m.get('reality', '')}")
                md_lines.append(f"  ⚠️ *Why it matters:* {m.get('why_it_matters', '')}")
            md_lines.append("")

        if pack.get("flashcards"):
            md_lines.append("## Flashcards")
            for idx, fc in enumerate(pack.get("flashcards", []), 1):
                md_lines.append(f"**Q{idx}:** {fc.get('front', '')}")
                md_lines.append(f"**A{idx}:** {fc.get('back', '')}")
                if fc.get("mnemonic"):
                    md_lines.append(f"*Mnemonic:* {fc.get('mnemonic', '')}")
                md_lines.append("")

        if pack.get("study_roadmap"):
            md_lines.append("## 3-Step Study Roadmap")
            for idx, step in enumerate(pack.get("study_roadmap", []), 1):
                md_lines.append(f"{idx}. **{step.get('step_title', '')}** (~{step.get('estimated_minutes', 20)} min)")
                md_lines.append(f"   Focus: {step.get('focus_area', '')}")
            md_lines.append("")

        content = "\n".join(md_lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        
        safe_title = "".join(ch for ch in pack.get('topic_title', 'study_guide') if ch.isalnum() or ch in ('_', '-'))[:32]
        filename = f"cognify_{safe_title}_{session_id}.md"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="text/markdown"
        )
    except Exception as exc:
        logger.error(f"Error exporting markdown: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/export/<int:session_id>/anki", methods=["GET"])
def export_anki(session_id: int):
    """Generates and downloads a tab-separated text file formatted for Anki deck import."""
    try:
        record = database.get_study_session(session_id)
        if not record:
            return jsonify({"status": "error", "message": "Session not found."}), 404

        pack = json.loads(record["payload_json"])
        flashcards = pack.get("flashcards", [])
        
        # If no explicit flashcards exist, build cards from key concepts
        if not flashcards:
            flashcards = [
                {
                    "front": f"What is {c.get('term')}?",
                    "back": f"{c.get('definition')} (Tip: {c.get('exam_tip', '')})",
                    "mnemonic": ""
                }
                for c in pack.get("key_concepts", [])
            ]

        # Anki TSV format: Front \t Back \t Tags
        tag = "".join(ch for ch in pack.get('subject_category', 'Cognify') if ch.isalnum())
        lines = ["#separator:tab", "#html:true", "#tags column:3"]

        for fc in flashcards:
            front = fc.get("front", "").replace("\t", " ")
            back = fc.get("back", "").replace("\t", " ")
            if fc.get("mnemonic"):
                back += f"<br><br><i>Mnemonic:</i> {fc.get('mnemonic')}"
            lines.append(f"{front}\t{back}\t{tag}")

        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))

        safe_title = "".join(ch for ch in pack.get('topic_title', 'anki_deck') if ch.isalnum() or ch in ('_', '-'))[:32]
        filename = f"cognify_anki_{safe_title}_{session_id}.txt"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="text/tab-separated-values"
        )
    except Exception as exc:
        logger.error(f"Error exporting Anki deck: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/reset_demo", methods=["POST"])
def reset_demo_data():
    """Resets the SQLite database to factory seed data."""
    try:
        database.reset_and_seed_db()
        return jsonify({
            "status": "success",
            "message": "Database successfully reset and re-seeded with 12 historical telemetry attempts."
        })
    except Exception as exc:
        logger.error(f"Error resetting database: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


# -------------------------------------------------------------
# Server Entrypoint
# -------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    logger.info(f"Starting Cognify Server at http://{host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug, threaded=True)
