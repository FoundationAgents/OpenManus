"""
Konfigurationseinstellungen für Upload-System
"""

import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Haupt-Konfiguration"""

    # =====================================================================
    # APP SETTINGS
    # =====================================================================
    APP_NAME: str = "Upload-Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # =====================================================================
    # DATABASE
    # =====================================================================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/upload_system"
    )
    DATABASE_ECHO: bool = DEBUG

    # =====================================================================
    # STORAGE
    # =====================================================================
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # "local", "s3", "gcs"
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "/var/uploads")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png", "docx", "xlsx"]

    # S3 Settings (if applicable)
    AWS_BUCKET: str = os.getenv("AWS_BUCKET", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-central-1")

    # =====================================================================
    # SECURITY
    # =====================================================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://yourdomain.com"
    ]

    # =====================================================================
    # EMAIL SETTINGS
    # =====================================================================
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@example.com")
    SMTP_FROM_NAME: str = "Upload System"

    # Email Template Settings
    EMAIL_TEMPLATE_PATH: str = "/app/templates/emails"
    SEND_EMAIL_IMMEDIATELY: bool = False  # Async via Celery

    # =====================================================================
    # DOCUMENT REQUIREMENTS
    # =====================================================================
    DOCUMENT_CONFIG_PATH: str = os.getenv(
        "DOCUMENT_CONFIG_PATH",
        "/app/config/documents.json"
    )
    BANK_PROFILES_PATH: str = os.getenv(
        "BANK_PROFILES_PATH",
        "/app/config/bank_profiles.json"
    )

    # Document Expiry (in days)
    DOCUMENT_EXPIRY_SETTINGS: dict = {
        "personalausweis": 3650,  # 10 Jahre
        "grundbuchauszug": 180,   # 6 Monate
        "flurkarte": 180,         # 6 Monate
        "energieausweis": 3650,   # 10 Jahre
        "salary_slip": 90,        # 3 Monate
        "other": None             # Unbegrenzt
    }

    # =====================================================================
    # UPLOAD REQUEST SETTINGS
    # =====================================================================
    DEFAULT_UPLOAD_DEADLINE_DAYS: int = 30
    AUTO_EXPIRE_UPLOAD_AFTER_DAYS: int = 90
    SEND_REMINDER_AFTER_DAYS: int = 7
    SEND_OVERDUE_AFTER_DAYS: int = 3

    # =====================================================================
    # CELERY / BACKGROUND TASKS
    # =====================================================================
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1"
    )

    # =====================================================================
    # LOGGING
    # =====================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "/var/log/upload_system.log"

    # =====================================================================
    # ADMIN SETTINGS
    # =====================================================================
    ADMIN_APPROVAL_REQUIRED: bool = True
    AUTO_SEND_CUSTOMER_EMAILS: bool = False  # Wenn False, muss Admin genehmigen
    SEND_CUSTOMER_SUCCESS_EMAIL: bool = True

    # =====================================================================
    # FEATURE FLAGS
    # =====================================================================
    FEATURE_OCR: bool = False
    FEATURE_DOCUMENT_VERIFICATION: bool = True
    FEATURE_MOBILE_APP: bool = False
    FEATURE_E_SIGNATURE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
