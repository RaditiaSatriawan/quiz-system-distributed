-- ============================================
-- Distributed Quiz Assessment System
-- Database Initialization Script
-- ============================================

-- Create tables
CREATE TABLE IF NOT EXISTS quizzes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    time_limit_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    option_a VARCHAR(255) NOT NULL,
    option_b VARCHAR(255) NOT NULL,
    option_c VARCHAR(255) NOT NULL,
    option_d VARCHAR(255) NOT NULL,
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('a','b','c','d')),
    points INTEGER DEFAULT 10
);

CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    quiz_id INTEGER REFERENCES quizzes(id),
    score DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','grading','graded')),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submission_answers (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER REFERENCES submissions(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id),
    selected_answer CHAR(1) NOT NULL CHECK (selected_answer IN ('a','b','c','d'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER REFERENCES submissions(id),
    student_name VARCHAR(255),
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'grade_result',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO quizzes (title, description, time_limit_minutes) VALUES
('Distributed Systems Basics', 'Test your knowledge of distributed systems fundamentals', 30),
('Network Protocols Quiz', 'Quiz about TCP/IP, UDP, and HTTP protocols', 20),
('Database Replication', 'Understanding database replication strategies', 25);

INSERT INTO questions (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer, points) VALUES
(1, 'What is the CAP theorem?', 'Consistency, Availability, Partition tolerance', 'Cache, API, Protocol', 'Client, Agent, Proxy', 'Cluster, Application, Process', 'a', 10),
(1, 'Which algorithm is used for leader election?', 'Dijkstra', 'Bully Algorithm', 'A* Search', 'Binary Search', 'b', 10),
(1, 'What is RPC?', 'Remote Procedure Call', 'Random Process Control', 'Rapid Protocol Check', 'Real-time Process Communication', 'a', 10),
(1, 'What does ACID stand for in databases?', 'Atomicity, Consistency, Isolation, Durability', 'Access, Control, Identity, Data', 'Asynchronous, Cached, Indexed, Distributed', 'Algorithm, Computation, Integration, Design', 'a', 10),
(1, 'Which is NOT a type of distributed system?', 'Client-Server', 'Peer-to-Peer', 'Monolithic Desktop App', 'Microservices', 'c', 10),
(2, 'What port does HTTP use by default?', '21', '80', '443', '8080', 'b', 10),
(2, 'Which protocol is connectionless?', 'TCP', 'HTTP', 'UDP', 'FTP', 'c', 10),
(2, 'What does DNS stand for?', 'Data Network Service', 'Domain Name System', 'Digital Network Security', 'Dynamic Node Setup', 'b', 10),
(2, 'Which HTTP method is idempotent?', 'POST', 'GET', 'PATCH', 'None of the above', 'b', 10),
(3, 'What is master-slave replication?', 'All nodes are equal', 'One node handles writes, others replicate', 'Data is split across nodes', 'No replication', 'b', 10),
(3, 'What is eventual consistency?', 'Data is always consistent', 'Data will become consistent over time', 'Data is never consistent', 'Data is deleted eventually', 'b', 10),
(3, 'Which is a benefit of replication?', 'Increased complexity', 'Higher availability', 'More storage cost only', 'Slower reads', 'b', 10);
