import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Clock, CheckCircle2, XCircle, Loader2, Download, Film } from 'lucide-react'
import { useJobsStore } from '../stores/jobsStore'
import { usePoseVisualizationStore } from '../stores/poseVisualizationStore'
import { PoseVideoPlayer } from '../components/PoseVideoPlayer'
import { ExportModal } from '../components/ExportModal'

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const { jobs, getJob } = useJobsStore()
  const { events, loadPoseEvents, loadPoseMetadataCache, seekToTime } = usePoseVisualizationStore()

  const [job, setJob] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedEventType, setSelectedEventType] = useState<'all' | 'enter' | 'exit'>('all')
  const [showExportModal, setShowExportModal] = useState(false)

  // Load job data
  useEffect(() => {
    if (!jobId) return

    const loadJobData = async () => {
      setLoading(true)
      const jobData = await getJob(jobId)
      setJob(jobData)
      setLoading(false)

      // Load pose events and metadata cache if job is completed
      if (jobData?.status === 'completed') {
        await loadPoseEvents(jobId)
        await loadPoseMetadataCache(jobId)
      }
    }

    loadJobData()
  }, [jobId, getJob, loadPoseEvents, loadPoseMetadataCache])

  // Auto-refresh while processing
  useEffect(() => {
    if (!jobId || !job || job.status === 'completed' || job.status === 'failed') {
      return
    }

    const interval = setInterval(async () => {
      const updatedJob = await getJob(jobId)
      setJob(updatedJob)

      // Load events and metadata cache when job completes
      if (updatedJob?.status === 'completed' && job.status !== 'completed') {
        await loadPoseEvents(jobId)
        await loadPoseMetadataCache(jobId)
      }
    }, 2000) // Refresh every 2 seconds

    return () => clearInterval(interval)
  }, [jobId, job, getJob, loadPoseEvents, loadPoseMetadataCache])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-white text-xl mb-4">Job not found</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    )
  }

  const isProcessing = job.status === 'running' || job.status === 'queued'
  const isCompleted = job.status === 'completed'
  const isFailed = job.status === 'failed'

  const filteredEvents = selectedEventType === 'all'
    ? events
    : events.filter(e => e.eventType === selectedEventType)

  const enterEvents = events.filter(e => e.eventType === 'enter').length
  const exitEvents = events.filter(e => e.eventType === 'exit').length

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString()
  }

  const handleEventClick = (timestamp: number) => {
    seekToTime(timestamp)
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Upload
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">{job.videoName}</h1>
              <p className="text-slate-400 text-sm mt-1">
                Created {formatDate(job.createdAt)}
              </p>
            </div>

            {/* Status Badge and Actions */}
            <div className="flex items-center gap-3">
              {isProcessing && (
                <div className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="font-medium">Processing</span>
                </div>
              )}
              {isCompleted && (
                <>
                  <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg">
                    <CheckCircle2 className="w-4 h-4" />
                    <span className="font-medium">Completed</span>
                  </div>
                  {job.result?.poseMetadataCache && (
                    <button
                      onClick={() => setShowExportModal(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors font-medium"
                    >
                      <Film className="w-4 h-4" />
                      Export with Overlays
                    </button>
                  )}
                </>
              )}
              {isFailed && (
                <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg">
                  <XCircle className="w-4 h-4" />
                  <span className="font-medium">Failed</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Processing Progress */}
        {isProcessing && (
          <div className="bg-slate-800 rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Processing Progress</h2>
              <span className="text-slate-400">
                {job.chunksCompleted || 0} / {job.chunkCount || 0} chunks
              </span>
            </div>

            <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                style={{
                  width: `${job.chunkCount > 0 ? (job.chunksCompleted / job.chunkCount) * 100 : 0}%`
                }}
              />
            </div>

            <div className="mt-4 text-slate-400 text-sm">
              {job.progress?.message || 'Initializing...'}
            </div>
          </div>
        )}

        {/* Error Display */}
        {isFailed && job.error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-6 mb-6">
            <h3 className="text-red-400 font-semibold mb-2">Error</h3>
            <p className="text-slate-300">{job.error.message || 'Processing failed'}</p>
          </div>
        )}

        {/* Video Player & Pose Visualization */}
        {isCompleted && job.videoPath && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            {/* Video Player (2/3 width) */}
            <div className="lg:col-span-2">
              <h2 className="text-lg font-semibold mb-3">Video with Pose Detection</h2>
              <PoseVideoPlayer videoPath={job.videoPath} />
            </div>

            {/* Stats Panel (1/3 width) */}
            <div className="space-y-4">
              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Detection Summary</h3>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Total Events</span>
                    <span className="text-2xl font-bold">{events.length}</span>
                  </div>

                  <div className="h-px bg-slate-700" />

                  <div className="flex justify-between items-center">
                    <span className="text-green-400">Enter Events</span>
                    <span className="text-xl font-semibold text-green-400">{enterEvents}</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-red-400">Exit Events</span>
                    <span className="text-xl font-semibold text-red-400">{exitEvents}</span>
                  </div>

                  <div className="h-px bg-slate-700" />

                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Video Duration</span>
                    <span className="font-mono">{job.videoDuration ? formatTime(job.videoDuration) : 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Pose Metadata Info */}
              {job.result?.poseMetadataCache && (
                <div className="bg-slate-800 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-3">Metadata</h3>
                  <div className="text-sm text-slate-400">
                    <p className="mb-2">Cached pose data available</p>
                    <button
                      onClick={() => window.electron.openInFinder(job.result.poseMetadataCache)}
                      className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      Open Cache Folder
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Events Table */}
        {isCompleted && events.length > 0 && (
          <div className="bg-slate-800 rounded-lg overflow-hidden">
            <div className="p-6 border-b border-slate-700">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Pose Events Timeline</h2>

                {/* Filter Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => setSelectedEventType('all')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      selectedEventType === 'all'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    All ({events.length})
                  </button>
                  <button
                    onClick={() => setSelectedEventType('enter')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      selectedEventType === 'enter'
                        ? 'bg-green-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    Enter ({enterEvents})
                  </button>
                  <button
                    onClick={() => setSelectedEventType('exit')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      selectedEventType === 'exit'
                        ? 'bg-red-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    Exit ({exitEvents})
                  </button>
                </div>
              </div>
            </div>

            {/* Scrollable Table Container */}
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <table className="w-full">
                <thead className="bg-slate-900/50 sticky top-0 z-10">
                  <tr>
                    <th className="text-left px-6 py-3 text-sm font-semibold text-slate-400">Timestamp</th>
                    <th className="text-left px-6 py-3 text-sm font-semibold text-slate-400">Event</th>
                    <th className="text-left px-6 py-3 text-sm font-semibold text-slate-400">Person ID</th>
                    <th className="text-left px-6 py-3 text-sm font-semibold text-slate-400">Confidence</th>
                    <th className="text-left px-6 py-3 text-sm font-semibold text-slate-400">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.map((event, idx) => (
                    <tr
                      key={idx}
                      className="border-t border-slate-700 hover:bg-slate-700/50 transition-colors"
                    >
                      <td
                        className="px-6 py-4 text-sm font-mono flex items-center gap-2 cursor-pointer hover:text-blue-400 transition-colors"
                        onClick={() => handleEventClick(event.timestamp)}
                        title="Click to seek to this time"
                      >
                        <Clock className="w-4 h-4 text-slate-500" />
                        {formatTime(event.timestamp)}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                            event.eventType === 'enter'
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {event.eventType.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">Person {event.personId}</td>
                      <td className="px-6 py-4 text-sm">{(event.confidence * 100).toFixed(1)}%</td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleEventClick(event.timestamp)}
                          className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
                        >
                          Seek →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* No Events Message */}
        {isCompleted && events.length === 0 && (
          <div className="bg-slate-800 rounded-lg p-12 text-center">
            <p className="text-slate-400 text-lg">No pose events detected in this video.</p>
          </div>
        )}
      </div>

      {/* Export Modal */}
      {job && (
        <ExportModal
          isOpen={showExportModal}
          job={job}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </div>
  )
}
