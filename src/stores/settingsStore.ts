import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface ClipperConfig {
  clipperType: 'multimodal' | 'pose' | 'face' | 'mediapipe' | 'scene' | 'diarization' | 'yolo_pose';
  minDuration: number;
  maxDuration: number;
  debug: boolean;
  outputDir: string;
  configFile: string;
  exitThreshold?: number;
  exitStabilityFrames?: number;
  yoloModel?: 'yolo11n-pose.pt' | 'yolo11s-pose.pt' | 'yolo11m-pose.pt' | 'yolo11l-pose.pt' | 'yolo11x-pose.pt';
  yoloEnabled?: boolean;
  personCountMethod?: string;
  zoneCrossingEnabled?: boolean;
  stageBoundary?: {
    left?: number;
    right?: number;
    top?: number;
    bottom?: number;
  };
}

export interface OverlayConfig {
  exportFullVideo: boolean;
  includeSkeletons: boolean;
  includeBoundingBoxes: boolean;
  includeInfoOverlay: boolean;
  includeStageMarkers: boolean;
  opacity: number;
  timeRange?: { start: number; end: number };
}

interface SettingsStore {
  config: ClipperConfig;
  overlayConfig: OverlayConfig;

  setConfig: (config: Partial<ClipperConfig>) => void;
  setOverlayConfig: (config: Partial<OverlayConfig>) => void;
  resetToDefaults: () => void;
}

const defaultConfig: ClipperConfig = {
  clipperType: 'multimodal',
  minDuration: 30,
  maxDuration: 600,
  debug: true,
  outputDir: '',
  configFile: 'clipper_rules_pose_only.yaml',
  exitThreshold: 0.12,
  exitStabilityFrames: 2,
  yoloModel: 'yolo11m-pose.pt',
};

const defaultOverlayConfig: OverlayConfig = {
  exportFullVideo: true,
  includeSkeletons: true,
  includeBoundingBoxes: false,
  includeInfoOverlay: true,
  includeStageMarkers: true,
  opacity: 0.7,
};

// Custom storage that uses Electron IPC for persistence
const electronStorage = {
  getItem: async (name: string): Promise<string | null> => {
    try {
      return await window.electron?.getStorageItem(name) || null;
    } catch {
      return null;
    }
  },
  setItem: async (name: string, value: string): Promise<void> => {
    try {
      await window.electron?.setStorageItem(name, value);
    } catch (error) {
      console.error('Failed to save to storage:', error);
    }
  },
  removeItem: async (name: string): Promise<void> => {
    try {
      await window.electron?.removeStorageItem(name);
    } catch (error) {
      console.error('Failed to remove from storage:', error);
    }
  },
};

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      config: defaultConfig,
      overlayConfig: defaultOverlayConfig,

      setConfig: (configUpdate) =>
        set((state) => ({
          config: { ...state.config, ...configUpdate },
        })),

      setOverlayConfig: (configUpdate) =>
        set((state) => ({
          overlayConfig: { ...state.overlayConfig, ...configUpdate },
        })),

      resetToDefaults: () =>
        set({
          config: defaultConfig,
          overlayConfig: defaultOverlayConfig,
        }),
    }),
    {
      name: 'comedy-clipper-settings',
      storage: createJSONStorage(() => electronStorage),
    }
  )
);
