"""
Storage Service für Dateispeicherung und -verwaltung
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from fastapi import UploadFile
from fastapi.responses import FileResponse
import logging

from config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service für Dateienspeicherung (lokal oder S3)"""

    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.storage_path = Path(settings.STORAGE_PATH)
        self.max_file_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        # Stelle sicher, dass das Verzeichnis existiert
        if self.storage_type == "local":
            self.storage_path.mkdir(parents=True, exist_ok=True)

    async def store_file(
        self,
        file: UploadFile,
        request_id: str,
        document_type: str,
    ) -> Dict:
        """
        Speichert hochgeladene Datei

        Args:
            file: UploadFile vom Frontend
            request_id: ID der Upload-Anfrage
            document_type: Dokumenttyp

        Returns:
            Dict mit path, hash, size
        """
        try:
            # Erstelle Verzeichnis für diese Upload-Anfrage
            request_dir = self.storage_path / request_id
            request_dir.mkdir(parents=True, exist_ok=True)

            # Sicherer Dateiname
            safe_filename = self._sanitize_filename(file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{document_type}_{timestamp}_{safe_filename}"

            file_path = request_dir / unique_filename

            # Datei speichern und Hash berechnen
            file_content = await file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Speichern
            with open(file_path, "wb") as f:
                f.write(file_content)

            logger.info(
                f"File stored: {request_id}/{unique_filename} "
                f"(Size: {len(file_content)} bytes)"
            )

            return {
                "path": str(file_path),
                "hash": file_hash,
                "size": len(file_content),
                "filename": unique_filename,
            }

        except Exception as e:
            logger.error(f"Error storing file: {str(e)}")
            raise

    def get_file_response(self, file_path: str) -> FileResponse:
        """
        Gibt Datei als Download zurück

        Args:
            file_path: Pfad zur Datei

        Returns:
            FileResponse für Download
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return FileResponse(
            path=path,
            filename=path.name,
            media_type="application/octet-stream",
        )

    def create_export_zip(
        self,
        upload_request,
        db,
    ) -> str:
        """
        Erstellt ZIP-Datei mit allen hochgeladenen Dokumenten
        für Bank-Export

        Args:
            upload_request: UploadRequest Objekt
            db: Database Session

        Returns:
            Pfad zur ZIP-Datei
        """
        try:
            import zipfile

            request_dir = self.storage_path / upload_request.id
            zip_path = self.storage_path / f"{upload_request.id}_export.zip"

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Füge alle Dateien der Upload-Anfrage hinzu
                for document in upload_request.documents:
                    if document.status == "uploaded":
                        file_path = Path(document.file_path)
                        if file_path.exists():
                            # Archiviere mit Kategorien
                            arcname = f"{document.category}/{document.label}/{file_path.name}"
                            zipf.write(file_path, arcname=arcname)

                # Füge Metadaten-JSON hinzu
                import json
                metadata = {
                    "requestId": upload_request.id,
                    "customerId": upload_request.customer_id,
                    "exportedAt": datetime.utcnow().isoformat(),
                    "documents": [
                        {
                            "id": doc.id,
                            "type": doc.document_type,
                            "label": doc.label,
                            "status": doc.status,
                            "uploadedAt": doc.uploaded_at.isoformat()
                            if doc.uploaded_at
                            else None,
                        }
                        for doc in upload_request.documents
                    ],
                }
                zipf.writestr("_metadata.json", json.dumps(metadata, indent=2))

            logger.info(f"ZIP export created: {zip_path}")
            return str(zip_path)

        except Exception as e:
            logger.error(f"Error creating ZIP export: {str(e)}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Löscht eine Datei (z.B. bei DSGVO-Anfrage)

        Args:
            file_path: Pfad zur zu löschenden Datei

        Returns:
            True wenn erfolgreich
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

    def delete_request_directory(self, request_id: str) -> bool:
        """
        Löscht gesamtes Verzeichnis einer Upload-Anfrage
        (z.B. bei Stornierung oder DSGVO)

        Args:
            request_id: ID der Upload-Anfrage

        Returns:
            True wenn erfolgreich
        """
        try:
            request_dir = self.storage_path / request_id
            if request_dir.exists():
                shutil.rmtree(request_dir)
                logger.info(f"Request directory deleted: {request_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting request directory: {str(e)}")
            return False

    def verify_file_integrity(
        self,
        file_path: str,
        expected_hash: str,
    ) -> bool:
        """
        Verifiziert Dateiintegrität via Hash-Vergleich

        Args:
            file_path: Pfad zur Datei
            expected_hash: Erwarteter SHA256 Hash

        Returns:
            True wenn Hashes stimmen
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return False

            with open(path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            return file_hash == expected_hash

        except Exception as e:
            logger.error(f"Error verifying file integrity: {str(e)}")
            return False

    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """
        Gibt Informationen über eine Datei zurück

        Args:
            file_path: Pfad zur Datei

        Returns:
            Dict mit size, created_at, modified_at
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            stat = path.stat()
            return {
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
                "name": path.name,
            }

        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Bereinigt Dateinamen für sichere Speicherung

        Args:
            filename: Original-Dateiname

        Returns:
            Sichere Variante des Dateinamens
        """
        import re

        # Entferne gefährliche Zeichen
        filename = re.sub(r"[^\w\s\-\.]", "", filename)
        # Entferne mehrfache Leerzeichen
        filename = re.sub(r"\s+", "_", filename)
        # Begrenze Länge
        filename = filename[:255]

        return filename


# Singleton Instance
storage_service = StorageService()
