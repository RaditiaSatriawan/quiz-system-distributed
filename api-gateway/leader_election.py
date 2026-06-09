"""
Ring-based Leader Election Algorithm

Implements the Chang-Roberts ring-based leader election algorithm
for distributed API Gateway nodes. Each node has a unique ID and 
nodes are arranged in a logical ring topology.

Algorithm:
1. Any node can initiate an election by sending its ID to its successor
2. Each node compares received candidate ID with its own:
   - If candidate > own: forward the message
   - If candidate < own and not yet participant: replace with own ID, forward
   - If candidate == own: this node is the leader, send coordinator message
3. Coordinator message circulates the ring to inform all nodes of the new leader
"""

import os
import json
import time
import logging
import threading
import requests

logger = logging.getLogger(__name__)


class RingLeaderElection:
    """Ring-based leader election among API Gateway nodes."""

    def __init__(self, node_id, node_port, nodes_config):
        """
        Initialize the ring-based leader election.

        Args:
            node_id (int): Unique identifier for this node
            node_port (int): Port this node is listening on
            nodes_config (list): List of dicts with 'id', 'host', 'port' for all nodes
        """
        self.node_id = int(node_id)
        self.node_port = int(node_port)
        
        # Sort nodes by ID to form the ring
        self.nodes = sorted(nodes_config, key=lambda x: x['id'])
        
        self.leader_id = None
        self.is_election_in_progress = False
        self.participant = False
        self.election_lock = threading.Lock()
        self.health_monitor_thread = None
        self.running = True
        
        # Election history for tracking
        self.election_history = []
        self.election_count = 0
        
        logger.info(f"[Node {self.node_id}] Ring-based Leader Election initialized")
        logger.info(f"[Node {self.node_id}] Ring topology: {[n['id'] for n in self.nodes]}")

    def get_successor(self):
        """Get the next node in the ring (circular)."""
        node_ids = [n['id'] for n in self.nodes]
        try:
            current_index = node_ids.index(self.node_id)
            successor_index = (current_index + 1) % len(self.nodes)
            return self.nodes[successor_index]
        except ValueError:
            logger.error(f"[Node {self.node_id}] Node not found in ring configuration")
            return None

    def get_node_by_id(self, node_id):
        """Get node configuration by ID."""
        for node in self.nodes:
            if node['id'] == node_id:
                return node
        return None

    def start_election(self):
        """Initiate a new leader election."""
        with self.election_lock:
            if self.is_election_in_progress:
                logger.info(f"[Node {self.node_id}] Election already in progress, skipping")
                return {"status": "election_already_in_progress"}

            self.is_election_in_progress = True
            self.participant = True
            self.election_count += 1

            logger.info(f"[Node {self.node_id}] ===== STARTING ELECTION #{self.election_count} =====")

        # Send election message with own ID to successor
        successor = self.get_successor()
        if successor:
            self._send_election_async(successor, self.node_id)
            return {
                "status": "election_started",
                "node_id": self.node_id,
                "candidate_id": self.node_id,
                "successor": successor['id']
            }
        else:
            logger.error(f"[Node {self.node_id}] No successor found, cannot start election")
            self.is_election_in_progress = False
            return {"status": "error", "message": "No successor found"}

    def receive_election(self, candidate_id):
        """
        Receive an election message from a predecessor.

        Args:
            candidate_id (int): The candidate ID being forwarded in the ring

        Returns:
            dict: Result of processing the election message
        """
        candidate_id = int(candidate_id)
        logger.info(f"[Node {self.node_id}] Received election message with candidate_id={candidate_id}")

        with self.election_lock:
            self.is_election_in_progress = True

        successor = self.get_successor()
        if not successor:
            logger.error(f"[Node {self.node_id}] No successor found")
            return {"status": "error", "message": "No successor found"}

        if candidate_id > self.node_id:
            # Candidate has higher ID, forward the message
            logger.info(f"[Node {self.node_id}] candidate {candidate_id} > my_id {self.node_id}, forwarding")
            with self.election_lock:
                self.participant = True
            self._send_election_async(successor, candidate_id)
            return {
                "status": "forwarded",
                "node_id": self.node_id,
                "candidate_id": candidate_id,
                "forwarded_to": successor['id']
            }

        elif candidate_id < self.node_id:
            if not self.participant:
                # Replace with own ID and forward
                logger.info(f"[Node {self.node_id}] candidate {candidate_id} < my_id {self.node_id}, replacing with own ID")
                with self.election_lock:
                    self.participant = True
                self._send_election_async(successor, self.node_id)
                return {
                    "status": "replaced",
                    "node_id": self.node_id,
                    "new_candidate_id": self.node_id,
                    "forwarded_to": successor['id']
                }
            else:
                # Already participant, ignore (swallow) the lower candidate ID
                logger.info(f"[Node {self.node_id}] Already participant, dropping lower candidate {candidate_id}")
                return {
                    "status": "dropped",
                    "node_id": self.node_id,
                    "candidate_id": candidate_id,
                    "message": "Lower candidate ID dropped by higher participant"
                }

        else:
            # candidate_id == self.node_id -> I am the leader!
            logger.info(f"[Node {self.node_id}] ★★★ I AM THE LEADER! ★★★")
            with self.election_lock:
                self.leader_id = self.node_id
                self.is_election_in_progress = False
                self.participant = False

            # Record in history
            self.election_history.append({
                "election_number": self.election_count,
                "leader_id": self.node_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

            # Send coordinator message to inform all nodes
            self._send_coordinator_async(successor, self.node_id)
            return {
                "status": "elected",
                "leader_id": self.node_id,
                "message": f"Node {self.node_id} is the new leader"
            }

    def receive_coordinator(self, leader_id):
        """
        Receive a coordinator message announcing the new leader.

        Args:
            leader_id (int): The ID of the newly elected leader

        Returns:
            dict: Result of processing the coordinator message
        """
        leader_id = int(leader_id)
        logger.info(f"[Node {self.node_id}] Received coordinator message: leader={leader_id}")

        with self.election_lock:
            self.leader_id = leader_id
            self.is_election_in_progress = False
            self.participant = False

        # Record in history
        self.election_history.append({
            "election_number": self.election_count,
            "leader_id": leader_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        if leader_id != self.node_id:
            # Forward coordinator message to successor
            successor = self.get_successor()
            if successor:
                logger.info(f"[Node {self.node_id}] Forwarding coordinator message to Node {successor['id']}")
                self._send_coordinator_async(successor, leader_id)

        logger.info(f"[Node {self.node_id}] Acknowledged leader: Node {leader_id}")
        return {
            "status": "acknowledged",
            "node_id": self.node_id,
            "leader_id": leader_id
        }

    def _send_election_async(self, target_node, candidate_id):
        """Send election message asynchronously."""
        thread = threading.Thread(
            target=self._send_election_message,
            args=(target_node, candidate_id),
            daemon=True
        )
        thread.start()

    def _send_coordinator_async(self, target_node, leader_id):
        """Send coordinator message asynchronously."""
        thread = threading.Thread(
            target=self._send_coordinator_message,
            args=(target_node, leader_id),
            daemon=True
        )
        thread.start()

    def _send_election_message(self, target_node, candidate_id):
        """Send election message to target node via HTTP POST."""
        url = f"http://{target_node['host']}:{target_node['port']}/election/receive"
        try:
            response = requests.post(
                url,
                json={"candidate_id": candidate_id},
                timeout=5
            )
            logger.info(
                f"[Node {self.node_id}] Election message sent to Node {target_node['id']}: "
                f"candidate_id={candidate_id}, response={response.status_code}"
            )
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"[Node {self.node_id}] Failed to send election to Node {target_node['id']}: {e}"
            )
            # If successor is unreachable, try next node
            self._try_next_node_election(target_node, candidate_id)

    def _send_coordinator_message(self, target_node, leader_id):
        """Send coordinator message to target node via HTTP POST."""
        url = f"http://{target_node['host']}:{target_node['port']}/election/coordinator"
        try:
            response = requests.post(
                url,
                json={"leader_id": leader_id},
                timeout=5
            )
            logger.info(
                f"[Node {self.node_id}] Coordinator message sent to Node {target_node['id']}: "
                f"leader_id={leader_id}, response={response.status_code}"
            )
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"[Node {self.node_id}] Failed to send coordinator to Node {target_node['id']}: {e}"
            )
            self._try_next_node_coordinator(target_node, leader_id)

    def _try_next_node_coordinator(self, failed_node, leader_id):
        """If a node is unreachable, skip to the next node in the ring for coordinator message."""
        node_ids = [n['id'] for n in self.nodes]
        try:
            failed_index = node_ids.index(failed_node['id'])
            next_index = (failed_index + 1) % len(self.nodes)
            next_node = self.nodes[next_index]

            if next_node['id'] == self.node_id:
                # Full circle reached, all other nodes are dead
                return

            logger.info(f"[Node {self.node_id}] Skipping failed Node {failed_node['id']} for coordinator, trying Node {next_node['id']}")
            self._send_coordinator_message(next_node, leader_id)
        except ValueError:
            logger.error(f"[Node {self.node_id}] Failed node not found in ring")

    def _try_next_node_election(self, failed_node, candidate_id):
        """If a node is unreachable, skip to the next node in the ring."""
        node_ids = [n['id'] for n in self.nodes]
        try:
            failed_index = node_ids.index(failed_node['id'])
            # Try the next node after the failed one
            next_index = (failed_index + 1) % len(self.nodes)
            next_node = self.nodes[next_index]

            if next_node['id'] == self.node_id:
                # We've gone full circle, we're the only node alive
                logger.info(f"[Node {self.node_id}] Only node alive, becoming leader")
                with self.election_lock:
                    self.leader_id = self.node_id
                    self.is_election_in_progress = False
                    self.participant = False
                return

            logger.info(f"[Node {self.node_id}] Skipping failed Node {failed_node['id']}, trying Node {next_node['id']}")
            self._send_election_message(next_node, candidate_id)
        except ValueError:
            logger.error(f"[Node {self.node_id}] Failed node not found in ring")

    def check_leader_health(self):
        """Check if the current leader is still alive."""
        if self.leader_id is None:
            return False

        if self.leader_id == self.node_id:
            return True  # We are the leader

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
        """Start background thread for periodic leader health monitoring."""
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True
        )
        self.health_monitor_thread.start()
        logger.info(f"[Node {self.node_id}] Health monitor started")

    def _health_monitor_loop(self):
        """Periodically check leader health and trigger election if needed."""
        while self.running:
            time.sleep(10)  # Check every 10 seconds

            if not self.running:
                break

            if self.is_election_in_progress:
                continue

            if self.leader_id is None:
                logger.info(f"[Node {self.node_id}] No leader known, starting election")
                self.start_election()
                continue

            if not self.check_leader_health():
                logger.warning(
                    f"[Node {self.node_id}] Leader (Node {self.leader_id}) is unresponsive! "
                    f"Starting new election..."
                )
                with self.election_lock:
                    self.leader_id = None
                self.start_election()

    def get_status(self):
        """Get current election status."""
        return {
            "node_id": self.node_id,
            "node_port": self.node_port,
            "leader_id": self.leader_id,
            "is_leader": self.leader_id == self.node_id,
            "is_election_in_progress": self.is_election_in_progress,
            "participant": self.participant,
            "election_count": self.election_count,
            "ring_topology": [n['id'] for n in self.nodes],
            "successor": self.get_successor()['id'] if self.get_successor() else None,
            "election_history": self.election_history[-5:]  # Last 5 elections
        }

    def stop(self):
        """Stop the health monitor."""
        self.running = False
        logger.info(f"[Node {self.node_id}] Leader election stopped")
