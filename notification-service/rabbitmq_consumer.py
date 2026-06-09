import os
import json
import time
import logging
import threading
import pika
from models import create_notification
logger = logging.getLogger(__name__)
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', '5672'))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'guest')
QUEUE_NAME = 'notification_queue'
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 5

def _connect_with_retry():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials, heartbeat=600, blocked_connection_timeout=300)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info('Connecting to RabbitMQ at %s:%s (attempt %d/%d)...', RABBITMQ_HOST, RABBITMQ_PORT, attempt, MAX_RETRIES)
            connection = pika.BlockingConnection(parameters)
            logger.info('Successfully connected to RabbitMQ.')
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning('RabbitMQ connection attempt %d/%d failed: %s', attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_SECONDS * attempt
                logger.info('Retrying in %d seconds...', delay)
                time.sleep(delay)
            else:
                logger.error('Exhausted all %d RabbitMQ connection attempts.', MAX_RETRIES)
                raise

def _on_message(channel, method_frame, header_frame, body):
    try:
        data = json.loads(body.decode('utf-8'))
        logger.info('Received message: %s', json.dumps(data, indent=2))
        submission_id = data.get('submission_id')
        student_name = data.get('student_name', 'Unknown Student')
        quiz_title = data.get('quiz_title', 'Unknown Quiz')
        score = data.get('score', 0)
        status = data.get('status', 'graded')
        message = f'Quiz "{quiz_title}" has been graded. Score: {score}/100'
        if status:
            message += f' (Status: {status})'
        notification = create_notification(submission_id=submission_id, student_name=student_name, message=message, notification_type='grade_result')
        logger.info('=' * 60)
        logger.info('📧 NOTIFICATION (simulated email)')
        logger.info('-' * 60)
        logger.info('  To:      %s', student_name)
        logger.info('  Subject: Quiz Grading Result')
        logger.info('  Body:    %s', message)
        logger.info('  ID:      %s', notification.get('id'))
        logger.info('=' * 60)
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    except json.JSONDecodeError as e:
        logger.error('Failed to decode message body as JSON: %s', e)
        channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=False)
    except Exception as e:
        logger.error('Error processing notification message: %s', e)
        channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=True)

def _consume():
    while True:
        try:
            connection = _connect_with_retry()
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message)
            logger.info("Waiting for messages on queue '%s'...", QUEUE_NAME)
            channel.start_consuming()
        except pika.exceptions.ConnectionClosedByBroker:
            logger.warning('Connection closed by RabbitMQ broker. Reconnecting...')
            time.sleep(RETRY_DELAY_SECONDS)
        except pika.exceptions.AMQPChannelError as e:
            logger.error('AMQP channel error: %s. Reconnecting...', e)
            time.sleep(RETRY_DELAY_SECONDS)
        except pika.exceptions.AMQPConnectionError:
            logger.warning('Lost connection to RabbitMQ. Reconnecting...')
            time.sleep(RETRY_DELAY_SECONDS)
        except Exception as e:
            logger.error('Unexpected error in consumer loop: %s. Restarting...', e)
            time.sleep(RETRY_DELAY_SECONDS)

def start_consumer():
    thread = threading.Thread(target=_consume, name='rabbitmq-consumer', daemon=True)
    thread.start()
    logger.info('RabbitMQ consumer thread started (daemon).')
    return thread
