import { Settings, Info } from 'lucide-react'

interface ClipperConfig {
  clipperType: 'configurable' | 'speaker' | 'pose' | 'ffmpeg'
  minDuration: number
  debug: boolean
  outputDir: string
  configFile: string
}

interface SettingsPanelProps {
  config: ClipperConfig
  onChange: (config: ClipperConfig) => void
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ config, onChange }) => {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Settings className="w-5 h-5 text-primary-400" />
        <h2 className="text-lg font-bold">Clipper Settings</h2>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Detection Method
          </label>
          <select
            value={config.clipperType}
            onChange={e => onChange({ ...config, clipperType: e.target.value as any })}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="configurable">Configurable (Multi-Modal)</option>
            <option value="speaker">Speaker Detection</option>
            <option value="pose">Pose Detection</option>
            <option value="ffmpeg">Scene Detection</option>
          </select>
          <p className="mt-2 text-xs text-slate-400">
            {config.clipperType === 'configurable' && 'Uses face + pose detection with configurable rules'}
            {config.clipperType === 'speaker' && 'Identifies comedians by voice characteristics'}
            {config.clipperType === 'pose' && 'Detects when person enters/exits stage'}
            {config.clipperType === 'ffmpeg' && 'Uses scene changes to detect cuts'}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Minimum Duration (seconds)
          </label>
          <input
            type="number"
            value={config.minDuration}
            onChange={e => onChange({ ...config, minDuration: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            min="0"
            step="30"
            disabled={config.clipperType === 'configurable'}
          />
          <p className="mt-2 text-xs text-slate-400">
            {config.clipperType === 'configurable'
              ? 'Set in YAML config file (clipper_rules.yaml)'
              : 'Filter out segments shorter than this duration'
            }
          </p>
        </div>

        {config.clipperType === 'configurable' && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Config File
            </label>
            <input
              type="text"
              value={config.configFile}
              onChange={e => onChange({ ...config, configFile: e.target.value })}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="clipper_rules.yaml"
            />
            <p className="mt-2 text-xs text-slate-400">
              YAML file with detection rules
            </p>
          </div>
        )}

        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.debug}
              onChange={e => onChange({ ...config, debug: e.target.checked })}
              className="w-4 h-4 bg-slate-700 border-slate-600 rounded focus:ring-2 focus:ring-primary-500"
            />
            <span className="text-sm font-medium text-slate-300">Enable Debug Mode</span>
          </label>
          <p className="mt-2 text-xs text-slate-400 ml-6">
            Save debug frames showing detection overlays
          </p>
        </div>
      </div>

      <div className="p-4 bg-slate-900 rounded-lg border border-slate-700">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-primary-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 space-y-2">
            <p className="font-medium text-primary-400">Tips:</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>Use Configurable for best accuracy</li>
              <li>Enable debug to see what's detected</li>
              <li>Adjust min duration to filter short clips</li>
              <li>Speaker detection works best with good audio</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-slate-700">
        <h3 className="text-sm font-medium text-slate-300 mb-3">Detection Methods</h3>
        <div className="space-y-3 text-xs">
          <div className="p-3 bg-slate-900 rounded">
            <div className="font-medium text-primary-400 mb-1">Configurable</div>
            <div className="text-slate-400">
              Multi-modal detection with face tracking, pose estimation, and Kalman filtering.
              Highly customizable via YAML rules.
            </div>
          </div>
          <div className="p-3 bg-slate-900 rounded">
            <div className="font-medium text-primary-400 mb-1">Speaker</div>
            <div className="text-slate-400">
              Voice-based identification using embeddings. Best for static camera shows with
              clear audio.
            </div>
          </div>
          <div className="p-3 bg-slate-900 rounded">
            <div className="font-medium text-primary-400 mb-1">Pose</div>
            <div className="text-slate-400">
              YOLO-based person detection. Works well when comedians physically enter/exit stage.
            </div>
          </div>
          <div className="p-3 bg-slate-900 rounded">
            <div className="font-medium text-primary-400 mb-1">Scene</div>
            <div className="text-slate-400">
              FFmpeg scene detection. Fast and simple for multi-camera shows with visible cuts.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsPanel
