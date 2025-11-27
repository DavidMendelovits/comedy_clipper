import { useRef, useEffect, useState, useCallback } from 'react'
import { Play, Pause, SkipForward, SkipBack } from 'lucide-react'
import { usePoseVisualizationStore, POSE_SKELETON } from '../stores/poseVisualizationStore'
import { VideoOverlayContainer } from './VideoOverlayContainer'

interface PoseVideoPlayerProps {
  videoPath: string
  className?: string
}

export function PoseVideoPlayer({ videoPath, className = '' }: PoseVideoPlayerProps) {
  const videoElementRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const {
    currentTime,
    duration,
    isPlaying,
    showSkeleton,
    showBoundingBoxes,
    currentPoses,
    events,
    setCurrentTime,
    setDuration,
    setIsPlaying,
    setVideoElement,
    applyPendingSeek,
    seekToTime,
    getNextEvent,
    getPreviousEvent
  } = usePoseVisualizationStore()

  const [videoLoaded, setVideoLoaded] = useState(false)

  // Convert file path to video URL
  const videoUrl = videoPath ? window.electron.getVideoUrl(videoPath) : ''

  // Handle video ref from VideoOverlayContainer
  const handleVideoRef = useCallback((video: HTMLVideoElement | null) => {
    videoElementRef.current = video
    setVideoElement(video)
  }, [setVideoElement])

  // Handle video loaded metadata
  const handleLoadedMetadata = useCallback((video: HTMLVideoElement) => {
    setDuration(video.duration)
    setVideoLoaded(true)
  }, [setDuration])

  // Handle video can play (ready for seeking)
  const handleCanPlay = useCallback(() => {
    applyPendingSeek()
  }, [applyPendingSeek])

  // Handle seek completed - sync store time with actual video time
  const handleSeeked = useCallback(() => {
    const video = videoElementRef.current
    if (video) {
      setCurrentTime(video.currentTime)
    }
  }, [setCurrentTime])

  // Draw pose overlay on canvas - triggered by pose changes
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !videoLoaded) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw poses
    currentPoses.forEach((pose) => {
      const { bbox, keypoints, personId } = pose

      // Person-specific color (cycle through colors)
      const colors = [
        '#f59e0b', // amber (more visible)
        '#3b82f6', // blue
        '#10b981', // green
        '#ef4444', // red
        '#8b5cf6', // purple
      ]
      const color = colors[personId % colors.length]

      // Draw bounding box
      if (showBoundingBoxes && bbox) {
        const [x1, y1, x2, y2] = bbox
        ctx.strokeStyle = color
        ctx.lineWidth = 3
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

        // Draw person ID label
        ctx.fillStyle = color
        ctx.fillRect(x1, y1 - 25, 80, 25)
        ctx.fillStyle = 'white'
        ctx.font = 'bold 14px sans-serif'
        ctx.fillText(`Person ${personId}`, x1 + 5, y1 - 8)
      }

      // Draw skeleton
      if (showSkeleton && keypoints && keypoints.length > 0) {
        // Draw skeleton connections
        ctx.strokeStyle = color
        ctx.lineWidth = 2

        POSE_SKELETON.forEach(([startIdx, endIdx]) => {
          if (startIdx < keypoints.length && endIdx < keypoints.length) {
            const [x1, y1, conf1] = keypoints[startIdx]
            const [x2, y2, conf2] = keypoints[endIdx]

            // Only draw if both keypoints are confident
            if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0 && conf1 > 0.3 && conf2 > 0.3) {
              ctx.beginPath()
              ctx.moveTo(x1, y1)
              ctx.lineTo(x2, y2)
              ctx.stroke()
            }
          }
        })

        // Draw keypoints
        keypoints.forEach(([x, y, conf]) => {
          if (x > 0 && y > 0 && conf > 0.3) {
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(x, y, 4, 0, 2 * Math.PI)
            ctx.fill()

            // Outline for visibility
            ctx.strokeStyle = 'white'
            ctx.lineWidth = 1
            ctx.stroke()
          }
        })
      }
    })
  }, [currentPoses, showSkeleton, showBoundingBoxes, videoLoaded])

  // Playback controls
  const togglePlayPause = () => {
    const video = videoElementRef.current
    if (!video) return

    if (video.paused) {
      video.play()
    } else {
      video.pause()
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    seekToTime(time)  // Use store's robust seeking logic with proper error handling
  }

  const jumpToNextEvent = () => {
    const nextEvent = getNextEvent(currentTime)
    if (nextEvent) {
      seekToTime(nextEvent.timestamp)
    }
  }

  const jumpToPreviousEvent = () => {
    const prevEvent = getPreviousEvent(currentTime)
    if (prevEvent) {
      seekToTime(prevEvent.timestamp)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className={`relative bg-black rounded-lg overflow-hidden ${className}`}>
      {/* Video and Canvas Container */}
      <VideoOverlayContainer
        videoUrl={videoUrl}
        className="aspect-video"
        onVideoRef={handleVideoRef}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={setCurrentTime}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onCanPlay={handleCanPlay}
        onSeeked={handleSeeked}
      >
        {(overlayBounds) => (
          <canvas
            ref={canvasRef}
            width={overlayBounds.videoWidth}
            height={overlayBounds.videoHeight}
            className="w-full h-full"
          />
        )}
      </VideoOverlayContainer>

      {/* Controls */}
      <div className="bg-slate-800 p-4">
        {/* Timeline with event markers */}
        <div className="relative w-full mb-3">
          <input
            type="range"
            min="0"
            max={duration || 0}
            step="0.1"
            value={currentTime}
            onChange={handleSeek}
            className="w-full accent-blue-500"
          />

          {/* Event markers overlay on slider */}
          {events.length > 0 && duration > 0 && (
            <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 pointer-events-none">
              {events.map((event, idx) => {
                const position = (event.timestamp / duration) * 100
                return (
                  <div
                    key={idx}
                    className={`absolute w-2 h-2 rounded-full border border-white/50 shadow-sm ${
                      event.eventType === 'enter' ? 'bg-green-500' : 'bg-red-500'
                    }`}
                    style={{ left: `${position}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
                    title={`${event.eventType} @ ${formatTime(event.timestamp)}`}
                  />
                )
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between">
          {/* Time display */}
          <div className="text-white text-sm font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          {/* Playback controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={jumpToPreviousEvent}
              className="p-2 hover:bg-slate-700 rounded transition-colors text-white"
              title="Previous Event"
            >
              <SkipBack className="w-5 h-5" />
            </button>

            <button
              onClick={togglePlayPause}
              className="p-3 bg-blue-600 hover:bg-blue-700 rounded-full transition-colors text-white"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>

            <button
              onClick={jumpToNextEvent}
              className="p-2 hover:bg-slate-700 rounded transition-colors text-white"
              title="Next Event"
            >
              <SkipForward className="w-5 h-5" />
            </button>
          </div>

          {/* Event count */}
          <div className="text-slate-400 text-sm">
            {events.length} events
          </div>
        </div>
      </div>
    </div>
  )
}
