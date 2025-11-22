import { useState } from 'react'
import {
  Video,
  Image as ImageIcon,
  ExternalLink,
  FolderOpen,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Grid3x3,
  List,
  Play,
  FileVideo,
  Sparkles
} from 'lucide-react'
import { Button, Card, Tooltip } from './ui'

interface Clip {
  name: string
  path: string
  size?: number
  modified?: Date
}

interface DebugFrame {
  path: string
  name: string
  category: string  // 'transitions', 'timeline', or 'segments'
  sortKey: string
}

interface OutputViewerProps {
  clips: Clip[]
  debugFrames: DebugFrame[]
}

type ViewMode = 'grid' | 'list' | 'detail'

const OutputViewer: React.FC<OutputViewerProps> = ({ clips, debugFrames }) => {
  const [activeTab, setActiveTab] = useState<'clips' | 'debug'>('clips')
  const [debugCategory, setDebugCategory] = useState<'all' | 'transitions' | 'timeline' | 'segments'>('all')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [viewMode, setViewMode] = useState<ViewMode>('detail')

  // Filter debug frames by category
  const filteredDebugFrames = debugCategory === 'all'
    ? debugFrames
    : debugFrames.filter(frame => frame.category === debugCategory)

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

  const currentItems = activeTab === 'clips' ? clips : filteredDebugFrames
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

  // Grid View Component
  const GridView = () => (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {currentItems.map((item, index) => (
          <Card
            key={index}
            variant={selectedIndex === index ? 'gradient-border' : 'elevated'}
            padding="none"
            hoverable
            onClick={() => setSelectedIndex(index)}
            className={`cursor-pointer transition-all duration-300 ${
              selectedIndex === index ? 'ring-2 ring-primary-400 scale-[1.02]' : ''
            }`}
          >
            {/* Thumbnail */}
            <div className="aspect-video bg-slate-950 flex items-center justify-center relative overflow-hidden group">
              {activeTab === 'clips' ? (
                <>
                  <Video className="w-12 h-12 text-slate-600" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                    <Play className="w-12 h-12 text-white" />
                  </div>
                </>
              ) : (
                <img
                  src={(window as any).electron?.getLocalFileUrl(item.path) || item.path}
                  alt={item.name}
                  className="w-full h-full object-cover"
                />
              )}
            </div>

            {/* Info */}
            <div className="p-4 space-y-2">
              <div className="font-medium text-sm text-slate-200 truncate" title={item.name}>
                {item.name}
              </div>
              {isClip(item) ? (
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span>{formatDuration(item.name)}</span>
                  <span>•</span>
                  <span>{formatFileSize(item.size)}</span>
                </div>
              ) : (
                <div className="inline-block">
                  <span className="px-2 py-1 bg-primary-500/20 text-primary-400 rounded text-xs font-medium">
                    {(item as DebugFrame).category}
                  </span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-3 border-t border-slate-700/50 flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                fullWidth
                icon={<ExternalLink size={14} />}
                onClick={(e) => {
                  e.stopPropagation()
                  handleOpenFile(item.path)
                }}
              >
                Open
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={<FolderOpen size={14} />}
                onClick={(e) => {
                  e.stopPropagation()
                  handleOpenInFinder(item.path)
                }}
              />
            </div>
          </Card>
        ))}
      </div>
    </div>
  )

  // List View Component
  const ListView = () => (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="space-y-3">
        {currentItems.map((item, index) => (
          <Card
            key={index}
            variant={selectedIndex === index ? 'gradient-border' : 'elevated'}
            padding="none"
            hoverable
            onClick={() => setSelectedIndex(index)}
            className={`cursor-pointer transition-all duration-300 ${
              selectedIndex === index ? 'ring-2 ring-primary-400' : ''
            }`}
          >
            <div className="flex items-center gap-4 p-4">
              {/* Icon */}
              <div className="flex-shrink-0 p-3 bg-slate-700/50 rounded-xl">
                {activeTab === 'clips' ? (
                  <FileVideo className="w-6 h-6 text-primary-400" />
                ) : (
                  <ImageIcon className="w-6 h-6 text-emerald-400" />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-200 truncate mb-1">{item.name}</div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  {isClip(item) ? (
                    <>
                      <span className="flex items-center gap-1">
                        <Video size={12} />
                        {formatDuration(item.name)}
                      </span>
                      <span>•</span>
                      <span>{formatFileSize(item.size)}</span>
                    </>
                  ) : (
                    <span className="px-2 py-1 bg-primary-500/20 text-primary-400 rounded font-medium">
                      {(item as DebugFrame).category}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<ExternalLink size={14} />}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleOpenFile(item.path)
                  }}
                >
                  Open
                </Button>
                <Tooltip content="Show in Finder">
                  <Button
                    variant="ghost"
                    size="icon"
                    icon={<FolderOpen size={16} />}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleOpenInFinder(item.path)
                    }}
                  />
                </Tooltip>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )

  // Detail View Component (original viewer)
  const DetailView = () => (
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
              <Card
                key={index}
                variant={selectedIndex === index ? 'gradient-border' : 'default'}
                padding="sm"
                onClick={() => setSelectedIndex(index)}
                className={`cursor-pointer transition-all ${
                  selectedIndex === index ? 'ring-2 ring-primary-400 shadow-glow-sm' : ''
                }`}
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
                      <div className="text-xs text-slate-300 mt-1">
                        <span className="px-2 py-0.5 bg-primary-500/20 text-primary-400 rounded">
                          {(item as DebugFrame).category}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* Main viewer */}
      <div className="flex-1 flex flex-col bg-black">
        {/* Navigation controls */}
        <div className="flex items-center justify-between p-4 bg-slate-900 border-b border-slate-700">
          <div className="flex items-center gap-4">
            <Tooltip content="Previous (←)">
              <Button
                variant="ghost"
                size="icon"
                onClick={goToPrevious}
                icon={<ChevronLeft size={20} />}
              />
            </Tooltip>
            <div className="text-sm">
              <div className="font-semibold text-slate-200">{currentItem.name}</div>
              <div className="text-slate-400">
                {selectedIndex + 1} / {currentItems.length}
              </div>
            </div>
            <Tooltip content="Next (→)">
              <Button
                variant="ghost"
                size="icon"
                onClick={goToNext}
                icon={<ChevronRight size={20} />}
              />
            </Tooltip>
          </div>

          <Tooltip content="Open in default app">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleOpenFile(currentItem.path)}
              icon={<Maximize2 size={16} />}
            />
          </Tooltip>
        </div>

        {/* Content area */}
        <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
          {activeTab === 'clips' && isClip(currentItem) ? (
            <video
              key={currentItem.path}
              src={(window as any).electron?.getLocalFileUrl(currentItem.path) || currentItem.path}
              controls
              className="max-w-full max-h-full rounded-lg shadow-2xl"
              autoPlay
            />
          ) : (
            <img
              key={currentItem.path}
              src={(window as any).electron?.getLocalFileUrl(currentItem.path) || currentItem.path}
              alt={currentItem.name}
              className="max-w-full max-h-full rounded-lg shadow-2xl object-contain"
            />
          )}
        </div>

        {/* File info */}
        <div className="p-4 bg-slate-900 border-t border-slate-700">
          <div className="flex items-center justify-between text-sm gap-4">
            <div className="text-slate-400 font-mono text-xs truncate flex-1">
              {currentItem.path}
            </div>
            {isClip(currentItem) && (
              <div className="text-slate-400 flex-shrink-0">
                {formatFileSize(currentItem.size)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-800/50">
        <div className="flex">
          <button
            onClick={() => { setActiveTab('clips'); setSelectedIndex(0); }}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-all duration-300 relative ${
              activeTab === 'clips'
                ? 'bg-slate-900 text-primary-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
            }`}
          >
            {activeTab === 'clips' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary-600 to-primary-400" />
            )}
            <Video className="w-5 h-5" />
            <span>Clips</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
              activeTab === 'clips'
                ? 'bg-primary-500/20 text-primary-300'
                : 'bg-slate-700 text-slate-400'
            }`}>
              {clips.length}
            </span>
          </button>
          <button
            onClick={() => { setActiveTab('debug'); setSelectedIndex(0); }}
            className={`flex items-center gap-2 px-6 py-4 font-medium transition-all duration-300 relative ${
              activeTab === 'debug'
                ? 'bg-slate-900 text-primary-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
            }`}
          >
            {activeTab === 'debug' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary-600 to-primary-400" />
            )}
            <ImageIcon className="w-5 h-5" />
            <span>Debug Frames</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
              activeTab === 'debug'
                ? 'bg-primary-500/20 text-primary-300'
                : 'bg-slate-700 text-slate-400'
            }`}>
              {debugFrames.length}
            </span>
          </button>
        </div>

        <div className="flex items-center gap-4 px-4">
          {/* Debug category filters */}
          {activeTab === 'debug' && debugFrames.length > 0 && (
            <div className="flex items-center gap-2 pr-4 border-r border-slate-700">
              <span className="text-sm text-slate-400">Filter:</span>
              {['all', 'transitions', 'timeline', 'segments'].map((cat) => (
                <button
                  key={cat}
                  onClick={() => { setDebugCategory(cat as any); setSelectedIndex(0); }}
                  className={`px-3 py-1 text-xs rounded-full transition-all duration-300 ${
                    debugCategory === cat
                      ? 'bg-gradient-to-r from-primary-600 to-primary-500 text-white shadow-glow-sm'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  {cat !== 'all' && (
                    <span className="ml-1 opacity-70">
                      ({debugFrames.filter(f => f.category === cat).length})
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* View mode toggle */}
          {currentItems.length > 0 && (
            <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg p-1">
              <Tooltip content="Grid View">
                <Button
                  variant={viewMode === 'grid' ? 'primary' : 'ghost'}
                  size="sm"
                  icon={<Grid3x3 size={16} />}
                  onClick={() => setViewMode('grid')}
                />
              </Tooltip>
              <Tooltip content="List View">
                <Button
                  variant={viewMode === 'list' ? 'primary' : 'ghost'}
                  size="sm"
                  icon={<List size={16} />}
                  onClick={() => setViewMode('list')}
                />
              </Tooltip>
              <Tooltip content="Detail View">
                <Button
                  variant={viewMode === 'detail' ? 'primary' : 'ghost'}
                  size="sm"
                  icon={<Maximize2 size={16} />}
                  onClick={() => setViewMode('detail')}
                />
              </Tooltip>
            </div>
          )}

          {/* Quick actions for current item */}
          {currentItem && viewMode === 'detail' && (
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                icon={<FolderOpen size={16} />}
                onClick={() => handleOpenInFinder(currentItem.path)}
              >
                Show in Finder
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<ExternalLink size={16} />}
                onClick={() => handleOpenFile(currentItem.path)}
              >
                Open
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Content area */}
      {currentItems.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <Card variant="glass" padding="lg" className="max-w-md border border-slate-700/50">
            <div className="text-center">
              {activeTab === 'clips' ? (
                <>
                  <div className="p-6 bg-primary-500/10 rounded-2xl inline-block mb-4">
                    <Video className="w-16 h-16 text-primary-400" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-200 mb-2">No Clips Yet</h3>
                  <p className="text-sm text-slate-400 mb-4">
                    Process a video to see your extracted clips here
                  </p>
                  <div className="flex items-start gap-3 p-4 bg-primary-900/20 border border-primary-600/30 rounded-xl">
                    <Sparkles className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-slate-300 text-left">
                      <span className="font-semibold text-primary-400">Tip:</span> Enable debug mode
                      to see how the AI detects comedians and segments your video
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="p-6 bg-emerald-500/10 rounded-2xl inline-block mb-4">
                    <ImageIcon className="w-16 h-16 text-emerald-400" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-200 mb-2">No Debug Frames</h3>
                  <p className="text-sm text-slate-400">
                    Enable debug mode in settings to see detection frames
                  </p>
                </>
              )}
            </div>
          </Card>
        </div>
      ) : (
        <>
          {viewMode === 'grid' && <GridView />}
          {viewMode === 'list' && <ListView />}
          {viewMode === 'detail' && <DetailView />}
        </>
      )}
    </div>
  )
}

export default OutputViewer
