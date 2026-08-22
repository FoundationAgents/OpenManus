"""
Validation Service für Datei- und Dokumenten-Validierung
"""

from fastapi import UploadFile
from pathlib import Path
from typing import Dict, Optional
import logging

from models import UploadRequest
from config import settings

logger = logging.getLogger(__name__)


class ValidationService:
    """Service für Validierung hochgeladener Dateien"""

    def __init__(self):
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        self.max_file_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    def validate_upload(
        self,
        file: UploadFile,
        document_type: str,
        upload_request: UploadRequest,
    ) -> Dict:
        """
        Validiert hochgeladene Datei

        Args:
            file: UploadFile vom Frontend
            document_type: Dokumenttyp
            upload_request: UploadRequest Objekt

        Returns:
            Dict mit {valid: bool, error: str}
        """
        # 1. Dateiname-Validierung
        if not file.filename:
            return {
                "valid": False,
                "error": "Kein Dateiname vorhanden",
            }

        # 2. Dateityp-Validierung
        file_ext = self._get_file_extension(file.filename)
        if file_ext.lower() not in self.allowed_extensions:
            return {
                "valid": False,
                "error": f"Dateityp .{file_ext} nicht erlaubt. "
                f"Erlaubt: {', '.join(self.allowed_extensions)}",
            }

        # 3. Größe-Validierung
        if file.size and file.size > self.max_file_size:
            return {
                "valid": False,
                "error": f"Datei zu groß. Max: {settings.MAX_FILE_SIZE_MB}MB",
            }

        # 4. MIME-Type Validierung
        if not self._validate_mime_type(file.content_type):
            return {
                "valid": False,
                "error": f"MIME-Type nicht erlaubt: {file.content_type}",
            }

        # 5. Virus-Scan (Optional, wenn verfügbar)
        if not self._scan_for_malware(file.filename):
            return {
                "valid": False,
                "error": "Datei konnte aus Sicherheitsgründen nicht hochgeladen werden",
            }

        return {"valid": True, "error": None}

    def _get_file_extension(self, filename: str) -> str:
        """
        Extrahiert Dateierweiterung

        Args:
            filename: Dateiname

        Returns:
            Erweiterung ohne Punkt
        """
        return Path(filename).suffix.lstrip(".")

    def _validate_mime_type(self, mime_type: str) -> bool:
        """
        Validiert MIME-Type

        Args:
            mime_type: MIME-Type der Datei

        Returns:
            True wenn erlaubt
        """
        allowed_mimes = [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]

        return mime_type in allowed_mimes

    def _scan_for_malware(self, filename: str) -> bool:
        """
        Scannt Datei auf Malware (optional)

        Args:
            filename: Dateiname

        Returns:
            True wenn sauber
        """
        # Implementierung mit python-magic oder ClamAV
        # Für jetzt: nur Dateiname-Prüfung
        dangerous_extensions = [
            "exe", "bat", "cmd", "com", "pif", "scr",
            "vbs", "js", "jar", "zip", "rar"
        ]

        ext = self._get_file_extension(filename).lower()
        if ext in dangerous_extensions:
            logger.warning(f"Dangerous file extension detected: {filename}")
            return False

        return True

    def validate_document_metadata(
        self,
        document_type: str,
        document_data: Dict,
    ) -> Dict:
        """
        Validiert Dokument-Metadaten

        Args:
            document_type: Dokumenttyp
            document_data: Dokumentdaten

        Returns:
            Validierungsergebnis
        """
        errors = []

        if not document_type:
            errors.append("document_type erforderlich")

        if not document_data.get("label"):
            errors.append("label erforderlich")

        if not document_data.get("category"):
            errors.append("category erforderlich")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def validate_upload_request(
        self,
        upload_request: UploadRequest,
    ) -> Dict:
        """
        Validiert gesamte Upload-Anfrage

        Args:
            upload_request: UploadRequest Objekt

        Returns:
            Validierungsergebnis mit Warnings
        """
        warnings = []
        errors = []

        # Prüfe ob Deadline überschritten
        if upload_request.deadline and upload_request.deadline < __import__('datetime').datetime.utcnow():
            errors.append("Deadline überschritten")

        # Prüfe auf fehlende erforderliche Dokumente
        missing_required = sum(
            1 for doc in upload_request.documents
            if doc.is_required and doc.status != "uploaded"
        )

        if missing_required > 0:
            warnings.append(
                f"{missing_required} erforderliche Dokumente fehlen"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def check_duplicate_upload(
        self,
        upload_request,
        document_type: str,
    ) -> Optional[str]:
        """
        Prüft ob Dokument bereits hochgeladen wurde

        Args:
            upload_request: UploadRequest Objekt
            document_type: Dokumenttyp

        Returns:
            ID des existierenden Dokuments oder None
        """
        for doc in upload_request.documents:
            if doc.document_type == document_type and doc.status == "uploaded":
                return doc.id

        return None

    def validate_conditional_requirement(
        self,
        upload_request: UploadRequest,
        condition: str,
    ) -> bool:
        """
        Validiert ob bedingte Anforderung erfüllt ist

        Args:
            upload_request: UploadRequest Objekt
            condition: Bedingung (z.B. "propertyType == 'rental'")

        Returns:
            True wenn Bedingung erfüllt
        """
        try:
            # Simple Bedingungsprüfung
            # In Production würde man einen Expression-Parser verwenden

            if "propertyType == 'rental'" in condition:
                return upload_request.property_type == "rental"

            if "ltvRatio > 0.85" in condition:
                return upload_request.ltv_ratio > 0.85 if upload_request.ltv_ratio else False

            if "customerStatus == 'employed'" in condition:
                return upload_request.customer_status == "employed"

            # Standard: true
            return True

        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return False


# Singleton Instance
validation_service = ValidationService()
