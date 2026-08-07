# Installation Guide — AG CMS

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.12 |
| RAM | 512 MB | 2 GB |
| Disk | 500 MB | 2 GB |
| Database | SQLite 3 | PostgreSQL 14+ |

## Development Setup (SQLite)

### 1. Clone and Configure

```bash
git clone <repository-url> ag-cms
cd ag-cms
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # Windows
```

### 2. Environment Variables

Edit `.env`:

```env
FLASK_ENV=development
SECRET_KEY=your-secure-random-key
DATABASE_URL=sqlite:///ag_cms.db
OPENAI_API_KEY=sk-...        # Optional
CHURCH_NAME=ASSEMBLIES OF GOD

```

### 3. Initialize Database

```bash
python seed.py
```

### 4. Run Application

```bash
python run.py
```

Visit http://localhost:5000

## Production Setup (PostgreSQL)

### 1. Create Database

```sql
CREATE DATABASE ag_cms;
CREATE USER ag_cms_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ag_cms TO ag_cms_user;
```

### 2. Configure Environment

```env
FLASK_ENV=production
SECRET_KEY=<64-char-random-string>
DATABASE_URL=postgresql://ag_cms_user:secure_password@localhost:5432/ag_cms
SESSION_TIMEOUT_MINUTES=30
```

### 3. Initialize and Deploy

```bash
pip install gunicorn
python seed.py
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

## Database Migrations

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate virtual environment |
| Database locked | Stop other processes using SQLite |
| CSRF errors | Ensure forms include `csrf_token` |
| AI not working | Set `OPENAI_API_KEY` in `.env` |

## Security Checklist

- [ ] Change default passwords after first login
- [ ] Set strong `SECRET_KEY` in production
- [ ] Enable HTTPS with reverse proxy (nginx)
- [ ] Configure PostgreSQL with SSL
- [ ] Set up regular database backups
- [ ] Restrict Developer role access
