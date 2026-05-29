"""
RabbitMQ consumer for the Submission Service.

Listens on 'grading_queue' for new submission IDs to grade.
After grading, publishes a notification to 'notification_queue'.
Designed to run as a daemon thread inside the Flask process.
"""

import os
import json
import time
import logging
import threading
import pika

from grader import grade_submission
from models import get_submission

logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS", "guest")

GRADING_QUEUE = "grading_queue"
NOTIFICATION_QUEUE = "notification_queue"

MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 5


def _get_connection():
    """Create a blocking connection to RabbitMQ with retry logic."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Connecting to RabbitMQ at %s:%s (attempt %d/%d)",
                RABBITMQ_HOST, RABBITMQ_PORT, attempt, MAX_RETRIES,
            )
            connection = pika.BlockingConnection(parameters)
            logger.info("Connected to RabbitMQ successfully.")
            return connection
        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning(
                "RabbitMQ connection attempt %d failed: %s – retrying in %ds",
                attempt, exc, RETRY_DELAY_SECONDS,
            )
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"Could not connect to RabbitMQ after {MAX_RETRIES} attempts")


def _publish_notification(channel, submission_id, grading_result):
    """Publish a grading-complete notification to notification_queue."""
    try:
        submission = get_submission(submission_id)
        notification = {
            "event": "grading_complete",
            "submission_id": submission_id,
            "student_name": submission["student_name"] if submission else "unknown",
            "quiz_id": submission["quiz_id"] if submission else None,
            "quiz_title": grading_result.get("quiz_title", "Unknown Quiz"),
            "score": grading_result.get("score"),
            "correct_count": grading_result.get("correct_count"),
            "total_questions": grading_result.get("total_questions"),
            "status": grading_result.get("status", "graded"),
        }
        channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=NOTIFICATION_QUEUE,
            body=json.dumps(notification),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        logger.info("Published notification for submission_id=%s", submission_id)
    except Exception:
        logger.exception("Failed to publish notification for submission_id=%s", submission_id)


def _on_message(channel, method, _properties, body):
    """Callback invoked for each message on grading_queue."""
    try:
        data = json.loads(body)
        submission_id = data.get("submission_id")
        if submission_id is None:
            logger.error("Received message without submission_id: %s", body)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.info("Received grading request for submission_id=%s", submission_id)

        grading_result = grade_submission(submission_id)

        # Publish notification after successful grading
        _publish_notification(channel, submission_id, grading_result)

        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Grading acknowledged for submission_id=%s", submission_id)

    except Exception:
        logger.exception("Error processing grading message: %s", body)
        # Negative-acknowledge so the message can be retried
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def _consume():
    """Main consume loop – reconnects automatically on connection loss."""
    while True:
        try:
            connection = _get_connection()
            channel = connection.channel()

            channel.queue_declare(queue=GRADING_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=GRADING_QUEUE, on_message_callback=_on_message)

            logger.info("Waiting for messages on '%s' …", GRADING_QUEUE)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            logger.warning("Lost connection to RabbitMQ – reconnecting in %ds", RETRY_DELAY_SECONDS)
            time.sleep(RETRY_DELAY_SECONDS)
        except Exception:
            logger.exception("Unexpected error in consumer – restarting in %ds", RETRY_DELAY_SECONDS)
            time.sleep(RETRY_DELAY_SECONDS)


def start_consumer_thread():
    """Start the RabbitMQ consumer in a background daemon thread."""
    thread = threading.Thread(target=_consume, name="rabbitmq-consumer", daemon=True)
    thread.start()
    logger.info("RabbitMQ consumer thread started.")
    return thread


# ---------------------------------------------------------------------------
# Publish helper used by the Flask routes
# ---------------------------------------------------------------------------

def publish_grading_task(submission_id):
    """Publish a submission_id to grading_queue for async grading."""
    connection = _get_connection()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=GRADING_QUEUE, durable=True)
        message = json.dumps({"submission_id": submission_id})
        channel.basic_publish(
            exchange="",
            routing_key=GRADING_QUEUE,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info("Published grading task for submission_id=%s", submission_id)
    finally:
        connection.close()
