import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// Types
export interface ClipperConfig {
  clipperType: 'multimodal' | 'pose' | 'face' | 'mediapipe' | 'scene' | 'diarization'
  minDuration: number
  debug: boolean
  outputDir: string
  configFile: string
  yoloEnabled?: boolean
  personCountMethod?: 'min' | 'max' | 'average' | 'yolo' | 'yolo_zone' | 'hybrid'
  zoneCrossingEnabled?: boolean
  stageBoundary?: {
    left: number
    right: number
    top: number
    bottom: number
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
  keyframeMarkers: KeyframeMarker[]

  // UI state
  showSettings: boolean
  showLogs: boolean
  showReviewModal: boolean
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
  addKeyframeMarker: (marker: KeyframeMarker) => void
  clearKeyframeMarkers: () => void
  setShowSettings: (show: boolean) => void
  setShowLogs: (show: boolean) => void
  setShowReviewModal: (show: boolean) => void
  setToast: (toast: Toast | null) => void
  resetProcessing: () => void
}

// Default values
const defaultConfig: ClipperConfig = {
  clipperType: 'multimodal',
  minDuration: 5,
  debug: true,
  outputDir: '',
  configFile: 'clipper_rules.yaml',
  yoloEnabled: false,
  personCountMethod: 'max',
  zoneCrossingEnabled: false,
  stageBoundary: {
    left: 0.05,
    right: 0.95,
    top: 0.0,
    bottom: 0.85
  }
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
      keyframeMarkers: [],
      showSettings: false,
      showLogs: false,
      showReviewModal: false,
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

      addKeyframeMarker: (marker) => set((state) => ({
        keyframeMarkers: [...state.keyframeMarkers, marker]
      })),

      clearKeyframeMarkers: () => set({ keyframeMarkers: [] }),

      setShowSettings: (show) => set({ showSettings: show }),
      setShowLogs: (show) => set({ showLogs: show }),
      setShowReviewModal: (show) => set({ showReviewModal: show }),
      setToast: (toast) => set({ toast }),

      resetProcessing: () => set({
        processState: defaultProcessState,
        clips: [],
        detectedSegments: [],
        filteredSegments: [],
        debugFrames: [],
        keyframeMarkers: []
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
