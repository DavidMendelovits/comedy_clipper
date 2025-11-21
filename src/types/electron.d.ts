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
  onClipperOutput: (callback: (data: { type: string; message: string }) => void) => void
  onClipperProgress: (callback: (data: { current: number; total: number; percent: number }) => void) => void
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}

export {}
