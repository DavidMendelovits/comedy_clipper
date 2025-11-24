import { create } from 'zustand';

export interface PhaseProgress {
  phase: string;
  percent: number;
  message?: string;
  current?: number;
  total?: number;
}

interface ProcessingStore {
  isProcessing: boolean;
  progress: number;
  currentFrame: number;
  totalFrames: number;
  currentStep: string;
  steps: string[];
  logs: string[];
  logFile?: string;
  phaseProgress?: PhaseProgress;

  setProcessing: (isProcessing: boolean) => void;
  setProgress: (progress: number) => void;
  setFrameProgress: (current: number, total: number) => void;
  setCurrentStep: (step: string) => void;
  addStep: (step: string) => void;
  addLog: (log: string) => void;
  setLogFile: (logFile: string) => void;
  setPhaseProgress: (phaseProgress: PhaseProgress) => void;
  reset: () => void;
}

export const useProcessingStore = create<ProcessingStore>((set) => ({
  isProcessing: false,
  progress: 0,
  currentFrame: 0,
  totalFrames: 0,
  currentStep: '',
  steps: [],
  logs: [],

  setProcessing: (isProcessing) => set({ isProcessing }),
  setProgress: (progress) => set({ progress }),
  setFrameProgress: (currentFrame, totalFrames) => set({ currentFrame, totalFrames }),
  setCurrentStep: (currentStep) => set({ currentStep }),
  addStep: (step) => set((state) => ({ steps: [...state.steps, step] })),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  setLogFile: (logFile) => set({ logFile }),
  setPhaseProgress: (phaseProgress) => set({ phaseProgress }),

  reset: () =>
    set({
      isProcessing: false,
      progress: 0,
      currentFrame: 0,
      totalFrames: 0,
      currentStep: '',
      steps: [],
      logs: [],
      logFile: undefined,
      phaseProgress: undefined,
    }),
}));
