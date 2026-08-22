import { create } from 'zustand';

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

interface UploadRequest {
  id: string;
  customerId: string;
  status: 'pending' | 'in_progress' | 'submitted' | 'complete';
  completionPercentage: number;
  documents: Document[];
  requiredMissing: number;
  optionalMissing: number;
  deadline?: string;
}

interface UploadStore {
  // State
  currentRequest: UploadRequest | null;
  documents: Document[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setCurrentRequest: (request: UploadRequest) => void;
  setDocuments: (documents: Document[]) => void;
  updateDocument: (documentId: string, updates: Partial<Document>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  resetStore: () => void;

  // Computed
  getCompletionPercentage: () => number;
  getMissingRequired: () => Document[];
  getMissingOptional: () => Document[];
  getDocumentsByCategory: (category: string) => Document[];
  isComplete: () => boolean;
}

export const useUploadStore = create<UploadStore>((set, get) => ({
  // Initial State
  currentRequest: null,
  documents: [],
  isLoading: false,
  error: null,

  // Actions
  setCurrentRequest: (request) => set({ currentRequest: request }),

  setDocuments: (documents) => set({ documents }),

  updateDocument: (documentId, updates) =>
    set((state) => ({
      documents: state.documents.map((doc) =>
        doc.id === documentId ? { ...doc, ...updates } : doc
      ),
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  resetStore: () =>
    set({
      currentRequest: null,
      documents: [],
      isLoading: false,
      error: null,
    }),

  // Computed
  getCompletionPercentage: () => {
    const { documents } = get();
    if (documents.length === 0) return 0;

    const required = documents.filter((d) => d.isRequired);
    const uploaded = required.filter((d) => d.status === 'uploaded');

    return Math.round((uploaded.length / required.length) * 100);
  },

  getMissingRequired: () => {
    const { documents } = get();
    return documents.filter((d) => d.isRequired && d.status !== 'uploaded');
  },

  getMissingOptional: () => {
    const { documents } = get();
    return documents.filter(
      (d) => !d.isRequired && d.status !== 'uploaded'
    );
  },

  getDocumentsByCategory: (category) => {
    const { documents } = get();
    return documents.filter((d) => d.category === category);
  },

  isComplete: () => {
    const { getMissingRequired } = get();
    return getMissingRequired().length === 0;
  },
}));

// Admin Store
interface AdminStats {
  totalRequests: number;
  pending: number;
  inProgress: number;
  submitted: number;
  complete: number;
}

interface AdminStore {
  stats: AdminStats | null;
  selectedRequest: UploadRequest | null;
  filter: 'all' | 'pending' | 'in_progress' | 'submitted' | 'complete';

  setStats: (stats: AdminStats) => void;
  setSelectedRequest: (request: UploadRequest | null) => void;
  setFilter: (filter: AdminStore['filter']) => void;
  resetAdmin: () => void;
}

export const useAdminStore = create<AdminStore>((set) => ({
  stats: null,
  selectedRequest: null,
  filter: 'all',

  setStats: (stats) => set({ stats }),
  setSelectedRequest: (selectedRequest) => set({ selectedRequest }),
  setFilter: (filter) => set({ filter }),
  resetAdmin: () =>
    set({
      stats: null,
      selectedRequest: null,
      filter: 'all',
    }),
}));

// Auth Store (für Rollen)
interface User {
  id: string;
  email: string;
  role: 'customer' | 'admin' | 'bank';
}

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;

  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: false,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: true,
    }),

  logout: () =>
    set({
      user: null,
      isAuthenticated: false,
    }),
}));
