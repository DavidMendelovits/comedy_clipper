/**
 * Job Management Type Definitions
 * Comprehensive types for the job tracking and management system
 */

// ============================================================================
// Job Status & Types
// ============================================================================

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
export type JobType = 'clipper' | 'comparison' | 'reclip';

// ============================================================================
// Job Configuration Types
// ============================================================================

export interface ClipperJobConfig {
  clipperType: string;
  minDuration: number;
  maxDuration?: number;
  outputDir?: string;
  debug?: boolean;
  // Position detection settings
  exitThreshold?: number;
  exitStabilityFrames?: number;
  // YOLO settings
  yoloModel?: string;
  yoloEnabled?: boolean;
  personCountMethod?: string;
  zoneCrossingEnabled?: boolean;
  configFile?: string;
  // Overlay video settings
  exportOverlayVideo?: boolean;
  overlayIncludeSkeletons?: boolean;
  overlayIncludeBoundingBoxes?: boolean;
  overlayShowInfo?: boolean;
}

export interface ComparisonJobConfig {
  modelIds: string[];
  overlayConfig?: any;
}

export interface ReclipJobConfig {
  segments: Array<{ start: number; end: number }>;
  outputDir?: string;
  debug?: boolean;
}

export type JobConfig = ClipperJobConfig | ComparisonJobConfig | ReclipJobConfig;

// ============================================================================
// Job Progress
// ============================================================================

export interface JobProgress {
  percent: number;
  phase?: string;
  message?: string;
  currentFrame?: number;
  totalFrames?: number;
  steps: string[];
}

// ============================================================================
// Job Results
// ============================================================================

export interface Clip {
  name: string;
  path: string;
  size: number;
  duration?: number;
}

export interface VideoSegment {
  start: number;
  end: number;
  score?: number;
  metadata?: Record<string, any>;
}

export interface DebugFrame {
  path: string;
  name: string;
  category: string;
  sortKey: string;
}

export interface ClipperJobResult {
  clips: Clip[];
  segmentsDetected: VideoSegment[];
  segmentsFiltered: VideoSegment[];
  outputDir?: string;
  debugDir?: string;
  debugFrames?: DebugFrame[];
  overlayVideo?: string; // Path to full video with pose detection overlays
}

export interface ComparisonJobResult {
  results: Array<{
    modelId: string;
    clips?: Clip[];
    performance?: {
      fps: number;
      processingTime: number;
    };
    error?: string;
  }>;
  reportPath?: string;
}

export interface ReclipJobResult {
  clips: Clip[];
  outputDir?: string;
}

export type JobResult = ClipperJobResult | ComparisonJobResult | ReclipJobResult;

// ============================================================================
// Job Logging
// ============================================================================

export interface JobLog {
  timestamp: number;
  level: 'info' | 'warning' | 'error';
  message: string;
}

// ============================================================================
// Job Error
// ============================================================================

export interface JobError {
  message: string;
  code?: string;
  stack?: string;
}

// ============================================================================
// Core Job Interface
// ============================================================================

export interface Job {
  // Identity
  id: string;
  type: JobType;

  // Lifecycle
  status: JobStatus;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;

  // Input Configuration
  videoPath: string;
  videoName: string;
  videoDuration?: number;
  config: JobConfig;

  // Progress Tracking
  progress: JobProgress;

  // Outputs
  result?: JobResult;

  // Logging
  logs: JobLog[];
  logFile?: string;

  // Error Handling
  error?: JobError;
}

// ============================================================================
// Job Filters & Queries
// ============================================================================

export interface JobFilter {
  status?: JobStatus | JobStatus[];
  type?: JobType | JobType[];
  startDate?: number;
  endDate?: number;
  videoPath?: string;
  limit?: number;
  offset?: number;
}

export interface JobQueryOptions {
  sortBy?: 'createdAt' | 'startedAt' | 'completedAt' | 'status';
  sortOrder?: 'asc' | 'desc';
  includeDeleted?: boolean;
}

// ============================================================================
// Job Statistics
// ============================================================================

export interface JobStatistics {
  total: number;
  queued: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  successRate: number;
  averageDuration: number;
}

// ============================================================================
// Job Creation Inputs
// ============================================================================

export interface CreateJobInput {
  type: JobType;
  videoPath: string;
  config: JobConfig;
}

// ============================================================================
// Job Update Inputs
// ============================================================================

export interface UpdateJobProgressInput {
  jobId: string;
  progress: Partial<JobProgress>;
}

export interface AddJobLogInput {
  jobId: string;
  log: Omit<JobLog, 'timestamp'>;
}

export interface CompleteJobInput {
  jobId: string;
  result: JobResult;
}

export interface FailJobInput {
  jobId: string;
  error: JobError;
}

// ============================================================================
// IPC Event Payloads
// ============================================================================

export interface JobProgressEvent {
  jobId: string;
  progress: JobProgress;
}

export interface JobLogEvent {
  jobId: string;
  log: JobLog;
}

export interface JobCompleteEvent {
  jobId: string;
  result: JobResult;
}

export interface JobErrorEvent {
  jobId: string;
  error: JobError;
}

export interface JobStatusChangeEvent {
  jobId: string;
  status: JobStatus;
  previousStatus: JobStatus;
  timestamp?: number;
}
