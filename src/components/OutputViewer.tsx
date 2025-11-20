import { useState } from 'react'
import { Video, Image as ImageIcon, ExternalLink } from 'lucide-react'

interface Clip {
  name: string
  path: string
  size?: number
  modified?: Date
}

interface DebugFrame {
  path: string
  name: string
  dir: string
}

interface OutputViewerProps {
  clips: Clip[]
  debugFrames: DebugFrame[]
}

const OutputViewer: React.FC<OutputViewerProps> = ({ clips, debugFrames }) => {
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null)
  const [selectedFrame, setSelectedFrame] = useState<DebugFrame | null>(null)
  const [activeTab, setActiveTab] = useState<'clips' | 'debug'>('clips')

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown'
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  const formatDuration = (filename: string) => {
    const match = filename.match(/(\d+)m(\d+)s/)
    if (match) {
      return `${match[1]}:${match[2].padStart(2, '0')}`
    }
    return 'Unknown'
  }

  const openInFinder = (path: string) => {
    // This would need to be implemented in the main process
    console.log('Open in Finder:', path)
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar with clips/frames list */}
      <div className="w-96 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="flex border-b border-slate-700">
          <button
            onClick={() => setActiveTab('clips')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 font-medium transition-colors ${
              activeTab === 'clips'
                ? 'bg-slate-900 text-primary-400 border-b-2 border-primary-400'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <Video className="w-4 h-4" />
            <span>Clips ({clips.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('debug')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 font-medium transition-colors ${
              activeTab === 'debug'
                ? 'bg-slate-900 text-primary-400 border-b-2 border-primary-400'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            <span>Debug ({debugFrames.length})</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {activeTab === 'clips' ? (
            <div className="p-4 space-y-2">
              {clips.map((clip, index) => (
                <div
                  key={index}
                  onClick={() => setSelectedClip(clip)}
                  className={`
                    p-3 rounded-lg cursor-pointer transition-colors
                    ${selectedClip?.path === clip.path
                      ? 'bg-primary-600 ring-2 ring-primary-400'
                      : 'bg-slate-700 hover:bg-slate-600'
                    }
                  `}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Video className="w-4 h-4 flex-shrink-0" />
                      <span className="text-sm font-medium truncate">{clip.name}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        openInFinder(clip.path)
                      }}
                      className="p-1 hover:bg-slate-800 rounded"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span>{formatDuration(clip.name)}</span>
                    <span>{formatFileSize(clip.size)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 space-y-2">
              {debugFrames.map((frame, index) => (
                <div
                  key={index}
                  onClick={() => setSelectedFrame(frame)}
                  className={`
                    p-3 rounded-lg cursor-pointer transition-colors
                    ${selectedFrame?.path === frame.path
                      ? 'bg-primary-600 ring-2 ring-primary-400'
                      : 'bg-slate-700 hover:bg-slate-600'
                    }
                  `}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <ImageIcon className="w-4 h-4 flex-shrink-0" />
                    <span className="text-sm font-medium truncate">{frame.name}</span>
                  </div>
                  <div className="text-xs text-slate-400">{frame.dir}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main viewer */}
      <div className="flex-1 flex flex-col bg-slate-900">
        {activeTab === 'clips' && selectedClip ? (
          <div className="flex-1 flex flex-col p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-xl font-bold mb-1">{selectedClip.name}</h3>
                <p className="text-sm text-slate-400">{selectedClip.path}</p>
              </div>
              <button
                onClick={() => openInFinder(selectedClip.path)}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 rounded-lg transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                <span>Open File</span>
              </button>
            </div>

            <div className="flex-1 flex items-center justify-center bg-black rounded-lg overflow-hidden">
              <video
                key={selectedClip.path}
                src={`file://${selectedClip.path}`}
                controls
                className="max-w-full max-h-full"
                autoPlay
              />
            </div>
          </div>
        ) : activeTab === 'debug' && selectedFrame ? (
          <div className="flex-1 flex flex-col p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-xl font-bold mb-1">{selectedFrame.name}</h3>
                <p className="text-sm text-slate-400">{selectedFrame.dir}</p>
              </div>
              <button
                onClick={() => openInFinder(selectedFrame.path)}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 rounded-lg transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                <span>Open File</span>
              </button>
            </div>

            <div className="flex-1 flex items-center justify-center bg-black rounded-lg overflow-hidden p-4">
              <img
                src={`file://${selectedFrame.path}`}
                alt={selectedFrame.name}
                className="max-w-full max-h-full object-contain"
              />
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              {activeTab === 'clips' ? (
                <>
                  <Video className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Select a clip to preview</p>
                </>
              ) : (
                <>
                  <ImageIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Select a debug frame to view</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default OutputViewer
