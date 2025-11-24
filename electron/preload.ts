// Preload script for Electron
// This runs in a privileged context and can expose APIs to the renderer

import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  // File operations
  selectVideo: () => ipcRenderer.invoke('select-video'),
  selectOutputDirectory: () => ipcRenderer.invoke('select-output-directory'),

  // Legacy clipper operations (maintained for backwards compatibility)
  runClipper: (config: any) => ipcRenderer.invoke('run-clipper', config),
  stopClipper: () => ipcRenderer.invoke('stop-clipper'),
  reclipSegments: (config: any) => ipcRenderer.invoke('reclip-segments', config),

  // Job Management (New)
  createJob: (input: any) => ipcRenderer.invoke('create-job', input),
  startJob: (jobId: string) => ipcRenderer.invoke('start-job', jobId),
  cancelJob: (jobId: string) => ipcRenderer.invoke('cancel-job', jobId),
  deleteJob: (jobId: string) => ipcRenderer.invoke('delete-job', jobId),
  getJob: (jobId: string) => ipcRenderer.invoke('get-job', jobId),
  getJobs: (filter?: any) => ipcRenderer.invoke('get-jobs', filter),
  getJobStatistics: () => ipcRenderer.invoke('get-job-statistics'),

  // File system operations
  getClips: (directory: string) => ipcRenderer.invoke('get-clips', directory),
  getDebugFrames: (directory: string) => ipcRenderer.invoke('get-debug-frames', directory),
  openInFinder: (filePath: string) => ipcRenderer.invoke('open-in-finder', filePath),
  openFile: (filePath: string) => ipcRenderer.invoke('open-file', filePath),

  // Pose model comparison
  runPoseComparison: (config: { videoPath: string; modelIds: string[]; overlayConfig?: any; onProgress?: (data: any) => void }) =>
    ipcRenderer.invoke('run-pose-comparison', config),
  saveFile: (sourceFile: string, suggestedName: string) => ipcRenderer.invoke('save-file', sourceFile, suggestedName),

  // Video utilities
  openVideo: (filePath: string) => ipcRenderer.invoke('open-file', filePath),
  openOutputDir: () => ipcRenderer.invoke('open-in-finder', '.'),
  getVideoDuration: (filePath: string) => ipcRenderer.invoke('get-video-duration', filePath),

  // Storage methods
  getStorageItem: (key: string) => ipcRenderer.invoke('get-storage-item', key),
  setStorageItem: (key: string, value: string) => ipcRenderer.invoke('set-storage-item', key, value),
  removeStorageItem: (key: string) => ipcRenderer.invoke('remove-storage-item', key),

  // Convert file path to video protocol URL (legacy)
  getVideoUrl: (filePath: string) => `video://${encodeURIComponent(filePath)}`,

  // Convert file path to local-file protocol URL (for all file types)
  getLocalFileUrl: (filePath: string) => `local-file://${encodeURIComponent(filePath)}`,

  // Legacy event listeners (maintained for backwards compatibility)
  onClipperOutput: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-output', subscription)
    return () => ipcRenderer.removeListener('clipper-output', subscription)
  },

  onClipperProgress: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-progress', subscription)
    return () => ipcRenderer.removeListener('clipper-progress', subscription)
  },

  onClipperStep: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-step', subscription)
    return () => ipcRenderer.removeListener('clipper-step', subscription)
  },

  onClipperLog: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-log', subscription)
    return () => ipcRenderer.removeListener('clipper-log', subscription)
  },

  onPoseComparisonProgress: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('pose-comparison-progress', subscription)
    return () => ipcRenderer.removeListener('pose-comparison-progress', subscription)
  },

  // New job event listeners
  onJobProgress: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('job-progress', subscription)
    return () => ipcRenderer.removeListener('job-progress', subscription)
  },

  onJobLog: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('job-log', subscription)
    return () => ipcRenderer.removeListener('job-log', subscription)
  },

  onJobComplete: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('job-complete', subscription)
    return () => ipcRenderer.removeListener('job-complete', subscription)
  },

  onJobError: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('job-error', subscription)
    return () => ipcRenderer.removeListener('job-error', subscription)
  },

  onJobStatusChange: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('job-status-change', subscription)
    return () => ipcRenderer.removeListener('job-status-change', subscription)
  },
})

console.log('Preload script loaded - window.electron is available')
