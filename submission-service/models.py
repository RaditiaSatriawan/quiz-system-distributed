import os
import logging
from datetime import datetime
import psycopg2
import psycopg2.extras
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = psycopg2.connect(host=os.environ.get('DB_HOST', 'submission-db'), port=int(os.environ.get('DB_PORT', 5432)), dbname=os.environ.get('DB_NAME', 'submission_db'), user=os.environ.get('DB_USER', 'postgres'), password=os.environ.get('DB_PASSWORD', 'postgres'))
    conn.autocommit = True
    return conn

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("\n                CREATE TABLE IF NOT EXISTS submissions (\n                    id            SERIAL PRIMARY KEY,\n                    student_name  VARCHAR(255) NOT NULL,\n                    quiz_id       INTEGER NOT NULL,\n                    score         NUMERIC(5,2),\n                    status        VARCHAR(20) DEFAULT 'pending'\n                                  CHECK (status IN ('pending','grading','graded')),\n                    submitted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                    graded_at     TIMESTAMP\n                );\n            ")
            cur.execute("\n                CREATE TABLE IF NOT EXISTS submission_answers (\n                    id              SERIAL PRIMARY KEY,\n                    submission_id   INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,\n                    question_id     INTEGER NOT NULL,\n                    selected_answer CHAR(1) NOT NULL CHECK (selected_answer IN ('a','b','c','d'))\n                );\n            ")
        logger.info('Database tables initialised successfully.')
    finally:
        conn.close()

def create_submission(student_name, quiz_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("\n                INSERT INTO submissions (student_name, quiz_id, status)\n                VALUES (%s, %s, 'pending')\n                RETURNING id, student_name, quiz_id, score, status, submitted_at, graded_at;\n                ", (student_name, quiz_id))
            submission = cur.fetchone()
            logger.info("Created submission id=%s student='%s' quiz_id=%s", submission['id'], student_name, quiz_id)
            return dict(submission)
    finally:
        conn.close()

def get_submission(submission_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM submissions WHERE id = %s;', (submission_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def get_all_submissions():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM submissions ORDER BY submitted_at DESC;')
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def update_submission_score(submission_id, score, status='graded'):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('\n                UPDATE submissions\n                   SET score = %s,\n                       status = %s,\n                       graded_at = %s\n                 WHERE id = %s\n                RETURNING *;\n                ', (score, status, datetime.utcnow(), submission_id))
            row = cur.fetchone()
            if row:
                logger.info('Updated submission id=%s score=%s status=%s', submission_id, score, status)
            return dict(row) if row else None
    finally:
        conn.close()

def create_answer(submission_id, question_id, selected_answer):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('\n                INSERT INTO submission_answers (submission_id, question_id, selected_answer)\n                VALUES (%s, %s, %s)\n                RETURNING *;\n                ', (submission_id, question_id, selected_answer.lower()))
            answer = cur.fetchone()
            return dict(answer)
    finally:
        conn.close()

def get_answers_by_submission(submission_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM submission_answers WHERE submission_id = %s ORDER BY id;', (submission_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
