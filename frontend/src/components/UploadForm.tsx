import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import clsx from 'clsx';

interface Document {
  id: string;
  type: string;
  label: string;
  category: string;
  isRequired: boolean;
  status: 'pending' | 'uploaded' | 'expired';
  uploadedFile?: {
    filename: string;
    uploadedAt: string;
  };
}

interface UploadFormProps {
  requestId: string;
  documents: Document[];
  onUploadSuccess: (documentId: string) => void;
}

export const UploadForm: React.FC<UploadFormProps> = ({
  requestId,
  documents,
  onUploadSuccess,
}) => {
  const [uploading, setUploading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleDrop = useCallback(
    async (acceptedFiles: File[], rejectedFiles: any[], docType: string) => {
      if (rejectedFiles.length > 0) {
        setError(`Datei zu groß oder ungültiges Format`);
        return;
      }

      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setUploading(docType);
      setError(null);
      setSuccess(null);

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('document_type', docType);

        const response = await axios.post(
          `/api/v1/upload-requests/${requestId}/upload`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );

        if (response.status === 200) {
          setSuccess(`${file.name} erfolgreich hochgeladen`);
          onUploadSuccess(response.data.documentId);
          setTimeout(() => setSuccess(null), 3000);
        }
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
            'Fehler beim Upload. Bitte versuchen Sie es erneut.'
        );
      } finally {
        setUploading(null);
      }
    },
    [requestId, onUploadSuccess]
  );

  // Gruppiere Dokumente nach Kategorie
  const documentsByCategory = documents.reduce(
    (acc, doc) => {
      if (!acc[doc.category]) {
        acc[doc.category] = [];
      }
      acc[doc.category].push(doc);
      return acc;
    },
    {} as Record<string, Document[]>
  );

  return (
    <div className="upload-form">
      {error && (
        <div className="alert alert-error mb-4">
          <svg className="w-5 h-5 mr-2">⚠️</svg>
          {error}
        </div>
      )}

      {success && (
        <div className="alert alert-success mb-4">
          <svg className="w-5 h-5 mr-2">✓</svg>
          {success}
        </div>
      )}

      {Object.entries(documentsByCategory).map(
        ([category, categoryDocs]) => (
          <div key={category} className="category-section mb-8">
            <h3 className="text-lg font-bold mb-4 capitalize">
              {category.replace(/_/g, ' ')}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {categoryDocs.map((doc) => (
                <DocumentUploadBox
                  key={doc.id}
                  document={doc}
                  isUploading={uploading === doc.type}
                  onDrop={(files, rejected) =>
                    handleDrop(files, rejected, doc.type)
                  }
                />
              ))}
            </div>
          </div>
        )
      )}
    </div>
  );
};

interface DocumentUploadBoxProps {
  document: Document;
  isUploading: boolean;
  onDrop: (acceptedFiles: File[], rejectedFiles: any[]) => void;
}

const DocumentUploadBox: React.FC<DocumentUploadBoxProps> = ({
  document,
  isUploading,
  onDrop,
}) => {
  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    maxSize: 50 * 1024 * 1024, // 50MB
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png'],
      'application/msword': ['.doc', '.docx'],
    },
  });

  const statusColor = {
    pending: 'border-gray-300',
    uploaded: 'border-green-500',
    expired: 'border-red-500',
  };

  return (
    <div
      {...getRootProps()}
      className={clsx(
        'border-2 border-dashed rounded-lg p-6 cursor-pointer transition',
        'hover:border-blue-500 hover:bg-blue-50',
        statusColor[document.status],
        isUploading && 'opacity-50 pointer-events-none'
      )}
    >
      <input {...getInputProps()} />

      <div className="text-center">
        <div className="text-3xl mb-2">
          {document.status === 'uploaded' && '✅'}
          {document.status === 'pending' && '📄'}
          {document.status === 'expired' && '⚠️'}
        </div>

        <h4 className="font-semibold text-sm mb-1">{document.label}</h4>

        {document.isRequired && (
          <span className="inline-block bg-red-100 text-red-800 text-xs px-2 py-1 rounded mb-2">
            Erforderlich
          </span>
        )}

        {document.status === 'uploaded' && document.uploadedFile ? (
          <div className="text-green-600 text-xs">
            <p className="font-semibold">{document.uploadedFile.filename}</p>
            <p>
              Hochgeladen am{' '}
              {new Date(document.uploadedFile.uploadedAt).toLocaleDateString(
                'de-DE'
              )}
            </p>
          </div>
        ) : (
          <div className="text-gray-600 text-xs">
            {isUploading ? (
              <p>Wird hochgeladen...</p>
            ) : (
              <>
                <p className="font-semibold">Datei hier ablegen</p>
                <p>oder klicken zum Durchsuchen</p>
              </>
            )}
          </div>
        )}
      </div>

      {isUploading && (
        <div className="mt-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-500 h-2 rounded-full animate-pulse"></div>
          </div>
        </div>
      )}
    </div>
  );
};
