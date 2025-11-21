import { useState } from 'react'
import { Video, Image as ImageIcon, ExternalLink, FolderOpen, ChevronLeft, ChevronRight, Maximize2 } from 'lucide-react'

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
  const [activeTab, setActiveTab] = useState<'clips' | 'debug'>('clips')
  const [selectedIndex, setSelectedIndex] = useState(0)

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

  const handleOpenInFinder = async (path: string) => {
    await (window as any).electron.openInFinder(path)
  }

  const handleOpenFile = async (path: string) => {
    await (window as any).electron.openFile(path)
  }

  const currentItems = activeTab === 'clips' ? clips : debugFrames
  const currentItem = currentItems[selectedIndex]

  const goToPrevious = () => {
    setSelectedIndex(prev => (prev > 0 ? prev - 1 : currentItems.length - 1))
  }

  const goToNext = () => {
    setSelectedIndex(prev => (prev < currentItems.length - 1 ? prev + 1 : 0))
  }

  const isClip = (item: any): item is Clip => {
    return 'size' in item
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b border-slate-700 bg-slate-800">
        <div className="flex">
          <button
            onClick={() => { setActiveTab('clips'); setSelectedIndex(0); }}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
              activeTab === 'clips'
                ? 'bg-slate-900 text-primary-400 border-b-2 border-primary-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Video className="w-5 h-5" />
            <span>Clips ({clips.length})</span>
          </button>
          <button
            onClick={() => { setActiveTab('debug'); setSelectedIndex(0); }}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
              activeTab === 'debug'
                ? 'bg-slate-900 text-primary-400 border-b-2 border-primary-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700'
            }`}
          >
            <ImageIcon className="w-5 h-5" />
            <span>Debug Frames ({debugFrames.length})</span>
          </button>
        </div>

        {currentItem && (
          <div className="flex items-center gap-2 px-6">
            <button
              onClick={() => handleOpenInFinder(currentItem.path)}
              className="flex items-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm"
              title="Show in Finder"
            >
              <FolderOpen className="w-4 h-4" />
              <span>Show in Finder</span>
            </button>
            <button
              onClick={() => handleOpenFile(currentItem.path)}
              className="flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-500 rounded-lg transition-colors text-sm"
              title="Open File"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Open</span>
            </button>
          </div>
        )}
      </div>

      {currentItems.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-500">
          <div className="text-center">
            {activeTab === 'clips' ? (
              <>
                <Video className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium mb-2">No Clips Yet</p>
                <p className="text-sm">Process a video to see clips here</p>
              </>
            ) : (
              <>
                <ImageIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium mb-2">No Debug Frames</p>
                <p className="text-sm">Enable debug mode to see detection frames</p>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* Thumbnail sidebar */}
          <div className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col">
            <div className="p-4 border-b border-slate-700">
              <h3 className="font-semibold text-slate-200">
                {activeTab === 'clips' ? 'Video Clips' : 'Detection Frames'}
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                {selectedIndex + 1} of {currentItems.length}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              <div className="space-y-2">
                {currentItems.map((item, index) => (
                  <div
                    key={index}
                    onClick={() => setSelectedIndex(index)}
                    className={`
                      p-3 rounded-lg cursor-pointer transition-all
                      ${selectedIndex === index
                        ? 'bg-primary-600 ring-2 ring-primary-400 shadow-lg'
                        : 'bg-slate-700 hover:bg-slate-600'
                      }
                    `}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 p-2 bg-slate-900 rounded">
                        {activeTab === 'clips' ? (
                          <Video className="w-4 h-4" />
                        ) : (
                          <ImageIcon className="w-4 h-4" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{item.name}</div>
                        {isClip(item) ? (
                          <div className="flex items-center gap-2 mt-1 text-xs text-slate-300">
                            <span>{formatDuration(item.name)}</span>
                            <span>•</span>
                            <span>{formatFileSize(item.size)}</span>
                          </div>
                        ) : (
                          <div className="text-xs text-slate-300 mt-1">{item.dir}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Main viewer */}
          <div className="flex-1 flex flex-col bg-black">
            {/* Navigation controls */}
            <div className="flex items-center justify-between p-4 bg-slate-900 border-b border-slate-700">
              <div className="flex items-center gap-4">
                <button
                  onClick={goToPrevious}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  title="Previous"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="text-sm">
                  <div className="font-semibold text-slate-200">{currentItem.name}</div>
                  <div className="text-slate-400">
                    {selectedIndex + 1} / {currentItems.length}
                  </div>
                </div>
                <button
                  onClick={goToNext}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  title="Next"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleOpenFile(currentItem.path)}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  title="Open in default app"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Content area */}
            <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
              {activeTab === 'clips' && isClip(currentItem) ? (
                <video
                  key={currentItem.path}
                  src={`file://${currentItem.path}`}
                  controls
                  className="max-w-full max-h-full rounded-lg shadow-2xl"
                  autoPlay
                />
              ) : (
                <img
                  key={currentItem.path}
                  src={`file://${currentItem.path}`}
                  alt={currentItem.name}
                  className="max-w-full max-h-full rounded-lg shadow-2xl object-contain"
                />
              )}
            </div>

            {/* File info */}
            <div className="p-4 bg-slate-900 border-t border-slate-700">
              <div className="flex items-center justify-between text-sm">
                <div className="text-slate-400">
                  <span className="font-mono">{currentItem.path}</span>
                </div>
                {isClip(currentItem) && (
                  <div className="text-slate-400">
                    {formatFileSize(currentItem.size)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default OutputViewer
