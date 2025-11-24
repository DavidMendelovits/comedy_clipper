/**
 * Dashboard Page
 * Overview of jobs, statistics, and recent activity
 */

import React, { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useJobsStore } from '../stores/jobsStore';
import type { Job } from '../types/jobs';

export function DashboardPage() {
  const navigate = useNavigate();
  const statistics = useJobsStore((state) => state.statistics);
  const jobsRecord = useJobsStore((state) => state.jobs);

  // Get recent jobs - memoized to avoid recreating array on every render
  const recentJobs = useMemo(() => {
    return Object.values(jobsRecord)
      .sort((a, b) => b.createdAt - a.createdAt)
      .slice(0, 5);
  }, [jobsRecord]);

  useEffect(() => {
    useJobsStore.getState().loadJobStatistics();
  }, []);

  const statCards = [
    { label: 'Total Jobs', value: statistics.total, icon: Video, color: 'text-[var(--color-primary)]' },
    { label: 'Running', value: statistics.running, icon: Loader2, color: 'text-[var(--color-warning)]' },
    { label: 'Completed', value: statistics.completed, icon: CheckCircle, color: 'text-[var(--color-accent)]' },
    { label: 'Failed', value: statistics.failed, icon: XCircle, color: 'text-[var(--color-error)]' },
  ];

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-8">
        {/* Header */}
        <div>
          <h2 className="text-3xl font-bold text-[var(--color-text-primary)]">
            Dashboard
          </h2>
          <p className="text-[var(--color-text-muted)] mt-2">
            Overview of your processing jobs and activity
          </p>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 hover:border-[var(--color-primary)] transition-colors cursor-pointer"
                onClick={() => navigate('/jobs')}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[var(--color-text-muted)] text-sm">{stat.label}</p>
                    <p className="text-3xl font-bold text-[var(--color-text-primary)] mt-2">
                      {stat.value}
                    </p>
                  </div>
                  <Icon className={`${stat.color}`} size={32} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => navigate('/process')}
            className="flex items-center gap-4 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg p-6 transition-colors text-left"
          >
            <Video size={32} />
            <div>
              <h3 className="text-lg font-semibold">Process New Video</h3>
              <p className="text-sm opacity-90">Start a new processing job</p>
            </div>
          </button>

          <button
            onClick={() => navigate('/jobs')}
            className="flex items-center gap-4 bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg p-6 transition-colors text-left"
          >
            <Clock size={32} />
            <div>
              <h3 className="text-lg font-semibold">View All Jobs</h3>
              <p className="text-sm text-[var(--color-text-muted)]">Browse job history</p>
            </div>
          </button>
        </div>

        {/* Recent Jobs */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-2xl font-bold text-[var(--color-text-primary)]">
              Recent Jobs
            </h3>
            <button
              onClick={() => navigate('/jobs')}
              className="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] text-sm font-medium"
            >
              View All →
            </button>
          </div>

          {recentJobs.length === 0 ? (
            <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-12 text-center">
              <Video className="mx-auto text-[var(--color-text-muted)] mb-4" size={48} />
              <p className="text-[var(--color-text-muted)]">No jobs yet</p>
              <button
                onClick={() => navigate('/process')}
                className="mt-4 px-6 py-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg transition-colors"
              >
                Process Your First Video
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {recentJobs.map((job) => (
                <JobRow key={job.id} job={job} onClick={() => navigate(`/jobs/${job.id}`)} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Job Row Component
function JobRow({ job, onClick }: { job: Job; onClick: () => void }) {
  const statusColors = {
    queued: 'text-[var(--color-text-muted)]',
    running: 'text-[var(--color-warning)]',
    completed: 'text-[var(--color-accent)]',
    failed: 'text-[var(--color-error)]',
    cancelled: 'text-[var(--color-text-muted)]',
  };

  const statusIcons = {
    queued: Clock,
    running: Loader2,
    completed: CheckCircle,
    failed: XCircle,
    cancelled: XCircle,
  };

  const StatusIcon = statusIcons[job.status];

  return (
    <div
      onClick={onClick}
      className="flex items-center justify-between bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4 hover:border-[var(--color-primary)] transition-colors cursor-pointer"
    >
      <div className="flex items-center gap-4 flex-1">
        <StatusIcon className={statusColors[job.status]} size={20} />
        <div className="flex-1">
          <h4 className="text-[var(--color-text-primary)] font-medium">
            {job.videoName}
          </h4>
          <p className="text-[var(--color-text-muted)] text-sm">
            {new Date(job.createdAt).toLocaleString()}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span className={`text-sm font-medium capitalize ${statusColors[job.status]}`}>
          {job.status}
        </span>
        {job.status === 'running' && (
          <div className="text-[var(--color-text-muted)] text-sm">
            {job.progress.percent.toFixed(0)}%
          </div>
        )}
      </div>
    </div>
  );
}
