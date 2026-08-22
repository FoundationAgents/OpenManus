"""
Email Service für automatisierte Benachrichtigungen
"""

from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service für E-Mail-Versendung"""

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

        # Jinja2 Environment für Templates
        self.template_env = Environment(
            loader=FileSystemLoader(settings.EMAIL_TEMPLATE_PATH)
        )

    def send_missing_documents_notification(
        self,
        customer_email: str,
        missing_documents: List[Dict],
        admin_message: Optional[str] = None,
    ) -> bool:
        """
        Sendet Benachrichtigung über fehlende Dokumente an Kunden

        Args:
            customer_email: E-Mail des Kunden
            missing_documents: Liste fehlender Dokumente
            admin_message: Optionale Nachricht vom Admin

        Returns:
            True wenn erfolgreich gesendet
        """
        try:
            template = self.template_env.get_template("missing_documents.html")

            html_content = template.render(
                customer_email=customer_email,
                missing_documents=missing_documents,
                admin_message=admin_message,
                company_name=settings.SMTP_FROM_NAME,
                support_email="support@example.com",
                timestamp=datetime.utcnow().isoformat(),
            )

            subject = f"📋 Bitte hochladen: {len(missing_documents)} Dokumente fehlen noch"

            return self._send_email(
                to_email=customer_email,
                subject=subject,
                html_content=html_content,
                email_type="missing_documents",
            )

        except Exception as e:
            logger.error(f"Fehler beim Versand fehlender Dokumente: {str(e)}")
            return False

    def send_additional_document_request(
        self,
        customer_email: str,
        documents: List[str],
        message: str,
    ) -> bool:
        """
        Sendet Anforderung für zusätzliche Dokumente
        """
        try:
            template = self.template_env.get_template(
                "additional_documents_request.html"
            )

            html_content = template.render(
                customer_email=customer_email,
                documents=documents,
                message=message,
                company_name=settings.SMTP_FROM_NAME,
                timestamp=datetime.utcnow().isoformat(),
            )

            subject = "📌 Zusätzliche Unterlagen erforderlich"

            return self._send_email(
                to_email=customer_email,
                subject=subject,
                html_content=html_content,
                email_type="additional_documents_request",
            )

        except Exception as e:
            logger.error(f"Fehler beim Versand Zusatzanforderung: {str(e)}")
            return False

    def send_upload_complete_notification(
        self,
        customer_email: str,
        completion_percentage: int,
    ) -> bool:
        """
        Sendet Benachrichtigung wenn Upload vollständig ist
        """
        try:
            template = self.template_env.get_template("upload_complete.html")

            html_content = template.render(
                customer_email=customer_email,
                completion_percentage=completion_percentage,
                company_name=settings.SMTP_FROM_NAME,
                timestamp=datetime.utcnow().isoformat(),
            )

            subject = "✅ Herzlichen Glückwunsch! Alle Dokumente hochgeladen"

            return self._send_email(
                to_email=customer_email,
                subject=subject,
                html_content=html_content,
                email_type="upload_complete",
            )

        except Exception as e:
            logger.error(f"Fehler beim Versand Uploadbestätigung: {str(e)}")
            return False

    def send_deadline_reminder(
        self,
        customer_email: str,
        days_remaining: int,
        missing_count: int,
    ) -> bool:
        """
        Sendet Deadline-Erinnerung an Kunden
        """
        try:
            template = self.template_env.get_template("deadline_reminder.html")

            html_content = template.render(
                customer_email=customer_email,
                days_remaining=days_remaining,
                missing_count=missing_count,
                company_name=settings.SMTP_FROM_NAME,
                timestamp=datetime.utcnow().isoformat(),
            )

            subject = f"⏰ Erinnerung: Noch {days_remaining} Tage bis zur Deadline"

            return self._send_email(
                to_email=customer_email,
                subject=subject,
                html_content=html_content,
                email_type="deadline_reminder",
            )

        except Exception as e:
            logger.error(f"Fehler beim Versand Erinnerung: {str(e)}")
            return False

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        email_type: str = "transactional",
    ) -> bool:
        """
        Interne Methode zum Versenden einer E-Mail

        Args:
            to_email: Ziel-E-Mail
            subject: Betreff
            html_content: HTML-Inhalt
            email_type: Typ der E-Mail (für Logging)

        Returns:
            True wenn erfolgreich
        """
        try:
            # Email erstellen
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Plain text fallback
            text_part = MIMEText("Bitte öffnen Sie diese E-Mail in einem HTML-fähigen Client.", "plain")
            msg.attach(text_part)

            # HTML part
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Versenden
            if settings.SEND_EMAIL_IMMEDIATELY:
                # Synchron versenden (Development)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                logger.info(f"Email sent: {email_type} to {to_email}")
                return True
            else:
                # Async via Celery (Production)
                from backend.celery_app import send_email_task
                send_email_task.delay(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content,
                    email_type=email_type,
                )
                logger.info(f"Email queued: {email_type} for {to_email}")
                return True

        except Exception as e:
            logger.error(f"SMTP Error ({email_type}): {str(e)}")
            return False

    def send_admin_notification(
        self,
        admin_email: str,
        notification_type: str,
        data: Dict,
    ) -> bool:
        """
        Sendet interne Benachrichtigungen an Admins
        """
        try:
            template_name = f"admin_{notification_type}.html"
            template = self.template_env.get_template(template_name)

            html_content = template.render(
                **data,
                timestamp=datetime.utcnow().isoformat(),
            )

            subject = f"[ADMIN] {notification_type}"

            return self._send_email(
                to_email=admin_email,
                subject=subject,
                html_content=html_content,
                email_type=f"admin_{notification_type}",
            )

        except Exception as e:
            logger.error(f"Fehler beim Versand Admin-Benachrichtigung: {str(e)}")
            return False


# Singleton Instance
email_service = EmailService()
