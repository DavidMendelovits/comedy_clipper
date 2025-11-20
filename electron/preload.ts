// Preload script for Electron
// This runs in a privileged context and can expose APIs to the renderer

import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  selectVideo: () => ipcRenderer.invoke('select-video'),
  selectOutputDirectory: () => ipcRenderer.invoke('select-output-directory'),
  runClipper: (config: any) => ipcRenderer.invoke('run-clipper', config),
  stopClipper: () => ipcRenderer.invoke('stop-clipper'),
  getClips: (directory: string) => ipcRenderer.invoke('get-clips', directory),
  getDebugFrames: (directory: string) => ipcRenderer.invoke('get-debug-frames', directory),

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
})

console.log('Preload script loaded - window.electron is available')
