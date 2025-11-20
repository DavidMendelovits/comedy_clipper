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
    ipcRenderer.on('clipper-output', (_event, data) => callback(data))
  },

  onClipperProgress: (callback: (data: any) => void) => {
    ipcRenderer.on('clipper-progress', (_event, data) => callback(data))
  },
})
