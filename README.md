# QueuePilot - Housing Queue Auto Login & Points Tracker

QueuePilot automates monthly logins to various Swedish municipal housing queue websites using the Momentum Property Management Platform. It prevents loss of queue points and retrieves your current status.

---

## ✅ Features

- Automatic login using OAuth2/PKCE (Momentum API)
- Fetches queue points (e.g., housing, parking, storage)
- Automatic logout
- Modular site support (driven by database)
- Centralized credential storage via MariaDB
- Dockerized and scalable via Docker Swarm

---

## 📁 Project Structure

```bash
/
├── app/
│   ├── config/              # Contains .env
│   ├── logs/                # Optional logging
│   ├── sites/               # Site logic (momentum.py)
│   ├── utils/               # DB and API helpers
│   │   ├── db.py
│   │   └── momentum_client.py
│   ├── main.py              # Main entry point
│   └── requirements.txt     # Python dependencies
├── docker-compose.yml       # For running via Docker
├── Dockerfile               # Builds the container
├── README.md
└── .gitignore
```

---

## ⚙️ Setup

1. Create MariaDB database with `credentials` and `sites` tables.
2. Create a `.env` file in the same folder as `docker-compose.yml` (root directory `/`):

```ini
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PASS=your-db-password
DB_NAME=queue_pilot
```

3. Build and run with Docker:

```bash
docker compose up --build
```

---

## 🐳 Docker Tips

- Edit `CMD` in Dockerfile to run a specific site or `all`
- Logs go to `app/logs/` by default
- Use volume mounts for persistence

---

## 🐝 Docker Swarm (Preview)

QueuePilot is designed to scale. Each customer/job can run in parallel as needed.

```bash
docker swarm init
docker stack deploy -c docker-compose.yml queuepilot
```

In the future: queue consumers and autoscaling via Docker events or task queues.

---

## 🛡 Security Tips

- Never store real passwords in code or VCS
- Use hashed or encrypted secrets where possible

---

## 🧩 Roadmap

- Web interface for queue selection and user management
- Notification integrations
- Job scheduler backend (e.g., Celery)
- Add other websites not using momentum (Already have two sites ready)
