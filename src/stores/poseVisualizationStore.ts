/**
 * Pose Visualization Store
 * Manages pose events, video playback state, and visualization data
 */

import { create } from 'zustand'

export interface PoseEvent {
  id: string
  jobId: string
  timestamp: number
  eventType: 'enter' | 'exit'
  personId: number
  confidence: number
  bbox: [number, number, number, number] // [x1, y1, x2, y2]
  keypoints: Array<[number, number, number]> // [x, y, confidence]
}

interface PoseVisualizationState {
  // Pose events
  events: PoseEvent[]
  eventsLoading: boolean

  // Video playback
  currentTime: number
  duration: number
  isPlaying: boolean

  // Visualization settings
  showSkeleton: boolean
  showBoundingBoxes: boolean
  showEventMarkers: boolean

  // Current frame pose data
  currentPoses: Array<{
    personId: number
    bbox: [number, number, number, number]
    keypoints: Array<[number, number, number]>
  }>

  // Video element reference (for seeking)
  videoElement: HTMLVideoElement | null

  // Pending seek time (applied when video becomes ready)
  pendingSeekTime: number | null

  // Pose metadata cache (frame-by-frame data)
  poseMetadataCache: Record<number, any> | null
  cacheLoading: boolean

  // Actions
  loadPoseEvents: (jobId: string) => Promise<void>
  loadPoseMetadataCache: (jobId: string) => Promise<void>
  setCurrentTime: (time: number) => void
  setDuration: (duration: number) => void
  setIsPlaying: (playing: boolean) => void
  seekToTime: (time: number) => void
  seekToEvent: (eventIndex: number) => void
  setVideoElement: (element: HTMLVideoElement | null) => void
  applyPendingSeek: () => void
  toggleSkeleton: () => void
  toggleBoundingBoxes: () => void
  toggleEventMarkers: () => void

  // Selectors
  getEventsAtTime: (time: number, threshold?: number) => PoseEvent[]
  getEventsByType: (type: 'enter' | 'exit') => PoseEvent[]
  getNextEvent: (fromTime: number) => PoseEvent | null
  getPreviousEvent: (fromTime: number) => PoseEvent | null
}

export const usePoseVisualizationStore = create<PoseVisualizationState>((set, get) => ({
  // Initial state
  events: [],
  eventsLoading: false,
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  showSkeleton: true,
  showBoundingBoxes: true,
  showEventMarkers: true,
  currentPoses: [],
  videoElement: null,
  pendingSeekTime: null,
  poseMetadataCache: null,
  cacheLoading: false,

  // Load pose events from backend
  loadPoseEvents: async (jobId: string) => {
    set({ eventsLoading: true })

    try {
      const events = await window.electron.getPoseEvents(jobId)

      set({
        events: events || [],
        eventsLoading: false
      })

      console.log(`Loaded ${events?.length || 0} pose events`)
    } catch (error) {
      console.error('Error loading pose events:', error)
      set({ eventsLoading: false })
    }
  },

  // Load pose metadata cache for continuous visualization
  loadPoseMetadataCache: async (jobId: string) => {
    set({ cacheLoading: true })

    try {
      const cache = await window.electron.getPoseMetadataCache(jobId)

      set({
        poseMetadataCache: cache,
        cacheLoading: false
      })

      if (cache) {
        console.log(`Loaded pose metadata cache: ${Object.keys(cache).length} timestamps`)
      } else {
        console.log('No pose metadata cache available')
      }
    } catch (error) {
      console.error('Error loading pose metadata cache:', error)
      set({ cacheLoading: false, poseMetadataCache: null })
    }
  },

  // Update current playback time
  setCurrentTime: (time: number) => {
    set({ currentTime: time })

    // Try to use pose metadata cache for continuous visualization
    const cache = get().poseMetadataCache
    if (cache) {
      // Find closest cached timestamp
      const timestamps = Object.keys(cache).map(Number).sort((a, b) => Math.abs(a - time) - Math.abs(b - time))
      const closestTime = timestamps[0]

      // Use cache data if within 1 second (accounts for sample rate)
      if (closestTime !== undefined && Math.abs(closestTime - time) < 1.0) {
        const framePoses = cache[closestTime]?.detections || []

        // Convert cache format to currentPoses format
        const currentPoses = framePoses.map((detection: any) => ({
          personId: detection.person_id,
          bbox: detection.bbox,
          keypoints: detection.keypoints || []
        }))

        set({ currentPoses })
        return
      }
    }

    // Fallback: Use events if cache not available or no nearby timestamp
    const events = get().getEventsAtTime(time, 0.5)
    const currentPoses = events
      .filter(e => e.eventType === 'enter')
      .map(e => ({
        personId: e.personId,
        bbox: e.bbox,
        keypoints: e.keypoints
      }))

    set({ currentPoses })
  },

  setDuration: (duration: number) => {
    set({ duration })
  },

  setIsPlaying: (playing: boolean) => {
    set({ isPlaying: playing })
  },

  // Set video element reference
  setVideoElement: (element: HTMLVideoElement | null) => {
    set({ videoElement: element })
    // Apply any pending seek when video element becomes available
    if (element) {
      get().applyPendingSeek()
    }
  },

  // Apply pending seek if video is ready
  applyPendingSeek: () => {
    const { videoElement, pendingSeekTime } = get()
    if (!videoElement || pendingSeekTime === null) {
      return
    }

    // Check if element is still in DOM (stale reference check)
    if (!videoElement.isConnected) {
      console.warn('[applyPendingSeek] Video element disconnected from DOM')
      set({ videoElement: null })
      return
    }

    // Check if video is ready to seek (readyState >= HAVE_METADATA)
    if (videoElement.readyState >= 1) {
      try {
        videoElement.currentTime = pendingSeekTime
        set({ pendingSeekTime: null })
        console.log('[applyPendingSeek] Applied pending seek to', pendingSeekTime)
      } catch (error) {
        console.error('[applyPendingSeek] Failed to seek:', error)
      }
    }
  },

  // Seek to a specific time (updates both store and video element)
  seekToTime: (time: number) => {
    const videoElement = get().videoElement

    // Always update pose visualization immediately
    get().setCurrentTime(time)

    if (!videoElement) {
      // No video element yet, store pending seek
      set({ pendingSeekTime: time })
      console.log('[seekToTime] No video element, storing pending seek to', time)
      return
    }

    // Check if element is still in DOM (stale reference check)
    if (!videoElement.isConnected) {
      console.warn('[seekToTime] Video element disconnected from DOM, clearing reference')
      set({ videoElement: null, pendingSeekTime: time })
      return
    }

    // Check if video is ready to seek (readyState >= HAVE_METADATA)
    if (videoElement.readyState >= 1) {
      try {
        videoElement.currentTime = time
        set({ pendingSeekTime: null })
      } catch (error) {
        console.error('[seekToTime] Failed to seek:', error)
        set({ pendingSeekTime: time })
      }
    } else {
      // Video not ready, store pending seek
      set({ pendingSeekTime: time })
      console.log('[seekToTime] Video not ready (readyState:', videoElement.readyState, '), storing pending seek to', time)
    }
  },

  // Seek to a specific event
  seekToEvent: (eventIndex: number) => {
    const events = get().events
    if (eventIndex >= 0 && eventIndex < events.length) {
      const event = events[eventIndex]
      get().seekToTime(event.timestamp)
    }
  },

  // Toggle visualization options
  toggleSkeleton: () => {
    set((state) => ({ showSkeleton: !state.showSkeleton }))
  },

  toggleBoundingBoxes: () => {
    set((state) => ({ showBoundingBoxes: !state.showBoundingBoxes }))
  },

  toggleEventMarkers: () => {
    set((state) => ({ showEventMarkers: !state.showEventMarkers }))
  },

  // Get events near a specific time
  getEventsAtTime: (time: number, threshold: number = 0.5) => {
    const events = get().events
    return events.filter(
      (e) => Math.abs(e.timestamp - time) <= threshold
    )
  },

  // Get events by type
  getEventsByType: (type: 'enter' | 'exit') => {
    return get().events.filter((e) => e.eventType === type)
  },

  // Get next event from a given time
  getNextEvent: (fromTime: number) => {
    const events = get().events
    const nextEvents = events.filter((e) => e.timestamp > fromTime)
    return nextEvents.length > 0 ? nextEvents[0] : null
  },

  // Get previous event from a given time
  getPreviousEvent: (fromTime: number) => {
    const events = get().events
    const prevEvents = events.filter((e) => e.timestamp < fromTime)
    return prevEvents.length > 0 ? prevEvents[prevEvents.length - 1] : null
  },
}))

// COCO keypoint skeleton connections
export const POSE_SKELETON = [
  [0, 1], [0, 2], [1, 3], [2, 4],  // Head
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],  // Arms
  [5, 11], [6, 12], [11, 12],  // Torso
  [11, 13], [13, 15], [12, 14], [14, 16]  // Legs
]

// COCO keypoint names (for reference)
export const KEYPOINT_NAMES = [
  'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
  'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
  'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]
