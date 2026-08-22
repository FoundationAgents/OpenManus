# Setup & Deployment Guide

## 🚀 Schnellstart (5 Minuten)

### Mit Docker (Empfohlen)

```bash
# 1. Repository klonen
git clone https://github.com/domituerk/openmanus.git
cd openmanus

# 2. Environment konfigurieren
cp .env.example .env
nano .env  # Bearbeiten Sie SMTP_USER, DB_PASSWORD, SECRET_KEY

# 3. Docker-Container starten
docker-compose up -d

# 4. Datenbank initialisieren
docker-compose exec backend python -m alembic upgrade head

# 5. Browser öffnen
# Frontend: http://localhost
# API Docs: http://localhost:8000/docs
```

### Lokal (Entwicklung)

#### Backend

```bash
cd backend

# Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies
pip install -r requirements.txt

# Umgebungsvariablen
export DATABASE_URL="postgresql://user:password@localhost/upload_system"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"

# Datenbank
python -m alembic upgrade head

# Server starten
uvicorn main:app --reload

# Auf http://localhost:8000 öffnen
```

#### Frontend

```bash
cd frontend

# Dependencies
npm install

# Development Server
npm run dev

# Auf http://localhost:5173 öffnen
```

---

## 📋 Anforderungen

### System
- Linux/macOS/Windows
- Docker & Docker Compose (oder lokal: Python 3.11+, Node.js 20+)

### Lokal installieren
- **Backend**: Python 3.11+, PostgreSQL 15+, Redis 7+
- **Frontend**: Node.js 20+

### Internet
- SMTP Server (Gmail, Strato, Office 365, etc.)
- Optional: AWS S3 für File Storage

---

## 🔧 Konfiguration

### .env Datei

```env
# =====================================================================
# CRITICAL - Ändern Sie diese!
# =====================================================================

# Database
DATABASE_URL=postgresql://user:secure_password@localhost/upload_system

# Email (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-char app password

# Security
SECRET_KEY=your-super-secret-key-change-this

# Storage
STORAGE_PATH=/var/uploads
MAX_FILE_SIZE_MB=50

# Admin
ADMIN_APPROVAL_REQUIRED=True
AUTO_SEND_CUSTOMER_EMAILS=False
```

### SMTP Konfiguration

**Gmail:**
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # Erstellen Sie App Password unter Google Account Security
```

**Strato:**
```env
SMTP_SERVER=smtp.strato.de
SMTP_PORT=587
SMTP_USER=your-email@yourdomain.de
SMTP_PASSWORD=your_strato_password
```

**Office 365:**
```env
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.onmicrosoft.com
SMTP_PASSWORD=your_office_password
```

---

## 📊 Datenbank

### Initialisierung

```bash
# Mit init.sql
psql -U postgres -d upload_system -f database/init.sql

# Oder mit Alembic
python -m alembic upgrade head
```

### Views

Das System erstellt automatisch diese Views:

```sql
-- Upload Request Statistiken
SELECT * FROM v_upload_request_stats;

-- Überfällige Anfragen
SELECT * FROM v_overdue_requests;
```

### Backup

```bash
# Backup
pg_dump -U user upload_system > backup.sql

# Restore
psql -U user upload_system < backup.sql
```

---

## 🧪 Testing

### Unit Tests

```bash
cd backend

# Install pytest
pip install pytest pytest-asyncio

# Alle Tests
pytest

# Spezifischer Test
pytest tests/test_document_service.py::TestDocumentService::test_calculate_completion_full

# Mit Coverage
pytest --cov=backend tests/
```

### Integration Tests

```bash
# API-Tests (benötigt laufende DB)
pytest tests/test_api_endpoints.py -v
```

### Manual Testing

**Health Check:**
```bash
curl http://localhost:8000/health
```

**API Documentation:**
Öffnen Sie http://localhost:8000/docs im Browser (Swagger UI)

---

## 🚀 Deployment

### Production Checklist

- [ ] Environment Variables aktualisiert
- [ ] SSL/TLS Zertifikate installiert
- [ ] Email SMTP getestet
- [ ] Database Backups konfiguriert
- [ ] Logging & Monitoring eingerichtet
- [ ] Security Audit durchgeführt
- [ ] Rate Limiting aktiviert
- [ ] CORS konfiguriert

### Docker Deployment

```bash
# Build Image
docker build -t upload-system:latest -f Dockerfile.upload .

# Push to Registry (z.B. Docker Hub)
docker tag upload-system:latest your-registry/upload-system:latest
docker push your-registry/upload-system:latest

# Production Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Nginx Reverse Proxy

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Frontend
    location / {
        alias /app/frontend/dist/;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🔐 Security

### Best Practices

1. **Environment Variables**
   - Speichern Sie niemals Secrets im Code
   - Verwenden Sie `.env` File (git-ignored)

2. **Database**
   - Verwenden Sie Strong Passwords
   - Regelmäßige Backups
   - Firewall-Regeln einschränken

3. **HTTPS/SSL**
   - Nutzen Sie Let's Encrypt
   - Erneuern Sie Zertifikate automatisch

4. **API Security**
   - Rate Limiting aktivieren
   - CORS restriktiv setzen
   - Input Validation überall

5. **File Upload**
   - Validieren Sie Dateitypen
   - Scannen Sie auf Malware
   - Speichern Sie außerhalb Web Root

---

## 📈 Monitoring & Logging

### Logs ansehen

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f celery_worker

# File
tail -f /var/log/upload_system.log
```

### Performance

```bash
# Database Queries
EXPLAIN ANALYZE SELECT * FROM upload_requests WHERE status = 'in_progress';

# Indexes prüfen
SELECT * FROM pg_stat_user_indexes;
```

---

## 🔧 Troubleshooting

### Database Connection fehlgeschlagen

```
Error: could not connect to server: Connection refused
```

**Lösung:**
```bash
# PostgreSQL Status prüfen
pg_isready -h localhost -p 5432

# Oder in Docker
docker-compose logs postgres
```

### Email nicht gesendet

**Prüfung:**
1. `.env` SMTP Konfiguration korrekt?
2. App-Password bei Gmail verwendet?
3. Firewall Port 587 erlaubt?

**Debug:**
```bash
# Celery Task Status
celery -A backend.celery_app inspect active

# Email Queue
SELECT * FROM email_queue WHERE status = 'failed';
```

### Frontend Build fehlgeschlagen

```bash
# Dependencies cleanen
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 📚 Weitere Ressourcen

- **API Docs**: http://localhost:8000/docs
- **Konzept**: `UPLOAD_STRUCTURE_CONCEPT.md`
- **README**: `UPLOAD_SYSTEM_README.md`
- **Datenbank**: `database/init.sql`

---

## 🆘 Support

Bei Problemen:

1. Überprüfen Sie die Logs
2. Konsultieren Sie Troubleshooting Section
3. Öffnen Sie ein GitHub Issue
4. Kontaktieren Sie Support

---

**Version**: 1.0.0  
**Letzte Aktualisierung**: 2026-04-14
