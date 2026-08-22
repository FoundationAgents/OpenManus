"""
Document Service für Dokumentenverwaltung und Status-Tracking
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging

from models import Document, UploadRequest, DocumentStatus, AuditLog

logger = logging.getLogger(__name__)


class DocumentService:
    """Service für Dokumentenverwaltung"""

    def calculate_completion(
        self,
        upload_request: UploadRequest,
        db: Session,
    ) -> int:
        """
        Berechnet Completeness-Prozentsatz einer Upload-Anfrage

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            Prozentsatz (0-100)
        """
        if not upload_request.documents:
            return 0

        uploaded_count = sum(
            1
            for doc in upload_request.documents
            if doc.status == DocumentStatus.uploaded
        )
        total_required = sum(
            1 for doc in upload_request.documents if doc.is_required
        )

        if total_required == 0:
            return 0

        return int((uploaded_count / total_required) * 100)

    def get_missing_required(
        self,
        upload_request: UploadRequest,
        db: Session,
    ) -> List[Dict]:
        """
        Gibt Liste aller fehlenden erforderlichen Dokumente zurück

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            Liste von Dokumenten mit Status != uploaded
        """
        missing = [
            {
                "id": doc.id,
                "type": doc.document_type,
                "label": doc.label,
                "category": doc.category,
                "status": doc.status,
            }
            for doc in upload_request.documents
            if doc.is_required and doc.status != DocumentStatus.uploaded
        ]
        return missing

    def get_missing_optional(
        self,
        upload_request: UploadRequest,
        db: Session,
    ) -> List[Dict]:
        """
        Gibt Liste aller fehlenden optionalen Dokumente zurück

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            Liste optionaler, nicht hochgeladener Dokumente
        """
        missing = [
            {
                "id": doc.id,
                "type": doc.document_type,
                "label": doc.label,
                "category": doc.category,
            }
            for doc in upload_request.documents
            if not doc.is_required and doc.status != DocumentStatus.uploaded
        ]
        return missing

    def is_complete(
        self,
        upload_request: UploadRequest,
        db: Session,
    ) -> bool:
        """
        Prüft ob alle erforderlichen Dokumente hochgeladen wurden

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            True wenn alle erforderlich sind hochgeladen
        """
        missing = self.get_missing_required(upload_request, db)
        return len(missing) == 0

    def check_document_expiry(
        self,
        document: Document,
    ) -> bool:
        """
        Prüft ob Dokument abgelaufen ist

        Args:
            document: Document Objekt

        Returns:
            True wenn noch gültig, False wenn abgelaufen
        """
        if document.expiry_date is None:
            return True  # Unbegrenzt gültig

        return datetime.utcnow() < document.expiry_date

    def mark_expired_documents(
        self,
        upload_request: UploadRequest,
        db: Session,
    ) -> List[Document]:
        """
        Markiert abgelaufene Dokumente

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            Liste der markierten Dokumente
        """
        expired_docs = []

        for doc in upload_request.documents:
            if not self.check_document_expiry(doc):
                doc.status = DocumentStatus.expired
                expired_docs.append(doc)
                logger.warning(
                    f"Document marked as expired: {doc.id} "
                    f"({doc.document_type})"
                )

        if expired_docs:
            db.commit()

        return expired_docs

    def get_documents_by_category(
        self,
        upload_request: UploadRequest,
        category: str,
    ) -> List[Document]:
        """
        Gibt alle Dokumente einer Kategorie zurück

        Args:
            upload_request: UploadRequest Objekt
            category: Dokumentkategorie

        Returns:
            Liste der Dokumente
        """
        return [
            doc
            for doc in upload_request.documents
            if doc.category == category
        ]

    def get_document_status_summary(
        self,
        upload_request: UploadRequest,
    ) -> Dict:
        """
        Gibt Zusammenfassung des Dokumenten-Status

        Args:
            upload_request: UploadRequest Objekt

        Returns:
            Dict mit Status-Statistiken
        """
        statuses = {}
        for doc in upload_request.documents:
            status = doc.status
            statuses[status] = statuses.get(status, 0) + 1

        return {
            "total": len(upload_request.documents),
            "uploaded": statuses.get(DocumentStatus.uploaded, 0),
            "pending": statuses.get(DocumentStatus.pending, 0),
            "expired": statuses.get(DocumentStatus.expired, 0),
            "missing": statuses.get(DocumentStatus.missing, 0),
            "verified": statuses.get(DocumentStatus.verified, 0),
        }

    def log_audit(
        self,
        upload_request_id: str,
        action: str,
        details: Dict = None,
        actor_id: str = None,
        db: Session = None,
    ) -> bool:
        """
        Protokolliert Aktion im Audit Trail

        Args:
            upload_request_id: ID der Upload-Anfrage
            action: Art der Aktion
            details: Detaillierte Informationen
            actor_id: ID des Akteurs (User/Admin/System)
            db: Database Session

        Returns:
            True wenn erfolgreich
        """
        try:
            audit_log = AuditLog(
                upload_request_id=upload_request_id,
                action=action,
                actor=actor_id or "system",
                actor_type="system" if not actor_id else "user",
                details=details or {},
                created_at=datetime.utcnow(),
            )

            if db:
                db.add(audit_log)
                db.commit()

            logger.info(
                f"Audit log created: {upload_request_id} - {action}"
            )
            return True

        except Exception as e:
            logger.error(f"Error logging audit: {str(e)}")
            return False

    def apply_conditional_requirements(
        self,
        upload_request: UploadRequest,
        db: Session,
    ) -> List[str]:
        """
        Wendet bedingte Dokumentanforderungen an
        basierend auf Upload-Request-Eigenschaften

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            Liste neu erforderlicher Dokumenttypen
        """
        new_required_docs = []

        # Logik für bedingte Anforderungen
        if upload_request.property_type == "rental":
            # Mietimmobilie: Mieterliste erforderlich
            if not any(
                d.document_type == "tenant_list"
                for d in upload_request.documents
            ):
                new_required_docs.append("tenant_list")

        if upload_request.ltv_ratio and upload_request.ltv_ratio > 0.85:
            # Hohes LTV: Zusätzliche Dokumente erforderlich
            if not any(
                d.document_type == "salary_slip_december_prev_year"
                for d in upload_request.documents
            ):
                new_required_docs.append("salary_slip_december_prev_year")

        if upload_request.loan_amount and upload_request.loan_amount > 1000000:
            # Hohe Kreditsumme: Professionelle Bewertung erforderlich
            new_required_docs.append("professional_valuation")

        return new_required_docs

    def validate_document_combination(
        self,
        upload_request: UploadRequest,
    ) -> Dict:
        """
        Validiert Konsistenz von Dokumenten
        (z.B. wenn Mieterliste vorhanden, dann auch Mietverträge)

        Args:
            upload_request: UploadRequest Objekt

        Returns:
            Dict mit Warnings/Errors
        """
        issues = {
            "warnings": [],
            "errors": [],
        }

        uploaded_docs = {
            d.document_type for d in upload_request.documents
            if d.status == DocumentStatus.uploaded
        }

        # Wenn Mieterliste, dann auch Mietverträge erforderlich
        if "tenant_list" in uploaded_docs and "tenant_contracts" not in uploaded_docs:
            issues["warnings"].append(
                "Mieterliste vorhanden, aber keine Mietverträge hochgeladen"
            )

        # Wenn vermietete Immobilie, dann Betriebskostenabrechnungen erforderlich
        if upload_request.property_type == "rental":
            if "operating_costs" not in uploaded_docs:
                issues["warnings"].append(
                    "Mietimmobilie: Betriebskostenabrechnungen empfohlen"
                )

        return issues

    def get_documents_for_bank(
        self,
        upload_request: UploadRequest,
        bank_profile: str,
    ) -> Dict:
        """
        Gibt Dokumente gruppiert nach Bank-Anforderung zurück

        Args:
            upload_request: UploadRequest Objekt
            bank_profile: Name des Bank-Profils

        Returns:
            Gruppierte Dokumente
        """
        # Hier würde Bank-spezifische Logik eingebaut
        result = {
            "required": [],
            "conditional": [],
            "uploaded": [],
            "missing": [],
        }

        for doc in upload_request.documents:
            if doc.status == DocumentStatus.uploaded:
                result["uploaded"].append(
                    {
                        "id": doc.id,
                        "type": doc.document_type,
                        "label": doc.label,
                    }
                )
            elif doc.is_required:
                result["required"].append(
                    {
                        "id": doc.id,
                        "type": doc.document_type,
                        "label": doc.label,
                    }
                )
            elif doc.is_conditional:
                result["conditional"].append(
                    {
                        "id": doc.id,
                        "type": doc.document_type,
                        "label": doc.label,
                    }
                )

        return result


# Singleton Instance
document_service = DocumentService()
