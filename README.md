# 📝 Distributed Quiz Assessment System

A distributed microservices-based Quiz and Assessment Submission system built with Python Flask, PostgreSQL, RabbitMQ, and Docker. The system supports quiz management, submission processing, automated grading, and real-time notifications through an event-driven architecture.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NGINX LOAD BALANCER                         │
│                         (Port 80 - GUI)                            │
└──────────┬──────────────────┬──────────────────┬────────────────────┘
           │                  │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │ API Gateway │   │ API Gateway │   │ API Gateway │
    │   Node 1    │   │   Node 2    │   │   Node 3    │
    │  (Port 5000)│   │  (Port 5001)│   │  (Port 5002)│
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │    Ring-based Leader Election       │
           └──────────────┬─────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
   ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼───────┐
   │Quiz Service │ │ Submission │ │ Notification │
   │ (Port 6000) │ │  Service   │ │   Service    │
   │  REST/RPC   │ │(Port 7000) │ │ (Port 8000)  │
   └──────┬──────┘ └─────┬──────┘ └──────┬───────┘
          │               │               │
          │          ┌────▼────┐           │
          │          │RabbitMQ │───────────┘
          │          │  (5672) │  Async Messaging
          │          └─────────┘
          │               │
   ┌──────▼───────────────▼──────┐
   │     PostgreSQL Cluster      │
   │  Primary (5432)             │
   │  Replica (5433)             │
   └─────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Technology     | Purpose                                    |
|----------------|--------------------------------------------|
| **Python Flask** | Microservice framework for REST APIs     |
| **PostgreSQL 15** | Primary relational database with replication |
| **RabbitMQ**   | Message broker for async communication     |
| **Nginx**      | Load balancer and static file server       |
| **Docker**     | Containerization of all services           |
| **Docker Compose** | Multi-container orchestration          |
| **HTML/CSS/JS** | Frontend GUI                              |

---

## ✨ Features

- **RESTful API** — Full CRUD operations for quizzes, questions, submissions, and notifications
- **RPC (Remote Procedure Call)** — Synchronous inter-service communication via REST-based RPC
- **RabbitMQ Message Queue** — Asynchronous event-driven grading and notification pipeline
- **PostgreSQL Replication** — Primary-Replica database setup for high availability
- **Ring-based Leader Election** — Distributed consensus among API Gateway nodes
- **Nginx Load Balancing** — Round-robin traffic distribution across 3 API gateway instances
- **Docker Containerization** — All services run in isolated Docker containers
- **Web GUI** — Browser-based interface for taking quizzes and viewing results
- **Health Checks** — Built-in health monitoring for all services
- **Auto-restart** — Services automatically restart on failure

---

## 📋 Prerequisites

Make sure you have the following installed on your machine:

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)

---

## 🚀 How to Run

1. **Clone or navigate to the project directory:**

   ```bash
   cd "d:\Tugas2 Disini Jal\SMT 6\Sistem Terdistribusi\uas"
   ```

2. **Build and start all services:**

   ```bash
   docker-compose up --build
   ```

3. **To run in detached (background) mode:**

   ```bash
   docker-compose up --build -d
   ```

4. **To stop all services:**

   ```bash
   docker-compose down
   ```

5. **To stop and remove all data (volumes):**

   ```bash
   docker-compose down -v
   ```

---

## 🌐 How to Access

| Service              | URL                          | Description                  |
|----------------------|------------------------------|------------------------------|
| **Web GUI**          | http://localhost              | Main quiz interface          |
| **API Gateway 1**    | http://localhost:5000         | API Gateway Node 1           |
| **API Gateway 2**    | http://localhost:5001         | API Gateway Node 2           |
| **API Gateway 3**    | http://localhost:5002         | API Gateway Node 3           |
| **Quiz Service**     | http://localhost:6000         | Quiz management service      |
| **Submission Service** | http://localhost:7000       | Submission processing        |
| **Notification Service** | http://localhost:8000     | Notification service         |
| **RabbitMQ Dashboard** | http://localhost:15672      | Message broker management    |
| **PostgreSQL Primary** | localhost:5432              | Primary database             |
| **PostgreSQL Replica** | localhost:5433              | Replica database             |

**RabbitMQ Credentials:** `guest` / `guest`
**PostgreSQL Credentials:** `admin` / `secret123` (Database: `quizdb`)

---

## 📡 API Documentation

All API endpoints are accessible through the Nginx load balancer at `http://localhost/api/` or directly through individual API Gateway instances.

### Quiz Endpoints

| Method | Endpoint                   | Description                  |
|--------|----------------------------|------------------------------|
| GET    | `/api/quizzes`             | Get all quizzes              |
| GET    | `/api/quizzes/<id>`        | Get quiz by ID               |
| POST   | `/api/quizzes`             | Create a new quiz            |
| GET    | `/api/quizzes/<id>/questions` | Get questions for a quiz  |
| POST   | `/api/quizzes/<id>/questions` | Add question to a quiz    |

### Submission Endpoints

| Method | Endpoint                   | Description                  |
|--------|----------------------------|------------------------------|
| GET    | `/api/submissions`         | Get all submissions          |
| GET    | `/api/submissions/<id>`    | Get submission by ID         |
| POST   | `/api/submissions`         | Submit quiz answers          |
| GET    | `/api/submissions/<id>/result` | Get grading result       |

### Notification Endpoints

| Method | Endpoint                          | Description                    |
|--------|-----------------------------------|--------------------------------|
| GET    | `/api/notifications`              | Get all notifications          |
| GET    | `/api/notifications/<student>`    | Get notifications for student  |
| PUT    | `/api/notifications/<id>/read`    | Mark notification as read      |

### System Endpoints

| Method | Endpoint                   | Description                  |
|--------|----------------------------|------------------------------|
| GET    | `/api/health`              | API Gateway health check     |
| GET    | `/api/leader`              | Get current leader info      |
| POST   | `/election/start`          | Trigger leader election      |

---

## 📂 Project Structure

```
uas/
├── docker-compose.yml          # Docker Compose orchestration
├── README.md                   # Project documentation
├── database/
│   └── init.sql                # PostgreSQL initialization script
├── nginx/
│   └── nginx.conf              # Nginx load balancer configuration
├── api-gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                  # API Gateway with leader election
├── quiz-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                  # Quiz management service
├── submission-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                  # Submission & grading service
├── notification-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                  # Notification service
└── gui/
    └── index.html              # Web GUI
```

---

## 🔄 System Workflow

1. **Student** opens the GUI and selects a quiz
2. **Nginx** load-balances the request to one of the **API Gateway** nodes
3. **API Gateway** forwards the request to the **Quiz Service** via REST/RPC
4. Student submits answers → **API Gateway** sends to **Submission Service**
5. **Submission Service** publishes a grading event to **RabbitMQ**
6. **Submission Service** consumes the grading event, calculates the score, and publishes a notification event
7. **Notification Service** consumes the notification event and stores the result
8. Student checks their grade via the GUI

---

## 👥 Team Information

| Name           | Student ID     | Role                        |
|----------------|----------------|-----------------------------|
| Member 1       | XXXXXXXXXX     | Backend Developer            |
| Member 2       | XXXXXXXXXX     | Backend Developer            |
| Member 3       | XXXXXXXXXX     | Frontend Developer           |
| Member 4       | XXXXXXXXXX     | DevOps / Infrastructure      |

---

## 📄 License

This project is developed as a coursework assignment for the **Distributed Systems (Sistem Terdistribusi)** course, Semester 6.
