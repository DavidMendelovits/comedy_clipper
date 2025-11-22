import { app, BrowserWindow, ipcMain, dialog, protocol } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'
import fs from 'fs'
import Database from 'better-sqlite3'

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null
let db: Database.Database | null = null

// All modes now use the unified clipper script
const UNIFIED_SCRIPT = 'clipper_unified.py'

// Map UI clipper types to unified script modes
const MODE_MAP: Record<string, string> = {
  multimodal: 'multimodal',
  pose: 'pose',
  face: 'face',
  mediapipe: 'mediapipe',
  scene: 'scene',
  diarization: 'diarization',
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

  console.log('Environment:', {
    VITE_DEV_SERVER_URL,
    NODE_ENV: process.env.NODE_ENV,
    isDev: !app.isPackaged
  })

  if (VITE_DEV_SERVER_URL) {
    console.log('Loading from dev server:', VITE_DEV_SERVER_URL)
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    console.log('Loading from file:', path.join(__dirname, '../dist/index.html'))
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
    if (pythonProcess) {
      pythonProcess.kill()
    }
  })
}

// Initialize SQLite database
function initDatabase() {
  const userDataPath = app.getPath('userData')
  const dbPath = path.join(userDataPath, 'comedy-clipper.db')

  db = new Database(dbPath)

  // Create storage table
  db.exec(`
    CREATE TABLE IF NOT EXISTS storage (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `)

  console.log('Database initialized at:', dbPath)
}

app.whenReady().then(() => {
  // Initialize database
  initDatabase()

  // Register custom protocol for serving all local files (videos, images, etc.)
  protocol.registerFileProtocol('local-file', (request, callback) => {
    const url = request.url.replace('local-file://', '')
    const decodedPath = decodeURIComponent(url)

    try {
      // Security check - ensure file exists and is readable
      if (fs.existsSync(decodedPath)) {
        callback({ path: decodedPath })
      } else {
        console.error('File not found:', decodedPath)
        callback({ error: -6 }) // FILE_NOT_FOUND
      }
    } catch (error) {
      console.error('Error serving file:', error)
      callback({ error: -2 }) // FAILED
    }
  })

  // Keep legacy 'video' protocol for backward compatibility
  protocol.registerFileProtocol('video', (request, callback) => {
    const url = request.url.replace('video://', '')
    const decodedPath = decodeURIComponent(url)

    try {
      if (fs.existsSync(decodedPath)) {
        callback({ path: decodedPath })
      } else {
        console.error('File not found:', decodedPath)
        callback({ error: -6 })
      }
    } catch (error) {
      console.error('Error serving video:', error)
      callback({ error: -2 })
    }
  })

  // Only create window if none exists
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }

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

ipcMain.handle('open-in-finder', async (_event, filePath: string) => {
  const { shell } = require('electron')
  try {
    // Show the file in Finder/Explorer
    shell.showItemInFolder(filePath)
    return { success: true }
  } catch (error: any) {
    console.error('Error opening in Finder:', error)
    return { success: false, error: error.message }
  }
})

ipcMain.handle('open-file', async (_event, filePath: string) => {
  const { shell } = require('electron')
  try {
    // Open the file with default application
    await shell.openPath(filePath)
    return { success: true }
  } catch (error: any) {
    console.error('Error opening file:', error)
    return { success: false, error: error.message }
  }
})

ipcMain.handle('run-clipper', async (_event, config: {
  videoPath: string
  clipperType: string
  options: Record<string, any>
}) => {
  return new Promise((resolve, reject) => {
    const { videoPath, clipperType, options } = config
    const scriptPath = path.join(app.getAppPath(), UNIFIED_SCRIPT)

    // Build command arguments for unified clipper
    const args = [scriptPath, videoPath]

    // Add mode flag
    const mode = MODE_MAP[clipperType] || clipperType
    args.push('--mode', mode)

    // Enable JSON output for structured parsing
    args.push('--json')

    if (options.outputDir) {
      args.push('-o', options.outputDir)
    }

    // Min duration override (optional)
    if (options.minDuration) {
      args.push('--min-duration', options.minDuration.toString())
    }

    if (options.debug) {
      args.push('-d')
    }

    // Config file for YAML-based configuration
    // If UI settings override YOLO/zone options, create a temporary config
    let configPath = options.configFile || 'clipper_rules.yaml'

    if (options.yoloEnabled !== undefined ||
        options.personCountMethod ||
        options.zoneCrossingEnabled !== undefined) {
      // Create temporary config with UI overrides
      const yaml = require('js-yaml')
      const appPath = app.getAppPath()
      const baseConfigPath = path.join(appPath, configPath)

      try {
        // Load base config
        let baseConfig: any = {}
        if (fs.existsSync(baseConfigPath)) {
          const baseConfigContent = fs.readFileSync(baseConfigPath, 'utf8')
          baseConfig = yaml.load(baseConfigContent) || {}
        }

        // Apply UI overrides
        if (options.yoloEnabled !== undefined) {
          if (!baseConfig.yolo_detection) baseConfig.yolo_detection = {}
          baseConfig.yolo_detection.enabled = options.yoloEnabled
        }

        if (options.personCountMethod) {
          if (!baseConfig.transition_detection) baseConfig.transition_detection = {}
          baseConfig.transition_detection.person_count_method = options.personCountMethod
        }

        if (options.zoneCrossingEnabled !== undefined) {
          if (!baseConfig.zone_crossing) baseConfig.zone_crossing = {}
          baseConfig.zone_crossing.enabled = options.zoneCrossingEnabled

          if (options.stageBoundary && options.zoneCrossingEnabled) {
            if (!baseConfig.zone_crossing.stage_boundary) {
              baseConfig.zone_crossing.stage_boundary = { type: 'rectangle' }
            }
            baseConfig.zone_crossing.stage_boundary.left = options.stageBoundary.left
            baseConfig.zone_crossing.stage_boundary.right = options.stageBoundary.right
            baseConfig.zone_crossing.stage_boundary.top = options.stageBoundary.top
            baseConfig.zone_crossing.stage_boundary.bottom = options.stageBoundary.bottom
          }
        }

        // Write temporary config
        const tempConfigPath = path.join(appPath, 'temp_clipper_config.yaml')
        fs.writeFileSync(tempConfigPath, yaml.dump(baseConfig))
        configPath = tempConfigPath
        console.log('Created temporary config with UI overrides:', tempConfigPath)
      } catch (error) {
        console.error('Error creating temporary config:', error)
        // Fall back to original config
      }
    }

    if (configPath) {
      args.push('-c', configPath)
    }

    // Find Python executable - prefer venv
    const appPath = app.getAppPath()
    let pythonCmd: string

    console.log('App path:', appPath)

    // Check for venv in the app directory
    const venvPaths = [
      path.join(appPath, 'venv_mediapipe', 'bin', 'python3'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python'),
      path.join(appPath, 'venv', 'bin', 'python3'),
      path.join(appPath, 'venv', 'bin', 'python'),
    ]

    console.log('Checking venv paths:', venvPaths)

    // Find first existing venv python
    pythonCmd = venvPaths.find(p => {
      const exists = fs.existsSync(p)
      console.log(`  ${p}: ${exists}`)
      return exists
    }) || (process.platform === 'win32' ? 'python' : 'python3')

    console.log('Using Python:', pythonCmd)
    console.log('Python exists:', fs.existsSync(pythonCmd))

    // Create log file for this processing session
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const videoName = path.basename(videoPath, path.extname(videoPath))
    const logDir = path.join(appPath, 'logs')
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true })
    }
    const logFile = path.join(logDir, `${videoName}_${timestamp}.log`)
    const logStream = fs.createWriteStream(logFile, { flags: 'a' })

    console.log('Logging to:', logFile)
    logStream.write(`=== Comedy Clipper Log ===\n`)
    logStream.write(`Video: ${videoPath}\n`)
    logStream.write(`Mode: ${mode}\n`)
    logStream.write(`Time: ${new Date().toISOString()}\n`)
    logStream.write(`Command: ${pythonCmd} ${args.join(' ')}\n\n`)

    pythonProcess = spawn(pythonCmd, args, {
      cwd: appPath,
    })

    let output = ''
    let errorOutput = ''
    let jsonOutput = ''
    let isJsonLine = false

    pythonProcess.stdout?.on('data', (data) => {
      const message = data.toString()
      output += message

      // Log to file
      logStream.write(`[STDOUT] ${message}`)

      // Stream ALL output to renderer in real-time
      mainWindow?.webContents.send('clipper-log', {
        level: 'info',
        message: message.trim(),
        timestamp: new Date().toISOString(),
      })

      // Check if this is JSON output (starts with { or is continuation)
      if (message.trim().startsWith('{') || isJsonLine) {
        jsonOutput += message
        isJsonLine = !message.includes('}') // Continue if JSON not closed
      } else {
        // Parse structured progress steps
        const stepMatch = message.match(/\[STEP\] (.+)/)
        if (stepMatch) {
          mainWindow?.webContents.send('clipper-step', {
            step: stepMatch[1].trim(),
          })
        }

        // Parse new JSON progress format
        const progressJsonMatch = message.match(/\[PROGRESS\] (.+)/)
        if (progressJsonMatch) {
          try {
            const progressData = JSON.parse(progressJsonMatch[1])
            mainWindow?.webContents.send('clipper-progress', progressData)
          } catch (e) {
            console.error('Failed to parse progress JSON:', e)
          }
        }

        // Parse legacy progress information (for backward compatibility)
        const progressMatch = message.match(/Processing frame (\d+)\/(\d+)/)
        if (progressMatch) {
          const [, current, total] = progressMatch
          mainWindow?.webContents.send('clipper-progress', {
            current: parseInt(current),
            total: parseInt(total),
            percent: (parseInt(current) / parseInt(total)) * 100,
          })
        }

        // Parse percentage-based progress
        const percentMatch = message.match(/Progress: (\d+)%/)
        if (percentMatch) {
          mainWindow?.webContents.send('clipper-progress', {
            percent: parseInt(percentMatch[1]),
          })
        }
      }
    })

    pythonProcess.stderr?.on('data', (data) => {
      const message = data.toString()
      errorOutput += message

      // Log to file
      logStream.write(`[STDERR] ${message}`)

      // Stream stderr to renderer as warnings/errors
      mainWindow?.webContents.send('clipper-log', {
        level: 'error',
        message: message.trim(),
        timestamp: new Date().toISOString(),
      })
    })

    pythonProcess.on('close', (code) => {
      pythonProcess = null

      // Close log stream
      logStream.write(`\n=== Process exited with code ${code} ===\n`)
      logStream.end()

      console.log('Python process exited with code:', code)
      console.log('Log file:', logFile)

      if (code === 0) {
        try {
          // Try to parse JSON output
          const result = JSON.parse(jsonOutput || output)

          console.log('Parsed result:', result)

          // Convert clip paths to proper format
          const clips = result.clips?.map((clipPath: string) => ({
            name: path.basename(clipPath),
            path: clipPath,
            size: fs.existsSync(clipPath) ? fs.statSync(clipPath).size : 0,
          })) || []

          resolve({
            success: true,
            clips,
            segments_detected: result.segments_detected || [],
            segments_filtered: result.segments_filtered || [],
            output_dir: result.output_dir,
            debug_dir: result.debug_dir,
            log_file: logFile,
          })
        } catch (e) {
          // Fallback to parsing output if JSON parsing fails
          console.error('JSON parsing failed:', e)
          console.error('Attempted to parse:', jsonOutput || output)
          const clips = parseOutputForClips(output, path.dirname(videoPath))
          resolve({ success: true, clips, log_file: logFile })
        }
      } else {
        const errorMsg = `Process failed. Check log file: ${logFile}`
        console.error('Python process failed with code:', code)
        reject({ success: false, error: errorMsg, log_file: logFile })
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

ipcMain.handle('reclip-segments', async (_event, config: {
  videoPath: string
  segments: Array<{ start: number; end: number }>
  outputDir?: string
  debug?: boolean
}) => {
  return new Promise((resolve, reject) => {
    const { videoPath, segments, outputDir, debug } = config

    // Create a temporary Python script to clip specific segments
    const clipScript = `
import sys
import json
from pathlib import Path

# Import the clipper
sys.path.insert(0, '${app.getAppPath()}')
from clipper_unified import UnifiedComedyClipper
from config_loader import load_config

# Load default config
config = load_config('${path.join(app.getAppPath(), 'clipper_rules.yaml')}')

# Create clipper instance
clipper = UnifiedComedyClipper(config, mode='multimodal', debug=${debug ? 'True' : 'False'})

# Segments to clip
segments = ${JSON.stringify(segments.map(s => [s.start, s.end]))}

# Clip the video
output_dir = '${outputDir || path.dirname(videoPath)}'
clips = clipper.clip_video('${videoPath}', segments, output_dir, json_output=True)

# Output result as JSON
result = {
    'success': True,
    'clips': [{'name': Path(c).name, 'path': c} for c in clips],
    'output_dir': str(Path(clips[0]).parent) if clips else None
}
print(json.dumps(result))
`

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const videoName = path.basename(videoPath, path.extname(videoPath))
    const logDir = path.join(app.getAppPath(), 'logs')
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true })
    }
    const logFile = path.join(logDir, `${videoName}_reclip_${timestamp}.log`)
    const logStream = fs.createWriteStream(logFile, { flags: 'a' })

    console.log('Re-clipping segments:', segments)
    logStream.write(`=== Re-clip Session ===\n`)
    logStream.write(`Video: ${videoPath}\n`)
    logStream.write(`Segments: ${JSON.stringify(segments)}\n`)
    logStream.write(`Time: ${new Date().toISOString()}\n\n`)

    // Find Python executable
    const appPath = app.getAppPath()
    const venvPaths = [
      path.join(appPath, 'venv_mediapipe', 'bin', 'python3'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python'),
      path.join(appPath, 'venv', 'bin', 'python3'),
      path.join(appPath, 'venv', 'bin', 'python'),
    ]
    const pythonCmd = venvPaths.find(p => fs.existsSync(p)) ||
      (process.platform === 'win32' ? 'python' : 'python3')

    pythonProcess = spawn(pythonCmd, ['-c', clipScript], {
      cwd: appPath,
    })

    let output = ''
    let errorOutput = ''

    pythonProcess.stdout?.on('data', (data) => {
      const message = data.toString()
      output += message
      logStream.write(`[STDOUT] ${message}`)

      // Stream to renderer
      mainWindow?.webContents.send('clipper-log', {
        level: 'info',
        message: message.trim(),
        timestamp: new Date().toISOString(),
      })
    })

    pythonProcess.stderr?.on('data', (data) => {
      const message = data.toString()
      errorOutput += message
      logStream.write(`[STDERR] ${message}`)

      mainWindow?.webContents.send('clipper-log', {
        level: 'error',
        message: message.trim(),
        timestamp: new Date().toISOString(),
      })
    })

    pythonProcess.on('close', (code) => {
      pythonProcess = null
      logStream.write(`\n=== Process exited with code ${code} ===\n`)
      logStream.end()

      if (code === 0) {
        try {
          // Parse JSON output
          const jsonMatch = output.match(/\{[^]*\}/)
          if (jsonMatch) {
            const result = JSON.parse(jsonMatch[0])

            // Convert clip paths to proper format
            const clips = result.clips?.map((clip: any) => ({
              name: clip.name,
              path: clip.path,
              size: fs.existsSync(clip.path) ? fs.statSync(clip.path).size : 0,
            })) || []

            resolve({
              success: true,
              clips,
              output_dir: result.output_dir,
              log_file: logFile,
            })
          } else {
            reject({ success: false, error: 'Failed to parse output', log_file: logFile })
          }
        } catch (e) {
          console.error('JSON parsing failed:', e)
          reject({ success: false, error: 'Failed to parse result', log_file: logFile })
        }
      } else {
        reject({ success: false, error: `Process failed with code ${code}`, log_file: logFile })
      }
    })

    pythonProcess.on('error', (error) => {
      pythonProcess = null
      reject({ success: false, error: error.message })
    })
  })
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

ipcMain.handle('get-debug-frames', async (_event, debugDir: string) => {
  try {
    if (!debugDir || !fs.existsSync(debugDir)) {
      console.log('Debug directory not found:', debugDir)
      return { frames: [], csv_path: null }
    }

    const frames: Array<{ path: string; name: string; category: string; sortKey: string }> = []

    // Read subdirectories
    const subdirs = ['transitions', 'timeline', 'segments']
    for (const subdir of subdirs) {
      const subdirPath = path.join(debugDir, subdir)
      if (!fs.existsSync(subdirPath)) continue

      const files = fs.readdirSync(subdirPath)
        .filter(file => /\.(jpg|jpeg|png)$/i.test(file))
        .map(file => ({
          path: path.join(subdirPath, file),
          name: file,
          category: subdir,
          sortKey: file, // For sorting within category
        }))
      frames.push(...files)
    }

    // Check for CSV file
    const csvPath = path.join(debugDir, 'detection_data.csv')
    const csvExists = fs.existsSync(csvPath)

    return {
      frames,
      csv_path: csvExists ? csvPath : null,
      debug_dir: debugDir,
    }
  } catch (error) {
    console.error('Error reading debug frames:', error)
    return { frames: [], csv_path: null }
  }
})

// SQLite storage IPC handlers
ipcMain.handle('get-storage-item', async (_event, key: string) => {
  if (!db) return null

  try {
    const stmt = db.prepare('SELECT value FROM storage WHERE key = ?')
    const row = stmt.get(key) as { value: string } | undefined
    return row?.value || null
  } catch (error) {
    console.error('Error getting storage item:', error)
    return null
  }
})

ipcMain.handle('set-storage-item', async (_event, key: string, value: string) => {
  if (!db) return

  try {
    const stmt = db.prepare(`
      INSERT INTO storage (key, value, updated_at)
      VALUES (?, ?, CURRENT_TIMESTAMP)
      ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        updated_at = CURRENT_TIMESTAMP
    `)
    stmt.run(key, value)
  } catch (error) {
    console.error('Error setting storage item:', error)
  }
})

ipcMain.handle('remove-storage-item', async (_event, key: string) => {
  if (!db) return

  try {
    const stmt = db.prepare('DELETE FROM storage WHERE key = ?')
    stmt.run(key)
  } catch (error) {
    console.error('Error removing storage item:', error)
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
