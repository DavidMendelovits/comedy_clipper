import { create } from 'zustand';

interface VideoStore {
  selectedVideo: string | null;
  duration: number;
  playing: boolean;

  setVideo: (path: string | null, duration?: number) => void;
  setDuration: (duration: number) => void;
  setPlaying: (playing: boolean) => void;
  reset: () => void;
}

export const useVideoStore = create<VideoStore>((set) => ({
  selectedVideo: null,
  duration: 0,
  playing: false,

  setVideo: (path, duration = 0) => set({ selectedVideo: path, duration }),
  setDuration: (duration) => set({ duration }),
  setPlaying: (playing) => set({ playing }),
  reset: () => set({ selectedVideo: null, duration: 0, playing: false }),
}));
