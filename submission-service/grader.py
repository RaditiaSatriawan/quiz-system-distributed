"""
Auto-grading logic for the Submission Service.

Fetches correct answers from the Quiz Service via HTTP,
compares them with student answers stored locally,
computes a percentage score, and persists the result.
"""

import os
import logging
import requests
from models import get_submission, get_answers_by_submission, update_submission_score

logger = logging.getLogger(__name__)

QUIZ_SERVICE_URL = os.environ.get("QUIZ_SERVICE_URL", "http://quiz-service:6000")


def grade_submission(submission_id):
    """
    Grade a single submission.

    Steps:
      1. Fetch the submission from the local DB.
      2. Fetch the quiz (with questions) from quiz-service via HTTP.
      3. Fetch the student's answers from the local DB.
      4. Compare each answer with the correct answer.
      5. Calculate score as (earned_points / total_points) * 100.
      6. Persist score + status='graded' + graded_at.
      7. Return a result dict.
    """
    logger.info("Starting grading for submission_id=%s", submission_id)

    # 1 – Load submission
    submission = get_submission(submission_id)
    if not submission:
        error_msg = f"Submission {submission_id} not found"
        logger.error(error_msg)
        raise ValueError(error_msg)

    quiz_id = submission["quiz_id"]

    # 2 – Fetch quiz + questions from quiz-service
    quiz_url = f"{QUIZ_SERVICE_URL}/rpc/quiz/{quiz_id}"
    logger.info("Fetching quiz from %s", quiz_url)

    resp = requests.get(quiz_url, timeout=10)
    if resp.status_code != 200:
        error_msg = f"Failed to fetch quiz {quiz_id}: HTTP {resp.status_code}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    quiz_data = resp.json().get("quiz", {})
    questions = quiz_data.get("questions", [])

    if not questions:
        logger.warning("Quiz %s has no questions – scoring 0", quiz_id)
        update_submission_score(submission_id, 0.0, status="graded")
        return {
            "submission_id": submission_id,
            "score": 0.0,
            "correct_count": 0,
            "total_questions": 0,
            "status": "graded",
        }

    # Build lookup: question_id -> {correct_answer, points}
    question_map = {
        q["id"]: {"correct_answer": q["correct_answer"].lower(), "points": q.get("points", 10)}
        for q in questions
    }

    # 3 – Load student answers
    answers = get_answers_by_submission(submission_id)

    # 4 – Compare
    correct_count = 0
    earned_points = 0
    total_points = sum(q["points"] for q in question_map.values())

    for ans in answers:
        qid = ans["question_id"]
        selected = ans["selected_answer"].lower()
        q_info = question_map.get(qid)
        if q_info and selected == q_info["correct_answer"]:
            correct_count += 1
            earned_points += q_info["points"]

    # 5 – Calculate percentage score
    score = round((earned_points / total_points) * 100, 2) if total_points > 0 else 0.0

    # 6 – Persist
    update_submission_score(submission_id, score, status="graded")

    result = {
        "submission_id": submission_id,
        "score": score,
        "correct_count": correct_count,
        "total_questions": len(questions),
        "earned_points": earned_points,
        "total_points": total_points,
        "status": "graded",
        "quiz_title": quiz_data.get("title", "Unknown Quiz"),
    }
    logger.info("Grading complete for submission_id=%s: %s", submission_id, result)
    return result
