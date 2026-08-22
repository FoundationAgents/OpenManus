# Upload-Struktur für Immobilienfinanzierungen
## Konzept & Anforderungsanalyse

**Version:** 1.0  
**Datum:** April 2026  
**Zweck:** Strukturiertes und zeitloses Upload-Management für Finanzierungsunterlagen

---

## 1. Überblick & Geschäftsanforderungen

### Zielsetzung
Schaffung eines transparenten, benutzerfreundlichen Upload-Systems, das:
- Kunden exakt wissen lässt, welche Dokumente sie hochladen müssen
- Automatisch überwacht, welche Unterlagen noch fehlen
- Admin-gesteuert ist (Admin genehmigt, bevor Kunde benachrichtigt wird)
- Zeitlos funktioniert (keine datumsspezifischen Bezeichnungen)
- Finanzierungskunden und Admins in Echtzeit den Status sehen lässt

### Hauptmerkmale
1. **Kundenansicht**: Klare Checkliste mit zu ladenden Dokumenten
2. **Statustransparenz**: Live-Übersicht über hochgeladene vs. fehlende Dokumente
3. **Admin-Steuerung**: Genehmigungsprozess vor automatischen Benachrichtigungen
4. **Automatisierte Kommunikation**: E-Mails an Kunden über fehlende Unterlagen (nach Admin-Freigabe)
5. **Flexible Anforderungen**: Admin kann optionale Zusatzdokumente anfordern

---

## 2. Dokumententypen & Bankenanforderungen

### 2.1 Kundenunterlagen (Persönliche Dokumente)

#### Identifizierung (Pflicht)
- **Personalausweis - Vorderseite** (erforderlich für KYC/AML)
- **Personalausweis - Rückseite** (erforderlich für KYC/AML)
- *Alternative*: Reisepass
- *Aktualisierung*: Alle 10 Jahre (Ausweisgiltig)

#### Einkommensnachweise (Pflicht für Angestellte)
- **Lohnabrechnung - Letzter Monat** (zuletzt gehaltsakt, z.B. März)
- **Lohnabrechnung - Vorletzter Monat** (z.B. Februar)
- **Lohnabrechnung - Vor 3 Monaten** (z.B. Januar)
- *Hintergrund*: Standard-Bankenanforderung = letzte 3 Monate zur Einkommensprüfung
- *Varianten*: 
  - Manche Banken verlangen nur 1 Monat
  - Manche Banken verlangen 6 Monate
  - Für Selbstständige: Letzte 2 Steuererklärungen

#### Dezember-Lohnabrechnung (Pflicht)
- **Lohnabrechnung - Dezember Vorjahr**
- *Hintergrund*: Enthält Jahressummmen, Bonuszahlungen, 13. Monatsgehalt
- *Zeitloser Label*: "Dezember des Vorjahres" (nicht "Dezember 2025")

#### Rentner/Pensionär
- **Rentenbescheid** (aktuell, nicht älter als 1 Jahr)
- **Kontoauszug mit letztem Renteneingang** (letzter Monat)

#### Weitere optionale Kundenunterlagen
- **Schufa-Auskunft** (optional, oft vom Kunden später angefordert)
- **Kontoauszüge** (letzte 3 Monate für Eigenkapitalnachweis)
- **Steuererklärung** (optional, für Selbstständige)
- **Arbeitsvertrag** (optional, bei Arbeitgeberwechsel)
- **Baubeschreibung** (optional, bei Neubau)

---

### 2.2 Objektunterlagen (Immobiliendokumente)

#### Kaufvertrag & Registrierung (Pflicht)
- **Kaufvertrag-Entwurf** (oder Kaufvertrag unterzeichnet)
- *Varianten*:
  - Kaufabsichtserklärung (bei früher Phase)
  - Zuschlagsbeschluss (bei Zwangsversteigerung)
  - Schenkungsvertrag (bei Schenkung statt Kauf)

#### Grundbuch & Kataster (Pflicht)
- **Grundbuchauszug** (Abteilungen I-III, nicht älter als 3-6 Monate)
- **Flurkarte/Katasterkarte** (nicht älter als 6 Monate)
- *Hintergrund*: Beschreibt Grundstück, Lage, Größe und Lasten

#### Energieeffizienz (Pflicht ab 2025/2026)
- **Energieausweis** (erforderlich für alle Finanzierungen)
- *Varianten*:
  - Bedarfsausweis (Neubau/Modernisierung)
  - Verbrauchsausweis (Bestandsimmobilien)
  - Gültig für 10 Jahre
- *Hintergrund*: Direkter Einfluss auf Konditionen und ESG-Bewertung der Bank

#### Gebäudepläne & Flächen (Pflicht)
- **Grundrisse (bemaßt)** - alle Ebenen
- **Wohnflächenberechnung** (DIN 277 oder nach WoFlV)
- **Deckenplän** (optional, bei mehreren Ebenen)
- *Hintergrund*: Bank prüft Belehnungswert, Grundfläche, Nutzbarkeit

#### Fotos des Objekts (Pflicht)
- **Außenfotos** (Ansichten von mindestens 2 Seiten)
  - Gesamtansicht
  - Eingang/Fassade
  - Zustand des Gebäudes
- **Innenfotos** (von Haupträumen)
  - Wohnzimmer
  - Küche
  - Schlafzimmer
  - Bad
  - Sonstige wichtige Räume
- *Hintergrund*: Bewertung des Objektzustands und Schadensfreiheit

#### Versicherung (Pflicht)
- **Gebäudeversicherungsnachweis** (aktuell)
- *Alternative*: Versicherungsbestätigung des Maklers

#### Vermietungsinformationen (wenn zutreffend - Pflicht)
- **Mieterliste** (aktuelle Mieter, wenn vermietetes Objekt)
- **Mietverträge** (aktuelle Mietverträge)
- **Betriebskostenabrechnung** (letztes Abrechnungsjahr)
- **Bewirtschaftungskostenaufstellung**
- *Varianten*: Leerstandsanteil, Nebenkosten

#### Renovierung/Modernisierung (wenn zutreffend - Optional)
- **Handwerkerrechnungen** (wenn geplante Renovierung)
- **Kostenvoranschläge** (für geplante Arbeiten)
- **Bauzustand und Renovierungsplan**

---

## 3. Upload-Struktur & Ordnerorganisation

### 3.1 Logischer Aufbau (Frontend-Sicht)

```
📁 Finanzierungsantrag [Name des Kunden / ID]
│
├─ 📁 KUNDENUNTERLAGEN
│  ├─ 📁 Identifizierung (Erforderlich)
│  │  ├─ □ Personalausweis - Vorderseite
│  │  └─ □ Personalausweis - Rückseite
│  │
│  ├─ 📁 Einkommensnachweise (Erforderlich)
│  │  ├─ □ Lohnabrechnung - Letzter Monat
│  │  ├─ □ Lohnabrechnung - Vorletzter Monat
│  │  ├─ □ Lohnabrechnung - Vor 3 Monaten
│  │  └─ □ Lohnabrechnung - Dezember des Vorjahres
│  │
│  ├─ 📁 Rentner/Pensionär (Bedingt erforderlich)
│  │  ├─ □ Rentenbescheid (falls Rentner)
│  │  └─ □ Kontoauszug mit Renteneintrag (falls Rentner)
│  │
│  └─ 📁 Optionale Unterlagen
│     ├─ □ Schufa-Auskunft
│     ├─ □ Kontoauszüge (3 Monate)
│     ├─ □ Steuererklärung
│     └─ □ Arbeitsvertrag
│
├─ 📁 OBJEKTUNTERLAGEN
│  ├─ 📁 Kaufvertrag & Registrierung (Erforderlich)
│  │  ├─ □ Kaufvertrag-Entwurf / Unterzeichnet
│  │  └─ □ Grundbuchauszug (nicht älter als 3-6 Monate)
│  │
│  ├─ 📁 Gebäude & Fläche (Erforderlich)
│  │  ├─ □ Flurkarte/Katasterkarte (nicht älter als 6 Monate)
│  │  ├─ □ Energieausweis
│  │  ├─ □ Grundrisse (bemaßt, alle Ebenen)
│  │  └─ □ Wohnflächenberechnung
│  │
│  ├─ 📁 Fotos (Erforderlich)
│  │  ├─ □ Außenfotos (Gesamtansicht, Eingang, 2+ Seiten)
│  │  ├─ □ Innenfotos (Wohnzimmer, Küche, Schlafzimmer, Bad)
│  │  └─ □ Sonstige relevante Räume
│  │
│  ├─ 📁 Versicherung (Erforderlich)
│  │  └─ □ Gebäudeversicherungsnachweis
│  │
│  ├─ 📁 Vermietung (Bedingt erforderlich - nur bei Mietimmobilien)
│  │  ├─ □ Mieterliste
│  │  ├─ □ Mietverträge
│  │  └─ □ Betriebskostenabrechnung
│  │
│  └─ 📁 Renovierung/Modernisierung (Optional)
│     ├─ □ Handwerkerrechnungen
│     ├─ □ Kostenvoranschläge
│     └─ □ Renovierungsplan
│
└─ 📁 ZUSÄTZLICHE UNTERLAGEN (Admin-gesteuert)
   └─ □ [Vom Admin manuell hinzugefügt, z.B. spezielle Bankanforderungen]
```

---

## 4. Datenschema & Metadaten

### 4.1 Upload-Dokumenttyp (JSON-Struktur)

```json
{
  "id": "doc_12345",
  "uploadRequestId": "req_67890",
  "documentType": "salary_slip_current_month",
  "category": "kundenunterlagen",
  "subcategory": "einkommensnachweise",
  "label": "Lohnabrechnung - Letzter Monat",
  "description": "Lohnabrechnung oder Gehaltsabrechnung des letzten Monats",
  "isRequired": true,
  "isConditional": false,
  "condition": null,
  "status": "uploaded", // "pending", "uploaded", "expired", "missing"
  "uploadedFile": {
    "filename": "lohnabrechnung_maerz_2026.pdf",
    "size": 245000,
    "uploadedAt": "2026-04-10T14:23:00Z",
    "uploadedBy": "customer_123",
    "fileHash": "sha256_abc123..."
  },
  "expiryDate": null, // null wenn unbegrenzt
  "acceptedFormats": ["pdf", "jpg", "png"],
  "maxFileSizeMB": 10,
  "bankVariants": [
    {
      "bankName": "Deutsche Bank",
      "required": true,
      "notes": "Letzte 3 Monate erforderlich"
    },
    {
      "bankName": "Commerzbank",
      "required": true,
      "notes": "Letzte 3 Monate + Dezember Vorjahr"
    }
  ],
  "adminNotes": null,
  "customerMessage": null
}
```

### 4.2 Upload-Anfrage (JSON-Struktur)

```json
{
  "id": "req_67890",
  "customerId": "customer_123",
  "propertyId": "prop_456",
  "status": "in_progress", // "pending", "in_progress", "submitted", "complete"
  "createdAt": "2026-04-01T10:00:00Z",
  "lastUpdatedAt": "2026-04-13T14:23:00Z",
  "deadline": "2026-04-30T23:59:59Z",
  "documents": ["doc_12345", "doc_12346", ...],
  "completionPercentage": 65,
  "requiredMissing": ["doc_salary_prev_month", "doc_property_photos"],
  "optionalMissing": ["doc_schufa"],
  "automatedEmailSent": false,
  "adminApprovalForEmail": null,
  "notes": {
    "customer": "Alle Unterlagen verständlich",
    "admin": "Warte auf Energieausweis, sonst OK"
  }
}
```

---

## 5. Benutzerrollen & Workflows

### 5.1 Kundensicht (Customer Portal)

**Funktionalitäten:**
1. Upload-Bereich mit klaren Kategorien
2. Checkliste: Was muss hochgeladen werden?
3. Live-Status: Was ist noch offen?
4. Drag-and-Drop Upload
5. Datei-Vorschau
6. Download von bereits hochgeladenen Dokumenten
7. Nachricht vom Admin (z.B. "Bitte Energieausweis hochladen")
8. Fortschrittsbalken (z.B. "65% vollständig")

### 5.2 Admin-Sicht (Admin Dashboard)

**Funktionalitäten:**
1. Übersicht aller Kunden & deren Upload-Status
2. Filterung: Vollständig, In Bearbeitung, Überfällig
3. Detail-Ansicht: Welche Unterlagen fehlen?
4. Dokument-Vorschau (PDF, Bilder)
5. Anforderung zusätzlicher Unterlagen möglich
6. **Wichtig: Genehmigung vor automatischer E-Mail**
   - Admin wählt: "Kunde sollte benachrichtigt werden"
   - Admin kann Nachricht anpassen
   - E-Mail wird dann automatisch gesendet
7. Notizen zu einzelnen Dokumenten
8. Automatisierte Berichte: Z.B. "Überfällige Uploads"

### 5.3 Finanzierungskunden-Sicht (Bank/Vermittler)

**Funktionalitäten:**
1. Lesezugriff auf alle hochgeladenen Unterlagen
2. Filterung nach Kategorie
3. Download-Paket (alle Unterlagen als ZIP)
4. Status: "Bereit zur Einreichung" oder "Unvollständig"
5. Notizen vom Admin sehen
6. Keine Uploadrechte (nur Lesezugriff)

---

## 6. Automatisierungsmöglichkeiten & Features

### 6.1 Automatisierte E-Mail-Benachrichtigungen

**Szenario 1: Fehlende erforderliche Unterlagen**
- Bedingung: Admin genehmigt Benachrichtigung
- Trigger: Automatisch prüfen am Ende des Tages
- Nachricht: "Folgende Unterlagen fehlen noch: [Liste]"
- Attachment: Optional - Checkliste mit noch zu ladenden Dokumenten

**Szenario 2: Upload-Deadline überschritten**
- Bedingung: Deadline in config, Admin-Genehmigung erforderlich
- Trigger: Täglich prüfen, 1x pro Woche E-Mail
- Nachricht: "Ihre Finanzierungsunterlagen sind noch unvollständig"

**Szenario 3: Dokument erfolgreich hochgeladen**
- Bedingung: Bestätigung zum Kunden (optional, manuell)
- Trigger: Nach Upload
- Nachricht: "Danke! Ihr [Dokumenttype] wurde erhalten"

### 6.2 Admin-gesteuerte Anforderungen

**Feature: "Zusätzliche Unterlagen anfordern"**
- Admin kann weitere Dokumente definieren (nicht in Standard-Liste)
- Beispiele:
  - "Bitte Gesamtkostenaufstellung hochladen"
  - "Bitte Rentenbescheid hochladen (für Cosigner)"
  - "Bitte aktuelle Nebenkostenabrechnung"
- Diese werden in Dashboard des Kunden angezeigt
- E-Mail wird nur nach Admin-Freigabe gesendet

### 6.3 Intelligente Bedingte Anforderungen

**Automatische Logik:**
- Wenn `propertyType === "rental"` → Mieterliste erforderlich
- Wenn `customerStatus === "retiree"` → Rentenbescheid erforderlich
- Wenn `propertyAge > 15 years` → Energieausweis + Inspektionsbericht empfohlen
- Wenn `loanAmount > 500000` → Zusätzliche Bonitätsprüfung erforderlich

### 6.4 Dokumentenverfallswarnung

**Automatische Prüfung:**
- Personalausweis: Gültig für 10 Jahre
- Grundbuchauszug: Maximal 6 Monate alt
- Flurkarte: Maximal 6 Monate alt
- Energieausweis: 10 Jahre gültig
- Lohnabrechnung: Maximal 3 Monate alt
- System zeigt: "Dokument verfällt am [Datum]"

### 6.5 Audit Trail & Compliance

**Automatisches Logging:**
- Wer uploadete wann welches Dokument?
- Wann hat Admin welche Entscheidung getroffen?
- Wann wurde welche E-Mail gesendet?
- Änderungen durch Admin (z.B. Status-Änderung)
- Pflicht für Regulatorische Compliance (KYC/AML)

---

## 7. Bankanforderungs-Varianten

### 7.1 Verschiedene Bankprofile

```json
{
  "banks": [
    {
      "id": "bank_deutsche",
      "name": "Deutsche Bank",
      "requirements": {
        "identity": ["personalausweis_front", "personalausweis_back"],
        "income": ["salary_slip_current", "salary_slip_prev_month", "salary_slip_3months_ago", "salary_slip_december_prev_year"],
        "property": ["purchase_contract", "grundbuchauszug", "flurkarte", "energy_certificate", "floor_plans", "living_space_calc", "photos_exterior", "photos_interior", "building_insurance"],
        "additionalIfRental": ["tenant_list", "rent_contracts", "cost_breakdown"],
        "minSalaryDocuments": 3
      }
    },
    {
      "id": "bank_commerzbank",
      "name": "Commerzbank",
      "requirements": {
        "identity": ["personalausweis_front", "personalausweis_back"],
        "income": ["salary_slip_current", "salary_slip_prev_month", "salary_slip_december_prev_year"],
        "property": ["purchase_contract", "grundbuchauszug", "flurkarte", "energy_certificate", "floor_plans", "living_space_calc", "photos_exterior", "photos_interior", "building_insurance"],
        "minSalaryDocuments": 2,
        "notes": "Weniger streng bei Eigenkapital > 40%"
      }
    },
    {
      "id": "bank_baufi24",
      "name": "Baufi24 (Online-Kreditvermittler)",
      "requirements": {
        "identity": ["personalausweis_front", "personalausweis_back"],
        "income": ["salary_slip_current", "salary_slip_prev_month", "salary_slip_3months_ago"],
        "property": ["purchase_contract", "grundbuchauszug", "flurkarte", "energy_certificate", "floor_plans", "photos"],
        "flexibleDocumentation": true
      }
    }
  ]
}
```

### 7.2 Risikoadjustierte Anforderungen

**Abhängig von:**
- Belehnungsquote (LTV): Höher LTV = mehr Dokumente erforderlich
- Kundenscore/Bonität: Schlechter Score = umfassendere Prüfung
- Objekttyp: Wohnimmobilie vs. Gewerbeobjekt vs. Mietimmobilie
- Finanzierungstyp: Kauf vs. Umschuldung vs. Neubau
- Gesamtkreditsumme: > 500.000€ = Erhöhte Prüfung

---

## 8. Integration & Schnittstellen

### 8.1 Externe Systeme

- **Cloud Storage**: AWS S3 / Google Drive / Nextcloud (secure storage)
- **Email Service**: SendGrid / AWS SES (für automatische E-Mails)
- **Document Scanner**: OCR-Integration für automatische Text-Erkennung (optional)
- **CRM-System**: Integration mit bestehenden Kundendaten
- **Bank-APIs**: Nachrichtenformat für Bank-Übergabe (EDIFACT, xDot, PDF-Pakete)

### 8.2 Sicherheit & Datenschutz

- **Verschlüsselung**: AES-256 für Dateispeicher, TLS 1.3 für Transit
- **KYC/AML-Compliance**: Deutsche Bankenrichtlinien (BaFin)
- **DSGVO**: Datenschutzkonformität, Recht auf Löschung
- **Audit Trail**: Vollständiges Logging aller Aktivitäten
- **Zugriffskontrolle**: Rollenbasiert (Customer, Admin, Bank)
- **Virenscanning**: Automatisches Scanning hochgeladener Dateien

---

## 9. Zusätzliche Features & Varianten

### 9.1 Geplante Features (Phase 2)

1. **OCR & Automatische Validierung**
   - Automatische Extraktion von Daten aus Dokumenten
   - Prüfung auf Gültigkeit/Vollständigkeit
   - Beispiel: "Personalausweis gültig bis 2035? ✓"

2. **Mobile App**
   - Kamera-Upload für Fotos & Dokumente
   - Push-Benachrichtigungen
   - Offline-Speicherung

3. **E-Signature Integration**
   - Unterzeichnung direkt im Portal
   - Rechtliche Gültigkeit (eIDAS)

4. **Template-Management**
   - Admin kann custom Upload-Templates pro Bank erstellen
   - Reusable für mehrere Kunden

5. **Analytics & Reporting**
   - Durchschnittliche Upload-Zeit
   - Häufigste fehlende Dokumente
   - Compliance-Reports

6. **Integration mit Online-Banking**
   - Video-Identifikation (VideoIdent)
   - Automatischer KYC-Abschluss

7. **Künstliche Intelligenz**
   - Automatische Dokumentenklassifizierung
   - Anomalieerkennung (z.B. verdächtige Einträge)
   - Chatbot für häufige Fragen

### 9.2 Konfigurierbare Einstellungen

**Admin kann anpassen:**
- Deadline für Upload-Einreichung
- Benachrichtigungshäufigkeit
- Pflichtfelder pro Bank
- Custom-Nachrichtentexte
- Farbschema / Branding
- Automatische vs. manuelle Genehmigungen

---

## 10. Implementierungsempfehlungen

### 10.1 Tech-Stack (Beispiel)

- **Backend**: FastAPI (Python) oder Node.js/Express
- **Frontend**: React / Vue.js / Next.js
- **Datenbank**: PostgreSQL (Dokument-Metadaten), S3 (File-Storage)
- **Auth**: OAuth 2.0, JWT Tokens
- **Task Queue**: Celery / Bull (für automatisierte E-Mails)
- **Monitoring**: Sentry, LogRocket

### 10.2 Priorisierte Entwicklungsschritte

**Phase 1 (MVP):**
1. Basis-Upload-Struktur
2. Kundensicht mit Checkliste
3. Admin-Dashboard mit fehlenden Dokumenten
4. Manuelle E-Mail-Versendung (Admin klickt "Senden")

**Phase 2:**
1. Automatische E-Mail-Benachrichtigungen
2. Conditional Requirements (Logik basierend auf Objekttyp)
3. Dokumentenverfallsprüfung
4. Finanzierungskunden-Zugriff (Bank)

**Phase 3:**
1. OCR & Automatische Validierung
2. Mobile App
3. E-Signature Integration
4. Analytics & Reporting

---

## 11. Sicherheits-Checkliste

- [ ] Verschlüsselung aller Dateien (in Ruhe & Transit)
- [ ] Multi-Factor Authentication für Admin
- [ ] Datenschutz-Konformität (DSGVO, BaFin-Richtlinien)
- [ ] Malware-Scanning hochgeladener Dateien
- [ ] Rollenseparation (Customer ≠ Admin ≠ Bank)
- [ ] Audit Trail für alle Änderungen
- [ ] Sichere Löschmechanismen (nach Aufbewahrungszeit)
- [ ] Regelmäßige Sicherheitsaudits

---

## Quellen & Referenzen

1. [Deutsche Bank Checkliste Baufinanzierung](https://www.deutsche-bank.de/dam/deutschebank/de/shared/pdf/pb-baufikampagne-checkliste.pdf)
2. [FINMA Hypothekarfinanzierung Richtlinien](https://www.finma.ch/de/~/media/finma/dokumente/dokumentencenter/myfinma/4dokumentation/selbstregulierung/sbvg_rl_hypofinanzierungen_20231213.pdf?sc_lang=de)
3. [Baufi24 - Unterlagen Checkliste](https://www.baufi24.de/unterlagen-baufinanzierung/)
4. [Objektunterlagen Immobilienfinanzierung 2026](https://www.finesthub.de/blog/objektunterlagen-immobilienfinanzierung-checkliste)
5. [KYC/AML Anforderungen](https://www.iproov.com/de/blog/kyc-aml-importance-difference/)
6. [Dr. Klein - Unterlagen Baufinanzierung](https://www.drklein.de/unterlagen-baufinanzierung-faq.html)
7. [Best Practices Financial Services Document Management](https://www.egnyte.com/guides/financial-services/financial-services-document-management-best-practices)

---

## Kontakt & Feedback

Für Rückfragen zum Konzept oder Änderungswünsche: [Support-Kontakt]
