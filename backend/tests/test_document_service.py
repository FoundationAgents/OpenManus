"""
Unit Tests für Document Service
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, UploadRequest, Document, Customer, DocumentStatus
from services.document_service import document_service


@pytest.fixture
def db():
    """In-Memory SQLite Database für Tests"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def sample_customer(db):
    """Erstelle Sample Customer"""
    customer = Customer(
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )
    db.add(customer)
    db.commit()
    return customer


@pytest.fixture
def sample_upload_request(db, sample_customer):
    """Erstelle Sample Upload Request"""
    request = UploadRequest(
        customer_id=sample_customer.id,
        status="in_progress",
        property_type="residential",
        bank_profile="deutsche_bank",
    )
    db.add(request)
    db.commit()
    return request


@pytest.fixture
def sample_documents(db, sample_upload_request):
    """Erstelle Sample Dokumente"""
    docs = [
        Document(
            upload_request_id=sample_upload_request.id,
            document_type="personalausweis_front",
            label="Personalausweis - Vorderseite",
            category="kundenunterlagen",
            is_required=True,
            status=DocumentStatus.uploaded,
        ),
        Document(
            upload_request_id=sample_upload_request.id,
            document_type="personalausweis_back",
            label="Personalausweis - Rückseite",
            category="kundenunterlagen",
            is_required=True,
            status=DocumentStatus.missing,
        ),
        Document(
            upload_request_id=sample_upload_request.id,
            document_type="salary_slip",
            label="Lohnabrechnung",
            category="kundenunterlagen",
            is_required=True,
            status=DocumentStatus.pending,
        ),
        Document(
            upload_request_id=sample_upload_request.id,
            document_type="schufa",
            label="Schufa-Auskunft",
            category="kundenunterlagen",
            is_required=False,
            status=DocumentStatus.missing,
        ),
    ]
    db.add_all(docs)
    db.commit()
    return docs


class TestDocumentService:
    """Test Suite für Document Service"""

    def test_calculate_completion_empty(self, db, sample_upload_request):
        """Test Completion-Berechnung mit leeren Dokumenten"""
        completion = document_service.calculate_completion(
            sample_upload_request, db
        )
        assert completion == 0

    def test_calculate_completion_partial(self, db, sample_upload_request, sample_documents):
        """Test Completion-Berechnung mit teilweise hochgeladenen Docs"""
        completion = document_service.calculate_completion(
            sample_upload_request, db
        )
        # 1 von 3 erforderlich hochgeladen = 33%
        assert completion == 33

    def test_calculate_completion_full(self, db, sample_upload_request, sample_documents):
        """Test Completion-Berechnung mit vollständigen Docs"""
        # Markiere alle erforderlichen als hochgeladen
        db.query(Document).filter(
            Document.is_required == True
        ).update({"status": DocumentStatus.uploaded})
        db.commit()

        completion = document_service.calculate_completion(
            sample_upload_request, db
        )
        assert completion == 100

    def test_get_missing_required(self, db, sample_upload_request, sample_documents):
        """Test Abrufen fehlender erforderlicher Dokumente"""
        missing = document_service.get_missing_required(
            sample_upload_request, db
        )
        assert len(missing) == 2  # 2 erforderlich, nicht hochgeladen
        assert all(doc['type'] in ['personalausweis_back', 'salary_slip'] for doc in missing)

    def test_get_missing_optional(self, db, sample_upload_request, sample_documents):
        """Test Abrufen fehlender optionaler Dokumente"""
        missing = document_service.get_missing_optional(
            sample_upload_request, db
        )
        assert len(missing) == 1  # 1 optional, nicht hochgeladen
        assert missing[0]['type'] == 'schufa'

    def test_is_complete_true(self, db, sample_upload_request, sample_documents):
        """Test Vollständigkeitsprüfung - True"""
        # Markiere alle erforderlichen als hochgeladen
        db.query(Document).filter(
            Document.is_required == True
        ).update({"status": DocumentStatus.uploaded})
        db.commit()

        is_complete = document_service.is_complete(
            sample_upload_request, db
        )
        assert is_complete is True

    def test_is_complete_false(self, db, sample_upload_request, sample_documents):
        """Test Vollständigkeitsprüfung - False"""
        is_complete = document_service.is_complete(
            sample_upload_request, db
        )
        assert is_complete is False

    def test_check_document_expiry_valid(self, db):
        """Test Verfallsprüfung - noch gültig"""
        doc = Document(
            upload_request_id="fake-id",
            document_type="test",
            label="Test",
            expiry_date=datetime.utcnow() + timedelta(days=30),
        )
        assert document_service.check_document_expiry(doc) is True

    def test_check_document_expiry_expired(self, db):
        """Test Verfallsprüfung - abgelaufen"""
        doc = Document(
            upload_request_id="fake-id",
            document_type="test",
            label="Test",
            expiry_date=datetime.utcnow() - timedelta(days=1),
        )
        assert document_service.check_document_expiry(doc) is False

    def test_check_document_expiry_unlimited(self, db):
        """Test Verfallsprüfung - unbegrenzt gültig"""
        doc = Document(
            upload_request_id="fake-id",
            document_type="test",
            label="Test",
            expiry_date=None,
        )
        assert document_service.check_document_expiry(doc) is True

    def test_get_documents_by_category(self, db, sample_upload_request, sample_documents):
        """Test Abrufen von Dokumenten nach Kategorie"""
        docs = document_service.get_documents_by_category(
            sample_upload_request, "kundenunterlagen"
        )
        assert len(docs) == 4
        assert all(doc.category == "kundenunterlagen" for doc in docs)

    def test_get_document_status_summary(self, db, sample_upload_request, sample_documents):
        """Test Dokumenten-Status-Zusammenfassung"""
        summary = document_service.get_document_status_summary(
            sample_upload_request
        )
        assert summary['total'] == 4
        assert summary['uploaded'] == 1
        assert summary['pending'] == 1
        assert summary['missing'] == 2

    def test_apply_conditional_requirements_rental(
        self, db, sample_upload_request, sample_documents
    ):
        """Test bedingte Anforderungen für Mietimmobilie"""
        sample_upload_request.property_type = 'rental'
        db.commit()

        new_required = document_service.apply_conditional_requirements(
            sample_upload_request, db
        )
        assert 'tenant_list' in new_required

    def test_apply_conditional_requirements_high_ltv(
        self, db, sample_upload_request, sample_documents
    ):
        """Test bedingte Anforderungen für hohes LTV"""
        sample_upload_request.ltv_ratio = 0.90
        db.commit()

        new_required = document_service.apply_conditional_requirements(
            sample_upload_request, db
        )
        assert 'salary_slip_december_prev_year' in new_required


class TestDocumentValidation:
    """Test Suite für Document Validation"""

    def test_validate_document_combination_valid(
        self, db, sample_upload_request, sample_documents
    ):
        """Test Dokumenten-Kombinations-Validierung - gültig"""
        issues = document_service.validate_document_combination(
            sample_upload_request
        )
        assert issues['errors'] == []

    def test_validate_document_combination_warning(
        self, db, sample_upload_request
    ):
        """Test Dokumenten-Kombinations-Validierung - Warning"""
        # Füge Mieterliste ohne Mietverträge hinzu
        doc = Document(
            upload_request_id=sample_upload_request.id,
            document_type="tenant_list",
            label="Mieterliste",
            category="objektunterlagen",
            is_required=False,
            status=DocumentStatus.uploaded,
        )
        db.add(doc)
        db.commit()

        issues = document_service.validate_document_combination(
            sample_upload_request
        )
        assert len(issues['warnings']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
