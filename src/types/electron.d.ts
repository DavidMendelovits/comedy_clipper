export interface ElectronAPI {
  selectVideo: () => Promise<string | null>
  selectOutputDirectory: () => Promise<string | null>
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
  getStorageItem: (key: string) => Promise<string | null>
  setStorageItem: (key: string, value: string) => Promise<void>
  removeStorageItem: (key: string) => Promise<void>
  onClipperOutput: (callback: (data: { type: string; message: string }) => void) => void
  onClipperProgress: (callback: (data: {
    phase?: string
    percent: number
    current?: number
    total?: number
    message?: string
  }) => void) => void
  onClipperStep: (callback: (data: { step: string }) => void) => void
  onClipperLog: (callback: (data: { level: string; message: string; timestamp: string }) => void) => void
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}

export {}
