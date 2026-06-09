import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from models import init_db, get_all_notifications, get_notification, mark_notification_read
from rabbitmq_consumer import start_consumer
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)

def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def _serialize_notification(n):
    return {'id': n['id'], 'submission_id': n['submission_id'], 'student_name': n['student_name'], 'message': n['message'], 'notification_type': n['notification_type'], 'is_read': n['is_read'], 'created_at': _serialize(n['created_at'])}

@app.route('/health', methods=['GET'])
def health():
    return (jsonify({'status': 'healthy', 'service': 'notification-service', 'port': 8000}), 200)

@app.route('/rpc/notification/list', methods=['GET'])
def list_notifications():
    try:
        notifications = get_all_notifications()
        return (jsonify({'status': 'success', 'data': [_serialize_notification(n) for n in notifications], 'count': len(notifications)}), 200)
    except Exception as e:
        logger.error('Error listing notifications: %s', e)
        return (jsonify({'status': 'error', 'message': str(e)}), 500)

@app.route('/rpc/notification/<int:notification_id>', methods=['GET'])
def get_single_notification(notification_id):
    try:
        notification = get_notification(notification_id)
        if notification is None:
            return (jsonify({'status': 'error', 'message': f'Notification with id {notification_id} not found'}), 404)
        return (jsonify({'status': 'success', 'data': _serialize_notification(notification)}), 200)
    except Exception as e:
        logger.error('Error fetching notification %s: %s', notification_id, e)
        return (jsonify({'status': 'error', 'message': str(e)}), 500)

@app.route('/rpc/notification/<int:notification_id>/read', methods=['PUT'])
def mark_read(notification_id):
    try:
        notification = mark_notification_read(notification_id)
        if notification is None:
            return (jsonify({'status': 'error', 'message': f'Notification with id {notification_id} not found'}), 404)
        return (jsonify({'status': 'success', 'data': _serialize_notification(notification), 'message': 'Notification marked as read'}), 200)
    except Exception as e:
        logger.error('Error marking notification %s as read: %s', notification_id, e)
        return (jsonify({'status': 'error', 'message': str(e)}), 500)
if __name__ == '__main__':
    logger.info('Initializing Notification Service database...')
    init_db()
    logger.info('Starting RabbitMQ consumer thread...')
    start_consumer()
    logger.info('Starting Notification Service on port 8000...')
    app.run(host='0.0.0.0', port=8000, debug=False)
