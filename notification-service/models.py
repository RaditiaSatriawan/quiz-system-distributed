import os
import logging
import psycopg2
import psycopg2.extras
logger = logging.getLogger(__name__)
DB_CONFIG = {'host': os.environ.get('DB_HOST', 'notification-db'), 'port': os.environ.get('DB_PORT', '5432'), 'dbname': os.environ.get('DB_NAME', 'notification_db'), 'user': os.environ.get('DB_USER', 'postgres'), 'password': os.environ.get('DB_PASSWORD', 'postgres')}
INIT_SQL = "\nCREATE TABLE IF NOT EXISTS notifications (\n    id SERIAL PRIMARY KEY,\n    submission_id INTEGER NOT NULL,\n    student_name VARCHAR(255) NOT NULL,\n    message TEXT NOT NULL,\n    notification_type VARCHAR(50) NOT NULL DEFAULT 'grade_result',\n    is_read BOOLEAN NOT NULL DEFAULT FALSE,\n    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP\n);\n"

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        logger.error('Failed to connect to database: %s', e)
        raise

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(INIT_SQL)
        cur.close()
        conn.close()
        logger.info('Database initialized successfully.')
    except Exception as e:
        logger.error('Failed to initialize database: %s', e)
        raise

def create_notification(submission_id, student_name, message, notification_type='grade_result'):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('\n            INSERT INTO notifications (submission_id, student_name, message, notification_type)\n            VALUES (%s, %s, %s, %s)\n            RETURNING id, submission_id, student_name, message, notification_type, is_read, created_at\n            ', (submission_id, student_name, message, notification_type))
        notification = dict(cur.fetchone())
        cur.close()
        logger.info("Created notification id=%s for student '%s'", notification['id'], student_name)
        return notification
    except Exception as e:
        logger.error('Failed to create notification: %s', e)
        raise
    finally:
        if conn:
            conn.close()

def get_all_notifications():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT id, submission_id, student_name, message, notification_type, is_read, created_at FROM notifications ORDER BY created_at DESC')
        notifications = [dict(row) for row in cur.fetchall()]
        cur.close()
        return notifications
    except Exception as e:
        logger.error('Failed to fetch notifications: %s', e)
        raise
    finally:
        if conn:
            conn.close()

def get_notification(notification_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT id, submission_id, student_name, message, notification_type, is_read, created_at FROM notifications WHERE id = %s', (notification_id,))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error('Failed to fetch notification id=%s: %s', notification_id, e)
        raise
    finally:
        if conn:
            conn.close()

def mark_notification_read(notification_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('\n            UPDATE notifications SET is_read = TRUE\n            WHERE id = %s\n            RETURNING id, submission_id, student_name, message, notification_type, is_read, created_at\n            ', (notification_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            logger.info('Marked notification id=%s as read', notification_id)
            return dict(row)
        return None
    except Exception as e:
        logger.error('Failed to mark notification id=%s as read: %s', notification_id, e)
        raise
    finally:
        if conn:
            conn.close()
