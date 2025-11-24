import { useState, useEffect } from 'react'
import { Play, X, Check, AlertCircle, Loader, Download, Eye } from 'lucide-react'
import { Button, Card } from './ui'

interface ModelResult {
  status: 'pending' | 'running' | 'complete' | 'failed' | 'skipped'
  progress?: number
  message?: string
  stats?: {
    total_frames?: number
    detected_frames?: number
    detection_rate?: number
    avg_fps?: number
    avg_time_per_frame_ms?: number
    total_time?: number
    output_file?: string
    model_name?: string
    debug_frame?: string
  }
  error?: string
}

interface ModelComparisonProps {
  videoPath: string
  onClose: () => void
}

const AVAILABLE_MODELS = {
  mediapipe: {
    name: 'MediaPipe Pose',
    description: 'Fast, lightweight, single-person detection',
    speed: 'Fast',
    accuracy: 'Good'
  },
  movenet_lightning: {
    name: 'MoveNet Lightning',
    description: 'Optimized for speed, edge devices',
    speed: 'Very Fast',
    accuracy: 'Moderate'
  },
  movenet_thunder: {
    name: 'MoveNet Thunder',
    description: 'Balanced speed and accuracy',
    speed: 'Fast',
    accuracy: 'Good'
  },
  yolo: {
    name: 'YOLO Pose',
    description: 'Multi-person detection, accurate',
    speed: 'Moderate',
    accuracy: 'High'
  },
  mmpose_rtmpose_m: {
    name: 'MMPose RTMPose-M',
    description: 'State-of-the-art, balanced',
    speed: 'Moderate',
    accuracy: 'High'
  },
  mmpose_hrnet_w48: {
    name: 'MMPose HRNet-W48',
    description: 'Highest accuracy, slower',
    speed: 'Slow',
    accuracy: 'Very High'
  }
}

export default function ModelComparison({ videoPath, onClose }: ModelComparisonProps) {
  const [selectedModels, setSelectedModels] = useState<Set<string>>(
    new Set(['mediapipe', 'movenet_thunder', 'yolo'])
  )
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<Record<string, ModelResult>>({})
  const [viewingDebugFrame, setViewingDebugFrame] = useState<string | null>(null)

  const toggleModel = (modelId: string) => {
    const newSelected = new Set(selectedModels)
    if (newSelected.has(modelId)) {
      newSelected.delete(modelId)
    } else {
      newSelected.add(modelId)
    }
    setSelectedModels(newSelected)
  }

  const startComparison = async () => {
    if (selectedModels.size === 0) return

    setRunning(true)

    // Initialize results
    const initialResults: Record<string, ModelResult> = {}
    selectedModels.forEach(modelId => {
      initialResults[modelId] = { status: 'pending' }
    })
    setResults(initialResults)

    try {
      await (window as any).electron.runPoseComparison({
        videoPath,
        modelIds: Array.from(selectedModels),
        onProgress: (data: { model_id: string; data: any }) => {
          setResults(prev => ({
            ...prev,
            [data.model_id]: {
              status: data.data.status,
              progress: data.data.progress,
              message: data.data.message,
              stats: data.data.stats,
              error: data.data.error
            }
          }))
        }
      })
    } catch (error: any) {
      console.error('Comparison error:', error)
    } finally {
      setRunning(false)
    }
  }

  const getStatusIcon = (status: ModelResult['status']) => {
    switch (status) {
      case 'pending':
        return <div className="w-5 h-5 border-2 border-slate-600 rounded-full" />
      case 'running':
        return <Loader className="w-5 h-5 text-blue-400 animate-spin" />
      case 'complete':
        return <Check className="w-5 h-5 text-green-400" />
      case 'failed':
        return <X className="w-5 h-5 text-red-400" />
      case 'skipped':
        return <AlertCircle className="w-5 h-5 text-yellow-400" />
    }
  }

  const getStatusColor = (status: ModelResult['status']) => {
    switch (status) {
      case 'pending': return 'border-slate-700'
      case 'running': return 'border-blue-500'
      case 'complete': return 'border-green-500'
      case 'failed': return 'border-red-500'
      case 'skipped': return 'border-yellow-500'
    }
  }

  const openOutputVideo = async (filePath: string) => {
    await (window as any).electron.openFile(filePath)
  }

  const exportComparisonReport = async () => {
    // Export results as JSON
    const dataStr = JSON.stringify(results, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'pose_comparison_report.json'
    link.click()
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-2xl border border-slate-700 max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gradient mb-1">Pose Model Comparison</h2>
            <p className="text-sm text-slate-400">
              Select models to compare performance and accuracy
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X size={20} />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Model Selection */}
          {!running && Object.keys(results).length === 0 && (
            <div className="space-y-4 mb-6">
              <h3 className="text-lg font-semibold text-slate-300">Select Models to Compare</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(AVAILABLE_MODELS).map(([modelId, config]) => (
                  <Card
                    key={modelId}
                    variant="elevated"
                    padding="sm"
                    className={`cursor-pointer transition-all ${
                      selectedModels.has(modelId)
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                    onClick={() => toggleModel(modelId)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-semibold text-sm">{config.name}</h4>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        selectedModels.has(modelId)
                          ? 'border-primary-500 bg-primary-500'
                          : 'border-slate-600'
                      }`}>
                        {selectedModels.has(modelId) && <Check size={14} className="text-white" />}
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 mb-3">{config.description}</p>
                    <div className="flex gap-2 text-xs">
                      <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-300">
                        {config.speed}
                      </span>
                      <span className="px-2 py-1 rounded bg-green-500/20 text-green-300">
                        {config.accuracy}
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {Object.keys(results).length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-300">Comparison Results</h3>
                {!running && (
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<Download size={16} />}
                    onClick={exportComparisonReport}
                  >
                    Export Report
                  </Button>
                )}
              </div>

              <div className="grid gap-4">
                {Object.entries(results).map(([modelId, result]) => (
                  <Card
                    key={modelId}
                    variant="elevated"
                    padding="md"
                    className={`border-2 ${getStatusColor(result.status)}`}
                  >
                    <div className="flex items-start gap-4">
                      {/* Status Icon */}
                      <div className="mt-1">{getStatusIcon(result.status)}</div>

                      {/* Model Info */}
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-semibold text-lg">
                            {AVAILABLE_MODELS[modelId as keyof typeof AVAILABLE_MODELS]?.name || modelId}
                          </h4>
                          <div className="flex gap-2">
                            {result.stats?.debug_frame && (
                              <Button
                                variant="secondary"
                                size="sm"
                                icon={<Eye size={14} />}
                                onClick={() => setViewingDebugFrame(result.stats!.debug_frame!)}
                              >
                                View Frame
                              </Button>
                            )}
                            {result.stats?.output_file && result.status === 'complete' && (
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => openOutputVideo(result.stats!.output_file!)}
                              >
                                Open Video
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* Progress Bar */}
                        {result.status === 'running' && result.progress !== undefined && (
                          <div className="mb-2">
                            <div className="w-full bg-slate-700 rounded-full h-2">
                              <div
                                className="bg-blue-500 h-2 rounded-full transition-all"
                                style={{ width: `${result.progress}%` }}
                              />
                            </div>
                            {result.message && (
                              <p className="text-xs text-slate-400 mt-1">{result.message}</p>
                            )}
                          </div>
                        )}

                        {/* Stats */}
                        {result.stats && result.status === 'complete' && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
                            {result.stats.detection_rate !== undefined && (
                              <div>
                                <p className="text-xs text-slate-400">Detection Rate</p>
                                <p className="text-lg font-semibold text-green-400">
                                  {result.stats.detection_rate.toFixed(1)}%
                                </p>
                              </div>
                            )}
                            {result.stats.avg_fps !== undefined && (
                              <div>
                                <p className="text-xs text-slate-400">Avg FPS</p>
                                <p className="text-lg font-semibold text-blue-400">
                                  {result.stats.avg_fps.toFixed(1)}
                                </p>
                              </div>
                            )}
                            {result.stats.total_time !== undefined && (
                              <div>
                                <p className="text-xs text-slate-400">Total Time</p>
                                <p className="text-lg font-semibold text-purple-400">
                                  {result.stats.total_time.toFixed(1)}s
                                </p>
                              </div>
                            )}
                            {result.stats.detected_frames !== undefined && result.stats.total_frames !== undefined && (
                              <div>
                                <p className="text-xs text-slate-400">Frames Detected</p>
                                <p className="text-lg font-semibold text-yellow-400">
                                  {result.stats.detected_frames}/{result.stats.total_frames}
                                </p>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Error */}
                        {result.error && (
                          <div className="mt-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                            <p className="text-sm text-red-400">{result.error}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-700 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            {selectedModels.size} model{selectedModels.size !== 1 ? 's' : ''} selected
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            {!running && Object.keys(results).length === 0 && (
              <Button
                variant="primary"
                icon={<Play size={16} />}
                onClick={startComparison}
                disabled={selectedModels.size === 0}
              >
                Start Comparison
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Debug Frame Viewer */}
      {viewingDebugFrame && (
        <div
          className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-4"
          onClick={() => setViewingDebugFrame(null)}
        >
          <div className="max-w-5xl max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
            <img
              src={viewingDebugFrame}
              alt="Debug frame"
              className="w-full h-full object-contain rounded-lg border border-slate-700"
            />
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => setViewingDebugFrame(null)}
            >
              Close
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
