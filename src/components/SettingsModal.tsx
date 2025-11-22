import { X, Play, Sparkles, Info, AlertCircle } from 'lucide-react'
import { useAppStore } from '../store'
import { useRef, useEffect, useState } from 'react'
import { Button, Select, Input, Toggle, Slider, Card } from './ui'

interface SettingsModalProps {
  onSubmit?: () => void
}

export default function SettingsModal({ onSubmit }: SettingsModalProps = {}) {
  const { config, setConfig, setShowSettings, showSettings, selectedVideo } = useAppStore()
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [videoLoaded, setVideoLoaded] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  // Get video URL
  const videoUrl = selectedVideo ? (window as any).electron?.getLocalFileUrl(selectedVideo) : null

  // Check if current mode supports YOLO/MediaPipe
  const supportsYOLO = ['multimodal', 'pose', 'face', 'mediapipe'].includes(config.clipperType)
  const requiresYOLO = config.personCountMethod === 'yolo' || config.personCountMethod === 'yolo_zone' || config.personCountMethod === 'hybrid'
  const isMediaPipeMode = ['multimodal', 'pose', 'face', 'mediapipe'].includes(config.clipperType)

  // Get mode-specific helper text
  const getModeDescription = () => {
    switch (config.clipperType) {
      case 'multimodal': return 'Combines face + pose detection with Kalman filtering - best for standup comedy'
      case 'pose': return 'Pose-only detection using MediaPipe - good for full-body tracking'
      case 'face': return 'Face-only detection using MediaPipe - best when faces are clearly visible'
      case 'mediapipe': return 'Advanced MediaPipe pose estimation with position tracking'
      case 'scene': return 'Fast FFmpeg scene detection - works for multi-camera shows with visible cuts'
      case 'diarization': return 'AI speaker identification - requires HuggingFace token and clear audio'
      default: return ''
    }
  }

  const getPersonCountMethodDescription = () => {
    if (!isMediaPipeMode) return ''

    switch (config.personCountMethod) {
      case 'min': return 'min(faces, poses) - Conservative, reduces false positives'
      case 'max': return 'max(faces, poses) - Liberal, works when face detection is unreliable'
      case 'average': return 'Average of face and pose counts - balanced approach'
      case 'yolo': return 'Use YOLO person count - requires YOLO enabled'
      case 'yolo_zone': return 'Count only people inside stage boundary - requires YOLO + zone crossing'
      case 'hybrid': return 'Prefer YOLO, fallback to MediaPipe - best of both worlds'
      default: return ''
    }
  }

  // Auto-fix invalid configuration combinations
  useEffect(() => {
    if (!supportsYOLO && config.yoloEnabled) {
      setConfig({ yoloEnabled: false })
    }
    if (!config.yoloEnabled && requiresYOLO) {
      setConfig({ personCountMethod: 'max' })
    }
    if (!config.yoloEnabled && config.zoneCrossingEnabled) {
      setConfig({ zoneCrossingEnabled: false })
    }
  }, [config.clipperType, config.yoloEnabled, config.personCountMethod, config.zoneCrossingEnabled, supportsYOLO, requiresYOLO])

  // Draw stage boundary overlay
  useEffect(() => {
    if (!videoLoaded || !canvasRef.current || !videoRef.current || !config.zoneCrossingEnabled) return

    const canvas = canvasRef.current
    const video = videoRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    if (config.stageBoundary && config.zoneCrossingEnabled) {
      const { left, right, top, bottom } = config.stageBoundary

      // Calculate pixel coordinates
      const x1 = left * canvas.width
      const x2 = right * canvas.width
      const y1 = top * canvas.height
      const y2 = bottom * canvas.height

      // Draw semi-transparent overlay for excluded areas
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'

      // Top exclusion
      ctx.fillRect(0, 0, canvas.width, y1)
      // Bottom exclusion
      ctx.fillRect(0, y2, canvas.width, canvas.height - y2)
      // Left exclusion
      ctx.fillRect(0, y1, x1, y2 - y1)
      // Right exclusion
      ctx.fillRect(x2, y1, canvas.width - x2, y2 - y1)

      // Draw stage boundary rectangle
      ctx.strokeStyle = '#22c55e'
      ctx.lineWidth = 3
      ctx.setLineDash([10, 5])
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

      // Draw corner markers
      const markerSize = 20
      ctx.fillStyle = '#22c55e'
      ctx.setLineDash([])

      // Top-left
      ctx.fillRect(x1 - 2, y1 - 2, markerSize, 4)
      ctx.fillRect(x1 - 2, y1 - 2, 4, markerSize)

      // Top-right
      ctx.fillRect(x2 - markerSize + 2, y1 - 2, markerSize, 4)
      ctx.fillRect(x2 - 2, y1 - 2, 4, markerSize)

      // Bottom-left
      ctx.fillRect(x1 - 2, y2 - 2, markerSize, 4)
      ctx.fillRect(x1 - 2, y2 - markerSize + 2, 4, markerSize)

      // Bottom-right
      ctx.fillRect(x2 - markerSize + 2, y2 - 2, markerSize, 4)
      ctx.fillRect(x2 - 2, y2 - markerSize + 2, 4, markerSize)

      // Draw labels
      ctx.font = 'bold 16px sans-serif'
      ctx.fillStyle = '#22c55e'
      ctx.fillText('STAGE AREA', x1 + 10, y1 + 30)

      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
      ctx.font = '14px sans-serif'
      ctx.fillText(`${(left * 100).toFixed(0)}%`, x1 + 5, y1 - 10)
      ctx.fillText(`${(right * 100).toFixed(0)}%`, x2 - 35, y1 - 10)
      ctx.fillText(`${(top * 100).toFixed(0)}%`, x1 - 35, y1 + 20)
      ctx.fillText(`${(bottom * 100).toFixed(0)}%`, x1 - 35, y2 + 5)
    }
  }, [videoLoaded, config.stageBoundary, config.zoneCrossingEnabled])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (onSubmit) {
      onSubmit()
    }
  }

  const handleClose = () => {
    setIsExiting(true)
    setTimeout(() => {
      setShowSettings(false)
      setIsExiting(false)
    }, 300)
  }

  if (!showSettings) return null

  return (
    <div className="fixed inset-0 z-50 flex bg-black/50 backdrop-blur-sm">
      {/* Backdrop */}
      <div
        className={`flex-1 transition-opacity duration-300 ${isExiting ? 'opacity-0' : 'opacity-100'}`}
        onClick={handleClose}
      />

      {/* Drawer */}
      <div className={`
        w-full max-w-6xl bg-slate-800/95 backdrop-blur-md shadow-2xl flex flex-col
        transition-transform duration-300 ease-in-out
        ${isExiting ? 'translate-x-full' : 'translate-x-0'}
      `}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700/50 bg-gradient-to-r from-slate-800 to-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-500/20 rounded-xl">
              <Sparkles className="w-6 h-6 text-primary-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gradient">Configure Clipper Settings</h2>
              <p className="text-sm text-slate-400 mt-0.5">
                Adjust settings and visualize detection zones on your video
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClose}
            icon={<X size={20} />}
          />
        </div>

        {/* Two-column layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Video Preview */}
          <div className="w-1/2 bg-black border-r border-slate-700 flex flex-col">
            <div className="flex-1 relative flex items-center justify-center p-6">
              {videoUrl ? (
                <div className="relative max-w-full max-h-full">
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    className="max-w-full max-h-full rounded-lg"
                    onLoadedMetadata={() => {
                      setVideoLoaded(true)
                      if (videoRef.current) {
                        videoRef.current.currentTime = 5 // Seek to 5s for a good frame
                      }
                    }}
                    style={{ maxHeight: 'calc(95vh - 200px)' }}
                  />
                  <canvas
                    ref={canvasRef}
                    className="absolute top-0 left-0 w-full h-full pointer-events-none"
                    style={{ objectFit: 'contain' }}
                  />
                </div>
              ) : (
                <div className="text-center text-slate-400">
                  <Play className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No video selected</p>
                  <p className="text-sm mt-2">Select a video to preview detection zones</p>
                </div>
              )}
            </div>

            {/* Video info */}
            {videoLoaded && videoRef.current && (
              <div className="p-4 bg-slate-900/50 border-t border-slate-700">
                <div className="text-xs text-slate-400 space-y-1">
                  <div>Resolution: {videoRef.current.videoWidth} × {videoRef.current.videoHeight}</div>
                  <div>Duration: {Math.floor(videoRef.current.duration / 60)}:{(Math.floor(videoRef.current.duration % 60)).toString().padStart(2, '0')}</div>
                  {config.zoneCrossingEnabled && config.stageBoundary && (
                    <div className="mt-2 pt-2 border-t border-slate-700">
                      <div className="text-green-400 font-medium mb-1">Stage Boundary Active</div>
                      <div className="grid grid-cols-2 gap-1">
                        <div>Left: {(config.stageBoundary.left * 100).toFixed(0)}%</div>
                        <div>Right: {(config.stageBoundary.right * 100).toFixed(0)}%</div>
                        <div>Top: {(config.stageBoundary.top * 100).toFixed(0)}%</div>
                        <div>Bottom: {(config.stageBoundary.bottom * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right: Settings Form */}
          <div className="w-1/2 overflow-y-auto">
            <form onSubmit={handleSubmit} className="p-6">
              <div className="space-y-6">
                {/* Detection Mode */}
                <Card variant="elevated" padding="sm">
                  <Select
                    label="Detection Mode"
                    value={config.clipperType}
                    onChange={(e) => setConfig({ clipperType: e.target.value as any })}
                    helperText={getModeDescription()}
                  >
                    <option value="multimodal">Multimodal (Recommended)</option>
                    <option value="pose">Pose Detection</option>
                    <option value="face">Face Detection</option>
                    <option value="mediapipe">MediaPipe</option>
                    <option value="scene">Scene Detection</option>
                    <option value="diarization">Diarization</option>
                  </Select>
                </Card>

                {/* Minimum Duration */}
                <Card variant="elevated" padding="sm">
                  <Input
                    type="number"
                    label="Minimum Clip Duration (seconds)"
                    value={config.minDuration}
                    onChange={(e) => setConfig({ minDuration: parseInt(e.target.value) || 5 })}
                    min={5}
                    max={600}
                    helperText="Shorter clips will be filtered out"
                  />
                </Card>

                {/* Config File */}
                <Card variant="elevated" padding="sm">
                  <Input
                    type="text"
                    label="Configuration File"
                    value={config.configFile}
                    onChange={(e) => setConfig({ configFile: e.target.value })}
                    placeholder="clipper_rules.yaml"
                    helperText="YAML file with detection rules"
                    className="font-mono text-sm"
                  />
                </Card>

                {/* Debug Mode */}
                <Card variant="elevated" padding="md">
                  <Toggle
                    label="Debug Mode"
                    description="Save frame snapshots and detection data"
                    checked={config.debug}
                    onChange={(e) => setConfig({ debug: e.target.checked })}
                  />
                </Card>

                {/* Advanced Settings - Only for MediaPipe modes */}
                {isMediaPipeMode && (
                  <div className="border-t border-slate-700/50 pt-6">
                    <h3 className="text-lg font-semibold text-gradient mb-4">Advanced Detection</h3>

                    {/* Info banner */}
                    <Card variant="glass" padding="sm" className="mb-4 border border-blue-500/30">
                      <div className="flex items-start gap-2 text-xs text-blue-200">
                        <Info size={16} className="flex-shrink-0 mt-0.5 text-blue-400" />
                        <div>
                          <div className="font-semibold mb-1">MediaPipe Mode Settings</div>
                          <div className="text-slate-300">
                            These settings only apply to MediaPipe-based detection modes (multimodal, pose, face, mediapipe).
                          </div>
                        </div>
                      </div>
                    </Card>

                    {/* YOLO Detection */}
                    <Card variant="elevated" padding="md" className="mb-4">
                      <Toggle
                        label="Enable YOLO Person Detection"
                        description="Adds YOLOv8 person detection - more accurate for 2+ people (requires ultralytics)"
                        checked={config.yoloEnabled ?? false}
                        onChange={(e) => setConfig({ yoloEnabled: e.target.checked })}
                      />
                    </Card>

                    {/* Person Count Method */}
                    <Card variant="elevated" padding="sm" className="mb-4">
                      <Select
                        label="Person Count Method"
                        value={config.personCountMethod ?? 'max'}
                        onChange={(e) => setConfig({ personCountMethod: e.target.value as any })}
                        helperText={getPersonCountMethodDescription()}
                      >
                        <optgroup label="MediaPipe-based (always available)">
                          <option value="max">Max (Recommended)</option>
                          <option value="min">Min (Conservative)</option>
                          <option value="average">Average</option>
                        </optgroup>
                        {config.yoloEnabled && (
                          <optgroup label="YOLO-based (requires YOLO enabled)">
                            <option value="yolo_zone">YOLO Zone (Stage Only)</option>
                            <option value="yolo">YOLO (All Detections)</option>
                            <option value="hybrid">Hybrid (YOLO + MediaPipe)</option>
                          </optgroup>
                        )}
                      </Select>
                    </Card>

                    {/* Zone Crossing */}
                    <Card variant="elevated" padding="md" className="mb-4">
                      <Toggle
                        label="Enable Zone Crossing"
                        description="Define stage boundary to exclude audience from person counts"
                        checked={config.zoneCrossingEnabled ?? false}
                        onChange={(e) => setConfig({ zoneCrossingEnabled: e.target.checked })}
                        disabled={!config.yoloEnabled}
                      />
                      {!config.yoloEnabled && (
                        <div className="mt-2 flex items-start gap-2 text-xs text-amber-400">
                          <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                          <span>Zone crossing requires YOLO to be enabled</span>
                        </div>
                      )}
                    </Card>

                    {/* Stage Boundary */}
                    {config.zoneCrossingEnabled && config.stageBoundary && (
                      <Card variant="gradient-border" padding="md" className="border-emerald-500/30">
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold text-emerald-400">Stage Boundary</h4>
                            <span className="text-xs text-slate-400">Adjust on video preview →</span>
                          </div>

                          <Slider
                            label="Left"
                            min={0}
                            max={0.5}
                            step={0.01}
                            value={config.stageBoundary.left}
                            onChange={(e) => setConfig({
                              stageBoundary: { ...config.stageBoundary!, left: parseFloat(e.target.value) }
                            })}
                            valueFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />

                          <Slider
                            label="Right"
                            min={0.5}
                            max={1}
                            step={0.01}
                            value={config.stageBoundary.right}
                            onChange={(e) => setConfig({
                              stageBoundary: { ...config.stageBoundary!, right: parseFloat(e.target.value) }
                            })}
                            valueFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />

                          <Slider
                            label="Top"
                            min={0}
                            max={0.5}
                            step={0.01}
                            value={config.stageBoundary.top}
                            onChange={(e) => setConfig({
                              stageBoundary: { ...config.stageBoundary!, top: parseFloat(e.target.value) }
                            })}
                            valueFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />

                          <Slider
                            label="Bottom"
                            min={0.5}
                            max={1}
                            step={0.01}
                            value={config.stageBoundary.bottom}
                            onChange={(e) => setConfig({
                              stageBoundary: { ...config.stageBoundary!, bottom: parseFloat(e.target.value) }
                            })}
                            valueFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />

                          <div className="pt-2 border-t border-slate-700/50">
                            <p className="text-xs text-slate-400 flex items-start gap-2">
                              <Sparkles size={14} className="flex-shrink-0 mt-0.5 text-emerald-400" />
                              <span>The green area on the video shows the stage detection zone. People outside this area (like audience) will be excluded from person counts.</span>
                            </p>
                          </div>
                        </div>
                      </Card>
                    )}
                  </div>
                )}

                {/* Scene Detection Mode Tips */}
                {config.clipperType === 'scene' && (
                  <Card variant="glass" padding="md" className="border border-purple-500/30">
                    <div className="flex items-start gap-2 text-xs text-purple-200">
                      <Info size={16} className="flex-shrink-0 mt-0.5 text-purple-400" />
                      <div>
                        <div className="font-semibold mb-2">Scene Detection Mode</div>
                        <div className="text-slate-300 space-y-1">
                          <div>• Works best for multi-camera shows with visible cuts between performers</div>
                          <div>• Very fast - no ML models required</div>
                          <div>• Configure scene threshold in clipper_rules.yaml (default: 0.3)</div>
                          <div>• Lower threshold = more sensitive to scene changes</div>
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Diarization Mode Tips */}
                {config.clipperType === 'diarization' && (
                  <Card variant="glass" padding="md" className="border border-amber-500/30">
                    <div className="flex items-start gap-2 text-xs text-amber-200">
                      <AlertCircle size={16} className="flex-shrink-0 mt-0.5 text-amber-400" />
                      <div>
                        <div className="font-semibold mb-2">Diarization Mode Requirements</div>
                        <div className="text-slate-300 space-y-1">
                          <div>• Requires HuggingFace token (set in environment or config)</div>
                          <div>• Needs clear, high-quality audio</div>
                          <div>• Best for shows with distinct speaker voices</div>
                          <div>• Processing is slower than other modes</div>
                          <div>• May require additional dependencies (pyannote.audio)</div>
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Footer */}
                <div className="flex gap-3 pt-6 mt-6 border-t border-slate-700/50 sticky bottom-0 bg-slate-800/95 backdrop-blur-sm">
                  <Button
                    type="button"
                    variant="secondary"
                    size="lg"
                    fullWidth
                    onClick={handleClose}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    fullWidth
                    icon={<Play size={18} />}
                  >
                    Start Processing
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
