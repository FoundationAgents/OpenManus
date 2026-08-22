"""
Admin Service für Admin-spezifische Funktionen
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import logging

from models import UploadRequest, AdminApproval, AuditLog

logger = logging.getLogger(__name__)


class AdminService:
    """Service für Admin-Funktionen"""

    def validate_bank_api_key(self, api_key: str) -> bool:
        """
        Validiert Bank API Key

        Args:
            api_key: API Key zum Validieren

        Returns:
            True wenn gültig
        """
        # In Production: Prüfung gegen gespeicherte Keys
        # Für Demo: einfache Validierung
        return len(api_key) >= 20 and api_key.startswith("bank_")

    def get_upload_request_statistics(
        self,
        db: Session,
    ) -> Dict:
        """
        Gibt Statistiken über alle Upload-Anfragen

        Args:
            db: Database Session

        Returns:
            Statistiken Dict
        """
        from models import UploadRequestStatus

        requests = db.query(UploadRequest).all()

        statuses = {}
        for req in requests:
            status = req.status
            statuses[status] = statuses.get(status, 0) + 1

        return {
            "total_requests": len(requests),
            "by_status": statuses,
            "pending": statuses.get(UploadRequestStatus.pending, 0),
            "in_progress": statuses.get(UploadRequestStatus.in_progress, 0),
            "submitted": statuses.get(UploadRequestStatus.submitted, 0),
            "complete": statuses.get(UploadRequestStatus.complete, 0),
        }

    def get_overdue_requests(
        self,
        db: Session,
    ) -> List[Dict]:
        """
        Gibt alle überfälligen Upload-Anfragen zurück

        Args:
            db: Database Session

        Returns:
            Liste überfälliger Anfragen
        """
        from models import UploadRequestStatus

        overdue_requests = db.query(UploadRequest).filter(
            UploadRequest.status == UploadRequestStatus.in_progress,
            UploadRequest.deadline.isnot(None),
            UploadRequest.deadline < datetime.utcnow(),
        ).all()

        return [
            {
                "id": req.id,
                "customer_id": req.customer_id,
                "customer_email": req.customer.email,
                "deadline": req.deadline,
                "days_overdue": (datetime.utcnow() - req.deadline).days,
                "missing_docs_count": sum(
                    1
                    for doc in req.documents
                    if doc.status != "uploaded"
                ),
            }
            for req in overdue_requests
        ]

    def get_customer_summary(
        self,
        db: Session,
        customer_id: str,
    ) -> Optional[Dict]:
        """
        Gibt Zusammenfassung eines Kunden

        Args:
            db: Database Session
            customer_id: ID des Kunden

        Returns:
            Kunden-Zusammenfassung
        """
        request = db.query(UploadRequest).filter(
            UploadRequest.customer_id == customer_id
        ).first()

        if not request:
            return None

        from services.document_service import document_service

        return {
            "customer_id": customer_id,
            "customer_email": request.customer.email if request.customer else None,
            "latest_request_id": request.id,
            "status": request.status,
            "completion_percentage": document_service.calculate_completion(
                request, db
            ),
            "missing_required": len(
                document_service.get_missing_required(request, db)
            ),
            "missing_optional": len(
                document_service.get_missing_optional(request, db)
            ),
            "created_at": request.created_at,
            "last_updated": request.last_updated_at,
            "deadline": request.deadline,
        }

    def approve_customer_submission(
        self,
        upload_request_id: str,
        admin_id: str,
        notes: Optional[str],
        db: Session,
    ) -> bool:
        """
        Admin genehmigt Customer-Einreichung

        Args:
            upload_request_id: ID der Upload-Anfrage
            admin_id: Admin User ID
            notes: Admin-Notizen
            db: Database Session

        Returns:
            True wenn erfolgreich
        """
        try:
            from models import UploadRequestStatus

            request = db.query(UploadRequest).filter(
                UploadRequest.id == upload_request_id
            ).first()

            if not request:
                return False

            # Prüfe ob vollständig
            from services.document_service import document_service

            if not document_service.is_complete(request, db):
                logger.warning(
                    f"Cannot approve incomplete request: {upload_request_id}"
                )
                return False

            # Aktualisiere Status
            request.status = UploadRequestStatus.submitted
            request.admin_notes = notes

            # Log Aktion
            audit_log = AuditLog(
                upload_request_id=upload_request_id,
                action="submission_approved",
                actor=admin_id,
                actor_type="admin",
                details={"notes": notes},
            )

            db.add(audit_log)
            db.commit()

            logger.info(f"Submission approved: {upload_request_id}")
            return True

        except Exception as e:
            logger.error(f"Error approving submission: {str(e)}")
            return False

    def reject_submission(
        self,
        upload_request_id: str,
        admin_id: str,
        reason: str,
        db: Session,
    ) -> bool:
        """
        Admin lehnt Einreichung ab

        Args:
            upload_request_id: ID der Upload-Anfrage
            admin_id: Admin User ID
            reason: Grund der Ablehnung
            db: Database Session

        Returns:
            True wenn erfolgreich
        """
        try:
            from models import UploadRequestStatus

            request = db.query(UploadRequest).filter(
                UploadRequest.id == upload_request_id
            ).first()

            if not request:
                return False

            # Aktualisiere Status
            request.status = UploadRequestStatus.in_progress
            request.admin_notes = f"REJECTED: {reason}"

            # Log Aktion
            audit_log = AuditLog(
                upload_request_id=upload_request_id,
                action="submission_rejected",
                actor=admin_id,
                actor_type="admin",
                details={"reason": reason},
            )

            db.add(audit_log)
            db.commit()

            logger.info(f"Submission rejected: {upload_request_id}")
            return True

        except Exception as e:
            logger.error(f"Error rejecting submission: {str(e)}")
            return False

    def add_admin_note(
        self,
        upload_request_id: str,
        admin_id: str,
        note: str,
        db: Session,
    ) -> bool:
        """
        Fügt Admin-Notiz zu Upload-Anfrage hinzu

        Args:
            upload_request_id: ID der Upload-Anfrage
            admin_id: Admin User ID
            note: Notiz-Text
            db: Database Session

        Returns:
            True wenn erfolgreich
        """
        try:
            request = db.query(UploadRequest).filter(
                UploadRequest.id == upload_request_id
            ).first()

            if not request:
                return False

            # Füge zu existierender Note hinzu
            if request.admin_notes:
                request.admin_notes += f"\n\n[{datetime.utcnow().isoformat()}] {note}"
            else:
                request.admin_notes = note

            # Log
            audit_log = AuditLog(
                upload_request_id=upload_request_id,
                action="admin_note_added",
                actor=admin_id,
                actor_type="admin",
                details={"note": note},
            )

            db.add(audit_log)
            db.commit()

            logger.info(f"Admin note added: {upload_request_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding admin note: {str(e)}")
            return False

    def get_pending_approvals(
        self,
        db: Session,
    ) -> List[Dict]:
        """
        Gibt alle ausstehenden Genehmigungen

        Args:
            db: Database Session

        Returns:
            Liste ausstehender Genehmigungen
        """
        pending = db.query(AdminApproval).filter(
            AdminApproval.email_sent == False,
        ).all()

        return [
            {
                "id": approval.id,
                "request_id": approval.upload_request_id,
                "approval_type": approval.approval_type,
                "message": approval.message,
                "created_at": approval.created_at,
            }
            for approval in pending
        ]


# Singleton Instance
admin_service = AdminService()
