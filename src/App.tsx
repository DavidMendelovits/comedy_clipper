import { useState, useEffect } from 'react'
import { Film, Settings, Play, Pause, FolderOpen } from 'lucide-react'
import DropZone from './components/DropZone'
import ProgressPanel from './components/ProgressPanel'
import OutputViewer from './components/OutputViewer'
import SettingsPanel from './components/SettingsPanel'

interface ClipperConfig {
  clipperType: 'configurable' | 'speaker' | 'pose' | 'ffmpeg'
  minDuration: number
  debug: boolean
  outputDir: string
  configFile: string
}

interface ProcessState {
  running: boolean
  progress: number
  currentFrame: number
  totalFrames: number
  output: string[]
}

interface Clip {
  name: string
  path: string
  size?: number
  modified?: Date
}

function App() {
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null)
  const [config, setConfig] = useState<ClipperConfig>({
    clipperType: 'configurable',
    minDuration: 180,
    debug: true,
    outputDir: '',
    configFile: 'clipper_rules.yaml',
  })
  const [processState, setProcessState] = useState<ProcessState>({
    running: false,
    progress: 0,
    currentFrame: 0,
    totalFrames: 0,
    output: [],
  })
  const [clips, setClips] = useState<Clip[]>([])
  const [showSettings, setShowSettings] = useState(false)
  const [debugFrames, setDebugFrames] = useState<any[]>([])

  useEffect(() => {
    // Listen for clipper output
    ;(window as any).electron?.onClipperOutput((data: any) => {
      setProcessState(prev => ({
        ...prev,
        output: [...prev.output, `[${data.type}] ${data.message}`],
      }))
    })

    // Listen for progress updates
    ;(window as any).electron?.onClipperProgress((data: any) => {
      setProcessState(prev => ({
        ...prev,
        progress: data.percent,
        currentFrame: data.current,
        totalFrames: data.total,
      }))
    })
  }, [])

  const handleVideoSelect = async (videoPath: string) => {
    setSelectedVideo(videoPath)
    // Auto-set output directory to video's directory
    const videoDir = videoPath.substring(0, videoPath.lastIndexOf('/'))
    setConfig(prev => ({ ...prev, outputDir: videoDir }))
  }

  const handleRunClipper = async () => {
    if (!selectedVideo) return

    setProcessState({
      running: true,
      progress: 0,
      currentFrame: 0,
      totalFrames: 0,
      output: [],
    })

    try {
      const result = await (window as any).electron.runClipper({
        videoPath: selectedVideo,
        clipperType: config.clipperType,
        options: {
          outputDir: config.outputDir,
          minDuration: config.minDuration,
          debug: config.debug,
          configFile: config.configFile,
        },
      })

      if (result.success) {
        setClips(result.clips || [])
        setProcessState(prev => ({ ...prev, running: false, progress: 100 }))

        // Load debug frames if available
        if (config.debug && config.outputDir) {
          const frames = await (window as any).electron.getDebugFrames(config.outputDir)
          setDebugFrames(frames)
        }
      }
    } catch (error: any) {
      console.error('Clipper error:', error)
      setProcessState(prev => ({
        ...prev,
        running: false,
        output: [...prev.output, `[ERROR] ${error.error || error.message}`],
      }))
    }
  }

  const handleStopClipper = async () => {
    await (window as any).electron.stopClipper()
    setProcessState(prev => ({ ...prev, running: false }))
  }

  const handleSelectOutputDir = async () => {
    const dir = await (window as any).electron.selectOutputDirectory()
    if (dir) {
      setConfig(prev => ({ ...prev, outputDir: dir }))
    }
  }

  return (
    <div className="flex h-screen bg-slate-900 text-white">
      {/* Sidebar */}
      <div className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-primary-600 rounded-lg">
              <Film className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Comedy Clipper</h1>
              <p className="text-sm text-slate-400">AI-Powered Video Clipping</p>
            </div>
          </div>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className="w-full flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </button>
        </div>

        {showSettings ? (
          <SettingsPanel config={config} onChange={setConfig} />
        ) : (
          <div className="flex-1 flex flex-col p-6 gap-4 overflow-y-auto">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Video File
              </label>
              {selectedVideo ? (
                <div className="p-3 bg-slate-700 rounded-lg text-sm break-all">
                  {selectedVideo.split('/').pop()}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No video selected</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Output Directory
              </label>
              <button
                onClick={handleSelectOutputDir}
                className="w-full flex items-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
              >
                <FolderOpen className="w-4 h-4" />
                <span className="truncate">{config.outputDir || 'Select...'}</span>
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Clipper Type
              </label>
              <select
                value={config.clipperType}
                onChange={e => setConfig(prev => ({ ...prev, clipperType: e.target.value as any }))}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="configurable">Configurable (Multi-Modal)</option>
                <option value="speaker">Speaker Detection</option>
                <option value="pose">Pose Detection</option>
                <option value="ffmpeg">Scene Detection</option>
              </select>
            </div>

            <div className="flex-1" />

            <div className="space-y-2">
              <button
                onClick={handleRunClipper}
                disabled={!selectedVideo || processState.running}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg font-medium transition-colors"
              >
                <Play className="w-5 h-5" />
                <span>Start Clipping</span>
              </button>

              {processState.running && (
                <button
                  onClick={handleStopClipper}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-500 rounded-lg font-medium transition-colors"
                >
                  <Pause className="w-5 h-5" />
                  <span>Stop</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedVideo && !processState.running && clips.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <DropZone onVideoSelect={handleVideoSelect} />
          </div>
        ) : processState.running || processState.output.length > 0 ? (
          <ProgressPanel processState={processState} />
        ) : clips.length > 0 ? (
          <OutputViewer clips={clips} debugFrames={debugFrames} />
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <DropZone onVideoSelect={handleVideoSelect} />
          </div>
        )}
      </div>
    </div>
  )
}

export default App
