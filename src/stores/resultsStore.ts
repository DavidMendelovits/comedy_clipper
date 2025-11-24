import { create } from 'zustand';

export interface VideoSegment {
  start: number;
  end: number;
}

export interface Clip {
  name: string;
  path: string;
  size?: number;
  modified?: Date;
}

export interface KeyframeMarker {
  frameNumber: number;
  timestamp: number;
  type: 'transition' | 'segment_start' | 'segment_end';
}

interface ResultsStore {
  clips: Clip[];
  detectedSegments: VideoSegment[];
  filteredSegments: VideoSegment[];
  debugFrames: any[];
  debugVideos: string[];
  keyframeMarkers: KeyframeMarker[];

  setClips: (clips: Clip[]) => void;
  addClip: (clip: Clip) => void;
  setDetectedSegments: (segments: VideoSegment[]) => void;
  setFilteredSegments: (segments: VideoSegment[]) => void;
  setDebugFrames: (frames: any[]) => void;
  setDebugVideos: (videos: string[]) => void;
  addKeyframeMarker: (marker: KeyframeMarker) => void;
  clearKeyframeMarkers: () => void;
  reset: () => void;
}

export const useResultsStore = create<ResultsStore>((set) => ({
  clips: [],
  detectedSegments: [],
  filteredSegments: [],
  debugFrames: [],
  debugVideos: [],
  keyframeMarkers: [],

  setClips: (clips) => set({ clips }),
  addClip: (clip) => set((state) => ({ clips: [...state.clips, clip] })),
  setDetectedSegments: (detectedSegments) => set({ detectedSegments }),
  setFilteredSegments: (filteredSegments) => set({ filteredSegments }),
  setDebugFrames: (debugFrames) => set({ debugFrames }),
  setDebugVideos: (debugVideos) => set({ debugVideos }),
  addKeyframeMarker: (marker) =>
    set((state) => ({ keyframeMarkers: [...state.keyframeMarkers, marker] })),
  clearKeyframeMarkers: () => set({ keyframeMarkers: [] }),

  reset: () =>
    set({
      clips: [],
      detectedSegments: [],
      filteredSegments: [],
      debugFrames: [],
      debugVideos: [],
      keyframeMarkers: [],
    }),
}));
