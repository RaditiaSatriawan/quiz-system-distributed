"""
Quiz Service – Flask REST/RPC API
Runs on port 6000.
"""

import logging
import json
from datetime import datetime, date
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import (
    init_db,
    create_quiz,
    get_quiz,
    get_all_quizzes,
    update_quiz,
    delete_quiz,
    create_question,
    get_questions_by_quiz,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quiz-service")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


# Custom JSON encoder to handle datetime / date objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


app.json_provider_class = None  # use custom serialisation below


def _jsonify(data, status=200):
    """Return a JSON response with proper datetime serialisation."""
    body = json.dumps(data, cls=CustomJSONEncoder)
    return app.response_class(body, status=status, mimetype="application/json")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return _jsonify({"status": "healthy", "service": "quiz-service"})


# ---------------------------------------------------------------------------
# Quiz routes
# ---------------------------------------------------------------------------
@app.route("/rpc/quiz/create", methods=["POST"])
def rpc_create_quiz():
    """Create a new quiz."""
    try:
        data = request.get_json(force=True)
        title = data.get("title")
        if not title:
            return _jsonify({"error": "title is required"}, 400)

        quiz = create_quiz(
            title=title,
            description=data.get("description"),
            time_limit_minutes=data.get("time_limit_minutes", 30),
        )
        logger.info("Quiz created: %s", quiz["id"])
        return _jsonify({"message": "Quiz created successfully", "quiz": quiz}, 201)
    except Exception as exc:
        logger.exception("Error creating quiz")
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/quiz/list", methods=["GET"])
def rpc_list_quizzes():
    """List all quizzes."""
    try:
        quizzes = get_all_quizzes()
        return _jsonify({"quizzes": quizzes, "count": len(quizzes)})
    except Exception as exc:
        logger.exception("Error listing quizzes")
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/quiz/<int:quiz_id>", methods=["GET"])
def rpc_get_quiz(quiz_id):
    """Get a quiz by ID including its questions."""
    try:
        quiz = get_quiz(quiz_id)
        if not quiz:
            return _jsonify({"error": "Quiz not found"}, 404)

        questions = get_questions_by_quiz(quiz_id)
        quiz["questions"] = questions
        return _jsonify({"quiz": quiz})
    except Exception as exc:
        logger.exception("Error fetching quiz %s", quiz_id)
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/quiz/<int:quiz_id>", methods=["PUT"])
def rpc_update_quiz(quiz_id):
    """Update an existing quiz."""
    try:
        data = request.get_json(force=True)
        quiz = update_quiz(
            quiz_id,
            title=data.get("title"),
            description=data.get("description"),
            time_limit_minutes=data.get("time_limit_minutes"),
        )
        if not quiz:
            return _jsonify({"error": "Quiz not found"}, 404)

        logger.info("Quiz updated: %s", quiz_id)
        return _jsonify({"message": "Quiz updated successfully", "quiz": quiz})
    except Exception as exc:
        logger.exception("Error updating quiz %s", quiz_id)
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/quiz/<int:quiz_id>", methods=["DELETE"])
def rpc_delete_quiz(quiz_id):
    """Delete a quiz and its questions (CASCADE)."""
    try:
        deleted = delete_quiz(quiz_id)
        if not deleted:
            return _jsonify({"error": "Quiz not found"}, 404)

        logger.info("Quiz deleted: %s", quiz_id)
        return _jsonify({"message": "Quiz deleted successfully"})
    except Exception as exc:
        logger.exception("Error deleting quiz %s", quiz_id)
        return _jsonify({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# Question routes
# ---------------------------------------------------------------------------
@app.route("/rpc/quiz/<int:quiz_id>/question", methods=["POST"])
def rpc_add_question(quiz_id):
    """Add a question to a quiz."""
    try:
        # Verify quiz exists
        quiz = get_quiz(quiz_id)
        if not quiz:
            return _jsonify({"error": "Quiz not found"}, 404)

        data = request.get_json(force=True)

        # Validate required fields
        required = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return _jsonify({"error": f"Missing required fields: {', '.join(missing)}"}, 400)

        correct = data["correct_answer"].lower()
        if correct not in ("a", "b", "c", "d"):
            return _jsonify({"error": "correct_answer must be one of: a, b, c, d"}, 400)

        question = create_question(
            quiz_id=quiz_id,
            question_text=data["question_text"],
            option_a=data["option_a"],
            option_b=data["option_b"],
            option_c=data["option_c"],
            option_d=data["option_d"],
            correct_answer=correct,
            points=data.get("points", 10),
        )
        logger.info("Question added to quiz %s: question_id=%s", quiz_id, question["id"])
        return _jsonify({"message": "Question added successfully", "question": question}, 201)
    except Exception as exc:
        logger.exception("Error adding question to quiz %s", quiz_id)
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/quiz/<int:quiz_id>/questions", methods=["GET"])
def rpc_get_questions(quiz_id):
    """Get all questions for a quiz."""
    try:
        quiz = get_quiz(quiz_id)
        if not quiz:
            return _jsonify({"error": "Quiz not found"}, 404)

        questions = get_questions_by_quiz(quiz_id)
        return _jsonify({"quiz_id": quiz_id, "questions": questions, "count": len(questions)})
    except Exception as exc:
        logger.exception("Error fetching questions for quiz %s", quiz_id)
        return _jsonify({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Initialising database tables …")
    init_db()
    logger.info("Starting Quiz Service on port 6000")
    app.run(host="0.0.0.0", port=6000, debug=False)
