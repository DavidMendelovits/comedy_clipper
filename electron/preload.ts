// Preload script for Electron
// This runs in a privileged context and can expose APIs to the renderer

import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  selectVideo: () => ipcRenderer.invoke('select-video'),
  selectOutputDirectory: () => ipcRenderer.invoke('select-output-directory'),
  runClipper: (config: any) => ipcRenderer.invoke('run-clipper', config),
  stopClipper: () => ipcRenderer.invoke('stop-clipper'),
  reclipSegments: (config: any) => ipcRenderer.invoke('reclip-segments', config),
  getClips: (directory: string) => ipcRenderer.invoke('get-clips', directory),
  getDebugFrames: (directory: string) => ipcRenderer.invoke('get-debug-frames', directory),
  openInFinder: (filePath: string) => ipcRenderer.invoke('open-in-finder', filePath),
  openFile: (filePath: string) => ipcRenderer.invoke('open-file', filePath),

  // Storage methods
  getStorageItem: (key: string) => ipcRenderer.invoke('get-storage-item', key),
  setStorageItem: (key: string, value: string) => ipcRenderer.invoke('set-storage-item', key, value),
  removeStorageItem: (key: string) => ipcRenderer.invoke('remove-storage-item', key),

  // Convert file path to video protocol URL (legacy)
  getVideoUrl: (filePath: string) => `video://${encodeURIComponent(filePath)}`,

  // Convert file path to local-file protocol URL (for all file types)
  getLocalFileUrl: (filePath: string) => `local-file://${encodeURIComponent(filePath)}`,

  onClipperOutput: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-output', subscription)
    // Return cleanup function
    return () => {
      ipcRenderer.removeListener('clipper-output', subscription)
    }
  },

  onClipperProgress: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-progress', subscription)
    // Return cleanup function
    return () => {
      ipcRenderer.removeListener('clipper-progress', subscription)
    }
  },

  onClipperStep: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-step', subscription)
    // Return cleanup function
    return () => {
      ipcRenderer.removeListener('clipper-step', subscription)
    }
  },

  onClipperLog: (callback: (data: any) => void) => {
    const subscription = (_event: any, data: any) => callback(data)
    ipcRenderer.on('clipper-log', subscription)
    // Return cleanup function
    return () => {
      ipcRenderer.removeListener('clipper-log', subscription)
    }
  },
})

console.log('Preload script loaded - window.electron is available')
