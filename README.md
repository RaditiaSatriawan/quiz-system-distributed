# 📝 QuizNet: Distributed Assessment System

A full-fledged distributed microservices-based Quiz and Assessment Submission system built with Python Flask, PostgreSQL, RabbitMQ, and Docker. This project is specifically designed to fulfill the **Distributed Systems (Sistem Terdistribusi) Final Exam (UAS)** requirements.

---

## 🎯 Academic Requirements Fulfilled

This project fully implements all the requested rubrics:

1. **REST-API (15%)**: All communication between the Frontend (Browser) and Backend Gateway uses standard HTTP REST protocols.
2. **Service-to-Service RPC (20%)**: Microservices communicate internally using REST-based RPC calls (e.g., Submission Service querying Quiz Service for answer keys).
3. **RabbitMQ for Asynchronous Workflow (20%)**: Quiz submissions are pushed to a RabbitMQ queue. Grading and Notification happen asynchronously in the background.
4. **Persistent Storage (10%)**: Utilizes PostgreSQL with a Database-per-Service architecture.
5. **Case Study Domain (10%)**: Implements the **Quiz/assessment submission** domain.
6. **Leader Election (10%-20%)**: Features a custom 5-Node **Ring-based (Chang-Roberts)** leader election algorithm with split-brain prevention and fault-tolerance handling.
7. **API Load Balancing (5%)**: Utilizes Nginx to distribute incoming traffic evenly across the 5 Gateway Nodes using Round-Robin.

---

## 🏗️ System Architecture (5-Node Cluster)

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                            NGINX LOAD BALANCER                             │
│                             (Port 80 - GUI)                                │
└─────┬───────────┬─────────────┬──────────────┬──────────────┬──────────────┘
      │           │             │              │              │
┌─────▼────┐ ┌────▼─────┐ ┌─────▼────┐   ┌─────▼────┐   ┌─────▼────┐
│ Gateway 1│ │ Gateway 2│ │ Gateway 3│   │ Gateway 4│   │ Gateway 5│
│ (P:5000) │ │ (P:5001) │ │ (P:5002) │   │ (P:5003) │   │ (P:5004) │
└─────┬────┘ └────┬─────┘ └─────┬────┘   └─────┬────┘   └─────┬────┘
      │           │             │              │              │
      └───────────┴─── Ring-based Leader Election ────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
         ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼───────┐
         │Quiz Service │ │ Submission │ │ Notification │
         │ (Port 6000) │ │  Service   │ │   Service    │
         │  REST/RPC   │ │(Port 7000) │ │ (Port 8000)  │
         └──────┬──────┘ └─────┬──────┘ └──────┬───────┘
                │               │               │
                │          ┌────▼────┐          │
                │          │RabbitMQ │──────────┘
                │          │  (5672) │ Async Messaging
                │          └─────────┘
                │               │
         ┌──────▼───────────────▼──────┐
         │     PostgreSQL Cluster      │
         │   Primary / Replica DBs     │
         └─────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Technology     | Purpose                                    |
|----------------|--------------------------------------------|
| **Python Flask** | Microservice framework for REST APIs     |
| **PostgreSQL 15** | Primary relational database             |
| **RabbitMQ**   | Message broker for async communication     |
| **Nginx**      | Load balancer and static file server       |
| **Docker**     | Containerization of all services           |
| **Docker Compose** | Multi-container orchestration          |
| **HTML/CSS/JS** | Dynamic Web Frontend (Admin & Student)    |

---

## 🚀 How to Run

1. **Clone or navigate to the project directory:**
   ```bash
   cd "uas"
   ```

2. **Build and start all 10+ containers in detached mode:**
   ```bash
   docker-compose up --build -d
   ```

3. **To test Fault Tolerance (Leader Election):**
   ```bash
   # Kill the current leader (e.g., Node 5) to watch Node 4 take over
   docker stop uas-api-gateway-5-1
   ```

4. **To stop all services:**
   ```bash
   docker-compose down
   ```

---

## 🌐 How to Access

| Interface            | URL                          | Description                  |
|----------------------|------------------------------|------------------------------|
| **Student Portal**   | http://localhost/student.html| Take quizzes, view grades    |
| **Admin Dashboard**  | http://localhost/admin.html  | Manage quizzes, view nodes   |
| **RabbitMQ Admin**   | http://localhost:15672       | Monitor async queues         |

**Credentials:**
- RabbitMQ: `guest` / `guest`
- PostgreSQL: `admin` / `secret123` (Database: `quizdb`)

---

## 👥 Team Information

| Name           | Student ID     |
|----------------|----------------|
| Member 1       | XXXXXXXXXX     |
| Member 2       | XXXXXXXXXX     |
| Member 3       | XXXXXXXXXX     |

---

## 📄 License

This project is developed exclusively as a coursework assignment for the **Distributed Systems (Sistem Terdistribusi)** course, Semester 6.
