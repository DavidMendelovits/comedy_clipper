import { useState } from 'react'
import { X, Play, CheckCircle, XCircle, Clock, Scissors, AlertCircle } from 'lucide-react'

interface VideoSegment {
  start: number
  end: number
  enabled?: boolean
}

interface SegmentReviewModalProps {
  isOpen: boolean
  segments: VideoSegment[]
  videoPath: string
  videoDuration: number
  onApprove: (selectedSegments: VideoSegment[]) => void
  onCancel: () => void
}

export default function SegmentReviewModal({
  isOpen,
  segments: initialSegments,
  videoDuration,
  onApprove,
  onCancel
}: SegmentReviewModalProps) {
  const [segments, setSegments] = useState<VideoSegment[]>(
    initialSegments.map(seg => ({ ...seg, enabled: true }))
  )

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    if (mins > 0) {
      return `${mins}m ${secs}s`
    }
    return `${secs}s`
  }

  const toggleSegment = (index: number) => {
    setSegments(prev => prev.map((seg, i) =>
      i === index ? { ...seg, enabled: !seg.enabled } : seg
    ))
  }

  const handleApprove = () => {
    const selectedSegments = segments.filter(seg => seg.enabled)
    onApprove(selectedSegments)
  }

  const enabledCount = segments.filter(seg => seg.enabled).length
  const totalDuration = segments
    .filter(seg => seg.enabled)
    .reduce((sum, seg) => sum + (seg.end - seg.start), 0)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col border border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-600 rounded-lg">
              <Scissors className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Review Detected Segments</h2>
              <p className="text-sm text-slate-400 mt-1">
                Select which segments to clip
              </p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-3 gap-4 p-4 bg-slate-800 border-b border-slate-700">
          <div className="flex items-center gap-3 p-3 bg-slate-900 rounded-lg">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <div>
              <div className="text-xs text-slate-400">Selected Segments</div>
              <div className="text-xl font-bold text-white">
                {enabledCount} <span className="text-sm text-slate-400">/ {segments.length}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-slate-900 rounded-lg">
            <Clock className="w-5 h-5 text-primary-400" />
            <div>
              <div className="text-xs text-slate-400">Total Duration</div>
              <div className="text-xl font-bold text-white">{formatDuration(totalDuration)}</div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-slate-900 rounded-lg">
            <Play className="w-5 h-5 text-blue-400" />
            <div>
              <div className="text-xs text-slate-400">Video Duration</div>
              <div className="text-xl font-bold text-white">{formatDuration(videoDuration)}</div>
            </div>
          </div>
        </div>

        {/* Timeline Visualization */}
        <div className="p-6 bg-slate-800/50 border-b border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Timeline</h3>
          <div className="relative h-16 bg-slate-950 rounded-lg overflow-hidden">
            {/* Time markers */}
            <div className="absolute inset-0 flex items-end px-2 pb-1">
              {[0, 0.25, 0.5, 0.75, 1].map(fraction => (
                <div
                  key={fraction}
                  className="absolute bottom-0 flex flex-col items-center"
                  style={{ left: `${fraction * 100}%` }}
                >
                  <div className="h-2 w-px bg-slate-600" />
                  <span className="text-[10px] text-slate-500 mt-1">
                    {formatTime(videoDuration * fraction)}
                  </span>
                </div>
              ))}
            </div>

            {/* Segment bars */}
            <div className="absolute inset-0 pt-2">
              {segments.map((segment, index) => {
                const startPercent = (segment.start / videoDuration) * 100
                const widthPercent = ((segment.end - segment.start) / videoDuration) * 100

                return (
                  <div
                    key={index}
                    className={`absolute h-10 rounded cursor-pointer transition-all hover:opacity-80 ${
                      segment.enabled
                        ? 'bg-gradient-to-r from-primary-600 to-primary-500 border-2 border-primary-400'
                        : 'bg-slate-700 border-2 border-slate-600 opacity-40'
                    }`}
                    style={{
                      left: `${startPercent}%`,
                      width: `${widthPercent}%`,
                      top: '8px',
                    }}
                    onClick={() => toggleSegment(index)}
                    title={`Segment ${index + 1}: ${formatTime(segment.start)} - ${formatTime(segment.end)}`}
                  >
                    <div className="flex items-center justify-center h-full">
                      <span className="text-[10px] font-bold text-white drop-shadow">
                        {index + 1}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Click on a segment in the timeline to enable/disable it
          </p>
        </div>

        {/* Segment List */}
        <div className="flex-1 overflow-y-auto p-6">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Segments</h3>
          <div className="space-y-2">
            {segments.map((segment, index) => {
              const duration = segment.end - segment.start

              return (
                <div
                  key={index}
                  className={`flex items-center gap-4 p-4 rounded-lg border-2 transition-all cursor-pointer ${
                    segment.enabled
                      ? 'bg-slate-800 border-primary-600 hover:bg-slate-750'
                      : 'bg-slate-900 border-slate-700 opacity-50 hover:opacity-70'
                  }`}
                  onClick={() => toggleSegment(index)}
                >
                  {/* Checkbox */}
                  <div className="flex-shrink-0">
                    {segment.enabled ? (
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    ) : (
                      <XCircle className="w-6 h-6 text-slate-500" />
                    )}
                  </div>

                  {/* Segment info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">Segment {index + 1}</span>
                      <span className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300">
                        {formatDuration(duration)}
                      </span>
                    </div>
                    <div className="text-sm text-slate-400 mt-1">
                      {formatTime(segment.start)} → {formatTime(segment.end)}
                    </div>
                  </div>

                  {/* Duration badge */}
                  <div className="text-right">
                    <div className="text-xs text-slate-500">Duration</div>
                    <div className="text-lg font-bold text-white">{formatDuration(duration)}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between p-6 bg-slate-800 border-t border-slate-700">
          <div className="text-sm text-slate-400">
            {enabledCount === 0 ? (
              <span className="text-yellow-400 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                No segments selected. Select at least one to proceed.
              </span>
            ) : (
              <span>
                Ready to create <strong className="text-white">{enabledCount}</strong> clip{enabledCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onCancel}
              className="px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApprove}
              disabled={enabledCount === 0}
              className="px-6 py-3 bg-primary-600 hover:bg-primary-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed rounded-lg font-medium transition-colors flex items-center gap-2"
            >
              <Scissors className="w-5 h-5" />
              <span>Create {enabledCount} Clip{enabledCount !== 1 ? 's' : ''}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
