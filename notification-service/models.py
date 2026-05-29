"""
Database helper module for Notification Service.
Uses psycopg2 to interact with PostgreSQL.
"""

import os
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'notification-db'),
    'port': os.environ.get('DB_PORT', '5432'),
    'dbname': os.environ.get('DB_NAME', 'notification_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'postgres'),
}

INIT_SQL = """
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'grade_result',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db_connection():
    """Create and return a new database connection using environment variables."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        logger.error("Failed to connect to database: %s", e)
        raise


def init_db():
    """Initialize the database schema, creating the notifications table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(INIT_SQL)
        cur.close()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise


def create_notification(submission_id, student_name, message, notification_type='grade_result'):
    """
    Insert a new notification record into the database.

    Args:
        submission_id: The ID of the related submission.
        student_name: Name of the student.
        message: Notification message body.
        notification_type: Type of notification (default: 'grade_result').

    Returns:
        dict: The created notification record.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO notifications (submission_id, student_name, message, notification_type)
            VALUES (%s, %s, %s, %s)
            RETURNING id, submission_id, student_name, message, notification_type, is_read, created_at
            """,
            (submission_id, student_name, message, notification_type)
        )
        notification = dict(cur.fetchone())
        cur.close()
        logger.info("Created notification id=%s for student '%s'", notification['id'], student_name)
        return notification
    except Exception as e:
        logger.error("Failed to create notification: %s", e)
        raise
    finally:
        if conn:
            conn.close()


def get_all_notifications():
    """
    Retrieve all notification records from the database, ordered by newest first.

    Returns:
        list[dict]: List of notification records.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, submission_id, student_name, message, notification_type, is_read, created_at "
            "FROM notifications ORDER BY created_at DESC"
        )
        notifications = [dict(row) for row in cur.fetchall()]
        cur.close()
        return notifications
    except Exception as e:
        logger.error("Failed to fetch notifications: %s", e)
        raise
    finally:
        if conn:
            conn.close()


def get_notification(notification_id):
    """
    Retrieve a single notification by its ID.

    Args:
        notification_id: The notification's primary key.

    Returns:
        dict or None: The notification record, or None if not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, submission_id, student_name, message, notification_type, is_read, created_at "
            "FROM notifications WHERE id = %s",
            (notification_id,)
        )
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error("Failed to fetch notification id=%s: %s", notification_id, e)
        raise
    finally:
        if conn:
            conn.close()


def mark_notification_read(notification_id):
    """
    Mark a notification as read.

    Args:
        notification_id: The notification's primary key.

    Returns:
        dict or None: The updated notification record, or None if not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            UPDATE notifications SET is_read = TRUE
            WHERE id = %s
            RETURNING id, submission_id, student_name, message, notification_type, is_read, created_at
            """,
            (notification_id,)
        )
        row = cur.fetchone()
        cur.close()
        if row:
            logger.info("Marked notification id=%s as read", notification_id)
            return dict(row)
        return None
    except Exception as e:
        logger.error("Failed to mark notification id=%s as read: %s", notification_id, e)
        raise
    finally:
        if conn:
            conn.close()
