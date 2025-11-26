import { useState, useEffect } from 'react'
import { X, Film, Download, CheckCircle, FolderOpen, Play, Loader2 } from 'lucide-react'
import type { Job } from '../types/jobs'

interface ExportModalProps {
  isOpen: boolean
  job: Job
  onClose: () => void
}

interface ExportProgress {
  phase: string
  percent: number
  frame: number
  total: number
  message?: string
}

export function ExportModal({ isOpen, job, onClose }: ExportModalProps) {
  // Overlay toggles
  const [showSkeleton, setShowSkeleton] = useState(true)
  const [showBbox, setShowBbox] = useState(true)
  const [showKeypoints, setShowKeypoints] = useState(true)

  // Export state
  const [exportState, setExportState] = useState<'configure' | 'exporting' | 'complete' | 'error'>('configure')
  const [progress, setProgress] = useState<ExportProgress>({ phase: '', percent: 0, frame: 0, total: 0 })
  const [outputPath, setOutputPath] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setExportState('configure')
      setProgress({ phase: '', percent: 0, frame: 0, total: 0 })
      setOutputPath(null)
      setErrorMessage(null)
    }
  }, [isOpen])

  // Listen for export progress events
  useEffect(() => {
    if (!isOpen || exportState !== 'exporting') return

    const unsubscribe = window.electron.onExportProgress((data) => {
      if (data.jobId === job.id) {
        setProgress({
          phase: data.phase,
          percent: data.percent,
          frame: data.frame,
          total: data.total,
          message: data.message
        })

        if (data.phase === 'complete') {
          setExportState('complete')
        }
      }
    })

    return () => unsubscribe()
  }, [isOpen, exportState, job.id])

  const handleStartExport = async () => {
    // Build overlays list
    const overlays: string[] = []
    if (showSkeleton) overlays.push('skeleton')
    if (showBbox) overlays.push('bbox')
    if (showKeypoints) overlays.push('keypoints')

    if (overlays.length === 0) {
      setErrorMessage('Please select at least one overlay')
      return
    }

    // Get save location
    const saveDir = await window.electron.selectOutputDirectory()
    if (!saveDir) return

    const videoName = job.videoName?.replace(/\.[^/.]+$/, '') || 'video'
    const outputFile = `${saveDir}/${videoName}_with_overlays.mp4`

    setExportState('exporting')
    setProgress({ phase: 'loading', percent: 0, frame: 0, total: 0 })

    try {
      const result = await window.electron.exportVideoWithOverlays({
        jobId: job.id,
        videoPath: job.videoPath,
        poseCachePath: job.result?.poseMetadataCache || '',
        outputPath: outputFile,
        overlays
      })

      if (result.success) {
        setOutputPath(result.outputPath || outputFile)
        setExportState('complete')
      } else {
        setErrorMessage(result.error || 'Export failed')
        setExportState('error')
      }
    } catch (error: any) {
      setErrorMessage(error.message || 'Export failed')
      setExportState('error')
    }
  }

  const handleCancel = async () => {
    if (exportState === 'exporting') {
      await window.electron.cancelExport(job.id)
    }
    onClose()
  }

  const handleShowInFinder = () => {
    if (outputPath) {
      window.electron.openInFinder(outputPath)
    }
  }

  const handleOpenVideo = () => {
    if (outputPath) {
      window.electron.openFile(outputPath)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 rounded-xl shadow-2xl max-w-lg w-full flex flex-col border border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-600 rounded-lg">
              <Film className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Export with Overlays</h2>
              <p className="text-sm text-slate-400 mt-1">
                {exportState === 'configure' && 'Select overlays to include in export'}
                {exportState === 'exporting' && 'Exporting video...'}
                {exportState === 'complete' && 'Export complete!'}
                {exportState === 'error' && 'Export failed'}
              </p>
            </div>
          </div>
          <button
            onClick={handleCancel}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Configure State */}
        {exportState === 'configure' && (
          <>
            {/* Overlay Options */}
            <div className="p-6 space-y-4">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">Overlay Options</h3>

              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-750 transition-colors">
                  <input
                    type="checkbox"
                    checked={showSkeleton}
                    onChange={(e) => setShowSkeleton(e.target.checked)}
                    className="w-5 h-5 rounded bg-slate-700 border-slate-600 text-green-500 focus:ring-green-500 focus:ring-offset-slate-900"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-white">Skeleton Connections</div>
                    <div className="text-sm text-slate-400">Draw lines connecting body joints</div>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-750 transition-colors">
                  <input
                    type="checkbox"
                    checked={showBbox}
                    onChange={(e) => setShowBbox(e.target.checked)}
                    className="w-5 h-5 rounded bg-slate-700 border-slate-600 text-green-500 focus:ring-green-500 focus:ring-offset-slate-900"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-white">Bounding Boxes</div>
                    <div className="text-sm text-slate-400">Draw person detection boxes with ID labels</div>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-750 transition-colors">
                  <input
                    type="checkbox"
                    checked={showKeypoints}
                    onChange={(e) => setShowKeypoints(e.target.checked)}
                    className="w-5 h-5 rounded bg-slate-700 border-slate-600 text-green-500 focus:ring-green-500 focus:ring-offset-slate-900"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-white">Keypoint Circles</div>
                    <div className="text-sm text-slate-400">Draw circles at each detected joint</div>
                  </div>
                </label>
              </div>

              {errorMessage && (
                <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                  {errorMessage}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-6 bg-slate-800 border-t border-slate-700">
              <button
                onClick={handleCancel}
                className="px-5 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStartExport}
                disabled={!showSkeleton && !showBbox && !showKeypoints}
                className="px-5 py-2.5 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <Download className="w-5 h-5" />
                Export Video
              </button>
            </div>
          </>
        )}

        {/* Exporting State */}
        {exportState === 'exporting' && (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-12 h-12 text-green-500 animate-spin" />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">
                  {progress.phase === 'loading' && 'Loading pose data...'}
                  {progress.phase === 'rendering' && `Rendering frame ${progress.frame} / ${progress.total}`}
                  {progress.phase === 'encoding' && 'Encoding video...'}
                </span>
                <span className="font-mono text-white">{progress.percent}%</span>
              </div>

              <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-green-600 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${progress.percent}%` }}
                />
              </div>

              {progress.message && (
                <p className="text-sm text-slate-400 text-center">{progress.message}</p>
              )}
            </div>

            <div className="flex justify-center">
              <button
                onClick={handleCancel}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-500 rounded-lg font-medium transition-colors"
              >
                Cancel Export
              </button>
            </div>
          </div>
        )}

        {/* Complete State */}
        {exportState === 'complete' && (
          <div className="p-6 space-y-6">
            <div className="flex flex-col items-center py-4">
              <div className="p-3 bg-green-500/20 rounded-full mb-4">
                <CheckCircle className="w-12 h-12 text-green-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Export Complete!</h3>
              <p className="text-slate-400 mt-2 text-center text-sm">
                Your video with overlays has been saved
              </p>
            </div>

            {outputPath && (
              <div className="p-4 bg-slate-800 rounded-lg">
                <div className="text-xs text-slate-400 mb-1">Saved to:</div>
                <div className="text-sm text-white font-mono break-all">{outputPath}</div>
              </div>
            )}

            <div className="flex items-center justify-center gap-3">
              <button
                onClick={handleShowInFinder}
                className="px-5 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <FolderOpen className="w-5 h-5" />
                Show in Finder
              </button>
              <button
                onClick={handleOpenVideo}
                className="px-5 py-2.5 bg-green-600 hover:bg-green-500 rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <Play className="w-5 h-5" />
                Open Video
              </button>
            </div>

            <div className="flex justify-center">
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white transition-colors text-sm"
              >
                Close
              </button>
            </div>
          </div>
        )}

        {/* Error State */}
        {exportState === 'error' && (
          <div className="p-6 space-y-6">
            <div className="flex flex-col items-center py-4">
              <div className="p-3 bg-red-500/20 rounded-full mb-4">
                <X className="w-12 h-12 text-red-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Export Failed</h3>
              <p className="text-slate-400 mt-2 text-center text-sm">
                {errorMessage || 'An error occurred during export'}
              </p>
            </div>

            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setExportState('configure')}
                className="px-5 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={onClose}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-500 rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
