import type {
  Job,
  JobFilter,
  CreateJobInput,
  JobProgressEvent,
  JobLogEvent,
  JobCompleteEvent,
  JobErrorEvent,
  JobStatusChangeEvent
} from './jobs';

export interface ElectronAPI {
  // Legacy file operations
  selectVideo: () => Promise<string | null>
  selectOutputDirectory: () => Promise<string | null>
  getVideoDuration?: (filePath: string) => Promise<number>

  // Legacy clipper operations (maintained for backwards compatibility)
  runClipper: (config: {
    videoPath: string
    clipperType: string
    options: Record<string, any>
  }) => Promise<{
    success: boolean
    clips?: Array<{ name: string; path: string }>
    output?: string
    error?: string
  }>
  stopClipper: () => Promise<{ success: boolean; message?: string }>
  reclipSegments: (config: {
    videoPath: string
    segments: Array<{ start: number; end: number }>
    outputDir?: string
    debug?: boolean
  }) => Promise<{
    success: boolean
    clips?: Array<{ name: string; path: string; size: number }>
    output_dir?: string
    log_file?: string
    error?: string
  }>

  // Job Management (New)
  createJob: (input: CreateJobInput) => Promise<{ jobId: string }>
  startJob: (jobId: string) => Promise<{ success: boolean; error?: string }>
  cancelJob: (jobId: string) => Promise<{ success: boolean; error?: string }>
  deleteJob: (jobId: string) => Promise<{ success: boolean; error?: string }>
  getJob: (jobId: string) => Promise<Job | null>
  getJobs: (filter?: JobFilter) => Promise<Job[]>
  getJobStatistics: () => Promise<{
    total: number
    queued: number
    running: number
    completed: number
    failed: number
    cancelled: number
  }>

  // File system operations
  getClips: (directory: string) => Promise<
    Array<{
      name: string
      path: string
      size: number
      modified: Date
    }>
  >
  getDebugFrames: (directory: string) => Promise<
    Array<{
      path: string
      name: string
      dir: string
    }>
  >
  openInFinder: (filePath: string) => Promise<{ success: boolean; error?: string }>
  openFile: (filePath: string) => Promise<{ success: boolean; error?: string }>
  getVideoUrl: (filePath: string) => string
  getLocalFileUrl: (filePath: string) => string

  // Storage operations
  getStorageItem: (key: string) => Promise<string | null>
  setStorageItem: (key: string, value: string) => Promise<void>
  removeStorageItem: (key: string) => Promise<void>

  // Legacy event listeners (maintained for backwards compatibility)
  onClipperOutput?: (callback: (data: { type: string; message: string }) => void) => void
  onClipperProgress?: (callback: (data: {
    phase?: string
    percent: number
    current?: number
    total?: number
    message?: string
  }) => void) => void
  onClipperStep?: (callback: (data: { step: string }) => void) => void
  onClipperLog?: (callback: (data: { level: string; message: string; timestamp: string }) => void) => void

  // New job event listeners
  onJobProgress: (callback: (event: JobProgressEvent) => void) => void
  onJobLog: (callback: (event: JobLogEvent) => void) => void
  onJobComplete: (callback: (event: JobCompleteEvent) => void) => void
  onJobError: (callback: (event: JobErrorEvent) => void) => void
  onJobStatusChange: (callback: (event: JobStatusChangeEvent) => void) => void

  // Pose comparison (existing)
  runPoseComparison?: (config: {
    videoPath: string
    modelIds: string[]
    overlayConfig?: any
  }) => Promise<{
    success: boolean
    results?: any
    report_path?: string
  }>
  onPoseComparisonProgress?: (callback: (data: any) => void) => void
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}

export {}
