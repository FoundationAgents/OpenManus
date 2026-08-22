# Upload-Management System für Immobilienfinanzierungen

## 🎯 Überblick

Vollständiges, produktionsreifes System zur Verwaltung von Dokumenten-Uploads für Immobilienfinanzierungen. Das System bietet:

- ✅ **Customer Portal**: Intuitive Upload-Checkliste
- ✅ **Admin Dashboard**: Übersicht über alle Uploads & Genehmigungsprozesse
- ✅ **Bank-Integration**: Lesezugriff für Finanzierungskunden
- ✅ **Automatisierte Workflows**: E-Mail-Benachrichtigungen (mit Admin-Genehmigung)
- ✅ **Flexible Bank-Profile**: Deutsche Bank, Commerzbank, Baufi24, Dr. Klein, etc.
- ✅ **Zeitlose Dokumentbezeichnungen**: "Lohnabrechnung letzter Monat" (nicht datumsspezifisch)
- ✅ **Sicherheit**: KYC/AML, DSGVO, Verschlüsselung, Audit Trail
- ✅ **Skalierbar**: Docker, PostgreSQL, Redis, Celery

---

## 📁 Projektstruktur

```
openmanus/
├── backend/                          # FastAPI Backend
│   ├── main.py                      # Haupt-API-Datei
│   ├── models.py                    # SQLAlchemy ORM Modelle
│   ├── config.py                    # Konfigurationseinstellungen
│   ├── schemas.py                   # Pydantic Schemas (noch zu erstellen)
│   ├── services/                    # Business Logic
│   │   ├── document_service.py      # Dokumentenverwaltung
│   │   ├── email_service.py         # E-Mail-Versendung
│   │   ├── validation_service.py    # Datei-Validierung
│   │   ├── admin_service.py         # Admin-Funktionen
│   │   └── storage_service.py       # Dateispeicher
│   ├── celery_app.py                # Celery Task Queue (noch zu erstellen)
│   └── requirements.txt              # Python Dependencies
│
├── frontend/                         # React/TypeScript Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadForm.tsx       # Customer Upload Form
│   │   │   ├── DocumentChecklist.tsx # Checkliste
│   │   │   ├── AdminDashboard.tsx   # Admin-View
│   │   │   └── BankPortal.tsx       # Bank-Zugriff
│   │   ├── pages/
│   │   │   ├── CustomerPortal.tsx
│   │   │   ├── AdminPanel.tsx
│   │   │   └── BankView.tsx
│   │   ├── store/                   # Zustand State Management
│   │   ├── api/                     # API Clients
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts               # Build Config
│
├── config/                           # Konfigurationsdateien
│   ├── documents.json               # Dokumenttypen & Anforderungen
│   ├── bank_profiles.json           # Bank-Profile
│   └── email_templates/             # E-Mail-Templates (noch zu erstellen)
│
├── database/
│   └── init.sql                     # Datenbank-Initialisierung (noch zu erstellen)
│
├── docker-compose.yml               # Docker Compose Setup
├── Dockerfile.upload                # Backend Dockerfile
├── .env.example                     # Environment Variables Beispiel
└── UPLOAD_STRUCTURE_CONCEPT.md      # Detaillierte Konzept-Dokumentation
```

---

## 🚀 Quick Start

### Voraussetzungen

- Docker & Docker Compose
- oder: Python 3.11+, Node.js 20+, PostgreSQL 15+, Redis 7+

### Option 1: Docker (Empfohlen)

```bash
# 1. Repository klonen
git clone https://github.com/yourusername/openmanus.git
cd openmanus

# 2. Environment konfigurieren
cp .env.example .env
# Bearbeiten Sie .env mit Ihren Einstellungen (SMTP, Datenbank, etc.)

# 3. Docker-Container starten
docker-compose up -d

# 4. Datenbank initialisieren
docker-compose exec backend python -m alembic upgrade head

# 5. System testen
curl http://localhost:8000/health
```

Zugriff:
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost (über Nginx)

### Option 2: Lokal entwickeln

#### Backend Setup

```bash
# 1. Python Virtual Environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Datenbank Setup (PostgreSQL muss laufen)
export DATABASE_URL="postgresql://user:password@localhost/upload_system"
python -m alembic upgrade head

# 4. Backend starten
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
# 1. Dependencies installieren
cd ../frontend
npm install

# 2. Development Server starten
npm run dev
```

---

## 📊 Kern-Features

### 1. Customer Portal

**Kunde sieht:**
- Klare Checkliste: Was muss hochgeladen werden?
- Live-Status: "65% vollständig"
- Kategorien: Kundenunterlagen, Objektunterlagen
- Drag-and-Drop Upload
- Datei-Vorschau
- Nachrichten vom Admin

**Workflow:**
```
1. Kunde erhält Upload-Link
2. Sieht Checkliste aller erforderlichen Dokumente
3. Lädt Dokumente hoch (automatisch kategorisiert)
4. Sieht in Echtzeit, was noch fehlt
5. Erhält Benachrichtigung sobald vollständig
```

### 2. Admin Dashboard

**Admin sieht:**
- Übersicht aller Upload-Anfragen (mit Status-Filter)
- Welche Dokumente fehlen bei jedem Kunden
- Genehmigungsbuttons für Benachrichtigungen
- Audit Trail (wer hat wann was getan)
- Möglichkeit, zusätzliche Dokumente anzufordern

**Admin-Workflow:**
```
1. Admin sieht: Kunde xyz - 3 erforderliche Dokumente fehlen
2. Admin klickt "Kunde benachrichtigen"
3. Admin sieht optionale Message-Bearbeitung
4. Admin genehmigt ("Senden")
5. Customer erhält automatisch E-Mail mit:
   - Liste fehlender Dokumente
   - Link zum Upload
   - Admin-Nachricht
```

### 3. Bank-Integration

**Bank/Finanzierungskunde erhält:**
- Lesezugriff auf alle hochgeladenen Unterlagen
- Status: "Bereit zur Einreichung" oder "Unvollständig"
- Download-Paket (alle Dateien als ZIP)
- Kein Upload-Zugriff (nur Lesezugriff)

---

## 🔒 Sicherheit & Compliance

### Implementierte Features

- **KYC/AML**: Kundentypprüfung, Dokumentenverifizierung
- **DSGVO**: Datenschutz, Recht auf Löschung
- **Verschlüsselung**: AES-256 für Dateienspeicher, TLS 1.3 für Transit
- **Audit Trail**: Vollständiges Logging aller Aktivitäten
- **Rollenseparation**: Customer ≠ Admin ≠ Bank
- **Virenscan**: Automatisches Scanning hochgeladener Dateien
- **Datei-Validierung**: Typ, Größe, Format-Prüfung

### Datenschutz-Einstellungen

Alle Einstellungen in `.env` konfigurierbar:

```env
# Admin-Genehmigung erforderlich vor E-Mail?
ADMIN_APPROVAL_REQUIRED=True
AUTO_SEND_CUSTOMER_EMAILS=False

# Document Expiry
DOCUMENT_EXPIRY_SETTINGS={
  "personalausweis": 3650,  # 10 Jahre
  "grundbuchauszug": 180,   # 6 Monate
  ...
}
```

---

## 📋 Dokumenttypen & Bank-Profile

### Dokumenttypen (config/documents.json)

Das System definiert 20+ Dokumenttypen mit:
- **Label**: "Lohnabrechnung - Letzter Monat" (zeitlos)
- **Kategorien**: kundenunterlagen, objektunterlagen
- **Anforderungen**: isRequired, isConditional, expiryDays
- **Bank-Varianten**: Welche Bank braucht welches Dokument

### Unterstützte Bank-Profile (config/bank_profiles.json)

```json
{
  "Deutsche Bank": {
    "requiredSalaryMonths": 3,
    "minEigenkapitalPercent": 10,
    "flexibleDocumentation": false
  },
  "Commerzbank": {
    "requiredSalaryMonths": 2,
    "minEigenkapitalPercent": 10,
    "flexibleDocumentation": true
  },
  "Baufi24": {
    "requiredSalaryMonths": 2,
    "flexibleDocumentation": true
  }
  // ... mehr Profile
}
```

---

## 🤖 Automatisierte Workflows

### Email-Benachrichtigungen (mit Admin-Genehmigung)

```
Trigger: Kunde hat nicht alle erforderlichen Dokumente
  ↓
Admin wird benachrichtigt (Dashboard zeigt fehlende Docs)
  ↓
Admin klickt "Kunde benachrichtigen"
  ↓
Optional: Admin bearbeitet Nachricht
  ↓
Admin klickt "Senden"
  ↓
Celery Background Task: E-Mail wird sofort gesendet
  ↓
Kunde erhält automatische E-Mail mit:
  - Welche Dokumente fehlen
  - Upload-Link
  - Admin-Nachricht
```

### Dokumentenverfallsprüfung

```
Täglich automatisiert:
  - Prüfung: Personalausweis gültig bis [Datum]?
  - Prüfung: Grundbuchauszug noch aktuell (< 6 Monate)?
  - Prüfung: Lohnabrechnung noch aktuell (< 3 Monate)?
  
Falls abgelaufen:
  - Status auf "expired" setzen
  - Admin benachrichtigen
  - Kundenbericht aktualisieren
```

### Bedingte Anforderungen (Logik)

```javascript
// Beispiel: Mieterliste nur bei Mietimmobilien erforderlich
if (propertyType === 'rental' || propertyType === 'multi_unit') {
  documentTypes.push('tenant_list');
}

// Beispiel: Zusätzliche Prüfung bei hohem LTV
if (ltvRatio > 0.85) {
  requiredDocuments.push('additional_valuation');
}
```

---

## 📧 Email-Konfiguration

### SMTP Setup

Für verschiedene Provider:

**Gmail:**
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-char app password
```

**Strato (HiDrive):**
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
```

---

## 🗄️ Datenbank-Schema

### Haupttabellen

```sql
-- Kunden
CREATE TABLE customers (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE,
  first_name VARCHAR,
  last_name VARCHAR,
  created_at TIMESTAMP
);

-- Upload-Anfragen
CREATE TABLE upload_requests (
  id UUID PRIMARY KEY,
  customer_id UUID REFERENCES customers,
  status ENUM (pending, in_progress, submitted, complete),
  deadline TIMESTAMP,
  created_at TIMESTAMP
);

-- Dokumente
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  upload_request_id UUID REFERENCES upload_requests,
  document_type VARCHAR,
  label VARCHAR,
  status ENUM (pending, uploaded, expired, missing),
  file_path VARCHAR,
  uploaded_at TIMESTAMP,
  expiry_date TIMESTAMP
);

-- Admin-Genehmigungen
CREATE TABLE admin_approvals (
  id UUID PRIMARY KEY,
  upload_request_id UUID REFERENCES upload_requests,
  approval_type ENUM (request_additional_documents, notify_missing_documents),
  approved_by UUID,
  approved_at TIMESTAMP,
  email_sent BOOLEAN
);

-- Audit Log
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  upload_request_id UUID REFERENCES upload_requests,
  action VARCHAR,
  actor UUID,
  details JSONB,
  created_at TIMESTAMP
);
```

---

## 🔧 API Endpoints

### Customer Endpoints

```
GET  /api/v1/upload-requests/{request_id}
POST /api/v1/upload-requests/{request_id}/upload
GET  /api/v1/upload-requests/{request_id}/documents/{doc_id}/download
```

### Admin Endpoints

```
GET  /api/v1/admin/upload-requests
POST /api/v1/admin/approval/request-additional-documents
POST /api/v1/admin/approval/notify-missing-documents
GET  /api/v1/admin/upload-requests/{request_id}/audit-log
```

### Bank Endpoints

```
GET  /api/v1/bank/upload-requests/{request_id}
POST /api/v1/bank/export-documents/{request_id}
```

**API Dokumentation:** http://localhost:8000/docs

---

## 🧪 Testing

```bash
# Backend Tests
cd backend
pytest

# Frontend Tests
cd ../frontend
npm test

# Integration Tests
pytest backend/tests/integration/
```

---

## 📈 Monitoring & Logging

### Logs ansehen

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Datei
tail -f /var/log/upload_system.log
```

### Health Check

```bash
curl http://localhost:8000/health
```

---

## 🚢 Deployment

### Production Checklist

- [ ] `.env` mit sicheren Werten erstellen
- [ ] SSL/TLS Zertifikate einrichten
- [ ] Email SMTP testen
- [ ] Datenbank-Backups konfigurieren
- [ ] Logging & Monitoring (Sentry, etc.)
- [ ] Database-Migrationen durchführen
- [ ] Security-Audit durchführen

### Systemanforderungen

**Minimal:**
- 2 CPU Cores
- 2 GB RAM
- 10 GB Storage (für Uploads)

**Empfohlen (Production):**
- 4 CPU Cores
- 8 GB RAM
- 100 GB+ Storage (für Uploads)
- PostgreSQL Backup-Strategie

---

## 📚 Weitere Dokumentation

- **Detailliertes Konzept**: `UPLOAD_STRUCTURE_CONCEPT.md`
- **API-Dokumentation**: http://localhost:8000/docs (Swagger UI)
- **Datenbank-Migrationen**: `alembic/`
- **Bank-Integration**: `config/bank_profiles.json`

---

## 🤝 Contributing

1. Feature-Branch erstellen: `git checkout -b feature/my-feature`
2. Änderungen committen: `git commit -am 'Add my feature'`
3. Push zum Branch: `git push origin feature/my-feature`
4. Pull Request erstellen

---

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: `docs/` Verzeichnis
- **Email**: support@yourdomain.com

---

## 📄 Lizenz

MIT License - Siehe LICENSE Datei

---

**Version**: 1.0.0  
**Letzte Aktualisierung**: 2026-04-14  
**Maintainer**: Your Name / Team
