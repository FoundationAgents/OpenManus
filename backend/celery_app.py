"""
Celery Configuration für Background Tasks
"""

from celery import Celery, shared_task
from celery.schedules import crontab
from datetime import datetime, timedelta
import logging

from config import settings

logger = logging.getLogger(__name__)

# Celery App Initialisierung
celery_app = Celery(
    "upload_system",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Konfiguration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 Minuten hard limit
    task_soft_time_limit=25 * 60,  # 25 Minuten soft limit
)

# ============================================================================
# PERIODIC TASKS (Celery Beat)
# ============================================================================

celery_app.conf.beat_schedule = {
    # Täglich um 02:00 UTC: Prüfe abgelaufene Dokumente
    "check-document-expiry": {
        "task": "backend.celery_app.check_document_expiry_task",
        "schedule": crontab(hour=2, minute=0),
    },
    # Jeden Morgen um 08:00 UTC: Sende Erinnerungen
    "send-deadline-reminders": {
        "task": "backend.celery_app.send_deadline_reminders_task",
        "schedule": crontab(hour=8, minute=0),
    },
    # Täglich um 18:00 UTC: Verarbeite E-Mail-Queue
    "process-email-queue": {
        "task": "backend.celery_app.process_email_queue_task",
        "schedule": crontab(hour=18, minute=0),
    },
    # Wöchentlich: Cleanup alte Audit Logs
    "cleanup-old-logs": {
        "task": "backend.celery_app.cleanup_old_logs_task",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),  # Sonntag 03:00
    },
}

# ============================================================================
# IMMEDIATE TASKS
# ============================================================================


@shared_task(bind=True, max_retries=3)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    html_content: str,
    email_type: str = "transactional",
):
    """
    Sendet E-Mail asynchron

    Args:
        to_email: Ziel-E-Mail
        subject: Betreff
        html_content: HTML-Inhalt
        email_type: Typ der E-Mail
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        text_part = MIMEText("Bitte öffnen Sie diese E-Mail in einem HTML-Client.", "plain")
        msg.attach(text_part)

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent: {email_type} to {to_email}")
        return {"status": "sent", "email_type": email_type}

    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {str(e)}")
        # Retry nach exponentiellem Backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise


# ============================================================================
# SCHEDULED TASKS
# ============================================================================


@shared_task
def check_document_expiry_task():
    """
    Täglich: Prüfe abgelaufene Dokumente und aktualisiere Status
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        from models import Document, DocumentStatus

        # Finde abgelaufene Dokumente
        expired_docs = db.query(Document).filter(
            Document.expiry_date.isnot(None),
            Document.expiry_date < datetime.utcnow(),
            Document.status != DocumentStatus.expired,
        ).all()

        for doc in expired_docs:
            doc.status = DocumentStatus.expired
            logger.warning(f"Document marked as expired: {doc.id}")

        db.commit()
        db.close()

        return {
            "status": "completed",
            "expired_count": len(expired_docs),
        }

    except Exception as e:
        logger.error(f"Error in document expiry check: {str(e)}")
        raise


@shared_task
def send_deadline_reminders_task():
    """
    Täglich: Sende Erinnerungen für bevorstehende Deadlines
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        from models import UploadRequest, UploadRequestStatus
        from services.document_service import document_service
        from services.email_service import email_service

        # Finde Upload-Anfragen mit Deadline in 3 Tagen
        deadline_soon = datetime.utcnow() + timedelta(days=3)
        upload_requests = db.query(UploadRequest).filter(
            UploadRequest.status == UploadRequestStatus.in_progress,
            UploadRequest.deadline.isnot(None),
            UploadRequest.deadline <= deadline_soon,
            UploadRequest.deadline > datetime.utcnow(),
        ).all()

        sent_count = 0
        for req in upload_requests:
            missing = document_service.get_missing_required(req, db)
            if missing:
                days_remaining = (req.deadline - datetime.utcnow()).days

                # Sende Erinnerung an Kunde
                if email_service.send_deadline_reminder(
                    customer_email=req.customer.email,
                    days_remaining=days_remaining,
                    missing_count=len(missing),
                ):
                    sent_count += 1

        db.close()

        return {
            "status": "completed",
            "reminders_sent": sent_count,
        }

    except Exception as e:
        logger.error(f"Error in deadline reminders: {str(e)}")
        raise


@shared_task
def process_email_queue_task():
    """
    Täglich: Verarbeite ausstehende E-Mails aus der Queue
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        from models import EmailQueue
        from services.email_service import email_service

        # Finde ausstehende E-Mails
        pending_emails = db.query(EmailQueue).filter(
            EmailQueue.status == "pending",
        ).limit(100).all()

        sent_count = 0
        failed_count = 0

        for email in pending_emails:
            try:
                if email_service._send_email(
                    to_email=email.recipient_email,
                    subject=email.subject,
                    html_content=email.html_body or email.body,
                    email_type=email.email_type,
                ):
                    email.status = "sent"
                    email.sent_at = datetime.utcnow()
                    sent_count += 1
                else:
                    email.retry_count += 1
                    if email.retry_count >= 3:
                        email.status = "failed"
                        failed_count += 1

            except Exception as e:
                email.failed_reason = str(e)
                email.retry_count += 1
                if email.retry_count >= 3:
                    email.status = "failed"
                    failed_count += 1

        db.commit()
        db.close()

        return {
            "status": "completed",
            "sent": sent_count,
            "failed": failed_count,
        }

    except Exception as e:
        logger.error(f"Error processing email queue: {str(e)}")
        raise


@shared_task
def cleanup_old_logs_task():
    """
    Wöchentlich: Lösche alte Audit Logs (älter als 1 Jahr)
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        from models import AuditLog

        cutoff_date = datetime.utcnow() - timedelta(days=365)
        deleted = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).delete()

        db.commit()
        db.close()

        logger.info(f"Cleanup: Deleted {deleted} old audit logs")

        return {
            "status": "completed",
            "deleted": deleted,
        }

    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        raise


if __name__ == "__main__":
    celery_app.start()
