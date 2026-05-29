"""
Database helper module for Quiz Service.
Uses psycopg2 directly for PostgreSQL operations.
"""

import os
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db_connection():
    """Create and return a new PostgreSQL connection using environment variables."""
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "quiz-db"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "quiz_db"),
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
                CREATE TABLE IF NOT EXISTS quizzes (
                    id          SERIAL PRIMARY KEY,
                    title       VARCHAR(255) NOT NULL,
                    description TEXT,
                    time_limit_minutes INTEGER DEFAULT 30,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id              SERIAL PRIMARY KEY,
                    quiz_id         INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                    question_text   TEXT NOT NULL,
                    option_a        VARCHAR(255) NOT NULL,
                    option_b        VARCHAR(255) NOT NULL,
                    option_c        VARCHAR(255) NOT NULL,
                    option_d        VARCHAR(255) NOT NULL,
                    correct_answer  CHAR(1) NOT NULL CHECK (correct_answer IN ('a','b','c','d')),
                    points          INTEGER DEFAULT 10
                );
            """)
        logger.info("Database tables initialised successfully.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Quiz CRUD
# ---------------------------------------------------------------------------

def create_quiz(title, description=None, time_limit_minutes=30):
    """Insert a new quiz and return its full row as a dict."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO quizzes (title, description, time_limit_minutes)
                VALUES (%s, %s, %s)
                RETURNING id, title, description, time_limit_minutes, created_at;
                """,
                (title, description, time_limit_minutes),
            )
            quiz = cur.fetchone()
            logger.info("Created quiz id=%s title='%s'", quiz["id"], quiz["title"])
            return dict(quiz)
    finally:
        conn.close()


def get_quiz(quiz_id):
    """Return a single quiz dict or None."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM quizzes WHERE id = %s;", (quiz_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_all_quizzes():
    """Return a list of all quiz dicts ordered by creation date."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM quizzes ORDER BY created_at DESC;")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_quiz(quiz_id, title=None, description=None, time_limit_minutes=None):
    """Update quiz fields that are not None. Returns updated row or None."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Build dynamic SET clause
            fields = []
            values = []
            if title is not None:
                fields.append("title = %s")
                values.append(title)
            if description is not None:
                fields.append("description = %s")
                values.append(description)
            if time_limit_minutes is not None:
                fields.append("time_limit_minutes = %s")
                values.append(time_limit_minutes)

            if not fields:
                return get_quiz(quiz_id)

            values.append(quiz_id)
            sql = f"UPDATE quizzes SET {', '.join(fields)} WHERE id = %s RETURNING *;"
            cur.execute(sql, values)
            row = cur.fetchone()
            if row:
                logger.info("Updated quiz id=%s", quiz_id)
            return dict(row) if row else None
    finally:
        conn.close()


def delete_quiz(quiz_id):
    """Delete a quiz (CASCADE removes its questions). Returns True if deleted."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM quizzes WHERE id = %s RETURNING id;", (quiz_id,))
            deleted = cur.fetchone()
            if deleted:
                logger.info("Deleted quiz id=%s", quiz_id)
            return deleted is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Question CRUD
# ---------------------------------------------------------------------------

def create_question(quiz_id, question_text, option_a, option_b, option_c, option_d,
                    correct_answer, points=10):
    """Insert a new question linked to a quiz. Returns the new row dict."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO questions
                    (quiz_id, question_text, option_a, option_b, option_c, option_d,
                     correct_answer, points)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (quiz_id, question_text, option_a, option_b, option_c, option_d,
                 correct_answer.lower(), points),
            )
            question = cur.fetchone()
            logger.info("Created question id=%s for quiz_id=%s", question["id"], quiz_id)
            return dict(question)
    finally:
        conn.close()


def get_questions_by_quiz(quiz_id):
    """Return all questions for a given quiz."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM questions WHERE quiz_id = %s ORDER BY id;",
                (quiz_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_question(question_id):
    """Return a single question dict or None."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM questions WHERE id = %s;", (question_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
