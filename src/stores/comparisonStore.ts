import { create } from 'zustand';

export interface ModelResult {
  modelId: string;
  stats?: {
    detectionRate?: number;
    avgFps?: number;
    totalTime?: number;
    framesDetected?: number;
    totalFrames?: number;
  };
  outputFile?: string;
  overlayVideo?: string;
  clips?: string[];
  segments?: Array<{ start: number; end: number }>;
  debugFrames?: any[];
  error?: string;
}

interface ComparisonStore {
  isRunning: boolean;
  selectedModels: string[];
  modelProgress: Record<string, number>;
  modelResults: Record<string, ModelResult>;
  overlayVideos: Record<string, string>;

  setRunning: (isRunning: boolean) => void;
  toggleModel: (modelId: string) => void;
  setSelectedModels: (models: string[]) => void;
  setModelProgress: (modelId: string, progress: number) => void;
  setModelResult: (modelId: string, result: ModelResult) => void;
  setOverlayVideo: (modelId: string, videoPath: string) => void;
  reset: () => void;
}

export const useComparisonStore = create<ComparisonStore>((set) => ({
  isRunning: false,
  selectedModels: [],
  modelProgress: {},
  modelResults: {},
  overlayVideos: {},

  setRunning: (isRunning) => set({ isRunning }),

  toggleModel: (modelId) =>
    set((state) => ({
      selectedModels: state.selectedModels.includes(modelId)
        ? state.selectedModels.filter((id) => id !== modelId)
        : [...state.selectedModels, modelId],
    })),

  setSelectedModels: (selectedModels) => set({ selectedModels }),

  setModelProgress: (modelId, progress) =>
    set((state) => ({
      modelProgress: { ...state.modelProgress, [modelId]: progress },
    })),

  setModelResult: (modelId, result) =>
    set((state) => ({
      modelResults: { ...state.modelResults, [modelId]: result },
    })),

  setOverlayVideo: (modelId, videoPath) =>
    set((state) => ({
      overlayVideos: { ...state.overlayVideos, [modelId]: videoPath },
    })),

  reset: () =>
    set({
      isRunning: false,
      selectedModels: [],
      modelProgress: {},
      modelResults: {},
      overlayVideos: {},
    }),
}));
