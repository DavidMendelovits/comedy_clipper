/**
 * Job Detail Page
 * Detailed view of a specific job including results
 */

import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, X, Trash2, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { useJobsStore } from '../stores/jobsStore';
import { ResultsTab } from '../components/tabs/ResultsTab';
import { useResultsStore, useComparisonStore } from '../stores';

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const jobs = useJobsStore((state) => state.jobs);

  // Get job from state, or fetch if not loaded
  const job = jobId ? jobs[jobId] : undefined;

  // Load job initially and when jobId changes
  useEffect(() => {
    if (jobId) {
      useJobsStore.getState().getJob(jobId);
    }
  }, [jobId]);

  // Refresh job periodically while it's running
  useEffect(() => {
    if (!jobId || !job || job.status !== 'running') return;

    const intervalId = setInterval(() => {
      console.log('Refreshing job:', jobId);
      useJobsStore.getState().getJob(jobId);
    }, 2000); // Refresh every 2 seconds

    return () => clearInterval(intervalId);
  }, [jobId, job?.status]);

  // Load results into ResultsStore for ResultsTab compatibility
  useEffect(() => {
    if (job?.result && 'clips' in job.result) {
      const resultsStore = useResultsStore.getState();
      resultsStore.setClips(job.result.clips);
      if ('segmentsDetected' in job.result && job.result.segmentsDetected) {
        resultsStore.setDetectedSegments(job.result.segmentsDetected);
      }
      if ('segmentsFiltered' in job.result && job.result.segmentsFiltered) {
        resultsStore.setFilteredSegments(job.result.segmentsFiltered);
      }

      // Load overlay video into ComparisonStore if available
      if ('overlayVideo' in job.result && job.result.overlayVideo) {
        const comparisonStore = useComparisonStore.getState();
        const modelId = 'clipperType' in job.config ? job.config.clipperType : 'default';
        console.log('[JobDetailPage] Setting overlay video for model:', modelId, job.result.overlayVideo);
        comparisonStore.setOverlayVideo(modelId, job.result.overlayVideo);
      }
    }
  }, [job]);

  if (!job) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto text-[var(--color-text-muted)] animate-spin mb-4" size={48} />
          <p className="text-[var(--color-text-muted)]">Loading job...</p>
        </div>
      </div>
    );
  }

  const statusIcons = {
    queued: Clock,
    running: Loader2,
    completed: CheckCircle,
    failed: XCircle,
    cancelled: XCircle,
  };

  const statusColors = {
    queued: 'text-[var(--color-text-muted)]',
    running: 'text-[var(--color-warning)]',
    completed: 'text-[var(--color-accent)]',
    failed: 'text-[var(--color-error)]',
    cancelled: 'text-[var(--color-text-muted)]',
  };

  const StatusIcon = statusIcons[job.status];

  const handleCancel = async () => {
    if (confirm('Are you sure you want to cancel this job?')) {
      const success = await useJobsStore.getState().cancelJob(job.id);
      if (success) {
        navigate('/jobs');
      }
    }
  };

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this job? This cannot be undone.')) {
      const success = await useJobsStore.getState().deleteJob(job.id);
      if (success) {
        navigate('/jobs');
      }
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/jobs')}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              <ArrowLeft size={24} />
            </button>
            <div>
              <h2 className="text-3xl font-bold text-[var(--color-text-primary)]">
                {job.videoName}
              </h2>
              <p className="text-[var(--color-text-muted)] mt-1">
                Job ID: {job.id}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            {job.status === 'running' && (
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-error)] hover:bg-red-600 text-white rounded-lg transition-colors"
              >
                <X size={18} />
                Cancel
              </button>
            )}
            {job.status !== 'running' && (
              <button
                onClick={handleDelete}
                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg transition-colors"
              >
                <Trash2 size={18} />
                Delete
              </button>
            )}
          </div>
        </div>

        {/* Status Card */}
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6">
          <div className="flex items-center gap-4 mb-4">
            <StatusIcon className={statusColors[job.status]} size={32} />
            <div>
              <h3 className="text-xl font-semibold text-[var(--color-text-primary)] capitalize">
                {job.status}
              </h3>
              <p className="text-[var(--color-text-muted)] text-sm">
                Created {new Date(job.createdAt).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Progress Bar (if running) */}
          {job.status === 'running' && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--color-text-muted)]">
                  {job.progress.message || 'Processing...'}
                </span>
                <span className="text-[var(--color-text-primary)] font-medium">
                  {job.progress.percent.toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-[var(--color-bg-tertiary)] rounded-full h-3">
                <div
                  className="bg-[var(--color-primary)] h-3 rounded-full transition-all"
                  style={{ width: `${job.progress.percent}%` }}
                />
              </div>
              {job.progress.currentFrame && job.progress.totalFrames && (
                <p className="text-sm text-[var(--color-text-muted)]">
                  Frame {job.progress.currentFrame} of {job.progress.totalFrames}
                </p>
              )}
            </div>
          )}

          {/* Error (if failed) */}
          {job.error && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-[var(--color-error)] font-medium">Error:</p>
              <p className="text-[var(--color-text-secondary)] mt-1">{job.error.message}</p>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-[var(--color-border)]">
            <div>
              <p className="text-[var(--color-text-muted)] text-sm">Type</p>
              <p className="text-[var(--color-text-primary)] font-medium capitalize">{job.type}</p>
            </div>
            {job.startedAt && (
              <div>
                <p className="text-[var(--color-text-muted)] text-sm">Started</p>
                <p className="text-[var(--color-text-primary)] font-medium">
                  {new Date(job.startedAt).toLocaleTimeString()}
                </p>
              </div>
            )}
            {job.completedAt && (
              <div>
                <p className="text-[var(--color-text-muted)] text-sm">Completed</p>
                <p className="text-[var(--color-text-primary)] font-medium">
                  {new Date(job.completedAt).toLocaleTimeString()}
                </p>
              </div>
            )}
            {job.result && 'clips' in job.result && (
              <div>
                <p className="text-[var(--color-text-muted)] text-sm">Clips</p>
                <p className="text-[var(--color-text-primary)] font-medium">
                  {job.result.clips.length}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Results (if completed) */}
        {job.status === 'completed' && job.result && 'clips' in job.result && (
          <div>
            <ResultsTab />
          </div>
        )}

        {/* Logs */}
        {job.logs && job.logs.length > 0 && (
          <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6">
            <h3 className="text-xl font-semibold text-[var(--color-text-primary)] mb-4">
              Logs ({job.logs.length})
            </h3>
            <div className="max-h-96 overflow-y-auto space-y-1 font-mono text-sm">
              {job.logs.map((log, index) => (
                <div
                  key={index}
                  className={`${
                    log.level === 'error'
                      ? 'text-[var(--color-error)]'
                      : log.level === 'warning'
                      ? 'text-[var(--color-warning)]'
                      : 'text-[var(--color-text-secondary)]'
                  }`}
                >
                  <span className="text-[var(--color-text-muted)]">
                    [{new Date(log.timestamp).toLocaleTimeString()}]
                  </span>{' '}
                  {log.message}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
