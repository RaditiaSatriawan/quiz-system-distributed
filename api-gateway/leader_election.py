import os
import json
import time
import logging
import threading
import requests
logger = logging.getLogger(__name__)

class RingLeaderElection:

    def __init__(self, node_id, node_port, nodes_config):
        self.node_id = int(node_id)
        self.node_port = int(node_port)
        self.nodes = sorted(nodes_config, key=lambda x: x['id'])
        self.leader_id = None
        self.is_election_in_progress = False
        self.participant = False
        self.election_lock = threading.Lock()
        self.health_monitor_thread = None
        self.running = True
        self.election_history = []
        self.election_count = 0
        logger.info(f'[Node {self.node_id}] Ring-based Leader Election initialized')
        logger.info(f"[Node {self.node_id}] Ring topology: {[n['id'] for n in self.nodes]}")

    def get_successor(self):
        node_ids = [n['id'] for n in self.nodes]
        try:
            current_index = node_ids.index(self.node_id)
            successor_index = (current_index + 1) % len(self.nodes)
            return self.nodes[successor_index]
        except ValueError:
            logger.error(f'[Node {self.node_id}] Node not found in ring configuration')
            return None

    def get_node_by_id(self, node_id):
        for node in self.nodes:
            if node['id'] == node_id:
                return node
        return None

    def start_election(self):
        with self.election_lock:
            if self.is_election_in_progress:
                logger.info(f'[Node {self.node_id}] Election already in progress, skipping')
                return {'status': 'election_already_in_progress'}
            self.is_election_in_progress = True
            self.participant = True
            self.election_count += 1
            logger.info(f'[Node {self.node_id}] ===== STARTING ELECTION #{self.election_count} =====')
        successor = self.get_successor()
        if successor:
            self._send_election_async(successor, self.node_id)
            return {'status': 'election_started', 'node_id': self.node_id, 'candidate_id': self.node_id, 'successor': successor['id']}
        else:
            logger.error(f'[Node {self.node_id}] No successor found, cannot start election')
            self.is_election_in_progress = False
            return {'status': 'error', 'message': 'No successor found'}

    def receive_election(self, candidate_id):
        candidate_id = int(candidate_id)
        logger.info(f'[Node {self.node_id}] Received election message with candidate_id={candidate_id}')
        with self.election_lock:
            self.is_election_in_progress = True
        successor = self.get_successor()
        if not successor:
            logger.error(f'[Node {self.node_id}] No successor found')
            return {'status': 'error', 'message': 'No successor found'}
        if candidate_id > self.node_id:
            logger.info(f'[Node {self.node_id}] candidate {candidate_id} > my_id {self.node_id}, forwarding')
            with self.election_lock:
                self.participant = True
            self._send_election_async(successor, candidate_id)
            return {'status': 'forwarded', 'node_id': self.node_id, 'candidate_id': candidate_id, 'forwarded_to': successor['id']}
        elif candidate_id < self.node_id:
            if not self.participant:
                logger.info(f'[Node {self.node_id}] candidate {candidate_id} < my_id {self.node_id}, replacing with own ID')
                with self.election_lock:
                    self.participant = True
                self._send_election_async(successor, self.node_id)
                return {'status': 'replaced', 'node_id': self.node_id, 'new_candidate_id': self.node_id, 'forwarded_to': successor['id']}
            else:
                logger.info(f'[Node {self.node_id}] Already participant, dropping lower candidate {candidate_id}')
                return {'status': 'dropped', 'node_id': self.node_id, 'candidate_id': candidate_id, 'message': 'Lower candidate ID dropped by higher participant'}
        else:
            logger.info(f'[Node {self.node_id}] ★★★ I AM THE LEADER! ★★★')
            with self.election_lock:
                self.leader_id = self.node_id
                self.is_election_in_progress = False
                self.participant = False
            self.election_history.append({'election_number': self.election_count, 'leader_id': self.node_id, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')})
            self._send_coordinator_async(successor, self.node_id)
            return {'status': 'elected', 'leader_id': self.node_id, 'message': f'Node {self.node_id} is the new leader'}

    def receive_coordinator(self, leader_id):
        leader_id = int(leader_id)
        logger.info(f'[Node {self.node_id}] Received coordinator message: leader={leader_id}')
        with self.election_lock:
            self.leader_id = leader_id
            self.is_election_in_progress = False
            self.participant = False
        self.election_history.append({'election_number': self.election_count, 'leader_id': leader_id, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')})
        if leader_id != self.node_id:
            successor = self.get_successor()
            if successor:
                logger.info(f"[Node {self.node_id}] Forwarding coordinator message to Node {successor['id']}")
                self._send_coordinator_async(successor, leader_id)
        logger.info(f'[Node {self.node_id}] Acknowledged leader: Node {leader_id}')
        return {'status': 'acknowledged', 'node_id': self.node_id, 'leader_id': leader_id}

    def _send_election_async(self, target_node, candidate_id):
        thread = threading.Thread(target=self._send_election_message, args=(target_node, candidate_id), daemon=True)
        thread.start()

    def _send_coordinator_async(self, target_node, leader_id):
        thread = threading.Thread(target=self._send_coordinator_message, args=(target_node, leader_id), daemon=True)
        thread.start()

    def _send_election_message(self, target_node, candidate_id):
        url = f"http://{target_node['host']}:{target_node['port']}/election/receive"
        try:
            response = requests.post(url, json={'candidate_id': candidate_id}, timeout=5)
            logger.info(f"[Node {self.node_id}] Election message sent to Node {target_node['id']}: candidate_id={candidate_id}, response={response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"[Node {self.node_id}] Failed to send election to Node {target_node['id']}: {e}")
            self._try_next_node_election(target_node, candidate_id)

    def _send_coordinator_message(self, target_node, leader_id):
        url = f"http://{target_node['host']}:{target_node['port']}/election/coordinator"
        try:
            response = requests.post(url, json={'leader_id': leader_id}, timeout=5)
            logger.info(f"[Node {self.node_id}] Coordinator message sent to Node {target_node['id']}: leader_id={leader_id}, response={response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"[Node {self.node_id}] Failed to send coordinator to Node {target_node['id']}: {e}")
            self._try_next_node_coordinator(target_node, leader_id)

    def _try_next_node_coordinator(self, failed_node, leader_id):
        node_ids = [n['id'] for n in self.nodes]
        try:
            failed_index = node_ids.index(failed_node['id'])
            next_index = (failed_index + 1) % len(self.nodes)
            next_node = self.nodes[next_index]
            if next_node['id'] == self.node_id:
                return
            logger.info(f"[Node {self.node_id}] Skipping failed Node {failed_node['id']} for coordinator, trying Node {next_node['id']}")
            self._send_coordinator_message(next_node, leader_id)
        except ValueError:
            logger.error(f'[Node {self.node_id}] Failed node not found in ring')

    def _try_next_node_election(self, failed_node, candidate_id):
        node_ids = [n['id'] for n in self.nodes]
        try:
            failed_index = node_ids.index(failed_node['id'])
            next_index = (failed_index + 1) % len(self.nodes)
            next_node = self.nodes[next_index]
            if next_node['id'] == self.node_id:
                logger.info(f'[Node {self.node_id}] Only node alive, becoming leader')
                with self.election_lock:
                    self.leader_id = self.node_id
                    self.is_election_in_progress = False
                    self.participant = False
                return
            logger.info(f"[Node {self.node_id}] Skipping failed Node {failed_node['id']}, trying Node {next_node['id']}")
            self._send_election_message(next_node, candidate_id)
        except ValueError:
            logger.error(f'[Node {self.node_id}] Failed node not found in ring')

    def check_leader_health(self):
        if self.leader_id is None:
            return False
        if self.leader_id == self.node_id:
            return True
        leader_node = self.get_node_by_id(self.leader_id)
        if not leader_node:
            return False
        try:
            url = f"http://{leader_node['host']}:{leader_node['port']}/api/health"
            response = requests.get(url, timeout=3)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def start_health_monitor(self):
        self.health_monitor_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self.health_monitor_thread.start()
        logger.info(f'[Node {self.node_id}] Health monitor started')

    def _health_monitor_loop(self):
        while self.running:
            time.sleep(10)
            if not self.running:
                break
            if self.is_election_in_progress:
                continue
            if self.leader_id is None:
                logger.info(f'[Node {self.node_id}] No leader known, starting election')
                self.start_election()
                continue
            if not self.check_leader_health():
                logger.warning(f'[Node {self.node_id}] Leader (Node {self.leader_id}) is unresponsive! Starting new election...')
                with self.election_lock:
                    self.leader_id = None
                self.start_election()

    def get_status(self):
        return {'node_id': self.node_id, 'node_port': self.node_port, 'leader_id': self.leader_id, 'is_leader': self.leader_id == self.node_id, 'is_election_in_progress': self.is_election_in_progress, 'participant': self.participant, 'election_count': self.election_count, 'ring_topology': [n['id'] for n in self.nodes], 'successor': self.get_successor()['id'] if self.get_successor() else None, 'election_history': self.election_history[-5:]}

    def stop(self):
        self.running = False
        logger.info(f'[Node {self.node_id}] Leader election stopped')
