/**
 * Jobs Store
 * Manages all processing jobs with persistence and IPC integration
 */

import { create } from 'zustand';
import type {
  Job,
  JobFilter,
  CreateJobInput,
  JobProgressEvent,
  JobLogEvent,
  JobCompleteEvent,
  JobErrorEvent,
  JobStatusChangeEvent,
} from '../types/jobs';

interface JobsState {
  // State
  jobs: Record<string, Job>;
  activeJobId: string | null;
  loading: boolean;
  error: string | null;

  // Statistics
  statistics: {
    total: number;
    queued: number;
    running: number;
    completed: number;
    failed: number;
    cancelled: number;
  };

  // Actions
  createJob: (input: CreateJobInput) => Promise<string | null>;
  startJob: (jobId: string) => Promise<boolean>;
  cancelJob: (jobId: string) => Promise<boolean>;
  deleteJob: (jobId: string) => Promise<boolean>;

  // Queries
  getJob: (jobId: string) => Promise<Job | null>;
  loadJobs: (filter?: JobFilter) => Promise<void>;
  loadJobStatistics: () => Promise<void>;

  // Event handlers (called by IPC listeners)
  handleJobProgress: (event: JobProgressEvent) => void;
  handleJobLog: (event: JobLogEvent) => void;
  handleJobComplete: (event: JobCompleteEvent) => void;
  handleJobError: (event: JobErrorEvent) => void;
  handleJobStatusChange: (event: JobStatusChangeEvent) => void;
  handleJobChunkComplete: (event: any) => void;

  // Selectors
  getActiveJob: () => Job | undefined;
  getJobsByStatus: (status: Job['status']) => Job[];
  getRecentJobs: (limit: number) => Job[];
  getActiveJobsCount: () => number;

  // Utilities
  setActiveJobId: (jobId: string | null) => void;
  clearError: () => void;
}

export const useJobsStore = create<JobsState>((set, get) => ({
  // Initial state
  jobs: {},
  activeJobId: null,
  loading: false,
  error: null,
  statistics: {
    total: 0,
    queued: 0,
    running: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
  },

  // Create a new job
  createJob: async (input: CreateJobInput) => {
    try {
      set({ loading: true, error: null });

      const response = await window.electron?.createJob(input);

      if (response?.jobId) {
        // Load the newly created job
        const job = await window.electron?.getJob(response.jobId);
        if (job) {
          set((state) => ({
            jobs: { ...state.jobs, [job.id]: job },
            loading: false,
          }));
        }
        return response.jobId;
      }

      set({ loading: false, error: 'Failed to create job' });
      return null;
    } catch (error: any) {
      set({ loading: false, error: error.message });
      return null;
    }
  },

  // Start a job
  startJob: async (jobId: string) => {
    try {
      set({ loading: true, error: null, activeJobId: jobId });

      const response = await window.electron?.startJob(jobId);

      if (response?.success) {
        set({ loading: false });
        return true;
      }

      set({ loading: false, error: response?.error || 'Failed to start job' });
      return false;
    } catch (error: any) {
      set({ loading: false, error: error.message });
      return false;
    }
  },

  // Cancel a job
  cancelJob: async (jobId: string) => {
    try {
      const response = await window.electron?.cancelJob(jobId);

      if (response?.success) {
        set((state) => {
          const updatedJobs = { ...state.jobs };
          if (updatedJobs[jobId]) {
            updatedJobs[jobId] = {
              ...updatedJobs[jobId],
              status: 'cancelled',
              completedAt: Date.now(),
            };
          }
          return { jobs: updatedJobs };
        });
        return true;
      }

      return false;
    } catch (error) {
      console.error('Error cancelling job:', error);
      return false;
    }
  },

  // Delete a job
  deleteJob: async (jobId: string) => {
    try {
      const response = await window.electron?.deleteJob(jobId);

      if (response?.success) {
        set((state) => {
          const updatedJobs = { ...state.jobs };
          delete updatedJobs[jobId];
          return {
            jobs: updatedJobs,
            activeJobId: state.activeJobId === jobId ? null : state.activeJobId,
          };
        });
        return true;
      }

      return false;
    } catch (error) {
      console.error('Error deleting job:', error);
      return false;
    }
  },

  // Get a specific job
  getJob: async (jobId: string) => {
    try {
      const job = await window.electron?.getJob(jobId);

      if (job) {
        set((state) => ({
          jobs: { ...state.jobs, [job.id]: job },
        }));
        return job;
      }

      return null;
    } catch (error) {
      console.error('Error getting job:', error);
      return null;
    }
  },

  // Load jobs with optional filtering
  loadJobs: async (filter?: JobFilter) => {
    try {
      set({ loading: true, error: null });

      const jobs = await window.electron?.getJobs(filter);

      if (jobs) {
        const jobsMap = jobs.reduce((acc, job) => {
          acc[job.id] = job;
          return acc;
        }, {} as Record<string, Job>);

        set({ jobs: jobsMap, loading: false });
      } else {
        set({ loading: false });
      }
    } catch (error: any) {
      set({ loading: false, error: error.message });
    }
  },

  // Load job statistics
  loadJobStatistics: async () => {
    try {
      const stats = await window.electron?.getJobStatistics();

      if (stats) {
        set({ statistics: stats });
      }
    } catch (error) {
      console.error('Error loading job statistics:', error);
    }
  },

  // Handle job progress event
  handleJobProgress: (event: JobProgressEvent) => {
    console.log('[JobStore] Progress event:', event);
    set((state) => {
      const job = state.jobs[event.jobId];
      if (!job) {
        console.warn('[JobStore] Job not found for progress event:', event.jobId);
        return state;
      }

      console.log('[JobStore] Updating job progress:', event.jobId, event.progress);
      return {
        jobs: {
          ...state.jobs,
          [event.jobId]: {
            ...job,
            progress: event.progress,
          },
        },
      };
    });
  },

  // Handle job log event
  handleJobLog: (event: JobLogEvent) => {
    set((state) => {
      const job = state.jobs[event.jobId];
      if (!job) return state;

      return {
        jobs: {
          ...state.jobs,
          [event.jobId]: {
            ...job,
            logs: [...job.logs, event.log],
          },
        },
      };
    });
  },

  // Handle job complete event
  handleJobComplete: (event: JobCompleteEvent) => {
    set((state) => {
      const job = state.jobs[event.jobId];
      if (!job) return state;

      return {
        jobs: {
          ...state.jobs,
          [event.jobId]: {
            ...job,
            status: 'completed',
            result: event.result,
            completedAt: Date.now(),
            progress: { ...job.progress, percent: 100 },
          },
        },
        activeJobId: state.activeJobId === event.jobId ? null : state.activeJobId,
      };
    });
  },

  // Handle job error event
  handleJobError: (event: JobErrorEvent) => {
    set((state) => {
      const job = state.jobs[event.jobId];
      if (!job) return state;

      return {
        jobs: {
          ...state.jobs,
          [event.jobId]: {
            ...job,
            status: 'failed',
            error: event.error,
            completedAt: Date.now(),
          },
        },
        activeJobId: state.activeJobId === event.jobId ? null : state.activeJobId,
      };
    });
  },

  // Handle job status change event
  handleJobStatusChange: (event: JobStatusChangeEvent) => {
    set((state) => {
      const job = state.jobs[event.jobId];
      if (!job) return state;

      const updates: Partial<Job> = { status: event.status };

      if (event.status === 'running') {
        updates.startedAt = event.timestamp || Date.now();
      } else if (['completed', 'failed', 'cancelled'].includes(event.status)) {
        updates.completedAt = event.timestamp || Date.now();
      }

      return {
        jobs: {
          ...state.jobs,
          [event.jobId]: {
            ...job,
            ...updates,
          },
        },
      };
    });
  },

  // Handle chunk completion event
  handleJobChunkComplete: (event: any) => {
    console.log('[JobStore] Chunk complete event:', event);
    set((state) => {
      const job = state.jobs[event.jobId];
      if (!job) {
        console.warn('[JobStore] Job not found for chunk complete event:', event.jobId);
        return state;
      }

      return {
        jobs: {
          ...state.jobs,
          [event.jobId]: {
            ...job,
            chunkCount: event.totalChunks,
            chunksCompleted: event.chunksCompleted,
            progress: {
              ...job.progress,
              percent: Math.round((event.chunksCompleted / event.totalChunks) * 100),
              message: `Processing chunk ${event.chunksCompleted}/${event.totalChunks}`
            }
          },
        },
      };
    });
  },

  // Get active job
  getActiveJob: () => {
    const state = get();
    return state.activeJobId ? state.jobs[state.activeJobId] : undefined;
  },

  // Get jobs by status
  getJobsByStatus: (status: Job['status']) => {
    const state = get();
    return Object.values(state.jobs).filter((job) => job.status === status);
  },

  // Get recent jobs
  getRecentJobs: (limit: number) => {
    const state = get();
    return Object.values(state.jobs)
      .sort((a, b) => b.createdAt - a.createdAt)
      .slice(0, limit);
  },

  // Get count of active jobs (running + queued)
  getActiveJobsCount: () => {
    const state = get();
    return Object.values(state.jobs).filter(
      (job) => job.status === 'running' || job.status === 'queued'
    ).length;
  },

  // Set active job ID
  setActiveJobId: (jobId: string | null) => {
    set({ activeJobId: jobId });
  },

  // Clear error
  clearError: () => {
    set({ error: null });
  },
}));

// Setup IPC event listeners
export function setupJobEventListeners() {
  console.log('[JobStore] Setting up job event listeners...');
  const store = useJobsStore.getState();

  if (!window.electron) {
    console.error('[JobStore] window.electron not available!');
    return;
  }

  // Job progress
  if (window.electron.onJobProgress) {
    window.electron.onJobProgress((event) => {
      console.log('[JobStore] Received job progress event:', event);
      store.handleJobProgress(event);
    });
    console.log('[JobStore] ✓ Job progress listener registered');
  }

  // Job logs
  if (window.electron.onJobLog) {
    window.electron.onJobLog((event) => {
      console.log('[JobStore] Received job log event:', event);
      store.handleJobLog(event);
    });
    console.log('[JobStore] ✓ Job log listener registered');
  }

  // Job complete
  if (window.electron.onJobComplete) {
    window.electron.onJobComplete((event) => {
      console.log('[JobStore] Received job complete event:', event);
      store.handleJobComplete(event);
      // Reload statistics
      store.loadJobStatistics();
    });
    console.log('[JobStore] ✓ Job complete listener registered');
  }

  // Job error
  if (window.electron.onJobError) {
    window.electron.onJobError((event) => {
      console.log('[JobStore] Received job error event:', event);
      store.handleJobError(event);
      // Reload statistics
      store.loadJobStatistics();
    });
    console.log('[JobStore] ✓ Job error listener registered');
  }

  // Job status change
  if (window.electron.onJobStatusChange) {
    window.electron.onJobStatusChange((event) => {
      console.log('[JobStore] Received job status change event:', event);
      store.handleJobStatusChange(event);
      // Reload statistics
      store.loadJobStatistics();
    });
    console.log('[JobStore] ✓ Job status change listener registered');
  }

  // Chunk completion (new for pose processing)
  if (window.electron.onJobChunkComplete) {
    window.electron.onJobChunkComplete((event) => {
      console.log('[JobStore] Received chunk complete event:', event);
      store.handleJobChunkComplete(event);
    });
    console.log('[JobStore] ✓ Chunk complete listener registered');
  }

  console.log('[JobStore] ✅ All job event listeners initialized');
}
