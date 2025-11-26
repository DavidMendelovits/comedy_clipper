import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { PipelineConfigForm } from '../components/pipeline'
import { getPipelineSchema } from '../schemas'

interface JobProgressState {
  percent: number
  chunksCompleted: number
  chunkCount: number
  message?: string
  status: 'creating' | 'starting' | 'processing' | 'completed' | 'failed'
}

export function UploadPage() {
  const navigate = useNavigate()
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [pipelineConfig, setPipelineConfig] = useState<Record<string, any> | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [jobProgress, setJobProgress] = useState<JobProgressState | null>(null)
  const unsubscribersRef = useRef<Array<() => void>>([])

  // Get pose detection schema
  const poseSchema = getPipelineSchema('pose_detection')

  // Cleanup event listeners on unmount
  useEffect(() => {
    return () => {
      unsubscribersRef.current.forEach(unsub => unsub())
      unsubscribersRef.current = []
    }
  }, [])

  const handleVideoSelect = async (file: File | null, filePath?: string) => {
    if (!file && !filePath) return

    setIsUploading(true)

    try {
      // Get the actual file path
      const videoPath = filePath || (file as any).path

      if (!videoPath) {
        console.error('No video path available')
        setIsUploading(false)
        return
      }

      // Get video duration (optional)
      try {
        await window.electron?.getVideoDuration?.(videoPath)
      } catch (e) {
        // Duration not critical, continue
      }

      // Create job with pipeline configuration
      const result = await window.electron.createJob({
        type: 'pose_detection',
        videoPath,
        config: pipelineConfig || {}
      })

      if (!result || 'error' in result) {
        console.error('Failed to create job:', result)
        setIsUploading(false)
        return
      }

      const { jobId } = result

      // Update state to show we're starting
      setActiveJobId(jobId)
      setJobProgress({
        percent: 0,
        chunksCompleted: 0,
        chunkCount: 0,
        status: 'starting'
      })
      setIsUploading(false)

      // Set up event listeners before starting job
      const unsubProgress = window.electron.onJobProgress((event) => {
        if (event.jobId === jobId) {
          setJobProgress(prev => prev ? {
            ...prev,
            percent: event.progress.percent,
            message: event.progress.message,
            status: 'processing'
          } : prev)
        }
      })

      const unsubChunk = window.electron.onJobChunkComplete((event) => {
        if (event.jobId === jobId) {
          setJobProgress(prev => prev ? {
            ...prev,
            chunksCompleted: event.chunksCompleted,
            chunkCount: event.totalChunks
          } : prev)
        }
      })

      const unsubComplete = window.electron.onJobComplete((event) => {
        if (event.jobId === jobId) {
          setJobProgress(prev => prev ? {
            ...prev,
            status: 'completed',
            percent: 100
          } : prev)
        }
      })

      const unsubError = window.electron.onJobError((event) => {
        if (event.jobId === jobId) {
          setJobProgress(prev => prev ? {
            ...prev,
            status: 'failed',
            message: event.error.message
          } : prev)
        }
      })

      // Store unsubscribers for cleanup
      unsubscribersRef.current = [unsubProgress, unsubChunk, unsubComplete, unsubError]

      // Start job
      await window.electron.startJob(jobId)
    } catch (error) {
      console.error('Error uploading video:', error)
      setIsUploading(false)
      setJobProgress(null)
      setActiveJobId(null)
    }
  }

  const handleFileBrowse = async () => {
    const videoPath = await window.electron.selectVideo()
    if (videoPath) {
      await handleVideoSelect(null, videoPath)
    }
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const videoFile = files.find(f =>
      f.type.startsWith('video/') ||
      f.name.match(/\.(mp4|mov|avi|mkv|webm)$/i)
    )

    if (videoFile) {
      await handleVideoSelect(videoFile)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  // Show progress UI when job is active
  if (jobProgress) {
    const isProcessing = jobProgress.status === 'starting' || jobProgress.status === 'processing'
    const isCompleted = jobProgress.status === 'completed'
    const isFailed = jobProgress.status === 'failed'

    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-8">
        <div className="max-w-2xl w-full">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-white mb-3">
              Video Pose Detection
            </h1>
            <p className="text-slate-400 text-lg">
              {isProcessing && 'Processing your video...'}
              {isCompleted && 'Processing complete!'}
              {isFailed && 'Processing failed'}
            </p>
          </div>

          <div className="border-2 border-dashed rounded-2xl p-16 text-center border-slate-700 bg-slate-800/50">
            {/* Status icon */}
            {isProcessing && (
              <Loader2 className="w-16 h-16 mx-auto mb-4 text-blue-500 animate-spin" />
            )}
            {isCompleted && (
              <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-500" />
            )}
            {isFailed && (
              <XCircle className="w-16 h-16 mx-auto mb-4 text-red-500" />
            )}

            {/* Status text */}
            <p className="text-xl text-white font-medium mb-4">
              {jobProgress.status === 'starting' && 'Starting job...'}
              {jobProgress.status === 'processing' && 'Processing Video...'}
              {jobProgress.status === 'completed' && 'Processing Complete!'}
              {jobProgress.status === 'failed' && 'Processing Failed'}
            </p>

            {/* Progress bar */}
            {isProcessing && (
              <div className="w-full bg-slate-700 rounded-full h-3 mb-4">
                <div
                  className="bg-blue-600 h-full rounded-full transition-all duration-300"
                  style={{ width: `${jobProgress.percent}%` }}
                />
              </div>
            )}

            {/* Chunk progress */}
            {isProcessing && jobProgress.chunkCount > 0 && (
              <p className="text-slate-400 mb-2">
                {jobProgress.chunksCompleted} / {jobProgress.chunkCount} chunks completed
              </p>
            )}

            {/* Percentage */}
            {isProcessing && (
              <p className="text-slate-500 text-sm mb-4">
                {jobProgress.percent.toFixed(0)}% complete
              </p>
            )}

            {/* Status message */}
            {jobProgress.message && (
              <p className="text-slate-500 text-sm mb-4">{jobProgress.message}</p>
            )}

            {/* Action buttons */}
            <div className="flex justify-center gap-4 mt-6">
              {isProcessing && (
                <button
                  onClick={() => navigate(`/jobs/${activeJobId}`)}
                  className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
                >
                  View Details →
                </button>
              )}
              {isCompleted && (
                <button
                  onClick={() => navigate(`/jobs/${activeJobId}`)}
                  className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                >
                  View Results →
                </button>
              )}
              {isFailed && (
                <>
                  <button
                    onClick={() => {
                      setJobProgress(null)
                      setActiveJobId(null)
                      unsubscribersRef.current.forEach(unsub => unsub())
                      unsubscribersRef.current = []
                    }}
                    className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={() => navigate(`/jobs/${activeJobId}`)}
                    className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                  >
                    View Details →
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="mt-8 text-center">
            <button
              onClick={() => navigate('/jobs')}
              className="text-slate-400 hover:text-white transition-colors"
            >
              View All Jobs →
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-3">
            Video Pose Detection
          </h1>
          <p className="text-slate-400 text-lg">
            Upload a video to detect pose events with YOLO
          </p>
        </div>

        <div
          className={`
            border-2 border-dashed rounded-2xl p-16 text-center
            transition-all duration-200
            ${isDragging
              ? 'border-blue-500 bg-blue-500/10'
              : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
            }
            ${isUploading ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
          `}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={!isUploading ? handleFileBrowse : undefined}
        >
          {isUploading ? (
            <Loader2 className="w-16 h-16 mx-auto mb-4 text-blue-500 animate-spin" />
          ) : (
            <Upload
              className={`w-16 h-16 mx-auto mb-4 ${isDragging ? 'text-blue-500' : 'text-slate-500'}`}
            />
          )}

          {isUploading ? (
            <>
              <p className="text-xl text-white font-medium mb-2">
                Creating job...
              </p>
              <p className="text-slate-400">
                Please wait while we set up your video processing
              </p>
            </>
          ) : (
            <>
              <p className="text-xl text-white font-medium mb-2">
                Drop a video here or click to browse
              </p>
              <p className="text-slate-400 mb-6">
                Supported formats: MP4, MOV, AVI, MKV, WebM
              </p>

              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleFileBrowse()
                }}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Select Video
              </button>
            </>
          )}
        </div>

        {/* Pipeline Configuration Form */}
        {poseSchema && (
          <div className="mt-8">
            <PipelineConfigForm
              schema={poseSchema}
              onConfigChange={setPipelineConfig}
              disabled={isUploading}
            />
          </div>
        )}

        <div className="mt-8 text-center">
          <button
            onClick={() => navigate('/jobs')}
            className="text-slate-400 hover:text-white transition-colors"
          >
            View Recent Jobs →
          </button>
        </div>
      </div>
    </div>
  )
}
