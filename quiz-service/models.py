import os
import logging
import psycopg2
import psycopg2.extras
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = psycopg2.connect(host=os.environ.get('DB_HOST', 'quiz-db'), port=int(os.environ.get('DB_PORT', 5432)), dbname=os.environ.get('DB_NAME', 'quiz_db'), user=os.environ.get('DB_USER', 'postgres'), password=os.environ.get('DB_PASSWORD', 'postgres'))
    conn.autocommit = True
    return conn

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('\n                CREATE TABLE IF NOT EXISTS quizzes (\n                    id          SERIAL PRIMARY KEY,\n                    title       VARCHAR(255) NOT NULL,\n                    description TEXT,\n                    time_limit_minutes INTEGER DEFAULT 30,\n                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n                );\n            ')
            cur.execute("\n                CREATE TABLE IF NOT EXISTS questions (\n                    id              SERIAL PRIMARY KEY,\n                    quiz_id         INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,\n                    question_text   TEXT NOT NULL,\n                    option_a        VARCHAR(255) NOT NULL,\n                    option_b        VARCHAR(255) NOT NULL,\n                    option_c        VARCHAR(255) NOT NULL,\n                    option_d        VARCHAR(255) NOT NULL,\n                    correct_answer  CHAR(1) NOT NULL CHECK (correct_answer IN ('a','b','c','d')),\n                    points          INTEGER DEFAULT 10\n                );\n            ")
        logger.info('Database tables initialised successfully.')
    finally:
        conn.close()

def create_quiz(title, description=None, time_limit_minutes=30):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('\n                INSERT INTO quizzes (title, description, time_limit_minutes)\n                VALUES (%s, %s, %s)\n                RETURNING id, title, description, time_limit_minutes, created_at;\n                ', (title, description, time_limit_minutes))
            quiz = cur.fetchone()
            logger.info("Created quiz id=%s title='%s'", quiz['id'], quiz['title'])
            return dict(quiz)
    finally:
        conn.close()

def get_quiz(quiz_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM quizzes WHERE id = %s;', (quiz_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def get_all_quizzes():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM quizzes ORDER BY created_at DESC;')
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def update_quiz(quiz_id, title=None, description=None, time_limit_minutes=None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            fields = []
            values = []
            if title is not None:
                fields.append('title = %s')
                values.append(title)
            if description is not None:
                fields.append('description = %s')
                values.append(description)
            if time_limit_minutes is not None:
                fields.append('time_limit_minutes = %s')
                values.append(time_limit_minutes)
            if not fields:
                return get_quiz(quiz_id)
            values.append(quiz_id)
            sql = f"UPDATE quizzes SET {', '.join(fields)} WHERE id = %s RETURNING *;"
            cur.execute(sql, values)
            row = cur.fetchone()
            if row:
                logger.info('Updated quiz id=%s', quiz_id)
            return dict(row) if row else None
    finally:
        conn.close()

def delete_quiz(quiz_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM quizzes WHERE id = %s RETURNING id;', (quiz_id,))
            deleted = cur.fetchone()
            if deleted:
                logger.info('Deleted quiz id=%s', quiz_id)
            return deleted is not None
    finally:
        conn.close()

def create_question(quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer, points=10):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('\n                INSERT INTO questions\n                    (quiz_id, question_text, option_a, option_b, option_c, option_d,\n                     correct_answer, points)\n                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)\n                RETURNING *;\n                ', (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer.lower(), points))
            question = cur.fetchone()
            logger.info('Created question id=%s for quiz_id=%s', question['id'], quiz_id)
            return dict(question)
    finally:
        conn.close()

def get_questions_by_quiz(quiz_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM questions WHERE quiz_id = %s ORDER BY id;', (quiz_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_question(question_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM questions WHERE id = %s;', (question_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
