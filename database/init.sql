-- ============================================================================
-- Upload-Management System - Database Initialization
-- PostgreSQL 15+
-- ============================================================================

-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE document_status AS ENUM (
    'pending',
    'uploaded',
    'expired',
    'missing',
    'verified'
);

CREATE TYPE upload_request_status AS ENUM (
    'pending',
    'in_progress',
    'submitted',
    'complete',
    'overdue'
);

CREATE TYPE approval_type AS ENUM (
    'request_additional_documents',
    'notify_missing_documents',
    'approve_submission'
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- Customers
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    company VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_created_at ON customers(created_at);

-- Upload Requests
CREATE TABLE upload_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    property_id UUID,
    bank_profile VARCHAR(50) DEFAULT 'standard',
    property_type VARCHAR(50),
    loan_amount NUMERIC(15, 2),
    ltv_ratio NUMERIC(5, 2),

    status upload_request_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP,

    customer_notes TEXT,
    admin_notes TEXT,

    CHECK (loan_amount >= 0),
    CHECK (ltv_ratio >= 0 AND ltv_ratio <= 1)
);

CREATE INDEX idx_upload_requests_customer_id ON upload_requests(customer_id);
CREATE INDEX idx_upload_requests_status ON upload_requests(status);
CREATE INDEX idx_upload_requests_created_at ON upload_requests(created_at);
CREATE INDEX idx_upload_requests_deadline ON upload_requests(deadline);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_request_id UUID NOT NULL REFERENCES upload_requests(id) ON DELETE CASCADE,

    document_type VARCHAR(100) NOT NULL,
    label VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    subcategory VARCHAR(100),

    status document_status NOT NULL DEFAULT 'missing',
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    is_conditional BOOLEAN NOT NULL DEFAULT FALSE,
    condition VARCHAR(255),

    filename VARCHAR(255),
    file_path VARCHAR(512),
    file_hash VARCHAR(256),
    size INTEGER,
    mime_type VARCHAR(50),

    uploaded_at TIMESTAMP,
    uploaded_by UUID,

    expiry_date TIMESTAMP,

    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_notes TEXT,

    bank_variants JSONB,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_upload_request_id ON documents(upload_request_id);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_expiry_date ON documents(expiry_date);

-- Admin Approvals
CREATE TABLE admin_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_request_id UUID NOT NULL REFERENCES upload_requests(id) ON DELETE CASCADE,

    approval_type approval_type NOT NULL,
    requested_documents JSONB,
    message TEXT,

    email_sent BOOLEAN NOT NULL DEFAULT FALSE,
    email_sent_at TIMESTAMP,

    approved_by UUID NOT NULL,
    approved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rejection_reason TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_approvals_upload_request_id ON admin_approvals(upload_request_id);
CREATE INDEX idx_admin_approvals_approval_type ON admin_approvals(approval_type);
CREATE INDEX idx_admin_approvals_created_at ON admin_approvals(created_at);

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_request_id UUID NOT NULL REFERENCES upload_requests(id) ON DELETE CASCADE,

    action VARCHAR(100) NOT NULL,
    actor UUID NOT NULL,
    actor_type VARCHAR(20),

    details JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_upload_request_id ON audit_logs(upload_request_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Bank Profiles
CREATE TABLE bank_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,

    required_documents JSONB,
    required_salary_months INTEGER DEFAULT 3,
    min_eigenkapital_percent INTEGER DEFAULT 10,

    flexible_documentation BOOLEAN NOT NULL DEFAULT FALSE,
    additional_requirements JSONB,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bank_profiles_code ON bank_profiles(code);
CREATE INDEX idx_bank_profiles_is_active ON bank_profiles(is_active);

-- Email Queue
CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    html_body TEXT,

    email_type VARCHAR(50),
    upload_request_id UUID REFERENCES upload_requests(id) ON DELETE SET NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMP,
    failed_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_email_queue_recipient_email ON email_queue(recipient_email);
CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_email_type ON email_queue(email_type);
CREATE INDEX idx_email_queue_created_at ON email_queue(created_at);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamps automatically
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER customers_update_timestamp
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER upload_requests_update_timestamp
BEFORE UPDATE ON upload_requests
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER documents_update_timestamp
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER bank_profiles_update_timestamp
BEFORE UPDATE ON bank_profiles
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER email_queue_update_timestamp
BEFORE UPDATE ON email_queue
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Upload Request Statistics
CREATE VIEW v_upload_request_stats AS
SELECT
    ur.id,
    ur.customer_id,
    ur.status,
    COUNT(d.id) as total_documents,
    SUM(CASE WHEN d.status = 'uploaded' THEN 1 ELSE 0 END) as uploaded_count,
    SUM(CASE WHEN d.is_required = TRUE AND d.status != 'uploaded' THEN 1 ELSE 0 END) as missing_required,
    SUM(CASE WHEN d.is_required = FALSE AND d.status != 'uploaded' THEN 1 ELSE 0 END) as missing_optional,
    ROUND((SUM(CASE WHEN d.status = 'uploaded' THEN 1 ELSE 0 END)::NUMERIC /
           NULLIF(COUNT(d.id), 0) * 100)::NUMERIC, 0) as completion_percentage
FROM upload_requests ur
LEFT JOIN documents d ON ur.id = d.upload_request_id
GROUP BY ur.id, ur.customer_id, ur.status;

-- Overdue Requests
CREATE VIEW v_overdue_requests AS
SELECT
    ur.id,
    ur.customer_id,
    c.email,
    ur.deadline,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - ur.deadline) as days_overdue,
    stats.missing_required
FROM upload_requests ur
JOIN customers c ON ur.customer_id = c.id
LEFT JOIN v_upload_request_stats stats ON ur.id = stats.id
WHERE ur.status = 'in_progress'
  AND ur.deadline < CURRENT_TIMESTAMP;

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert Bank Profiles
INSERT INTO bank_profiles (name, code, required_salary_months, min_eigenkapital_percent, is_active)
VALUES
    ('Deutsche Bank', 'deutsche_bank', 3, 10, TRUE),
    ('Commerzbank', 'commerzbank', 2, 10, TRUE),
    ('Baufi24', 'baufi24', 2, 10, TRUE),
    ('Dr. Klein', 'dr_klein', 2, 15, TRUE)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE customers IS 'Kunden/Antragsteller der Finanzierungen';
COMMENT ON TABLE upload_requests IS 'Finanzierungs-Upload-Anfragen mit Status-Tracking';
COMMENT ON TABLE documents IS 'Hochgeladene Dokumente mit Status und Verfallsdaten';
COMMENT ON TABLE admin_approvals IS 'Admin-Genehmigungen für Benachrichtigungen';
COMMENT ON TABLE audit_logs IS 'Compliance-Audit-Trail für alle Aktivitäten';
COMMENT ON TABLE bank_profiles IS 'Bank-spezifische Anforderungen und Profile';
COMMENT ON TABLE email_queue IS 'Queue für E-Mail-Versand (async via Celery)';

COMMENT ON VIEW v_upload_request_stats IS 'Statistik-View für Upload-Anfragen (Completion %, Fehlende Docs)';
COMMENT ON VIEW v_overdue_requests IS 'Überfällige Upload-Anfragen mit Tagen Überziehung';
