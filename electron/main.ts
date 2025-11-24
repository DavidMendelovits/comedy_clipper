import { app, BrowserWindow, ipcMain, dialog, protocol } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'
import fs from 'fs'
import Database from 'better-sqlite3'
import { v4 as uuidv4 } from 'uuid'

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null
let db: Database.Database | null = null

// Job tracking - Map of job IDs to child processes
const jobProcesses = new Map<string, ChildProcess>()

// All modes now use the unified clipper script (except YOLO pose which uses its own)
const UNIFIED_SCRIPT = 'clipper_unified.py'
const YOLO_POSE_SCRIPT = 'clipper_yolo_pose.py'

// Map UI clipper types to unified script modes
const MODE_MAP: Record<string, string> = {
  multimodal: 'multimodal',
  pose: 'pose',
  face: 'face',
  mediapipe: 'mediapipe',
  scene: 'scene',
  diarization: 'diarization',
  yolo_pose: 'yolo_pose', // Special case - uses separate script
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

  // Create jobs table
  db.exec(`
    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY,
      type TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      started_at INTEGER,
      completed_at INTEGER,

      video_path TEXT NOT NULL,
      video_name TEXT NOT NULL,
      video_duration REAL,
      config_json TEXT NOT NULL,

      progress_json TEXT NOT NULL,
      result_json TEXT,
      error_json TEXT,

      log_file TEXT,
      updated_at INTEGER NOT NULL
    )
  `)

  // Create indices for jobs table
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
    CREATE INDEX IF NOT EXISTS idx_jobs_video_path ON jobs(video_path);
  `)

  // Create job_logs table
  db.exec(`
    CREATE TABLE IF NOT EXISTS job_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL,
      timestamp INTEGER NOT NULL,
      level TEXT NOT NULL,
      message TEXT NOT NULL,

      FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
    )
  `)

  // Create index for job_logs
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id, timestamp);
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

ipcMain.handle('get-video-duration', async (_event, filePath: string) => {
  return new Promise((resolve, reject) => {
    // Use ffprobe to get video duration
    const ffprobeCmd = spawn('ffprobe', [
      '-v', 'error',
      '-show_entries', 'format=duration',
      '-of', 'default=noprint_wrappers=1:nokey=1',
      filePath
    ])

    let output = ''
    ffprobeCmd.stdout.on('data', (data) => {
      output += data.toString()
    })

    ffprobeCmd.on('close', (code) => {
      if (code === 0) {
        const duration = parseFloat(output.trim())
        resolve(duration)
      } else {
        reject(new Error('Failed to get video duration'))
      }
    })

    ffprobeCmd.on('error', () => {
      // Fallback: return a default duration
      resolve(0)
    })
  })
})

ipcMain.handle('run-clipper', async (_event, config: {
  videoPath: string
  clipperType: string
  options: Record<string, any>
}) => {
  return new Promise((resolve, reject) => {
    const { videoPath, clipperType, options } = config
    const appPath = app.getAppPath()
    const resourcesPath = process.resourcesPath || appPath

    // Choose script based on clipper type
    const useYoloScript = clipperType === 'yolo_pose'
    const scriptName = useYoloScript ? YOLO_POSE_SCRIPT : UNIFIED_SCRIPT

    // In packaged mode, scripts are in python-bundle directory
    const scriptPath = app.isPackaged
      ? path.join(resourcesPath, 'python-bundle', scriptName)
      : path.join(appPath, scriptName)

    console.log('Clipper type:', clipperType)
    console.log('Using script:', scriptName)
    console.log('Script path:', scriptPath)
    console.log('Script exists:', fs.existsSync(scriptPath))

    // Build command arguments
    const args = [scriptPath, videoPath]

    // Determine mode for logging
    let mode: string

    // Add mode flag (only for unified script)
    if (!useYoloScript) {
      mode = MODE_MAP[clipperType] || clipperType
      args.push('--mode', mode)
    } else {
      // YOLO-specific: add model selection
      mode = 'yolo_pose'
      if (options?.yoloModel) {
        args.push('--model', options.yoloModel)
      }
    }

    // Enable JSON output for structured parsing
    args.push('--json')

    if (options?.outputDir) {
      args.push('-o', options.outputDir)
    }

    // Min duration override (optional)
    if (options?.minDuration) {
      args.push('--min-duration', options.minDuration.toString())
    }

    if (options?.debug) {
      args.push('-d')
    }

    // Config file for YAML-based configuration
    // If UI settings override YOLO/zone options, create a temporary config
    let configPath = options?.configFile || 'clipper_rules.yaml'

    if (options?.yoloEnabled !== undefined ||
        options?.personCountMethod ||
        options?.zoneCrossingEnabled !== undefined) {
      // Create temporary config with UI overrides
      const yaml = require('js-yaml')

      // In packaged mode, config is in python-bundle
      const configDir = app.isPackaged
        ? path.join(resourcesPath, 'python-bundle')
        : appPath

      const baseConfigPath = path.join(configDir, configPath)

      try {
        // Load base config
        let baseConfig: any = {}
        if (fs.existsSync(baseConfigPath)) {
          const baseConfigContent = fs.readFileSync(baseConfigPath, 'utf8')
          baseConfig = yaml.load(baseConfigContent) || {}
        }

        // Apply UI overrides for position-based detection
        if (!baseConfig.position_detection) baseConfig.position_detection = {}
        if (!baseConfig.filtering) baseConfig.filtering = {}

        if (options?.exitThreshold !== undefined) {
          baseConfig.position_detection.exit_threshold = options.exitThreshold
        }

        if (options?.exitStabilityFrames !== undefined) {
          baseConfig.position_detection.exit_stability_frames = options.exitStabilityFrames
        }

        if (options?.maxDuration !== undefined) {
          baseConfig.filtering.max_duration = options.maxDuration
        }

        // Write temporary config to user data directory (writable in packaged app)
        const userDataPath = app.getPath('userData')
        const tempConfigPath = path.join(userDataPath, 'temp_clipper_config.yaml')
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

    // Find Python executable - prefer bundled Python
    let pythonCmd: string

    console.log('App path:', appPath)
    console.log('Resources path:', resourcesPath)
    console.log('Is packaged:', app.isPackaged)

    // In production, look for bundled Python in resources
    // In development, look for local venv
    const pythonSearchPaths = app.isPackaged ? [
      // Packaged app - look in resources
      path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python3'),
      path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python'),
      path.join(resourcesPath, 'python-bundle', 'python-env', 'Scripts', 'python.exe'), // Windows
      path.join(resourcesPath, 'python-bundle', 'python-env', 'Scripts', 'python3.exe'), // Windows
    ] : [
      // Development - look for local venv
      path.join(appPath, 'venv', 'bin', 'python3'),
      path.join(appPath, 'venv', 'bin', 'python'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python3'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python'),
    ]

    console.log('Checking Python paths:', pythonSearchPaths)

    // Find first existing Python
    pythonCmd = pythonSearchPaths.find(p => {
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
    const appPath = app.getAppPath()
    const resourcesPath = process.resourcesPath || appPath

    // Determine script directory based on packaging
    const scriptDir = app.isPackaged
      ? path.join(resourcesPath, 'python-bundle')
      : appPath

    const configPath = path.join(scriptDir, 'clipper_rules.yaml')

    // Create a temporary Python script to clip specific segments
    const clipScript = `
import sys
import json
from pathlib import Path

# Import the clipper
sys.path.insert(0, '${scriptDir}')
from clipper_unified import UnifiedComedyClipper
from config_loader import load_config

# Load default config
config = load_config('${configPath}')

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

    // Find Python executable - same logic as run-clipper
    const pythonSearchPaths = app.isPackaged ? [
      path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python3'),
      path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python'),
      path.join(resourcesPath, 'python-bundle', 'python-env', 'Scripts', 'python.exe'),
      path.join(resourcesPath, 'python-bundle', 'python-env', 'Scripts', 'python3.exe'),
    ] : [
      path.join(appPath, 'venv', 'bin', 'python3'),
      path.join(appPath, 'venv', 'bin', 'python'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python3'),
      path.join(appPath, 'venv_mediapipe', 'bin', 'python'),
    ]
    const pythonCmd = pythonSearchPaths.find(p => fs.existsSync(p)) ||
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

// ============================================================================
// Job Management IPC Handlers
// ============================================================================

// Create a new job
ipcMain.handle('create-job', async (_event, input: {
  type: string
  videoPath: string
  config: any
}) => {
  if (!db) return { error: 'Database not initialized' }

  try {
    const jobId = uuidv4()
    const now = Date.now()
    const videoName = path.basename(input.videoPath)

    const initialProgress = {
      percent: 0,
      steps: []
    }

    const stmt = db.prepare(`
      INSERT INTO jobs (
        id, type, status, created_at, updated_at,
        video_path, video_name, config_json, progress_json
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `)

    stmt.run(
      jobId,
      input.type,
      'queued',
      now,
      now,
      input.videoPath,
      videoName,
      JSON.stringify(input.config),
      JSON.stringify(initialProgress)
    )

    console.log('Created job:', jobId)
    return { jobId }
  } catch (error: any) {
    console.error('Error creating job:', error)
    return { error: error.message }
  }
})

// Get a specific job by ID
ipcMain.handle('get-job', async (_event, jobId: string) => {
  if (!db) return null

  try {
    const stmt = db.prepare('SELECT * FROM jobs WHERE id = ?')
    const row = stmt.get(jobId) as any

    if (!row) return null

    // Parse JSON fields
    const job = {
      id: row.id,
      type: row.type,
      status: row.status,
      createdAt: row.created_at,
      startedAt: row.started_at,
      completedAt: row.completed_at,
      videoPath: row.video_path,
      videoName: row.video_name,
      videoDuration: row.video_duration,
      config: JSON.parse(row.config_json),
      progress: JSON.parse(row.progress_json),
      result: row.result_json ? JSON.parse(row.result_json) : undefined,
      error: row.error_json ? JSON.parse(row.error_json) : undefined,
      logFile: row.log_file,
      logs: [] // Logs loaded separately if needed
    }

    return job
  } catch (error) {
    console.error('Error getting job:', error)
    return null
  }
})

// Get jobs with optional filtering
ipcMain.handle('get-jobs', async (_event, filter?: {
  status?: string | string[]
  type?: string | string[]
  limit?: number
  offset?: number
}) => {
  if (!db) return []

  try {
    let query = 'SELECT * FROM jobs WHERE 1=1'
    const params: any[] = []

    // Apply filters
    if (filter?.status) {
      if (Array.isArray(filter.status)) {
        query += ` AND status IN (${filter.status.map(() => '?').join(',')})`
        params.push(...filter.status)
      } else {
        query += ' AND status = ?'
        params.push(filter.status)
      }
    }

    if (filter?.type) {
      if (Array.isArray(filter.type)) {
        query += ` AND type IN (${filter.type.map(() => '?').join(',')})`
        params.push(...filter.type)
      } else {
        query += ' AND type = ?'
        params.push(filter.type)
      }
    }

    // Order by created_at descending
    query += ' ORDER BY created_at DESC'

    // Apply limit and offset
    if (filter?.limit) {
      query += ' LIMIT ?'
      params.push(filter.limit)
    }

    if (filter?.offset) {
      query += ' OFFSET ?'
      params.push(filter.offset)
    }

    const stmt = db.prepare(query)
    const rows = stmt.all(...params) as any[]

    // Parse JSON fields for each job
    const jobs = rows.map(row => ({
      id: row.id,
      type: row.type,
      status: row.status,
      createdAt: row.created_at,
      startedAt: row.started_at,
      completedAt: row.completed_at,
      videoPath: row.video_path,
      videoName: row.video_name,
      videoDuration: row.video_duration,
      config: JSON.parse(row.config_json),
      progress: JSON.parse(row.progress_json),
      result: row.result_json ? JSON.parse(row.result_json) : undefined,
      error: row.error_json ? JSON.parse(row.error_json) : undefined,
      logFile: row.log_file,
      logs: []
    }))

    return jobs
  } catch (error) {
    console.error('Error getting jobs:', error)
    return []
  }
})

// Get job statistics
ipcMain.handle('get-job-statistics', async () => {
  if (!db) return { total: 0, queued: 0, running: 0, completed: 0, failed: 0, cancelled: 0 }

  try {
    const stmt = db.prepare(`
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) as queued,
        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
      FROM jobs
    `)

    const stats = stmt.get() as any
    return {
      total: stats.total || 0,
      queued: stats.queued || 0,
      running: stats.running || 0,
      completed: stats.completed || 0,
      failed: stats.failed || 0,
      cancelled: stats.cancelled || 0
    }
  } catch (error) {
    console.error('Error getting job statistics:', error)
    return { total: 0, queued: 0, running: 0, completed: 0, failed: 0, cancelled: 0 }
  }
})

// Update job status
function updateJobStatus(jobId: string, status: string, additionalFields: any = {}) {
  if (!db) return

  try {
    const fields = ['status = ?', 'updated_at = ?']
    const values = [status, Date.now()]

    if (status === 'running' && !additionalFields.started_at) {
      fields.push('started_at = ?')
      values.push(Date.now())
    }

    if ((status === 'completed' || status === 'failed' || status === 'cancelled') && !additionalFields.completed_at) {
      fields.push('completed_at = ?')
      values.push(Date.now())
    }

    Object.entries(additionalFields).forEach(([key, value]) => {
      fields.push(`${key} = ?`)
      values.push(value as string | number)
    })

    values.push(jobId)

    const stmt = db.prepare(`UPDATE jobs SET ${fields.join(', ')} WHERE id = ?`)
    stmt.run(...values)

    // Emit status change event
    mainWindow?.webContents.send('job-status-change', {
      jobId,
      status,
      timestamp: Date.now()
    })
  } catch (error) {
    console.error('Error updating job status:', error)
  }
}

// Update job progress
function updateJobProgress(jobId: string, progress: any) {
  if (!db) return

  try {
    const stmt = db.prepare('UPDATE jobs SET progress_json = ?, updated_at = ? WHERE id = ?')
    stmt.run(JSON.stringify(progress), Date.now(), jobId)

    // Emit progress event
    mainWindow?.webContents.send('job-progress', {
      jobId,
      progress
    })
  } catch (error) {
    console.error('Error updating job progress:', error)
  }
}

// Add job log
function addJobLog(jobId: string, level: string, message: string) {
  if (!db) return

  try {
    const stmt = db.prepare(`
      INSERT INTO job_logs (job_id, timestamp, level, message)
      VALUES (?, ?, ?, ?)
    `)
    const timestamp = Date.now()
    stmt.run(jobId, timestamp, level, message)

    // Emit log event
    mainWindow?.webContents.send('job-log', {
      jobId,
      log: { timestamp, level, message }
    })
  } catch (error) {
    console.error('Error adding job log:', error)
  }
}

// Complete job with result
function completeJob(jobId: string, result: any) {
  if (!db) return

  try {
    const stmt = db.prepare(`
      UPDATE jobs
      SET status = ?, result_json = ?, completed_at = ?, updated_at = ?
      WHERE id = ?
    `)
    const now = Date.now()
    stmt.run('completed', JSON.stringify(result), now, now, jobId)

    // Emit completion event
    mainWindow?.webContents.send('job-complete', {
      jobId,
      result
    })
  } catch (error) {
    console.error('Error completing job:', error)
  }
}

// Fail job with error
function failJob(jobId: string, error: any) {
  if (!db) return

  try {
    const stmt = db.prepare(`
      UPDATE jobs
      SET status = ?, error_json = ?, completed_at = ?, updated_at = ?
      WHERE id = ?
    `)
    const now = Date.now()
    stmt.run('failed', JSON.stringify(error), now, now, jobId)

    // Emit error event
    mainWindow?.webContents.send('job-error', {
      jobId,
      error
    })
  } catch (error) {
    console.error('Error failing job:', error)
  }
}

// Cancel job
ipcMain.handle('cancel-job', async (_event, jobId: string) => {
  try {
    const process = jobProcesses.get(jobId)
    if (process) {
      process.kill()
      jobProcesses.delete(jobId)
    }

    updateJobStatus(jobId, 'cancelled')
    return { success: true }
  } catch (error: any) {
    console.error('Error cancelling job:', error)
    return { success: false, error: error.message }
  }
})

// Delete job
ipcMain.handle('delete-job', async (_event, jobId: string) => {
  if (!db) return { success: false, error: 'Database not initialized' }

  try {
    // Cancel if running
    const process = jobProcesses.get(jobId)
    if (process) {
      process.kill()
      jobProcesses.delete(jobId)
    }

    // Delete from database (cascades to job_logs)
    const stmt = db.prepare('DELETE FROM jobs WHERE id = ?')
    stmt.run(jobId)

    return { success: true }
  } catch (error: any) {
    console.error('Error deleting job:', error)
    return { success: false, error: error.message }
  }
})

// Start job - Execute the job
ipcMain.handle('start-job', async (_event, jobId: string) => {
  if (!db) return { success: false, error: 'Database not initialized' }

  try {
    // Get job from database
    const stmt = db.prepare('SELECT * FROM jobs WHERE id = ?')
    const jobRow = stmt.get(jobId) as any

    if (!jobRow) {
      return { success: false, error: 'Job not found' }
    }

    const config = JSON.parse(jobRow.config_json)
    const videoPath = jobRow.video_path

    // Update job status to running
    updateJobStatus(jobId, 'running')
    addJobLog(jobId, 'info', 'Starting job execution...')

    // Similar to run-clipper, but with job ID tracking
    return new Promise((resolve, reject) => {
      const appPath = app.getAppPath()
      const resourcesPath = process.resourcesPath || appPath

      // Choose script based on clipper type
      const clipperType = config.clipperType || 'multimodal'
      const useYoloScript = clipperType === 'yolo_pose'
      const scriptName = useYoloScript ? YOLO_POSE_SCRIPT : UNIFIED_SCRIPT

      const scriptPath = app.isPackaged
        ? path.join(resourcesPath, 'python-bundle', scriptName)
        : path.join(appPath, scriptName)

      // Build command arguments
      const args = [scriptPath, videoPath]

      if (!useYoloScript) {
        const mode = MODE_MAP[clipperType] || clipperType
        args.push('--mode', mode)
      } else if (config.yoloModel) {
        args.push('--model', config.yoloModel)
      }

      args.push('--json')

      if (config.outputDir) args.push('-o', config.outputDir)
      if (config.minDuration) args.push('--min-duration', config.minDuration.toString())
      if (config.debug) args.push('-d')

      // Overlay video options
      if (config.exportOverlayVideo) {
        args.push('--export-overlay')
        if (!config.overlayIncludeSkeletons) {
          args.push('--no-overlay-skeletons')
        }
        if (config.overlayShowInfo) {
          args.push('--overlay-show-info')
        }
      }

      // Handle config file
      let configPath = config.configFile || 'clipper_rules.yaml'
      if (configPath) args.push('-c', configPath)

      // Find Python executable
      const pythonSearchPaths = app.isPackaged ? [
        path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python3'),
        path.join(resourcesPath, 'python-bundle', 'python-env', 'bin', 'python'),
      ] : [
        path.join(appPath, 'venv', 'bin', 'python3'),
        path.join(appPath, 'venv', 'bin', 'python'),
      ]

      const pythonCmd = pythonSearchPaths.find(p => fs.existsSync(p)) || 'python3'

      // Create log file
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      const videoName = path.basename(videoPath, path.extname(videoPath))
      const logDir = path.join(appPath, 'logs')
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true })
      const logFile = path.join(logDir, `${videoName}_${jobId}_${timestamp}.log`)
      const logStream = fs.createWriteStream(logFile, { flags: 'a' })

      // Update job with log file path
      const updateLogStmt = db?.prepare('UPDATE jobs SET log_file = ? WHERE id = ?')
      updateLogStmt?.run(logFile, jobId)

      console.log(`Starting job ${jobId}:`, pythonCmd, args.join(' '))
      logStream.write(`=== Comedy Clipper Job ${jobId} ===\n`)
      logStream.write(`Video: ${videoPath}\n`)
      logStream.write(`Command: ${pythonCmd} ${args.join(' ')}\n\n`)

      const jobProcess = spawn(pythonCmd, args, { cwd: appPath })
      jobProcesses.set(jobId, jobProcess)

      let output = ''
      let jsonOutput = ''
      let isJsonLine = false

      // Get current progress from DB to update
      const getCurrentProgress = () => {
        const row = db?.prepare('SELECT progress_json FROM jobs WHERE id = ?').get(jobId) as any
        return row ? JSON.parse(row.progress_json) : { percent: 0, steps: [] }
      }

      jobProcess.stdout?.on('data', (data) => {
        const message = data.toString()
        output += message
        logStream.write(`[STDOUT] ${message}`)

        addJobLog(jobId, 'info', message.trim())

        // Check if this is JSON output
        if (message.trim().startsWith('{') || isJsonLine) {
          jsonOutput += message
          isJsonLine = !message.includes('}')
        } else {
          // Parse step messages
          const stepMatch = message.match(/\[STEP\] (.+)/)
          if (stepMatch) {
            const currentProgress = getCurrentProgress()
            currentProgress.steps.push(stepMatch[1].trim())
            updateJobProgress(jobId, currentProgress)
          }

          // Parse JSON progress
          const progressJsonMatch = message.match(/\[PROGRESS\] (.+)/)
          if (progressJsonMatch) {
            try {
              const progressData = JSON.parse(progressJsonMatch[1])
              const currentProgress = getCurrentProgress()
              Object.assign(currentProgress, progressData)
              updateJobProgress(jobId, currentProgress)
            } catch (e) {
              console.error('Failed to parse progress JSON:', e)
            }
          }

          // Legacy progress parsing
          const progressMatch = message.match(/Processing frame (\d+)\/(\d+)/)
          if (progressMatch) {
            const [, current, total] = progressMatch
            const currentProgress = getCurrentProgress()
            currentProgress.currentFrame = parseInt(current)
            currentProgress.totalFrames = parseInt(total)
            currentProgress.percent = (parseInt(current) / parseInt(total)) * 100
            updateJobProgress(jobId, currentProgress)
          }
        }
      })

      jobProcess.stderr?.on('data', (data) => {
        const message = data.toString()
        logStream.write(`[STDERR] ${message}`)
        addJobLog(jobId, 'error', message.trim())
      })

      jobProcess.on('close', (code) => {
        jobProcesses.delete(jobId)
        logStream.write(`\n=== Process exited with code ${code} ===\n`)
        logStream.end()

        if (code === 0) {
          try {
            const result = JSON.parse(jsonOutput || output)

            const clips = result.clips?.map((clipPath: string) => ({
              name: path.basename(clipPath),
              path: clipPath,
              size: fs.existsSync(clipPath) ? fs.statSync(clipPath).size : 0,
            })) || []

            const jobResult = {
              clips,
              segmentsDetected: result.segments_detected || [],
              segmentsFiltered: result.segments_filtered || [],
              outputDir: result.output_dir,
              debugDir: result.debug_dir,
              overlayVideo: result.overlay_video,
            }

            completeJob(jobId, jobResult)
            resolve({ success: true, jobId, result: jobResult })
          } catch (e) {
            console.error('JSON parsing failed:', e)
            failJob(jobId, { message: 'Failed to parse job output', code: 'PARSE_ERROR' })
            reject({ success: false, error: 'Failed to parse output' })
          }
        } else {
          const errorMsg = `Process failed with code ${code}`
          failJob(jobId, { message: errorMsg, code: code?.toString() })
          reject({ success: false, error: errorMsg })
        }
      })

      jobProcess.on('error', (error) => {
        jobProcesses.delete(jobId)
        failJob(jobId, { message: error.message, code: 'SPAWN_ERROR' })
        reject({ success: false, error: error.message })
      })
    })
  } catch (error: any) {
    console.error('Error starting job:', error)
    failJob(jobId, { message: error.message, code: 'START_ERROR' })
    return { success: false, error: error.message }
  }
})

// Model comparison IPC handler
ipcMain.handle('run-pose-comparison', async (_event, config: {
  videoPath: string
  modelIds: string[]
  overlayConfig?: any
  onProgress?: (data: any) => void
}) => {
  return new Promise((resolve, reject) => {
    const { videoPath, modelIds } = config
    const appPath = app.getAppPath()

    const scriptPath = app.isPackaged
      ? path.join(process.resourcesPath, 'python-bundle', 'pose_model_runner.py')
      : path.join(appPath, 'pose_model_runner.py')

    console.log('Running pose model comparison:', { scriptPath, videoPath, modelIds })

    const args = [scriptPath, videoPath, ...modelIds]

    const comparisonProcess = spawn('python3', args, {
      cwd: app.isPackaged ? path.join(process.resourcesPath, 'python-bundle') : appPath
    })

    let output = ''
    let errorOutput = ''

    comparisonProcess.stdout.on('data', (data) => {
      const text = data.toString()
      output += text

      // Try to parse as JSON for progress updates
      const lines = text.split('\n')
      lines.forEach((line: string) => {
        if (line.trim()) {
          try {
            const json = JSON.parse(line)
            if (json.type === 'progress' && mainWindow) {
              mainWindow.webContents.send('pose-comparison-progress', json)
            } else if (json.type === 'complete') {
              resolve({
                success: true,
                results: json.results,
                report_path: json.report_path
              })
            }
          } catch {
            // Not JSON, just regular output
            console.log('[Pose Comparison]', line)
          }
        }
      })
    })

    comparisonProcess.stderr.on('data', (data) => {
      const text = data.toString()
      errorOutput += text
      console.error('[Pose Comparison Error]', text)
    })

    comparisonProcess.on('close', (code) => {
      if (code !== 0) {
        reject({
          error: `Pose comparison failed with code ${code}`,
          details: errorOutput
        })
      }
    })

    comparisonProcess.on('error', (error) => {
      reject({
        error: 'Failed to start pose comparison',
        details: error.message
      })
    })
  })
})

// Save file dialog
ipcMain.handle('save-file', async (_event, sourceFile: string, suggestedName: string) => {
  const result = await dialog.showSaveDialog({
    defaultPath: suggestedName,
    filters: [
      { name: 'All Files', extensions: ['*'] }
    ]
  })

  if (!result.canceled && result.filePath) {
    try {
      fs.copyFileSync(sourceFile, result.filePath)
      return { success: true, path: result.filePath }
    } catch (error: any) {
      return { success: false, error: error.message }
    }
  }

  return { success: false, error: 'Cancelled' }
})

// Cache Management IPC Handlers
ipcMain.handle('get-cache-stats', async () => {
  try {
    const pythonPath = findPythonPath()
    const scriptPath = path.join(getResourcePath(), 'python_backend', 'cache_cli.py')

    const result = await new Promise<any>((resolve, reject) => {
      const process = spawn(pythonPath, [scriptPath, 'stats'])
      let output = ''

      process.stdout?.on('data', (data) => {
        output += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          try {
            const stats = JSON.parse(output)
            resolve(stats)
          } catch (error) {
            reject(new Error('Failed to parse cache stats'))
          }
        } else {
          reject(new Error(`Cache stats command failed with code ${code}`))
        }
      })
    })

    return result
  } catch (error: any) {
    console.error('Error getting cache stats:', error)
    return { entry_count: 0, total_size_mb: 0, error: error.message }
  }
})

ipcMain.handle('clear-cache', async () => {
  try {
    const pythonPath = findPythonPath()
    const scriptPath = path.join(getResourcePath(), 'python_backend', 'cache_cli.py')

    await new Promise<void>((resolve, reject) => {
      const process = spawn(pythonPath, [scriptPath, 'clear'])

      process.on('close', (code) => {
        if (code === 0) {
          resolve()
        } else {
          reject(new Error(`Clear cache command failed with code ${code}`))
        }
      })
    })

    return { success: true }
  } catch (error: any) {
    console.error('Error clearing cache:', error)
    return { success: false, error: error.message }
  }
})

ipcMain.handle('get-cached-videos', async () => {
  try {
    const pythonPath = findPythonPath()
    const scriptPath = path.join(getResourcePath(), 'python_backend', 'cache_cli.py')

    const result = await new Promise<any[]>((resolve, reject) => {
      const process = spawn(pythonPath, [scriptPath, 'list'])
      let output = ''

      process.stdout?.on('data', (data) => {
        output += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          try {
            const videos = JSON.parse(output)
            resolve(videos)
          } catch (error) {
            reject(new Error('Failed to parse cached videos'))
          }
        } else {
          reject(new Error(`List cache command failed with code ${code}`))
        }
      })
    })

    return result
  } catch (error: any) {
    console.error('Error getting cached videos:', error)
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
