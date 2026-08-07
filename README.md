# AG CMS — AI-Powered Church Management System

Enterprise-grade church management platform built with Flask, PostgreSQL, and AI integration.

## Features

- **Role-Based Access Control** — 7 user roles with granular permissions
- **Member Management** — Registration, profiles, QR codes, family tracking
- **Attendance** — QR check-in, manual entry, reports
- **Finance** — Tithes, offerings, expenses, budgets, receipts
- **Events & Departments** — Full lifecycle management
- **Communication** — Announcements and notifications
- **Reports & Analytics** — Interactive dashboards with Chart.js
- **AI Assistant** — Natural language queries powered by OpenAI
- **Smart Follow-Up** — Automated absence detection and visitor tracking
- **Security** — CSRF, password hashing, audit logs, account lockout
- **Dark/Light Mode** — Modern responsive UI

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (production) or SQLite (development)

### Installation

```bash
cd ag-cms
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python seed.py
python run.py
```

Open http://localhost:5000 and log in with `developer` / `dev123456`.

## Default Accounts

| Role | Username | Password |
|------|----------|----------|
| Developer | developer | dev123456 |
| Super Admin | pastor | admin123456 |
| Church Admin | secretary | admin123456 |
| Finance Officer | finance | admin123456 |
| Attendance Officer | usher | admin123456 |

## Project Structure

```
ag-cms/
├── app/
│   ├── blueprints/     # Flask blueprints (MVC controllers)
│   ├── models/         # SQLAlchemy models (3NF)
│   ├── services/       # Business logic (AI, QR, backup)
│   ├── utils/          # Helpers, decorators, permissions
│   ├── templates/      # Jinja2 HTML templates
│   └── static/         # CSS, JS assets
├── docs/               # Documentation
├── seed.py             # Database seeder
├── run.py              # Application entry point
└── requirements.txt
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [User Manual](docs/USER_MANUAL.md)
- [Administrator Manual](docs/ADMIN_MANUAL.md)
- [API Documentation](docs/API.md)
- [Database ER Diagram](docs/ER_DIAGRAM.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## Technology Stack

- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js, Font Awesome
- **Backend:** Python, Flask, Flask Blueprint Architecture
- **Database:** PostgreSQL / SQLite
- **AI:** OpenAI API (optional)
- **Security:** Flask-Login, Werkzeug hashing, CSRF protection

## License

Proprietary — AG CMS © 2026
