import { Video, Play, Scissors } from 'lucide-react'
import { useRef, useState, useEffect } from 'react'
import type { KeyframeMarker } from '../store'

interface VideoSegment {
  start: number
  end: number
}

interface VideoPreviewProps {
  videoPath: string
  onStartProcessing: () => void
  isProcessing: boolean
  segments?: VideoSegment[]
  keyframeMarkers?: KeyframeMarker[]
  onDurationChange?: (duration: number) => void
  onReviewSegments?: () => void
}

const VideoPreview: React.FC<VideoPreviewProps> = ({
  videoPath,
  onStartProcessing,
  isProcessing,
  segments = [],
  keyframeMarkers = [],
  onDurationChange,
  onReviewSegments
}) => {
  // Get the proper video URL using Electron's custom protocol
  const videoUrl = (window as any).electron?.getLocalFileUrl(videoPath) || videoPath
  const videoRef = useRef<HTMLVideoElement>(null)
  const progressBarRef = useRef<HTMLDivElement>(null)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  // Pause video when processing starts
  useEffect(() => {
    if (isProcessing && videoRef.current) {
      videoRef.current.pause()
      setIsPlaying(false)
    }
  }, [isProcessing])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleLoadedMetadata = () => {
      const dur = video.duration
      setDuration(dur)
      if (onDurationChange) {
        onDurationChange(dur)
      }
    }

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime)
    }

    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)

    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('play', handlePlay)
    video.addEventListener('pause', handlePause)

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('play', handlePlay)
      video.removeEventListener('pause', handlePause)
    }
  }, [videoUrl])

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const video = videoRef.current
    const progressBar = progressBarRef.current
    if (!video || !progressBar) return

    const rect = progressBar.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const percentage = clickX / rect.width
    video.currentTime = percentage * duration
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-900 overflow-hidden">
      <div className="flex items-center justify-between p-6 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-600 rounded-lg">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold">Video Preview</h2>
            <p className="text-sm text-slate-400">{videoPath.split('/').pop()}</p>
            {segments.length > 0 && (
              <p className="text-xs text-primary-400 mt-1">
                {segments.length} segment{segments.length !== 1 ? 's' : ''} detected
              </p>
            )}
          </div>
        </div>

        <button
          onClick={onStartProcessing}
          disabled={isProcessing}
          className="flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg font-medium transition-colors"
        >
          <Play className="w-5 h-5" />
          <span>{isProcessing ? 'Processing...' : 'Start Clipping'}</span>
        </button>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-black">
        <video
          ref={videoRef}
          key={videoUrl}
          src={videoUrl}
          controls={false}
          className="max-w-full max-h-full rounded-lg shadow-2xl"
          style={{ maxHeight: 'calc(100vh - 300px)' }}
        />

        {/* Custom video controls with segment markers */}
        <div className="w-full max-w-4xl mt-6 space-y-3">
          {/* Progress bar with markers */}
          <div className="relative">
            <div
              ref={progressBarRef}
              onClick={handleProgressClick}
              className="h-2 bg-slate-700 rounded-full cursor-pointer hover:h-3 transition-all relative"
            >
              {/* Current progress */}
              <div
                className="absolute top-0 left-0 h-full bg-primary-500 rounded-full"
                style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
              />

              {/* Keyframe markers (shown during processing) */}
              {keyframeMarkers.map((marker, index) => {
                const percent = duration ? (marker.timestamp / duration) * 100 : 0
                const markerColor = marker.type === 'transition' ? 'bg-yellow-400' :
                                   marker.type === 'segment_start' ? 'bg-green-400' : 'bg-red-400'

                return (
                  <div
                    key={`keyframe-${index}`}
                    className={`absolute top-0 w-1 h-full ${markerColor} opacity-75`}
                    style={{ left: `${percent}%` }}
                    title={`${marker.type} at ${marker.timestamp.toFixed(1)}s (frame ${marker.frameNumber})`}
                  />
                )
              })}

              {/* Segment markers (shown after processing) */}
              {segments.map((segment, index) => {
                const startPercent = duration ? (segment.start / duration) * 100 : 0
                const widthPercent = duration ? ((segment.end - segment.start) / duration) * 100 : 0

                return (
                  <div
                    key={index}
                    className="absolute top-0 h-full bg-green-500/40 hover:bg-green-500/60 transition-colors border-l-2 border-r-2 border-green-400"
                    style={{
                      left: `${startPercent}%`,
                      width: `${widthPercent}%`,
                    }}
                    title={`Segment ${index + 1}: ${segment.start.toFixed(1)}s - ${segment.end.toFixed(1)}s`}
                  />
                )
              })}
            </div>

            {/* Time display */}
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Play controls */}
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => videoRef.current && (videoRef.current.currentTime -= 10)}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
            >
              -10s
            </button>
            <button
              onClick={() => {
                const video = videoRef.current
                if (!video) return
                if (video.paused) video.play()
                else video.pause()
              }}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-500 rounded-lg font-medium transition-colors"
              disabled={isProcessing && !duration}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <button
              onClick={() => videoRef.current && (videoRef.current.currentTime += 10)}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
            >
              +10s
            </button>
          </div>

          {/* Review Segments button (shown after processing) */}
          {onReviewSegments && segments.length > 0 && (
            <div className="flex justify-center pt-2">
              <button
                onClick={onReviewSegments}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-500 rounded-lg font-medium transition-colors shadow-lg"
              >
                <Scissors className="w-5 h-5" />
                <span>Review & Re-clip Segments ({segments.length})</span>
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="p-4 border-t border-slate-700 bg-slate-800">
        <div className="text-sm text-slate-400">
          <p className="font-mono text-xs truncate">{videoPath}</p>
          <p className="mt-2 text-xs">
            Preview your video before processing. Adjust settings in the sidebar, then click "Start Clipping" to begin.
          </p>
        </div>
      </div>
    </div>
  )
}

function formatTime(seconds: number): string {
  if (!seconds || !isFinite(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export default VideoPreview
