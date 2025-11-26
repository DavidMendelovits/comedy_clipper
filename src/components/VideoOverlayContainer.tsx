import { useRef, useEffect, useState, ReactNode, useCallback } from 'react'

export interface OverlayBounds {
  width: number
  height: number
  left: number
  top: number
  videoWidth: number   // native resolution
  videoHeight: number  // native resolution
}

interface VideoOverlayContainerProps {
  videoUrl: string
  className?: string
  onVideoRef?: (video: HTMLVideoElement | null) => void
  onLoadedMetadata?: (video: HTMLVideoElement) => void
  onTimeUpdate?: (currentTime: number) => void
  onPlay?: () => void
  onPause?: () => void
  children: (bounds: OverlayBounds, videoRef: HTMLVideoElement | null) => ReactNode
}

export function VideoOverlayContainer({
  videoUrl,
  className = '',
  onVideoRef,
  onLoadedMetadata,
  onTimeUpdate,
  onPlay,
  onPause,
  children
}: VideoOverlayContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [bounds, setBounds] = useState<OverlayBounds>({
    width: 0, height: 0, left: 0, top: 0, videoWidth: 0, videoHeight: 0
  })

  // Store callbacks in refs to avoid effect re-runs (prevents infinite loops)
  const callbacksRef = useRef({ onVideoRef, onLoadedMetadata, onTimeUpdate, onPlay, onPause })
  callbacksRef.current = { onVideoRef, onLoadedMetadata, onTimeUpdate, onPlay, onPause }

  // Calculate overlay bounds based on actual video display area
  const updateBounds = useCallback(() => {
    const video = videoRef.current
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) return

    const videoAspect = video.videoWidth / video.videoHeight
    const containerAspect = video.offsetWidth / video.offsetHeight

    let displayWidth: number
    let displayHeight: number
    let offsetX: number
    let offsetY: number

    if (videoAspect > containerAspect) {
      // Video is wider - letterboxed (bars on top/bottom)
      displayWidth = video.offsetWidth
      displayHeight = video.offsetWidth / videoAspect
      offsetX = 0
      offsetY = (video.offsetHeight - displayHeight) / 2
    } else {
      // Video is taller - pillarboxed (bars on sides)
      displayHeight = video.offsetHeight
      displayWidth = video.offsetHeight * videoAspect
      offsetX = (video.offsetWidth - displayWidth) / 2
      offsetY = 0
    }

    setBounds({
      width: displayWidth,
      height: displayHeight,
      left: offsetX,
      top: offsetY,
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight
    })
  }, [])

  // Setup video element and event listeners (runs once)
  useEffect(() => {
    const video = videoRef.current
    const container = containerRef.current
    if (!video || !container) return

    // Notify parent of video ref
    callbacksRef.current.onVideoRef?.(video)

    const handleLoadedMetadata = () => {
      updateBounds()
      callbacksRef.current.onLoadedMetadata?.(video)
    }
    const handleTimeUpdate = () => callbacksRef.current.onTimeUpdate?.(video.currentTime)
    const handlePlay = () => callbacksRef.current.onPlay?.()
    const handlePause = () => callbacksRef.current.onPause?.()

    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('resize', updateBounds)
    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('play', handlePlay)
    video.addEventListener('pause', handlePause)

    const resizeObserver = new ResizeObserver(updateBounds)
    resizeObserver.observe(container)

    return () => {
      callbacksRef.current.onVideoRef?.(null)
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('resize', updateBounds)
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('play', handlePlay)
      video.removeEventListener('pause', handlePause)
      resizeObserver.disconnect()
    }
  }, [updateBounds])

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <video
        ref={videoRef}
        src={videoUrl}
        className="w-full h-full object-contain"
        playsInline
      />
      {/* Overlay container - positioned exactly over video content */}
      {bounds.width > 0 && (
        <div
          className="absolute pointer-events-none"
          style={{
            width: bounds.width,
            height: bounds.height,
            left: bounds.left,
            top: bounds.top
          }}
        >
          {children(bounds, videoRef.current)}
        </div>
      )}
    </div>
  )
}
