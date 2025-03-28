# Housing Queue Auto Login & Points Tracker

This project automates monthly logins to various Swedish municipal housing queue websites that use the Momentum Property Management Platform. The purpose is to retain your queue points, which can be lost if you don't log in regularly.

It also retrieves your current queue points and optionally logs out after the session. The project supports multiple sites using different domains but similar backend APIs.

## ✅ Features

- Automatic login via Momentum’s public API (OAuth2/PKCE)
- Fetch queue points for categories like Housing, Parking, Storage
- Automatic logout
- Modular setup for supporting multiple sites
- Configurable via `.env`
- Designed to run headlessly on a home server or cron job

## 📁 Project Structure

```bash
/
├── sites/                  # One file per supported site (e.g., KBAB, Gavlegårdarna)
│   ├── kbab.py
│   └── ...
├── utils/
│   └── momentum_client.py  # Shared logic for communicating with Momentum API
├── config/
│   └── .env                # Stores login credentials and secrets
├── main.py                 # Entry point to run a specific site
├── logs/                   # Optional: store log history
└── README.md
```

## ⚙️ Setup

1. Install dependencies

    pip install -r requirements.txt

2. Create `.env` file in `config/` with your credentials

    KBAB_USERNAME=your_username
    KBAB_PASSWORD=your_password

You can later add credentials for other sites as needed.

## 🚀 Running

Run login and point-check for a specific site:

    python sites/kbab.py

Or, if using `main.py` with CLI flags (future feature):

    python main.py --site kbab

## ➕ Adding a New Site

Each site typically differs only in domain and authentication keys. To add support for another site:

1. Copy `kbab.py` to `newsite.py`

2. Update the `base_url`, `client_id`, `device_key`, and `api_key`
3. Add corresponding credentials to `.env`

## 📅 Automation

You can run this monthly using `cron`, `systemd`, or a Python scheduler like `schedule`. Example cron job:

    0 8 1 * * /usr/bin/python3 /path/to/project/sites/kbab.py

## 🔐 Security Notes

- Never commit your `.env` file to version control
- If running publicly, consider encrypting credentials and using secure vaults

## 🧩 To Do

- CLI interface for selecting and running sites
- Logging with timestamped history
- Notifications via email or Telegram
- Docker support
