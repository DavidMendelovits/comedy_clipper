import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize2, SkipBack, SkipForward } from 'lucide-react';

interface OverlayVideoPlayerProps {
  videoPath: string;
  title?: string;
  onClose?: () => void;
}

export function OverlayVideoPlayer({ videoPath, title, onClose }: OverlayVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleDurationChange = () => setDuration(video.duration);
    const handleEnded = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('ended', handleEnded);
    };
  }, []);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const newTime = parseFloat(e.target.value);
    video.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const newVolume = parseFloat(e.target.value);
    video.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) return;

    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      video.requestFullscreen();
    }
  };

  const skip = (seconds: number) => {
    const video = videoRef.current;
    if (!video) return;

    video.currentTime = Math.max(0, Math.min(duration, currentTime + seconds));
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden">
      {/* Header */}
      {title && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
          <h3 className="font-semibold text-[var(--color-text-primary)]">{title}</h3>
          {onClose && (
            <button
              onClick={onClose}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Video */}
      <div className="relative bg-black">
        <video
          ref={videoRef}
          src={videoPath}
          className="w-full h-auto max-h-[70vh]"
          onClick={togglePlay}
        />
      </div>

      {/* Controls */}
      <div className="px-4 py-3 space-y-3 bg-[var(--color-bg-tertiary)]">
        {/* Progress Bar */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--color-text-muted)] w-12 text-right">
            {formatTime(currentTime)}
          </span>
          <input
            type="range"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
            className="flex-1 h-1.5 bg-[var(--color-bg-primary)] rounded-full appearance-none cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3
              [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--color-primary)]
              [&::-moz-range-thumb]:w-3 [&::-moz-range-thumb]:h-3 [&::-moz-range-thumb]:rounded-full
              [&::-moz-range-thumb]:bg-[var(--color-primary)] [&::-moz-range-thumb]:border-0"
          />
          <span className="text-xs text-[var(--color-text-muted)] w-12">
            {formatTime(duration)}
          </span>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              className="p-2 hover:bg-[var(--color-bg-secondary)] rounded transition-colors"
            >
              {isPlaying ? (
                <Pause size={20} className="text-[var(--color-text-primary)]" />
              ) : (
                <Play size={20} className="text-[var(--color-text-primary)]" />
              )}
            </button>

            {/* Skip Back */}
            <button
              onClick={() => skip(-10)}
              className="p-2 hover:bg-[var(--color-bg-secondary)] rounded transition-colors"
              title="Skip back 10s"
            >
              <SkipBack size={18} className="text-[var(--color-text-muted)]" />
            </button>

            {/* Skip Forward */}
            <button
              onClick={() => skip(10)}
              className="p-2 hover:bg-[var(--color-bg-secondary)] rounded transition-colors"
              title="Skip forward 10s"
            >
              <SkipForward size={18} className="text-[var(--color-text-muted)]" />
            </button>

            {/* Volume */}
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={toggleMute}
                className="p-2 hover:bg-[var(--color-bg-secondary)] rounded transition-colors"
              >
                {isMuted || volume === 0 ? (
                  <VolumeX size={18} className="text-[var(--color-text-muted)]" />
                ) : (
                  <Volume2 size={18} className="text-[var(--color-text-muted)]" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-20 h-1.5 bg-[var(--color-bg-primary)] rounded-full appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-2.5 [&::-webkit-slider-thumb]:h-2.5
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--color-text-muted)]
                  [&::-moz-range-thumb]:w-2.5 [&::-moz-range-thumb]:h-2.5 [&::-moz-range-thumb]:rounded-full
                  [&::-moz-range-thumb]:bg-[var(--color-text-muted)] [&::-moz-range-thumb]:border-0"
              />
            </div>
          </div>

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-[var(--color-bg-secondary)] rounded transition-colors"
          >
            <Maximize2 size={18} className="text-[var(--color-text-muted)]" />
          </button>
        </div>
      </div>
    </div>
  );
}
