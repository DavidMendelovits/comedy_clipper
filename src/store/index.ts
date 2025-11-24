import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// Types
export interface ClipperConfig {
  clipperType: 'multimodal' | 'pose' | 'face' | 'mediapipe' | 'scene' | 'diarization' | 'yolo_pose'
  minDuration: number
  maxDuration: number
  debug: boolean
  outputDir: string
  configFile: string
  // Position-based detection settings
  exitThreshold?: number
  exitStabilityFrames?: number
  // YOLO-specific settings
  yoloModel?: 'yolo11n-pose.pt' | 'yolo11s-pose.pt' | 'yolo11m-pose.pt' | 'yolo11l-pose.pt' | 'yolo11x-pose.pt'
  // Legacy settings (for SettingsModal compatibility)
  yoloEnabled?: boolean
  personCountMethod?: string
  zoneCrossingEnabled?: boolean
  stageBoundary?: {
    left?: number
    right?: number
    top?: number
    bottom?: number
  }
}

export interface PhaseProgress {
  phase: string
  percent: number
  message?: string
  current?: number
  total?: number
}

export interface ProcessState {
  running: boolean
  progress: number
  currentFrame: number
  totalFrames: number
  output: string[]
  steps: string[]
  currentStep: string
  logFile?: string
  phaseProgress?: PhaseProgress
}

export interface VideoSegment {
  start: number
  end: number
}

export interface Clip {
  name: string
  path: string
  size?: number
  modified?: Date
}

export interface KeyframeMarker {
  frameNumber: number
  timestamp: number
  type: 'transition' | 'segment_start' | 'segment_end'
}

export interface Toast {
  message: string
  type: 'success' | 'error' | 'info'
}

export interface ModelComparisonState {
  running: boolean
  selectedModels: string[]
  results: Record<string, any>
}

// Store interface
interface AppState {
  // Video state
  selectedVideo: string | null
  videoDuration: number
  videoPlaying: boolean

  // Config
  config: ClipperConfig

  // Process state
  processState: ProcessState

  // Results
  clips: Clip[]
  detectedSegments: VideoSegment[]
  filteredSegments: VideoSegment[]
  debugFrames: any[]
  debugVideos: string[]
  keyframeMarkers: KeyframeMarker[]

  // Model comparison
  modelComparison: ModelComparisonState

  // UI state
  showSettings: boolean
  showLogs: boolean
  showReviewModal: boolean
  showModelComparison: boolean
  showDebugFrameViewer: boolean
  toast: Toast | null

  // Actions
  setSelectedVideo: (path: string | null) => void
  setVideoDuration: (duration: number) => void
  setVideoPlaying: (playing: boolean) => void
  setConfig: (config: Partial<ClipperConfig>) => void
  setProcessState: (state: Partial<ProcessState>) => void
  setClips: (clips: Clip[]) => void
  setDetectedSegments: (segments: VideoSegment[]) => void
  setFilteredSegments: (segments: VideoSegment[]) => void
  setDebugFrames: (frames: any[]) => void
  setDebugVideos: (videos: string[]) => void
  addKeyframeMarker: (marker: KeyframeMarker) => void
  clearKeyframeMarkers: () => void
  setModelComparison: (state: Partial<ModelComparisonState>) => void
  setShowSettings: (show: boolean) => void
  setShowLogs: (show: boolean) => void
  setShowReviewModal: (show: boolean) => void
  setShowModelComparison: (show: boolean) => void
  setShowDebugFrameViewer: (show: boolean) => void
  setToast: (toast: Toast | null) => void
  resetProcessing: () => void
}

// Default values
const defaultConfig: ClipperConfig = {
  clipperType: 'multimodal',
  minDuration: 30,
  maxDuration: 600,
  debug: true,
  outputDir: '',
  configFile: 'clipper_rules_pose_only.yaml',
  exitThreshold: 0.12,
  exitStabilityFrames: 2,
  yoloModel: 'yolo11m-pose.pt' // Default to medium model for balanced performance
}

const defaultProcessState: ProcessState = {
  running: false,
  progress: 0,
  currentFrame: 0,
  totalFrames: 0,
  output: [],
  steps: [],
  currentStep: ''
}

// Custom storage that uses Electron IPC for persistence
const electronStorage = {
  getItem: async (name: string): Promise<string | null> => {
    try {
      return await window.electron?.getStorageItem(name) || null
    } catch {
      return null
    }
  },
  setItem: async (name: string, value: string): Promise<void> => {
    try {
      await window.electron?.setStorageItem(name, value)
    } catch (error) {
      console.error('Failed to save to storage:', error)
    }
  },
  removeItem: async (name: string): Promise<void> => {
    try {
      await window.electron?.removeStorageItem(name)
    } catch (error) {
      console.error('Failed to remove from storage:', error)
    }
  }
}

// Create store with persistence
export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Initial state
      selectedVideo: null,
      videoDuration: 0,
      videoPlaying: false,
      config: defaultConfig,
      processState: defaultProcessState,
      clips: [],
      detectedSegments: [],
      filteredSegments: [],
      debugFrames: [],
      debugVideos: [],
      keyframeMarkers: [],
      modelComparison: {
        running: false,
        selectedModels: [],
        results: {}
      },
      showSettings: false,
      showLogs: false,
      showReviewModal: false,
      showModelComparison: false,
      showDebugFrameViewer: false,
      toast: null,

      // Actions
      setSelectedVideo: (path) => set({ selectedVideo: path }),
      setVideoDuration: (duration) => set({ videoDuration: duration }),
      setVideoPlaying: (playing) => set({ videoPlaying: playing }),

      setConfig: (configUpdate) => set((state) => ({
        config: { ...state.config, ...configUpdate }
      })),

      setProcessState: (stateUpdate) => set((state) => ({
        processState: { ...state.processState, ...stateUpdate }
      })),

      setClips: (clips) => set({ clips }),
      setDetectedSegments: (segments) => set({ detectedSegments: segments }),
      setFilteredSegments: (segments) => set({ filteredSegments: segments }),
      setDebugFrames: (frames) => set({ debugFrames: frames }),
      setDebugVideos: (videos) => set({ debugVideos: videos }),

      addKeyframeMarker: (marker) => set((state) => ({
        keyframeMarkers: [...state.keyframeMarkers, marker]
      })),

      clearKeyframeMarkers: () => set({ keyframeMarkers: [] }),

      setModelComparison: (comparisonUpdate) => set((state) => ({
        modelComparison: { ...state.modelComparison, ...comparisonUpdate }
      })),

      setShowSettings: (show) => set({ showSettings: show }),
      setShowLogs: (show) => set({ showLogs: show }),
      setShowReviewModal: (show) => set({ showReviewModal: show }),
      setShowModelComparison: (show) => set({ showModelComparison: show }),
      setShowDebugFrameViewer: (show) => set({ showDebugFrameViewer: show }),
      setToast: (toast) => set({ toast }),

      resetProcessing: () => set({
        processState: defaultProcessState,
        clips: [],
        detectedSegments: [],
        filteredSegments: [],
        debugFrames: [],
        debugVideos: [],
        keyframeMarkers: [],
        modelComparison: {
          running: false,
          selectedModels: [],
          results: {}
        }
      })
    }),
    {
      name: 'comedy-clipper-storage',
      storage: createJSONStorage(() => electronStorage),
      partialize: (state) => ({
        // Only persist these fields
        config: state.config,
        selectedVideo: state.selectedVideo
      })
    }
  )
)
