import { useState } from 'react'
import { X, ChevronLeft, ChevronRight, Play, Download, Grid, Film } from 'lucide-react'
import { Button, Card } from './ui'

interface DebugFrame {
  path: string
  frame_number: number
  timestamp: number
  has_detection?: boolean
  detection_count?: number
}

interface DebugFrameViewerProps {
  frames: DebugFrame[]
  debugVideos?: string[]
  onClose: () => void
}

export default function DebugFrameViewer({ frames, debugVideos = [], onClose }: DebugFrameViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [viewMode, setViewMode] = useState<'grid' | 'single'>('grid')
  const [filterDetections, setFilterDetections] = useState(false)

  const filteredFrames = filterDetections
    ? frames.filter(f => f.has_detection)
    : frames

  const currentFrame = filteredFrames[currentIndex]

  const goToPrevious = () => {
    setCurrentIndex(Math.max(0, currentIndex - 1))
  }

  const goToNext = () => {
    setCurrentIndex(Math.min(filteredFrames.length - 1, currentIndex + 1))
  }

  const openFile = async (filePath: string) => {
    await (window as any).electron.openFile(filePath)
  }

  const downloadFrame = async (frame: DebugFrame) => {
    // Copy file to downloads
    const fileName = frame.path.split('/').pop() || 'debug_frame.jpg'
    await (window as any).electron.saveFile(frame.path, fileName)
  }

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-700 bg-slate-800/80 backdrop-blur-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold text-gradient">Debug Frame Viewer</h2>
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'grid' ? 'primary' : 'secondary'}
              size="sm"
              icon={<Grid size={16} />}
              onClick={() => setViewMode('grid')}
            >
              Grid
            </Button>
            <Button
              variant={viewMode === 'single' ? 'primary' : 'secondary'}
              size="sm"
              icon={<Film size={16} />}
              onClick={() => setViewMode('single')}
            >
              Single
            </Button>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={filterDetections}
              onChange={(e) => setFilterDetections(e.target.checked)}
              className="rounded border-slate-600 bg-slate-700"
            />
            Only show detections
          </label>
        </div>
        <div className="flex gap-2">
          {debugVideos.length > 0 && (
            <div className="flex gap-2 mr-4">
              <span className="text-sm text-slate-400">Debug Videos:</span>
              {debugVideos.map((video, idx) => (
                <Button
                  key={idx}
                  variant="secondary"
                  size="sm"
                  icon={<Play size={14} />}
                  onClick={() => openFile(video)}
                >
                  {video.split('/').pop()}
                </Button>
              ))}
            </div>
          )}
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X size={20} />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {viewMode === 'single' ? (
          /* Single Frame View */
          <div className="h-full flex flex-col items-center justify-center">
            {currentFrame && (
              <>
                <div className="max-w-6xl max-h-[70vh] mb-4">
                  <img
                    src={`local-file://${currentFrame.path}`}
                    alt={`Frame ${currentFrame.frame_number}`}
                    className="w-full h-full object-contain rounded-lg border border-slate-700"
                  />
                </div>

                {/* Frame Info */}
                <Card variant="elevated" padding="sm" className="mb-4">
                  <div className="flex items-center gap-6 text-sm">
                    <div>
                      <span className="text-slate-400">Frame:</span>{' '}
                      <span className="font-semibold">{currentFrame.frame_number}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Time:</span>{' '}
                      <span className="font-semibold">{currentFrame.timestamp.toFixed(2)}s</span>
                    </div>
                    {currentFrame.detection_count !== undefined && (
                      <div>
                        <span className="text-slate-400">Detections:</span>{' '}
                        <span className={`font-semibold ${currentFrame.detection_count > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {currentFrame.detection_count}
                        </span>
                      </div>
                    )}
                  </div>
                </Card>

                {/* Navigation */}
                <div className="flex items-center gap-4">
                  <Button
                    variant="secondary"
                    icon={<ChevronLeft size={16} />}
                    onClick={goToPrevious}
                    disabled={currentIndex === 0}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-slate-400">
                    {currentIndex + 1} / {filteredFrames.length}
                  </span>
                  <Button
                    variant="secondary"
                    icon={<ChevronRight size={16} />}
                    onClick={goToNext}
                    disabled={currentIndex === filteredFrames.length - 1}
                  >
                    Next
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    icon={<Download size={14} />}
                    onClick={() => downloadFrame(currentFrame)}
                  >
                    Download
                  </Button>
                </div>
              </>
            )}
          </div>
        ) : (
          /* Grid View */
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {filteredFrames.map((frame, idx) => (
              <Card
                key={idx}
                variant="elevated"
                padding="none"
                className={`cursor-pointer transition-all hover:scale-105 ${
                  idx === currentIndex ? 'ring-2 ring-primary-500' : ''
                }`}
                onClick={() => {
                  setCurrentIndex(idx)
                  setViewMode('single')
                }}
              >
                <div className="relative aspect-video overflow-hidden rounded-lg">
                  <img
                    src={`local-file://${frame.path}`}
                    alt={`Frame ${frame.frame_number}`}
                    className="w-full h-full object-cover"
                  />
                  {frame.has_detection && (
                    <div className="absolute top-2 right-2 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                  )}
                </div>
                <div className="p-2 bg-slate-900/50">
                  <p className="text-xs text-slate-400 truncate">
                    Frame {frame.frame_number}
                  </p>
                  <p className="text-xs text-slate-500">
                    {frame.timestamp.toFixed(2)}s
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}

        {filteredFrames.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-slate-400">
              <p className="text-lg mb-2">No debug frames available</p>
              {filterDetections && (
                <p className="text-sm">Try disabling the detection filter</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {frames.length > 0 && (
        <div className="p-4 border-t border-slate-700 bg-slate-800/80 backdrop-blur-sm flex items-center justify-between">
          <div className="flex gap-6 text-sm text-slate-300">
            <div>
              <span className="text-slate-400">Total Frames:</span>{' '}
              <span className="font-semibold">{frames.length}</span>
            </div>
            <div>
              <span className="text-slate-400">With Detections:</span>{' '}
              <span className="font-semibold text-green-400">
                {frames.filter(f => f.has_detection).length}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Detection Rate:</span>{' '}
              <span className="font-semibold text-blue-400">
                {((frames.filter(f => f.has_detection).length / frames.length) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
