import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response Interceptor für Error Handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired - redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // =====================================================================
  // CUSTOMER ENDPOINTS
  // =====================================================================

  async getUploadRequest(requestId: string) {
    return this.client.get(`/upload-requests/${requestId}`);
  }

  async uploadDocument(
    requestId: string,
    file: File,
    documentType: string
  ) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    return this.client.post(
      `/upload-requests/${requestId}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  }

  async downloadDocument(requestId: string, docId: string) {
    return this.client.get(
      `/upload-requests/${requestId}/documents/${docId}/download`,
      {
        responseType: 'blob',
      }
    );
  }

  // =====================================================================
  // ADMIN ENDPOINTS
  // =====================================================================

  async getAdminStats() {
    return this.client.get('/admin/upload-requests/stats');
  }

  async listAdminRequests(status?: string) {
    return this.client.get('/admin/upload-requests', {
      params: status ? { status } : {},
    });
  }

  async notifyMissingDocuments(
    requestId: string,
    message: string,
    adminId: string
  ) {
    return this.client.post(
      '/admin/approval/notify-missing-documents',
      {
        requestId,
        message,
        adminId,
        sendEmailToCustomer: true,
      }
    );
  }

  async requestAdditionalDocuments(
    requestId: string,
    documents: string[],
    message: string,
    adminId: string
  ) {
    return this.client.post(
      '/admin/approval/request-additional-documents',
      {
        requestId,
        documents,
        message,
        adminId,
        sendEmailToCustomer: true,
      }
    );
  }

  async getAuditLog(requestId: string) {
    return this.client.get(`/admin/upload-requests/${requestId}/audit-log`);
  }

  async approveSubmission(requestId: string, adminId: string, notes: string) {
    return this.client.post('/admin/approval/approve-submission', {
      requestId,
      adminId,
      notes,
    });
  }

  async rejectSubmission(requestId: string, adminId: string, reason: string) {
    return this.client.post('/admin/approval/reject-submission', {
      requestId,
      adminId,
      reason,
    });
  }

  // =====================================================================
  // BANK ENDPOINTS
  // =====================================================================

  async getBankUploadRequest(
    requestId: string,
    bankApiKey: string
  ) {
    return this.client.get(`/bank/upload-requests/${requestId}`, {
      headers: {
        'X-Bank-API-Key': bankApiKey,
      },
    });
  }

  async exportDocumentsZip(
    requestId: string,
    bankApiKey: string
  ) {
    return this.client.post(
      `/bank/export-documents/${requestId}`,
      {},
      {
        headers: {
          'X-Bank-API-Key': bankApiKey,
        },
        responseType: 'blob',
      }
    );
  }

  // =====================================================================
  // UTILITY
  // =====================================================================

  setAuthToken(token: string) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  removeAuthToken() {
    delete this.client.defaults.headers.common['Authorization'];
  }
}

export const apiClient = new ApiClient();
