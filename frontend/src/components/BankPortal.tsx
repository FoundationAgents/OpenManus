import React, { useState } from 'react';
import axios from 'axios';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';

interface Document {
  id: string;
  type: string;
  label: string;
  status: 'uploaded';
  uploadedAt: string;
}

interface BankUploadRequest {
  id: string;
  status: string;
  completionPercentage: number;
  documents: Document[];
  readyForSubmission: boolean;
}

interface BankPortalProps {
  requestId: string;
  bankApiKey: string;
}

export const BankPortal: React.FC<BankPortalProps> = ({ requestId, bankApiKey }) => {
  const [downloading, setDownloading] = useState(false);

  // Upload-Request abrufen
  const { data: uploadRequest, isLoading } = useQuery({
    queryKey: ['bank-upload-request', requestId],
    queryFn: async () => {
      const response = await axios.get<BankUploadRequest>(
        `/api/v1/bank/upload-requests/${requestId}`,
        {
          headers: {
            'X-Bank-API-Key': bankApiKey,
          },
        }
      );
      return response.data;
    },
  });

  const handleDownloadZip = async () => {
    try {
      setDownloading(true);
      const response = await axios.post(
        `/api/v1/bank/export-documents/${requestId}`,
        {},
        {
          headers: {
            'X-Bank-API-Key': bankApiKey,
          },
          responseType: 'blob',
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `unterlagen_${requestId}.zip`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (error) {
      alert('Fehler beim Download');
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">Laden...</div>;
  }

  if (!uploadRequest) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-6 text-center">
        <p className="text-red-800 font-semibold">
          Upload-Anfrage nicht gefunden
        </p>
      </div>
    );
  }

  return (
    <div className="bank-portal space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg shadow p-6">
        <h1 className="text-3xl font-bold mb-2">🏦 Bank-Portal</h1>
        <p className="text-purple-100">
          Einsicht in Finanzierungsunterlagen
        </p>
      </div>

      {/* Status Overview */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-gray-600 text-sm font-semibold">Status</p>
            <p className="text-2xl font-bold text-gray-800 mt-1">
              {uploadRequest.status}
            </p>
          </div>

          <div>
            <p className="text-gray-600 text-sm font-semibold">Vollständigkeit</p>
            <div className="mt-2">
              <p className="text-2xl font-bold text-blue-600">
                {uploadRequest.completionPercentage}%
              </p>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{
                    width: `${uploadRequest.completionPercentage}%`,
                  }}
                ></div>
              </div>
            </div>
          </div>

          <div>
            <p className="text-gray-600 text-sm font-semibold">Bereitschaft</p>
            {uploadRequest.readyForSubmission ? (
              <div className="mt-2">
                <span className="inline-block bg-green-100 text-green-800 px-3 py-1 rounded-full font-semibold">
                  ✅ Bereit zur Einreichung
                </span>
              </div>
            ) : (
              <div className="mt-2">
                <span className="inline-block bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full font-semibold">
                  ⏳ Noch nicht vollständig
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Documents Overview */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b px-6 py-4">
          <h2 className="text-xl font-bold text-gray-800">
            📄 Hochgeladene Unterlagen
          </h2>
        </div>

        <div className="divide-y">
          {uploadRequest.documents.length > 0 ? (
            uploadRequest.documents.map((doc) => (
              <DocumentRow key={doc.id} document={doc} />
            ))
          ) : (
            <div className="px-6 py-4 text-gray-500 text-center">
              Keine Unterlagen hochgeladen
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-col gap-3">
          <button
            onClick={handleDownloadZip}
            disabled={downloadingdisabled || uploadRequest.documents.length === 0}
            className={clsx(
              'w-full px-6 py-3 rounded font-semibold transition flex items-center justify-center gap-2',
              downloadng
                ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                : uploadRequest.documents.length > 0
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-300 text-gray-600 cursor-not-allowed'
            )}
          >
            {downloading ? '⏳ Wird heruntergeladen...' : '⬇️ Alle Unterlagen herunterladen (ZIP)'}
          </button>

          <p className="text-xs text-gray-600 text-center">
            Alle Dokumente werden als ZIP-Datei mit strukturierten Ordnern
            heruntergeladen
          </p>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded p-6">
        <h3 className="font-bold text-blue-900 mb-2">ℹ️ Hinweise</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>
            • Sie haben <strong>Lesezugriff</strong> auf alle hochgeladenen
            Unterlagen
          </li>
          <li>
            • Dokumente können nicht direkt hochgeladen oder gelöscht werden
          </li>
          <li>
            • Alle Unterlagen sind verschlüsselt und sicher gespeichert
          </li>
          <li>
            • Kontaktieren Sie den Kunden für fehlende Unterlagen
          </li>
        </ul>
      </div>
    </div>
  );
};

interface DocumentRowProps {
  document: Document;
}

const DocumentRow: React.FC<DocumentRowProps> = ({ document }) => {
  return (
    <div className="px-6 py-4 hover:bg-gray-50 transition">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <span className="text-2xl">📄</span>
          <div>
            <p className="font-semibold text-gray-800">{document.label}</p>
            <p className="text-xs text-gray-500 mt-1">
              {document.type} •{' '}
              {new Date(document.uploadedAt).toLocaleDateString('de-DE')}
            </p>
          </div>
        </div>

        <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
          ✅ Vorhanden
        </span>
      </div>
    </div>
  );
};
