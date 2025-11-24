/**
 * Job History Page
 * List and filter all processing jobs
 */

import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter } from 'lucide-react';
import { useJobsStore } from '../stores/jobsStore';
import type { JobStatus } from '../types/jobs';

export function JobHistoryPage() {
  const navigate = useNavigate();
  const jobsRecord = useJobsStore((state) => state.jobs);
  const loading = useJobsStore((state) => state.loading);

  // Convert jobs record to array only when the record changes
  const jobs = useMemo(() => Object.values(jobsRecord), [jobsRecord]);

  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Load jobs on mount
  useEffect(() => {
    const loadJobsAsync = async () => {
      await useJobsStore.getState().loadJobs();
    };
    loadJobsAsync();
  }, []);

  // Auto-refresh when there are running jobs
  useEffect(() => {
    const hasActiveJobs = jobs.some(
      (job) => job.status === 'running' || job.status === 'queued'
    );

    if (!hasActiveJobs) {
      return; // No active jobs, don't poll
    }

    // Poll every 2 seconds while there are active jobs
    const intervalId = setInterval(async () => {
      await useJobsStore.getState().loadJobs();
    }, 2000);

    return () => clearInterval(intervalId);
  }, [jobs]);

  // Filter jobs
  const filteredJobs = jobs.filter((job) => {
    const matchesStatus = statusFilter === 'all' || job.status === statusFilter;
    const matchesSearch =
      searchQuery === '' ||
      job.videoName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  // Sort by creation date (newest first)
  const sortedJobs = [...filteredJobs].sort((a, b) => b.createdAt - a.createdAt);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-3xl font-bold text-[var(--color-text-primary)]">
            Job History
          </h2>
          <p className="text-[var(--color-text-muted)] mt-2">
            View and manage all your processing jobs
          </p>
        </div>

        {/* Filters */}
        <div className="flex gap-4 flex-wrap">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[var(--color-text-muted)]"
                size={18}
              />
              <input
                type="text"
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          </div>

          {/* Status Filter */}
          <div className="flex gap-2 items-center">
            <Filter size={18} className="text-[var(--color-text-muted)]" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as JobStatus | 'all')}
              className="px-4 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]"
            >
              <option value="all">All Status</option>
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        {/* Jobs List */}
        {loading ? (
          <div className="text-center py-12 text-[var(--color-text-muted)]">
            Loading jobs...
          </div>
        ) : sortedJobs.length === 0 ? (
          <div className="text-center py-12 text-[var(--color-text-muted)]">
            {searchQuery || statusFilter !== 'all'
              ? 'No jobs match your filters'
              : 'No jobs yet. Process a video to get started!'}
          </div>
        ) : (
          <div className="space-y-2">
            {sortedJobs.map((job) => (
              <div
                key={job.id}
                onClick={() => navigate(`/jobs/${job.id}`)}
                className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4 hover:border-[var(--color-primary)] transition-colors cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-[var(--color-text-primary)] font-medium">
                      {job.videoName}
                    </h3>
                    <p className="text-[var(--color-text-muted)] text-sm mt-1">
                      Created: {new Date(job.createdAt).toLocaleString()}
                    </p>
                    {job.status === 'running' && (
                      <div className="mt-2">
                        <div className="w-full bg-[var(--color-bg-tertiary)] rounded-full h-2">
                          <div
                            className="bg-[var(--color-primary)] h-2 rounded-full transition-all"
                            style={{ width: `${job.progress.percent}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4 ml-4">
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                        job.status === 'completed'
                          ? 'bg-[var(--color-accent-light)] text-[var(--color-accent)]'
                          : job.status === 'failed'
                          ? 'bg-red-500/10 text-[var(--color-error)]'
                          : job.status === 'running'
                          ? 'bg-amber-500/10 text-[var(--color-warning)]'
                          : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]'
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
