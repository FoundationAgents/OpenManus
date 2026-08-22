"""
Upload-Management-System für Immobilienfinanzierungen
FastAPI Backend für Dokument-Verwaltung
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
import json
from datetime import datetime
from typing import List, Optional
import shutil

from models import Base, UploadRequest, Document, Customer, AdminApproval
from schemas import (
    UploadRequestCreate, DocumentUploadResponse, UploadStatusResponse,
    AdminApprovalRequest, AutomatedEmailRequest
)
from services import (
    document_service, email_service, validation_service,
    admin_service, storage_service
)
from config import settings

# FastAPI App
app = FastAPI(
    title="Upload-Management System",
    description="Finanzierungs-Dokumenten Upload & Verwaltung",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """System-Status prüfen"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.get("/api/v1/upload-requests/{request_id}")
async def get_upload_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    """
    Upload-Anfrage mit Status und fehlenden Dokumenten abrufen
    """
    upload_request = db.query(UploadRequest).filter(
        UploadRequest.id == request_id
    ).first()

    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload-Anfrage nicht gefunden")

    return {
        "id": upload_request.id,
        "customerId": upload_request.customer_id,
        "status": upload_request.status,
        "completionPercentage": document_service.calculate_completion(
            upload_request, db
        ),
        "documents": [
            {
                "id": doc.id,
                "type": doc.document_type,
                "status": doc.status,
                "label": doc.label,
                "isRequired": doc.is_required,
                "uploadedAt": doc.uploaded_at,
                "expiryDate": doc.expiry_date
            }
            for doc in upload_request.documents
        ],
        "requiredMissing": document_service.get_missing_required(
            upload_request, db
        ),
        "optionalMissing": document_service.get_missing_optional(
            upload_request, db
        ),
        "deadline": upload_request.deadline
    }

@app.post("/api/v1/upload-requests/{request_id}/upload")
async def upload_document(
    request_id: str,
    file: UploadFile = File(...),
    document_type: str = None,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Dokument hochladen
    """
    upload_request = db.query(UploadRequest).filter(
        UploadRequest.id == request_id
    ).first()

    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload-Anfrage nicht gefunden")

    # Validierung
    validation_result = validation_service.validate_upload(
        file, document_type, upload_request
    )

    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["error"])

    # Datei speichern
    stored_file = await storage_service.store_file(
        file, request_id, document_type
    )

    # Dokument in DB erstellen
    document = Document(
        upload_request_id=request_id,
        document_type=document_type,
        filename=file.filename,
        file_path=stored_file["path"],
        file_hash=stored_file["hash"],
        size=stored_file["size"],
        status="uploaded",
        uploaded_at=datetime.utcnow()
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Audit Log
    if background_tasks:
        background_tasks.add_task(
            document_service.log_audit,
            request_id, "document_uploaded", file.filename
        )

    return DocumentUploadResponse(
        documentId=document.id,
        status="success",
        message="Dokument erfolgreich hochgeladen"
    )

@app.get("/api/v1/upload-requests/{request_id}/documents/{doc_id}/download")
async def download_document(
    request_id: str,
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    Hochgeladenes Dokument herunterladen
    """
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.upload_request_id == request_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    return storage_service.get_file_response(document.file_path)

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/api/v1/admin/upload-requests")
async def list_upload_requests(
    status: Optional[str] = None,
    sort_by: str = "createdAt",
    db: Session = Depends(get_db)
):
    """
    Alle Upload-Anfragen auflisten (Admin-View)
    """
    query = db.query(UploadRequest)

    if status:
        query = query.filter(UploadRequest.status == status)

    requests = query.order_by(UploadRequest.created_at.desc()).all()

    return [
        {
            "id": req.id,
            "customerId": req.customer_id,
            "status": req.status,
            "completionPercentage": document_service.calculate_completion(req, db),
            "requiredMissing": len(document_service.get_missing_required(req, db)),
            "createdAt": req.created_at,
            "lastUpdated": req.last_updated_at
        }
        for req in requests
    ]

@app.post("/api/v1/admin/approval/request-additional-documents")
async def request_additional_documents(
    request_id: str,
    approval: AdminApprovalRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Admin fordert zusätzliche Dokumente an
    (mit Genehmigung vor E-Mail-Versendung)
    """
    upload_request = db.query(UploadRequest).filter(
        UploadRequest.id == request_id
    ).first()

    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload-Anfrage nicht gefunden")

    # Admin-Genehmigung speichern
    admin_approval = AdminApproval(
        upload_request_id=request_id,
        approval_type="request_additional_documents",
        requested_documents=approval.documents,
        message=approval.message,
        approved_by=approval.admin_id,
        approved_at=datetime.utcnow()
    )

    db.add(admin_approval)
    db.commit()

    # E-Mail nur wenn genehmigt
    if approval.send_email_to_customer:
        if background_tasks:
            background_tasks.add_task(
                email_service.send_additional_document_request,
                upload_request.customer_id,
                approval.documents,
                approval.message
            )

    return {
        "status": "success",
        "message": "Anforderung erstellt",
        "emailSent": approval.send_email_to_customer
    }

@app.post("/api/v1/admin/approval/notify-missing-documents")
async def notify_missing_documents(
    request_id: str,
    approval: AdminApprovalRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Admin genehmigt Benachrichtigung über fehlende erforderliche Dokumente
    """
    upload_request = db.query(UploadRequest).filter(
        UploadRequest.id == request_id
    ).first()

    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload-Anfrage nicht gefunden")

    missing = document_service.get_missing_required(upload_request, db)

    # Admin-Genehmigung speichern
    admin_approval = AdminApproval(
        upload_request_id=request_id,
        approval_type="notify_missing_documents",
        requested_documents=[doc["id"] for doc in missing],
        message=approval.message,
        approved_by=approval.admin_id,
        approved_at=datetime.utcnow()
    )

    db.add(admin_approval)
    db.commit()

    # Benachrichtigung versenden
    if background_tasks:
        background_tasks.add_task(
            email_service.send_missing_documents_notification,
            upload_request.customer_id,
            missing,
            approval.message
        )

    return {
        "status": "success",
        "message": "Benachrichtigung gesendet",
        "missingDocumentsCount": len(missing)
    }

@app.get("/api/v1/admin/upload-requests/{request_id}/audit-log")
async def get_audit_log(
    request_id: str,
    db: Session = Depends(get_db)
):
    """
    Audit Trail für eine Upload-Anfrage
    """
    audit_logs = db.query(AuditLog).filter(
        AuditLog.upload_request_id == request_id
    ).order_by(AuditLog.created_at.desc()).all()

    return [
        {
            "id": log.id,
            "action": log.action,
            "actor": log.actor,
            "details": log.details,
            "createdAt": log.created_at
        }
        for log in audit_logs
    ]

# ============================================================================
# BANK ENDPOINTS
# ============================================================================

@app.get("/api/v1/bank/upload-requests/{request_id}")
async def get_upload_request_for_bank(
    request_id: str,
    bank_api_key: str,
    db: Session = Depends(get_db)
):
    """
    Bank/Finanzierungskunde kann Status einsehen (Lesezugriff nur)
    """
    # Validiere Bank API Key
    if not admin_service.validate_bank_api_key(bank_api_key):
        raise HTTPException(status_code=401, detail="Ungültiger API Key")

    upload_request = db.query(UploadRequest).filter(
        UploadRequest.id == request_id
    ).first()

    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload-Anfrage nicht gefunden")

    return {
        "id": upload_request.id,
        "status": upload_request.status,
        "completionPercentage": document_service.calculate_completion(
            upload_request, db
        ),
        "documents": [
            {
                "id": doc.id,
                "type": doc.document_type,
                "label": doc.label,
                "status": doc.status,
                "uploadedAt": doc.uploaded_at
            }
            for doc in upload_request.documents if doc.status == "uploaded"
        ],
        "readyForSubmission": document_service.is_complete(upload_request, db)
    }

@app.post("/api/v1/bank/export-documents/{request_id}")
async def export_documents_for_bank(
    request_id: str,
    bank_api_key: str,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Alle Unterlagen als ZIP exportieren für Bank
    """
    if not admin_service.validate_bank_api_key(bank_api_key):
        raise HTTPException(status_code=401, detail="Ungültiger API Key")

    upload_request = db.query(UploadRequest).filter(
        UploadRequest.id == request_id
    ).first()

    if not upload_request:
        raise HTTPException(status_code=404, detail="Upload-Anfrage nicht gefunden")

    zip_file = storage_service.create_export_zip(upload_request, db)

    return storage_service.get_file_response(zip_file)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
