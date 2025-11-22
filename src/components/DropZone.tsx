import { useState, useCallback } from 'react'
import { Upload, Video, Sparkles, FileVideo } from 'lucide-react'
import Card from './ui/Card'

interface DropZoneProps {
  onVideoSelect: (path: string) => void
}

const DropZone: React.FC<DropZoneProps> = ({ onVideoSelect }) => {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const videoFile = files.find(file =>
      /\.(mp4|mov|avi|mkv|webm)$/i.test(file.name)
    )

    if (videoFile) {
      onVideoSelect((videoFile as any).path)
    }
  }, [onVideoSelect])

  const handleBrowse = async () => {
    const path = await (window as any).electron?.selectVideo()
    if (path) {
      onVideoSelect(path)
    }
  }

  const supportedFormats = [
    { name: 'MP4', icon: FileVideo },
    { name: 'MOV', icon: FileVideo },
    { name: 'AVI', icon: FileVideo },
    { name: 'MKV', icon: FileVideo },
    { name: 'WEBM', icon: FileVideo },
  ]

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleBrowse}
      className={`
        w-full max-w-2xl transition-all duration-300 cursor-pointer
        ${isDragging ? 'scale-[1.02]' : 'hover:scale-[1.01]'}
      `}
    >
      <Card
        variant={isDragging ? 'gradient-border' : 'elevated'}
        padding="lg"
        className={`
          border-2 border-dashed
          ${isDragging
            ? 'border-primary-400 bg-primary-900/20 shadow-glow-lg'
            : 'border-slate-600 hover:border-slate-500'
          }
        `}
      >
        <div className="flex flex-col items-center gap-8 text-center">
          {/* Icon with animation */}
          <div className="relative">
            <div className={`
              p-8 rounded-2xl transition-all duration-300
              ${isDragging
                ? 'bg-gradient-to-br from-primary-600 to-primary-500 shadow-glow-md scale-110'
                : 'bg-slate-700/50 hover:bg-slate-700'
              }
            `}>
              {isDragging ? (
                <Video className="w-16 h-16 text-white animate-bounce-subtle" />
              ) : (
                <Upload className="w-16 h-16 text-slate-300" />
              )}
            </div>
            {isDragging && (
              <div className="absolute -top-2 -right-2">
                <Sparkles className="w-8 h-8 text-primary-300 animate-pulse" />
              </div>
            )}
          </div>

          {/* Text content */}
          <div>
            <h3 className={`
              text-3xl font-bold mb-3 transition-all duration-300
              ${isDragging ? 'text-gradient scale-105' : 'text-slate-100'}
            `}>
              {isDragging ? 'Drop your video here!' : 'Drop a video to start'}
            </h3>
            <p className="text-slate-400 text-lg mb-6">
              or <span className="text-primary-400 font-medium">click to browse</span> your files
            </p>

            {/* Supported formats */}
            <div className="flex flex-wrap justify-center gap-3">
              {supportedFormats.map((format) => (
                <div
                  key={format.name}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 rounded-lg border border-slate-600 hover:border-primary-500/50 hover:bg-slate-700 transition-all"
                >
                  <format.icon size={14} className="text-slate-400" />
                  <span className="text-sm text-slate-300 font-medium">{format.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tip card */}
          <div className="w-full max-w-md">
            <Card
              variant="glass"
              padding="md"
              className="border border-primary-500/20"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 p-2 bg-primary-500/20 rounded-lg">
                  <Sparkles className="w-5 h-5 text-primary-400" />
                </div>
                <p className="text-sm text-slate-300 text-left">
                  <span className="font-semibold text-primary-400">Pro Tip:</span> The configurable clipper
                  uses AI to detect comedians by face and pose detection. Enable debug mode to see
                  detection frames in action!
                </p>
              </div>
            </Card>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default DropZone
