import React from 'react';
import clsx from 'clsx';

interface Document {
  id: string;
  type: string;
  label: string;
  category: string;
  isRequired: boolean;
  status: 'pending' | 'uploaded' | 'expired' | 'missing';
}

interface DocumentChecklistProps {
  documents: Document[];
  completionPercentage: number;
  requiredMissing: number;
  optionalMissing: number;
}

export const DocumentChecklist: React.FC<DocumentChecklistProps> = ({
  documents,
  completionPercentage,
  requiredMissing,
  optionalMissing,
}) => {
  const categories = [...new Set(documents.map((d) => d.category))];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploaded':
        return '✅';
      case 'expired':
        return '⚠️';
      case 'pending':
        return '⏳';
      default:
        return '❌';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'uploaded':
        return 'text-green-600';
      case 'expired':
        return 'text-orange-600';
      case 'pending':
        return 'text-yellow-600';
      default:
        return 'text-red-600';
    }
  };

  return (
    <div className="document-checklist space-y-6">
      {/* Progress Bar */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-bold">Fortschritt</h3>
          <span className="text-2xl font-bold text-blue-600">
            {completionPercentage}%
          </span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className="bg-gradient-to-r from-blue-500 to-blue-600 h-4 rounded-full transition-all duration-500"
            style={{ width: `${completionPercentage}%` }}
          ></div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-blue-50 rounded">
            <p className="text-2xl font-bold text-blue-600">
              {documents.filter((d) => d.status === 'uploaded').length}
            </p>
            <p className="text-sm text-gray-600">Hochgeladen</p>
          </div>

          <div className="text-center p-3 bg-red-50 rounded">
            <p className="text-2xl font-bold text-red-600">
              {requiredMissing}
            </p>
            <p className="text-sm text-gray-600">Noch erforderlich</p>
          </div>
        </div>
      </div>

      {/* Status Messages */}
      {requiredMissing > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-semibold">
            ⚠️ {requiredMissing} erforderliche Dokumente fehlen noch
          </p>
          <p className="text-red-600 text-sm mt-1">
            Bitte laden Sie diese Dokumente hoch, um Ihre Anfrage zu
            vervollständigen.
          </p>
        </div>
      )}

      {requiredMissing === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-800 font-semibold">
            ✅ Alle erforderlichen Dokumente hochgeladen!
          </p>
          <p className="text-green-600 text-sm mt-1">
            Ihre Anfrage ist nun vollständig und wird bald bearbeitet.
          </p>
        </div>
      )}

      {optionalMissing > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800 font-semibold">
            💡 {optionalMissing} optionale Dokumente empfohlen
          </p>
          <p className="text-yellow-600 text-sm mt-1">
            Diese könnten die Bearbeitung beschleunigen.
          </p>
        </div>
      )}

      {/* Categories */}
      {categories.map((category) => {
        const categoryDocs = documents.filter((d) => d.category === category);
        const uploadedCount = categoryDocs.filter(
          (d) => d.status === 'uploaded'
        ).length;

        return (
          <div key={category} className="bg-white rounded-lg shadow">
            <div className="border-b px-6 py-4">
              <div className="flex justify-between items-center">
                <h4 className="font-bold text-gray-800 capitalize">
                  {category.replace(/_/g, ' ')}
                </h4>
                <span className="text-sm font-semibold text-blue-600">
                  {uploadedCount}/{categoryDocs.length}
                </span>
              </div>

              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{
                    width: `${(uploadedCount / categoryDocs.length) * 100}%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="divide-y">
              {categoryDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="px-6 py-3 hover:bg-gray-50 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      <span className="text-xl">
                        {getStatusIcon(doc.status)}
                      </span>

                      <div className="flex-1">
                        <p className="font-medium text-gray-800">
                          {doc.label}
                        </p>

                        {doc.status === 'expired' && (
                          <p className="text-xs text-orange-600 mt-1">
                            ⚠️ Dieses Dokument ist abgelaufen und muss erneut
                            hochgeladen werden
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {doc.isRequired && (
                        <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded">
                          Pflicht
                        </span>
                      )}

                      <span
                        className={clsx(
                          'text-sm font-semibold capitalize',
                          getStatusColor(doc.status)
                        )}
                      >
                        {doc.status === 'uploaded' && 'Hochgeladen'}
                        {doc.status === 'pending' && 'Ausstehend'}
                        {doc.status === 'expired' && 'Abgelaufen'}
                        {doc.status === 'missing' && 'Fehlt'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};
