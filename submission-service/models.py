"""
Database helper module for Submission Service.
Uses psycopg2 directly for PostgreSQL operations.
"""

import os
import logging
from datetime import datetime
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db_connection():
    """Create and return a new PostgreSQL connection using environment variables."""
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "submission-db"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "submission_db"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
    )
    conn.autocommit = True
    return conn


def init_db():
    """Create tables if they do not exist."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id            SERIAL PRIMARY KEY,
                    student_name  VARCHAR(255) NOT NULL,
                    quiz_id       INTEGER NOT NULL,
                    score         NUMERIC(5,2),
                    status        VARCHAR(20) DEFAULT 'pending'
                                  CHECK (status IN ('pending','grading','graded')),
                    submitted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    graded_at     TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submission_answers (
                    id              SERIAL PRIMARY KEY,
                    submission_id   INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
                    question_id     INTEGER NOT NULL,
                    selected_answer CHAR(1) NOT NULL CHECK (selected_answer IN ('a','b','c','d'))
                );
            """)
        logger.info("Database tables initialised successfully.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Submission CRUD
# ---------------------------------------------------------------------------

def create_submission(student_name, quiz_id):
    """Insert a new submission with status='pending'. Returns the new id."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO submissions (student_name, quiz_id, status)
                VALUES (%s, %s, 'pending')
                RETURNING id, student_name, quiz_id, score, status, submitted_at, graded_at;
                """,
                (student_name, quiz_id),
            )
            submission = cur.fetchone()
            logger.info(
                "Created submission id=%s student='%s' quiz_id=%s",
                submission["id"], student_name, quiz_id,
            )
            return dict(submission)
    finally:
        conn.close()


def get_submission(submission_id):
    """Return a single submission dict or None."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM submissions WHERE id = %s;", (submission_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_all_submissions():
    """Return all submissions ordered by submitted_at DESC."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM submissions ORDER BY submitted_at DESC;")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_submission_score(submission_id, score, status="graded"):
    """Set score, status and graded_at timestamp for a submission."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE submissions
                   SET score = %s,
                       status = %s,
                       graded_at = %s
                 WHERE id = %s
                RETURNING *;
                """,
                (score, status, datetime.utcnow(), submission_id),
            )
            row = cur.fetchone()
            if row:
                logger.info("Updated submission id=%s score=%s status=%s", submission_id, score, status)
            return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# SubmissionAnswer CRUD
# ---------------------------------------------------------------------------

def create_answer(submission_id, question_id, selected_answer):
    """Insert a single answer record for a submission."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO submission_answers (submission_id, question_id, selected_answer)
                VALUES (%s, %s, %s)
                RETURNING *;
                """,
                (submission_id, question_id, selected_answer.lower()),
            )
            answer = cur.fetchone()
            return dict(answer)
    finally:
        conn.close()


def get_answers_by_submission(submission_id):
    """Return all answer rows for a given submission."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM submission_answers WHERE submission_id = %s ORDER BY id;",
                (submission_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
