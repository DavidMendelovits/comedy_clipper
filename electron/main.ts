import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'
import fs from 'fs'

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null

const PYTHON_SCRIPTS = {
  configurable: 'clipper_configurable.py',
  speaker: 'clipper_speaker.py',
  pose: 'clipper_pose.py',
  ffmpeg: 'clipper_ffmpeg.py',
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0f172a',
  })

  // VITE_DEV_SERVER_URL is set by vite-plugin-electron in dev mode
  const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

  if (VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
    if (pythonProcess) {
      pythonProcess.kill()
    }
  })
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
  if (pythonProcess) {
    pythonProcess.kill()
  }
})

// IPC Handlers

ipcMain.handle('select-video', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [
      { name: 'Videos', extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm'] },
    ],
  })

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0]
  }
  return null
})

ipcMain.handle('select-output-directory', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory', 'createDirectory'],
  })

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0]
  }
  return null
})

ipcMain.handle('run-clipper', async (_event, config: {
  videoPath: string
  clipperType: string
  options: Record<string, any>
}) => {
  return new Promise((resolve, reject) => {
    const { videoPath, clipperType, options } = config
    const scriptPath = path.join(app.getAppPath(), PYTHON_SCRIPTS[clipperType as keyof typeof PYTHON_SCRIPTS])

    // Build command arguments
    const args = [scriptPath, videoPath]

    if (options.outputDir) {
      args.push('-o', options.outputDir)
    }

    if (options.minDuration) {
      args.push('-m', options.minDuration.toString())
    }

    if (options.debug) {
      args.push('-d')
    }

    if (options.configFile && clipperType === 'configurable') {
      args.push('-c', options.configFile)
    }

    // Find Python executable - prefer venv
    const appPath = app.getAppPath()
    let pythonCmd: string

    // Check for venv in the app directory
    const venvPaths = [
      path.join(appPath, 'venv_mediapipe', 'bin', 'python3'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python'),
      path.join(appPath, 'venv', 'bin', 'python3'),
      path.join(appPath, 'venv', 'bin', 'python'),
    ]

    // Find first existing venv python
    pythonCmd = venvPaths.find(p => fs.existsSync(p)) || (process.platform === 'win32' ? 'python' : 'python3')

    console.log('Using Python:', pythonCmd)

    pythonProcess = spawn(pythonCmd, args, {
      cwd: appPath,
    })

    let output = ''
    let errorOutput = ''

    pythonProcess.stdout?.on('data', (data) => {
      const message = data.toString()
      output += message

      // Send real-time updates to renderer
      mainWindow?.webContents.send('clipper-output', {
        type: 'stdout',
        message: message.trim(),
      })

      // Parse progress information
      const progressMatch = message.match(/Processing frame (\d+)\/(\d+)/)
      if (progressMatch) {
        const [, current, total] = progressMatch
        mainWindow?.webContents.send('clipper-progress', {
          current: parseInt(current),
          total: parseInt(total),
          percent: (parseInt(current) / parseInt(total)) * 100,
        })
      }
    })

    pythonProcess.stderr?.on('data', (data) => {
      const message = data.toString()
      errorOutput += message
      mainWindow?.webContents.send('clipper-output', {
        type: 'stderr',
        message: message.trim(),
      })
    })

    pythonProcess.on('close', (code) => {
      pythonProcess = null

      if (code === 0) {
        // Parse output to find generated clips
        const clips = parseOutputForClips(output, path.dirname(videoPath))
        resolve({ success: true, clips, output })
      } else {
        reject({ success: false, error: errorOutput || output })
      }
    })

    pythonProcess.on('error', (error) => {
      pythonProcess = null
      reject({ success: false, error: error.message })
    })
  })
})

ipcMain.handle('stop-clipper', async () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
    return { success: true }
  }
  return { success: false, message: 'No process running' }
})

ipcMain.handle('get-clips', async (_event, directory: string) => {
  try {
    const files = fs.readdirSync(directory)
    const clips = files
      .filter(file => /\.(mp4|mov|avi|mkv)$/i.test(file))
      .map(file => ({
        name: file,
        path: path.join(directory, file),
        size: fs.statSync(path.join(directory, file)).size,
        modified: fs.statSync(path.join(directory, file)).mtime,
      }))
    return clips
  } catch (error) {
    console.error('Error reading clips:', error)
    return []
  }
})

ipcMain.handle('get-debug-frames', async (_event, directory: string) => {
  try {
    const debugDirs = fs.readdirSync(directory)
      .filter(dir => dir.includes('debug'))
      .map(dir => path.join(directory, dir))
      .filter(dir => fs.statSync(dir).isDirectory())

    const frames: Array<{ path: string; name: string; dir: string }> = []

    for (const dir of debugDirs) {
      const files = fs.readdirSync(dir)
        .filter(file => /\.(jpg|jpeg|png)$/i.test(file))
        .map(file => ({
          path: path.join(dir, file),
          name: file,
          dir: path.basename(dir),
        }))
      frames.push(...files)
    }

    return frames
  } catch (error) {
    console.error('Error reading debug frames:', error)
    return []
  }
})

function parseOutputForClips(output: string, baseDir: string): Array<{ name: string; path: string }> {
  const clips: Array<{ name: string; path: string }> = []

  // Look for created clip messages
  const clipRegex = /Created clip: (.+\.mp4)/g
  let match

  while ((match = clipRegex.exec(output)) !== null) {
    const clipName = path.basename(match[1])
    clips.push({
      name: clipName,
      path: path.join(baseDir, clipName),
    })
  }

  // If no explicit messages, look for output directory
  const dirMatch = output.match(/Output directory: (.+)/)
  if (dirMatch && clips.length === 0) {
    try {
      const outputDir = dirMatch[1].trim()
      const files = fs.readdirSync(outputDir)
      files.forEach(file => {
        if (/\.(mp4|mov|avi|mkv)$/i.test(file)) {
          clips.push({
            name: file,
            path: path.join(outputDir, file),
          })
        }
      })
    } catch (error) {
      console.error('Error reading output directory:', error)
    }
  }

  return clips
}
