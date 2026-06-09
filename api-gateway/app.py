import os
import json
import time
import logging
import threading
import requests as http_requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from rpc_client import QuizServiceStub, SubmissionServiceStub, NotificationServiceStub
from leader_election import RingLeaderElection
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
NODE_ID = int(os.environ.get('NODE_ID', '1'))
NODE_PORT = int(os.environ.get('NODE_PORT', '5000'))
DEFAULT_NODES_CONFIG = json.dumps([{'id': 1, 'host': 'api-gateway-1', 'port': 5000}, {'id': 2, 'host': 'api-gateway-2', 'port': 5001}, {'id': 3, 'host': 'api-gateway-3', 'port': 5002}])
NODES_CONFIG = json.loads(os.environ.get('NODES_CONFIG', DEFAULT_NODES_CONFIG))
app = Flask(__name__)
CORS(app)
quiz_stub = QuizServiceStub()
submission_stub = SubmissionServiceStub()
notification_stub = NotificationServiceStub()
election = RingLeaderElection(node_id=NODE_ID, node_port=NODE_PORT, nodes_config=NODES_CONFIG)

@app.route('/api/health', methods=['GET'])
def health():
    return (jsonify({'status': 'healthy', 'service': 'api-gateway', 'node_id': NODE_ID, 'port': NODE_PORT, 'leader_id': election.leader_id, 'is_leader': election.leader_id == NODE_ID}), 200)

@app.route('/api/quizzes', methods=['GET'])
def list_quizzes():
    data, status = quiz_stub.list_quizzes()
    return (jsonify(data.get('quizzes', []) if isinstance(data, dict) else data), status)

@app.route('/api/quizzes', methods=['POST'])
def create_quiz():
    body = request.get_json(force=True, silent=True) or {}
    data, status = quiz_stub.create_quiz(body)
    return (jsonify(data), status)

@app.route('/api/quizzes/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    data, status = quiz_stub.get_quiz(quiz_id)
    return (jsonify(data.get('quiz', data) if isinstance(data, dict) else data), status)

@app.route('/api/quizzes/<int:quiz_id>', methods=['PUT'])
def update_quiz(quiz_id):
    body = request.get_json(force=True, silent=True) or {}
    data, status = quiz_stub.update_quiz(quiz_id, body)
    return (jsonify(data), status)

@app.route('/api/quizzes/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    data, status = quiz_stub.delete_quiz(quiz_id)
    return (jsonify(data), status)

@app.route('/api/quizzes/<int:quiz_id>/questions', methods=['POST'])
def add_question(quiz_id):
    body = request.get_json(force=True, silent=True) or {}
    data, status = quiz_stub.add_question(quiz_id, body)
    return (jsonify(data), status)

@app.route('/api/quizzes/<int:quiz_id>/questions', methods=['GET'])
def get_questions(quiz_id):
    data, status = quiz_stub.get_questions(quiz_id)
    return (jsonify(data.get('questions', []) if isinstance(data, dict) else data), status)

@app.route('/api/submissions', methods=['POST'])
def create_submission():
    body = request.get_json(force=True, silent=True) or {}
    data, status = submission_stub.create_submission(body)
    return (jsonify(data), status)

@app.route('/api/submissions', methods=['GET'])
def list_submissions():
    data, status = submission_stub.list_submissions()
    return (jsonify(data.get('submissions', []) if isinstance(data, dict) else data), status)

@app.route('/api/submissions/<int:submission_id>', methods=['GET'])
def get_submission(submission_id):
    data, status = submission_stub.get_submission(submission_id)
    return (jsonify(data.get('submission', data) if isinstance(data, dict) else data), status)

@app.route('/api/notifications', methods=['GET'])
def list_notifications():
    data, status = notification_stub.list_notifications()
    return (jsonify(data.get('data', data.get('notifications', [])) if isinstance(data, dict) else data), status)

@app.route('/api/notifications/<int:notification_id>', methods=['GET'])
def get_notification(notification_id):
    data, status = notification_stub.get_notification(notification_id)
    return (jsonify(data.get('data', data.get('notification', data)) if isinstance(data, dict) else data), status)

@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    data, status = notification_stub.mark_read(notification_id)
    return (jsonify(data), status)

@app.route('/api/leader', methods=['GET'])
def leader_status():
    return (jsonify(election.get_status()), 200)

@app.route('/api/leader/election', methods=['POST'])
def trigger_election():
    logger.info('Manual election trigger received on Node %d', NODE_ID)
    threading.Thread(target=election.start_election, daemon=True).start()
    return (jsonify({'status': 'success', 'message': f'Election initiated by Node {NODE_ID}', 'node_id': NODE_ID}), 200)

@app.route('/election/receive', methods=['POST'])
def receive_election():
    body = request.get_json(force=True, silent=True) or {}
    candidate_id = body.get('candidate_id')
    if candidate_id is None:
        return (jsonify({'status': 'error', 'message': 'candidate_id is required'}), 400)
    logger.info('Node %d received election message: candidate_id=%d', NODE_ID, candidate_id)
    threading.Thread(target=election.receive_election, args=(candidate_id,), daemon=True).start()
    return (jsonify({'status': 'ok'}), 200)

@app.route('/election/coordinator', methods=['POST'])
def receive_coordinator():
    body = request.get_json(force=True, silent=True) or {}
    leader_id = body.get('leader_id')
    if leader_id is None:
        return (jsonify({'status': 'error', 'message': 'leader_id is required'}), 400)
    logger.info('Node %d received coordinator message: leader_id=%d', NODE_ID, leader_id)
    threading.Thread(target=election.receive_coordinator, args=(leader_id,), daemon=True).start()
    return (jsonify({'status': 'ok'}), 200)

@app.route('/api/system/nodes', methods=['GET'])
def system_nodes():
    results = []
    for node in NODES_CONFIG:
        node_info = {'id': node['id'], 'host': node['host'], 'port': node['port'], 'is_leader': election.leader_id == node['id'], 'status': 'unknown'}
        url = f"http://{node['host']}:{node['port']}/api/health"
        try:
            resp = http_requests.get(url, timeout=3)
            if resp.status_code == 200:
                node_info['status'] = 'healthy'
                node_info['details'] = resp.json()
            else:
                node_info['status'] = 'unhealthy'
        except http_requests.exceptions.RequestException:
            node_info['status'] = 'unreachable'
        results.append(node_info)
    return (jsonify({'status': 'success', 'nodes': results, 'total': len(results), 'current_leader': election.leader_id}), 200)

def _delayed_election(delay_seconds=5):
    logger.info('Node %d: will start initial election in %d seconds...', NODE_ID, delay_seconds)
    time.sleep(delay_seconds)
    election.start_election()
if __name__ == '__main__':
    logger.info('=' * 60)
    logger.info('  API Gateway - Node %d', NODE_ID)
    logger.info('  Port: %d', NODE_PORT)
    logger.info('  Ring: %s', [n['id'] for n in NODES_CONFIG])
    logger.info('=' * 60)
    election.start_health_monitor()
    threading.Thread(target=_delayed_election, args=(5,), daemon=True).start()
    app.run(host='0.0.0.0', port=NODE_PORT, debug=False)
