"""
Submission Service – Flask REST/RPC API
Runs on port 7000.
"""

import logging
import json
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request
from flask_cors import CORS
from models import (
    init_db,
    create_submission,
    get_submission,
    get_all_submissions,
    create_answer,
    get_answers_by_submission,
)
from rabbitmq_consumer import start_consumer_thread, publish_grading_task

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("submission-service")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


# Custom JSON encoder
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _jsonify(data, status=200):
    """Return a JSON response with proper datetime/Decimal serialisation."""
    body = json.dumps(data, cls=CustomJSONEncoder)
    return app.response_class(body, status=status, mimetype="application/json")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return _jsonify({"status": "healthy", "service": "submission-service"})


# ---------------------------------------------------------------------------
# Submission routes
# ---------------------------------------------------------------------------
@app.route("/rpc/submission/create", methods=["POST"])
def rpc_create_submission():
    """
    Create a new submission.

    Expected JSON body:
    {
        "student_name": "John",
        "quiz_id": 1,
        "answers": [
            {"question_id": 1, "selected_answer": "a"},
            {"question_id": 2, "selected_answer": "c"}
        ]
    }
    """
    try:
        data = request.get_json(force=True)

        student_name = data.get("student_name")
        quiz_id = data.get("quiz_id")
        answers = data.get("answers", [])

        # Validate
        if not student_name:
            return _jsonify({"error": "student_name is required"}, 400)
        if quiz_id is None:
            return _jsonify({"error": "quiz_id is required"}, 400)
        if not answers:
            return _jsonify({"error": "answers list is required and cannot be empty"}, 400)

        # 1 – Create submission record
        submission = create_submission(student_name=student_name, quiz_id=quiz_id)
        submission_id = submission["id"]

        # 2 – Create answer records
        saved_answers = []
        for ans in answers:
            qid = ans.get("question_id")
            sel = ans.get("selected_answer")
            if qid is None or sel is None:
                continue  # skip malformed entries
            answer = create_answer(
                submission_id=submission_id,
                question_id=qid,
                selected_answer=sel,
            )
            saved_answers.append(answer)

        # 3 – Publish to grading queue
        try:
            publish_grading_task(submission_id)
            logger.info("Grading task published for submission_id=%s", submission_id)
        except Exception:
            logger.exception(
                "Failed to publish grading task for submission_id=%s – will be graded later",
                submission_id,
            )

        # 4 – Return response
        return _jsonify(
            {
                "message": "Submission created successfully",
                "submission": submission,
                "answers_saved": len(saved_answers),
                "status": "pending",
            },
            201,
        )

    except Exception as exc:
        logger.exception("Error creating submission")
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/submission/list", methods=["GET"])
def rpc_list_submissions():
    """List all submissions."""
    try:
        submissions = get_all_submissions()
        return _jsonify({"submissions": submissions, "count": len(submissions)})
    except Exception as exc:
        logger.exception("Error listing submissions")
        return _jsonify({"error": str(exc)}, 500)


@app.route("/rpc/submission/<int:submission_id>", methods=["GET"])
def rpc_get_submission(submission_id):
    """Get a single submission with its answers."""
    try:
        submission = get_submission(submission_id)
        if not submission:
            return _jsonify({"error": "Submission not found"}, 404)

        answers = get_answers_by_submission(submission_id)
        submission["answers"] = answers
        return _jsonify({"submission": submission})
    except Exception as exc:
        logger.exception("Error fetching submission %s", submission_id)
        return _jsonify({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Initialising database tables …")
    init_db()

    logger.info("Starting RabbitMQ consumer thread …")
    start_consumer_thread()

    logger.info("Starting Submission Service on port 7000")
    app.run(host="0.0.0.0", port=7000, debug=False)
