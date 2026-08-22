"""
SQLAlchemy ORM Modelle für Upload-Management-System
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, ForeignKey,
    Text, DECIMAL, Enum as SQLEnum, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class DocumentStatus(str, enum.Enum):
    pending = "pending"
    uploaded = "uploaded"
    expired = "expired"
    missing = "missing"
    verified = "verified"

class UploadRequestStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    submitted = "submitted"
    complete = "complete"
    overdue = "overdue"

class ApprovalType(str, enum.Enum):
    request_additional_documents = "request_additional_documents"
    notify_missing_documents = "notify_missing_documents"
    approve_submission = "approve_submission"

# ============================================================================
# CUSTOMERS
# ============================================================================

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    company = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    upload_requests = relationship("UploadRequest", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.email}>"

# ============================================================================
# UPLOAD REQUESTS
# ============================================================================

class UploadRequest(Base):
    __tablename__ = "upload_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    property_id = Column(String(36), nullable=True)  # Immobilien-ID
    bank_profile = Column(String(50), default="standard")  # Bank-Profil (Deutsche Bank, etc.)
    property_type = Column(String(50))  # "residential", "commercial", "rental"
    loan_amount = Column(DECIMAL(15, 2))
    ltv_ratio = Column(DECIMAL(5, 2))  # Loan-to-Value Ratio

    status = Column(
        SQLEnum(UploadRequestStatus),
        default=UploadRequestStatus.pending,
        index=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)

    # Notes
    customer_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="upload_requests")
    documents = relationship("Document", back_populates="upload_request", cascade="all, delete-orphan")
    admin_approvals = relationship("AdminApproval", back_populates="upload_request", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="upload_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UploadRequest {self.id} - {self.status}>"

# ============================================================================
# DOCUMENTS
# ============================================================================

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_request_id = Column(String(36), ForeignKey("upload_requests.id"), nullable=False, index=True)

    # Document Metadata
    document_type = Column(String(100), nullable=False, index=True)  # e.g., "salary_slip_current_month"
    label = Column(String(255), nullable=False)  # e.g., "Lohnabrechnung - Letzter Monat"
    category = Column(String(50))  # "kundenunterlagen", "objektunterlagen"
    subcategory = Column(String(100))  # "einkommensnachweise", "gebaeude"

    # Status
    status = Column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.missing,
        index=True
    )
    is_required = Column(Boolean, default=True)
    is_conditional = Column(Boolean, default=False)
    condition = Column(String(255), nullable=True)  # z.B. "property_type == 'rental'"

    # File Info
    filename = Column(String(255))
    file_path = Column(String(512))  # Pfad im Storage
    file_hash = Column(String(256))  # SHA256 Hash
    size = Column(Integer)  # Bytes
    mime_type = Column(String(50))

    # Upload Info
    uploaded_at = Column(DateTime, nullable=True)
    uploaded_by = Column(String(36), nullable=True)  # Customer ID

    # Expiry
    expiry_date = Column(DateTime, nullable=True)  # Wann läuft das Dokument ab?

    # Validation
    is_verified = Column(Boolean, default=False)
    verification_notes = Column(Text, nullable=True)

    # Bank Variants
    bank_variants = Column(JSON, nullable=True)  # Liste der Banks, die das Dokument brauchen

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    upload_request = relationship("UploadRequest", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.document_type} - {self.status}>"

# ============================================================================
# ADMIN APPROVALS
# ============================================================================

class AdminApproval(Base):
    __tablename__ = "admin_approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_request_id = Column(String(36), ForeignKey("upload_requests.id"), nullable=False, index=True)

    # Approval Type
    approval_type = Column(
        SQLEnum(ApprovalType),
        nullable=False,
        index=True
    )

    # What was requested/approved
    requested_documents = Column(JSON)  # Liste der angeforderten Dokument-IDs
    message = Column(Text)  # Nachricht an Kunden

    # Email Status
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)

    # Approval Info
    approved_by = Column(String(36), nullable=False)  # Admin User ID
    approved_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    upload_request = relationship("UploadRequest", back_populates="admin_approvals")

    def __repr__(self):
        return f"<AdminApproval {self.approval_type}>"

# ============================================================================
# AUDIT LOGS
# ============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_request_id = Column(String(36), ForeignKey("upload_requests.id"), nullable=False, index=True)

    action = Column(String(100), nullable=False)  # "document_uploaded", "email_sent", "status_changed"
    actor = Column(String(36), nullable=False)  # Customer ID, Admin ID, System
    actor_type = Column(String(20))  # "customer", "admin", "system"

    # Details
    details = Column(JSON)  # Freie Daten pro Action
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    upload_request = relationship("UploadRequest", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} - {self.created_at}>"

# ============================================================================
# CONFIGURATION / TEMPLATES
# ============================================================================

class BankProfile(Base):
    __tablename__ = "bank_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)  # "Deutsche Bank", "Commerzbank"
    code = Column(String(50), unique=True)  # "deutsche_bank"

    # Requirements
    required_documents = Column(JSON)  # Liste der erforderlichen Dokumenttypen
    required_salary_months = Column(Integer, default=3)
    min_eigenkapital_percent = Column(Integer, default=10)

    # Flexible Anforderungen
    flexible_documentation = Column(Boolean, default=False)
    additional_requirements = Column(JSON, nullable=True)

    # Settings
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BankProfile {self.name}>"

# ============================================================================
# EMAIL QUEUE
# ============================================================================

class EmailQueue(Base):
    __tablename__ = "email_queue"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    html_body = Column(Text, nullable=True)

    email_type = Column(String(50))  # "missing_documents", "additional_request", etc.
    upload_request_id = Column(String(36), ForeignKey("upload_requests.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    failed_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailQueue {self.email_type} - {self.status}>"
