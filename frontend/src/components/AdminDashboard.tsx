import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';

interface UploadRequest {
  id: string;
  customerId: string;
  status: 'pending' | 'in_progress' | 'submitted' | 'complete';
  completionPercentage: number;
  requiredMissing: number;
  createdAt: string;
  lastUpdated: string;
}

interface DashboardStats {
  totalRequests: number;
  byStatus: Record<string, number>;
  pending: number;
  inProgress: number;
  submitted: number;
  complete: number;
}

export const AdminDashboard: React.FC = () => {
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'submitted' | 'complete'>('all');
  const [selectedRequest, setSelectedRequest] = useState<UploadRequest | null>(null);

  // Statistiken abrufen
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      const response = await axios.get<DashboardStats>('/api/v1/admin/upload-requests/stats');
      return response.data;
    },
  });

  // Upload-Anfragen abrufen
  const { data: requests, isLoading: requestsLoading } = useQuery({
    queryKey: ['upload-requests', filter],
    queryFn: async () => {
      const url = filter === 'all'
        ? '/api/v1/admin/upload-requests'
        : `/api/v1/admin/upload-requests?status=${filter}`;
      const response = await axios.get<UploadRequest[]>(url);
      return response.data;
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete':
        return 'bg-green-100 text-green-800';
      case 'submitted':
        return 'bg-blue-100 text-blue-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Ausstehend',
      in_progress: 'In Bearbeitung',
      submitted: 'Eingereicht',
      complete: 'Abgeschlossen',
    };
    return labels[status] || status;
  };

  return (
    <div className="admin-dashboard space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          📊 Admin Dashboard
        </h1>
        <p className="text-gray-600">
          Verwalten Sie alle Upload-Anfragen und überwachen Sie den Fortschritt
        </p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <StatCard
            label="Gesamt"
            value={stats.totalRequests}
            color="blue"
            icon="📋"
          />
          <StatCard
            label="Ausstehend"
            value={stats.pending}
            color="gray"
            icon="⏳"
          />
          <StatCard
            label="In Bearbeitung"
            value={stats.inProgress}
            color="yellow"
            icon="🔄"
          />
          <StatCard
            label="Eingereicht"
            value={stats.submitted}
            color="blue"
            icon="✓"
          />
          <StatCard
            label="Abgeschlossen"
            value={stats.complete}
            color="green"
            icon="✅"
          />
        </div>
      )}

      {/* Filter Buttons */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2 flex-wrap">
          {(['all', 'pending', 'in_progress', 'submitted', 'complete'] as const).map(
            (status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={clsx(
                  'px-4 py-2 rounded font-semibold transition',
                  filter === status
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
              >
                {getStatusLabel(status === 'all' ? 'all' : status)}
              </button>
            )
          )}
        </div>
      </div>

      {/* Requests Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Kunde
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Fortschritt
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Fehlend
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Erstellt
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Aktion
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {requestsLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Laden...
                  </td>
                </tr>
              ) : requests && requests.length > 0 ? (
                requests.map((req) => (
                  <tr key={req.id} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-semibold text-gray-800">
                          {req.customerId}
                        </span>
                        <span className="text-sm text-gray-500">{req.id}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={clsx(
                          'inline-block px-3 py-1 rounded-full text-sm font-semibold',
                          getStatusColor(req.status)
                        )}
                      >
                        {getStatusLabel(req.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${req.completionPercentage}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-600 mt-1">
                        {req.completionPercentage}%
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {req.requiredMissing > 0 ? (
                        <span className="inline-block bg-red-100 text-red-800 px-2 py-1 rounded text-sm font-semibold">
                          {req.requiredMissing} fehlend
                        </span>
                      ) : (
                        <span className="inline-block bg-green-100 text-green-800 px-2 py-1 rounded text-sm font-semibold">
                          Vollständig
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(req.createdAt).toLocaleDateString('de-DE')}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => setSelectedRequest(req)}
                        className="text-blue-600 hover:text-blue-800 font-semibold text-sm"
                      >
                        Details →
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Keine Anfragen gefunden
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Panel */}
      {selectedRequest && (
        <AdminDetailPanel
          request={selectedRequest}
          onClose={() => setSelectedRequest(null)}
        />
      )}
    </div>
  );
};

interface StatCardProps {
  label: string;
  value: number;
  color: 'blue' | 'gray' | 'yellow' | 'green';
  icon: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, color, icon }) => {
  const bgColor = {
    blue: 'bg-blue-50',
    gray: 'bg-gray-50',
    yellow: 'bg-yellow-50',
    green: 'bg-green-50',
  }[color];

  const textColor = {
    blue: 'text-blue-600',
    gray: 'text-gray-600',
    yellow: 'text-yellow-600',
    green: 'text-green-600',
  }[color];

  return (
    <div className={clsx('rounded-lg shadow p-6', bgColor)}>
      <div className="text-3xl mb-2">{icon}</div>
      <p className={clsx('text-2xl font-bold', textColor)}>{value}</p>
      <p className="text-gray-600 text-sm">{label}</p>
    </div>
  );
};

interface AdminDetailPanelProps {
  request: UploadRequest;
  onClose: () => void;
}

const AdminDetailPanel: React.FC<AdminDetailPanelProps> = ({ request, onClose }) => {
  const [activeTab, setActiveTab] = useState<'documents' | 'audit' | 'actions'>('documents');
  const [adminNote, setAdminNote] = useState('');
  const [showNotifyModal, setShowNotifyModal] = useState(false);

  const handleNotifyCustomer = async () => {
    try {
      await axios.post(
        `/api/v1/admin/approval/notify-missing-documents`,
        {
          requestId: request.id,
          message: adminNote,
          adminId: 'current-admin-id',
          sendEmailToCustomer: true,
        }
      );
      alert('Kunde wurde benachrichtigt!');
      setShowNotifyModal(false);
      setAdminNote('');
    } catch (error) {
      alert('Fehler beim Versand der Benachrichtigung');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-500 to-blue-600 text-white p-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Anfrage Details</h2>
            <p className="text-blue-100">{request.id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-2xl hover:opacity-80 transition"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b flex">
          {(['documents', 'audit', 'actions'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'flex-1 px-6 py-3 font-semibold text-center transition',
                activeTab === tab
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              )}
            >
              {tab === 'documents' && '📄 Dokumente'}
              {tab === 'audit' && '📋 Audit Log'}
              {tab === 'actions' && '⚙️ Aktionen'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'documents' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded p-4">
                <p className="text-sm text-blue-800">
                  <strong>Status:</strong> {request.status} ({request.completionPercentage}% vollständig)
                </p>
                <p className="text-sm text-red-800 mt-2">
                  {request.requiredMissing > 0
                    ? `⚠️ ${request.requiredMissing} erforderliche Dokumente fehlen`
                    : '✅ Alle erforderlichen Dokumente hochgeladen'}
                </p>
              </div>
              {/* Hier würde die Dokument-Liste angezeigt */}
            </div>
          )}

          {activeTab === 'audit' && (
            <div className="space-y-3">
              <p className="text-gray-600 text-sm">
                Audit Log wird hier angezeigt (Activity Timeline)
              </p>
            </div>
          )}

          {activeTab === 'actions' && (
            <div className="space-y-4">
              {/* Notify Customer */}
              <div className="border rounded p-4">
                <h4 className="font-bold text-gray-800 mb-3">
                  👤 Kunde benachrichtigen
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Sende Benachrichtigung über fehlende Dokumente
                </p>
                <button
                  onClick={() => setShowNotifyModal(true)}
                  className="w-full bg-blue-500 text-white px-4 py-2 rounded font-semibold hover:bg-blue-600 transition"
                >
                  Benachrichtigung senden
                </button>
              </div>

              {/* Request Additional Documents */}
              <div className="border rounded p-4">
                <h4 className="font-bold text-gray-800 mb-3">
                  📌 Zusätzliche Dokumente anfordern
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Fordern Sie optionale/zusätzliche Dokumente an
                </p>
                <button className="w-full bg-yellow-500 text-white px-4 py-2 rounded font-semibold hover:bg-yellow-600 transition">
                  Anfrage stellen
                </button>
              </div>

              {/* Approve/Reject */}
              {request.completionPercentage === 100 && (
                <div className="border rounded p-4">
                  <h4 className="font-bold text-gray-800 mb-3">
                    ✓ Einreichung genehmigen
                  </h4>
                  <p className="text-sm text-gray-600 mb-3">
                    Alle Dokumente sind vollständig
                  </p>
                  <div className="flex gap-2">
                    <button className="flex-1 bg-green-500 text-white px-4 py-2 rounded font-semibold hover:bg-green-600 transition">
                      Genehmigen ✓
                    </button>
                    <button className="flex-1 bg-red-500 text-white px-4 py-2 rounded font-semibold hover:bg-red-600 transition">
                      Ablehnen ✕
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Notify Modal */}
        {showNotifyModal && (
          <div className="border-t p-6 bg-gray-50">
            <h4 className="font-bold mb-3">Nachricht an Kunde</h4>
            <textarea
              value={adminNote}
              onChange={(e) => setAdminNote(e.target.value)}
              placeholder="Optionale Nachricht für den Kunden..."
              className="w-full border rounded p-3 mb-3"
              rows={4}
            />
            <div className="flex gap-2">
              <button
                onClick={handleNotifyCustomer}
                className="flex-1 bg-blue-500 text-white px-4 py-2 rounded font-semibold hover:bg-blue-600 transition"
              >
                Senden
              </button>
              <button
                onClick={() => setShowNotifyModal(false)}
                className="flex-1 bg-gray-300 text-gray-800 px-4 py-2 rounded font-semibold hover:bg-gray-400 transition"
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
