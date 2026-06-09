import logging
import json
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request
from flask_cors import CORS
from models import init_db, create_submission, get_submission, get_all_submissions, create_answer, get_answers_by_submission
from rabbitmq_consumer import start_consumer_thread, publish_grading_task
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('submission-service')
app = Flask(__name__)
CORS(app)

class CustomJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def _jsonify(data, status=200):
    body = json.dumps(data, cls=CustomJSONEncoder)
    return app.response_class(body, status=status, mimetype='application/json')

@app.route('/health', methods=['GET'])
def health():
    return _jsonify({'status': 'healthy', 'service': 'submission-service'})

@app.route('/rpc/submission/create', methods=['POST'])
def rpc_create_submission():
    try:
        data = request.get_json(force=True)
        student_name = data.get('student_name')
        quiz_id = data.get('quiz_id')
        answers = data.get('answers', [])
        if not student_name:
            return _jsonify({'error': 'student_name is required'}, 400)
        if quiz_id is None:
            return _jsonify({'error': 'quiz_id is required'}, 400)
        if not answers:
            return _jsonify({'error': 'answers list is required and cannot be empty'}, 400)
        submission = create_submission(student_name=student_name, quiz_id=quiz_id)
        submission_id = submission['id']
        saved_answers = []
        for ans in answers:
            qid = ans.get('question_id')
            sel = ans.get('selected_answer')
            if qid is None or sel is None:
                continue
            answer = create_answer(submission_id=submission_id, question_id=qid, selected_answer=sel)
            saved_answers.append(answer)
        try:
            publish_grading_task(submission_id)
            logger.info('Grading task published for submission_id=%s', submission_id)
        except Exception:
            logger.exception('Failed to publish grading task for submission_id=%s – will be graded later', submission_id)
        return _jsonify({'message': 'Submission created successfully', 'submission': submission, 'answers_saved': len(saved_answers), 'status': 'pending'}, 201)
    except Exception as exc:
        logger.exception('Error creating submission')
        return _jsonify({'error': str(exc)}, 500)

@app.route('/rpc/submission/list', methods=['GET'])
def rpc_list_submissions():
    try:
        submissions = get_all_submissions()
        return _jsonify({'submissions': submissions, 'count': len(submissions)})
    except Exception as exc:
        logger.exception('Error listing submissions')
        return _jsonify({'error': str(exc)}, 500)

@app.route('/rpc/submission/<int:submission_id>', methods=['GET'])
def rpc_get_submission(submission_id):
    try:
        submission = get_submission(submission_id)
        if not submission:
            return _jsonify({'error': 'Submission not found'}, 404)
        answers = get_answers_by_submission(submission_id)
        submission['answers'] = answers
        return _jsonify({'submission': submission})
    except Exception as exc:
        logger.exception('Error fetching submission %s', submission_id)
        return _jsonify({'error': str(exc)}, 500)
if __name__ == '__main__':
    logger.info('Initialising database tables …')
    init_db()
    logger.info('Starting RabbitMQ consumer thread …')
    start_consumer_thread()
    logger.info('Starting Submission Service on port 7000')
    app.run(host='0.0.0.0', port=7000, debug=False)
