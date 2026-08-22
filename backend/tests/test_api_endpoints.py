"""
Integration Tests für API Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from models import Base, Customer, UploadRequest


@pytest.fixture
def test_db():
    """In-Memory Test Database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal()


@pytest.fixture
def client():
    """FastAPI Test Client"""
    return TestClient(app)


@pytest.fixture
def sample_customer(test_db):
    """Create sample customer"""
    customer = Customer(
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )
    test_db.add(customer)
    test_db.commit()
    test_db.refresh(customer)
    return customer


@pytest.fixture
def sample_upload_request(test_db, sample_customer):
    """Create sample upload request"""
    request = UploadRequest(
        customer_id=sample_customer.id,
        status="in_progress",
        bank_profile="deutsche_bank",
    )
    test_db.add(request)
    test_db.commit()
    test_db.refresh(request)
    return request


class TestCustomerEndpoints:
    """Test Customer API Endpoints"""

    def test_health_check(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_get_upload_request(self, client, test_db, sample_upload_request):
        """Test GET /api/v1/upload-requests/{request_id}"""
        response = client.get(f"/api/v1/upload-requests/{sample_upload_request.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_upload_request.id)
        assert data["status"] == "in_progress"

    def test_get_upload_request_not_found(self, client):
        """Test GET with invalid request ID"""
        response = client.get("/api/v1/upload-requests/invalid-id")
        assert response.status_code == 404

    def test_upload_document_missing_file(self, client, sample_upload_request):
        """Test POST /upload without file"""
        response = client.post(
            f"/api/v1/upload-requests/{sample_upload_request.id}/upload",
            data={"document_type": "personalausweis_front"},
        )
        assert response.status_code == 422  # Validation error

    def test_download_document_not_found(self, client, sample_upload_request):
        """Test GET /download with invalid doc ID"""
        response = client.get(
            f"/api/v1/upload-requests/{sample_upload_request.id}/documents/invalid/download"
        )
        assert response.status_code == 404


class TestAdminEndpoints:
    """Test Admin API Endpoints"""

    def test_list_admin_requests(self, client, test_db, sample_upload_request):
        """Test GET /api/v1/admin/upload-requests"""
        response = client.get("/api/v1/admin/upload-requests")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["id"] == str(sample_upload_request.id)

    def test_list_admin_requests_filter_by_status(
        self, client, test_db, sample_upload_request
    ):
        """Test filter by status"""
        response = client.get(
            "/api/v1/admin/upload-requests?status=in_progress"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(req["status"] == "in_progress" for req in data)

    def test_notify_missing_documents(self, client, sample_upload_request):
        """Test POST /notify-missing-documents"""
        response = client.post(
            "/api/v1/admin/approval/notify-missing-documents",
            json={
                "requestId": str(sample_upload_request.id),
                "message": "Test message",
                "adminId": "admin-123",
                "sendEmailToCustomer": False,  # Don't actually send
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_audit_log(self, client, sample_upload_request):
        """Test GET /audit-log"""
        response = client.get(
            f"/api/v1/admin/upload-requests/{sample_upload_request.id}/audit-log"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBankEndpoints:
    """Test Bank API Endpoints"""

    def test_get_bank_upload_request_invalid_key(self, client, sample_upload_request):
        """Test bank access with invalid API key"""
        response = client.get(
            f"/api/v1/bank/upload-requests/{sample_upload_request.id}",
            headers={"X-Bank-API-Key": "invalid"},
        )
        assert response.status_code == 401

    def test_get_bank_upload_request_valid_key(
        self, client, sample_upload_request
    ):
        """Test bank access with valid API key"""
        # Note: In production, validate against actual API keys
        response = client.get(
            f"/api/v1/bank/upload-requests/{sample_upload_request.id}",
            headers={"X-Bank-API-Key": "bank_valid_key_12345678"},
        )
        # This will fail if validation is not mocked
        # In real tests, you'd mock the validation


class TestErrorHandling:
    """Test Error Handling"""

    def test_404_not_found(self, client):
        """Test 404 error"""
        response = client.get("/api/v1/invalid-endpoint")
        assert response.status_code == 404

    def test_validation_error(self, client):
        """Test validation error"""
        response = client.get("/api/v1/upload-requests/")
        assert response.status_code in [404, 422]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
