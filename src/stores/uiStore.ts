import { create } from 'zustand';
import type { TabType } from '../components/TabLayout';

export interface Toast {
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

interface UIStore {
  activeTab: TabType;
  showSettings: boolean;
  showLogs: boolean;
  showReviewModal: boolean;
  showDebugFrameViewer: boolean;
  toast: Toast | null;

  setActiveTab: (tab: TabType) => void;
  setShowSettings: (show: boolean) => void;
  setShowLogs: (show: boolean) => void;
  setShowReviewModal: (show: boolean) => void;
  setShowDebugFrameViewer: (show: boolean) => void;
  showToast: (message: string, type: Toast['type']) => void;
  clearToast: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  activeTab: 'process',
  showSettings: false,
  showLogs: false,
  showReviewModal: false,
  showDebugFrameViewer: false,
  toast: null,

  setActiveTab: (activeTab) => set({ activeTab }),
  setShowSettings: (showSettings) => set({ showSettings }),
  setShowLogs: (showLogs) => set({ showLogs }),
  setShowReviewModal: (showReviewModal) => set({ showReviewModal }),
  setShowDebugFrameViewer: (showDebugFrameViewer) => set({ showDebugFrameViewer }),
  showToast: (message, type) => set({ toast: { message, type } }),
  clearToast: () => set({ toast: null }),
}));
