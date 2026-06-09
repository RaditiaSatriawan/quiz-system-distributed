import logging
import requests
logger = logging.getLogger(__name__)
RPC_TIMEOUT = 5

class RPCError(Exception):

    def __init__(self, service, method, status_code=None, message=''):
        self.service = service
        self.method = method
        self.status_code = status_code
        self.message = message
        super().__init__(f'RPC Error [{service}.{method}]: {message} (status={status_code})')

class QuizServiceStub:

    def __init__(self, base_url='http://quiz-service:6000'):
        self.base_url = base_url.rstrip('/')
        self.service_name = 'QuizService'
        logger.info(f'[RPC Stub] {self.service_name} initialized -> {self.base_url}')

    def _request(self, method, path, data=None):
        url = f'{self.base_url}{path}'
        try:
            if method == 'GET':
                response = requests.get(url, timeout=RPC_TIMEOUT)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=RPC_TIMEOUT)
            elif method == 'PUT':
                response = requests.put(url, json=data, timeout=RPC_TIMEOUT)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=RPC_TIMEOUT)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            logger.debug(f'[RPC] {self.service_name} {method} {path} -> {response.status_code}')
            return (response.json(), response.status_code)
        except requests.exceptions.ConnectionError as e:
            logger.error(f'[RPC] {self.service_name} connection error: {e}')
            raise RPCError(self.service_name, path, message=f'Service unavailable: {e}')
        except requests.exceptions.Timeout as e:
            logger.error(f'[RPC] {self.service_name} timeout: {e}')
            raise RPCError(self.service_name, path, message=f'Request timeout: {e}')
        except requests.exceptions.RequestException as e:
            logger.error(f'[RPC] {self.service_name} request error: {e}')
            raise RPCError(self.service_name, path, message=str(e))

    def create_quiz(self, data):
        return self._request('POST', '/rpc/quiz/create', data)

    def list_quizzes(self):
        return self._request('GET', '/rpc/quiz/list')

    def get_quiz(self, quiz_id):
        return self._request('GET', f'/rpc/quiz/{quiz_id}')

    def update_quiz(self, quiz_id, data):
        return self._request('PUT', f'/rpc/quiz/{quiz_id}', data)

    def delete_quiz(self, quiz_id):
        return self._request('DELETE', f'/rpc/quiz/{quiz_id}')

    def add_question(self, quiz_id, data):
        return self._request('POST', f'/rpc/quiz/{quiz_id}/question', data)

    def get_questions(self, quiz_id):
        return self._request('GET', f'/rpc/quiz/{quiz_id}/questions')

    def health_check(self):
        try:
            result, status = self._request('GET', '/health')
            return status == 200
        except RPCError:
            return False

class SubmissionServiceStub:

    def __init__(self, base_url='http://submission-service:7000'):
        self.base_url = base_url.rstrip('/')
        self.service_name = 'SubmissionService'
        logger.info(f'[RPC Stub] {self.service_name} initialized -> {self.base_url}')

    def _request(self, method, path, data=None):
        url = f'{self.base_url}{path}'
        try:
            if method == 'GET':
                response = requests.get(url, timeout=RPC_TIMEOUT)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=RPC_TIMEOUT)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            logger.debug(f'[RPC] {self.service_name} {method} {path} -> {response.status_code}')
            return (response.json(), response.status_code)
        except requests.exceptions.ConnectionError as e:
            logger.error(f'[RPC] {self.service_name} connection error: {e}')
            raise RPCError(self.service_name, path, message=f'Service unavailable: {e}')
        except requests.exceptions.Timeout as e:
            logger.error(f'[RPC] {self.service_name} timeout: {e}')
            raise RPCError(self.service_name, path, message=f'Request timeout: {e}')
        except requests.exceptions.RequestException as e:
            logger.error(f'[RPC] {self.service_name} request error: {e}')
            raise RPCError(self.service_name, path, message=str(e))

    def create_submission(self, data):
        return self._request('POST', '/rpc/submission/create', data)

    def list_submissions(self):
        return self._request('GET', '/rpc/submission/list')

    def get_submission(self, submission_id):
        return self._request('GET', f'/rpc/submission/{submission_id}')

    def health_check(self):
        try:
            result, status = self._request('GET', '/health')
            return status == 200
        except RPCError:
            return False

class NotificationServiceStub:

    def __init__(self, base_url='http://notification-service:8000'):
        self.base_url = base_url.rstrip('/')
        self.service_name = 'NotificationService'
        logger.info(f'[RPC Stub] {self.service_name} initialized -> {self.base_url}')

    def _request(self, method, path, data=None):
        url = f'{self.base_url}{path}'
        try:
            if method == 'GET':
                response = requests.get(url, timeout=RPC_TIMEOUT)
            elif method == 'PUT':
                response = requests.put(url, json=data, timeout=RPC_TIMEOUT)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            logger.debug(f'[RPC] {self.service_name} {method} {path} -> {response.status_code}')
            return (response.json(), response.status_code)
        except requests.exceptions.ConnectionError as e:
            logger.error(f'[RPC] {self.service_name} connection error: {e}')
            raise RPCError(self.service_name, path, message=f'Service unavailable: {e}')
        except requests.exceptions.Timeout as e:
            logger.error(f'[RPC] {self.service_name} timeout: {e}')
            raise RPCError(self.service_name, path, message=f'Request timeout: {e}')
        except requests.exceptions.RequestException as e:
            logger.error(f'[RPC] {self.service_name} request error: {e}')
            raise RPCError(self.service_name, path, message=str(e))

    def list_notifications(self):
        return self._request('GET', '/rpc/notification/list')

    def get_notification(self, notification_id):
        return self._request('GET', f'/rpc/notification/{notification_id}')

    def mark_read(self, notification_id):
        return self._request('PUT', f'/rpc/notification/{notification_id}/read')

    def health_check(self):
        try:
            result, status = self._request('GET', '/health')
            return status == 200
        except RPCError:
            return False
