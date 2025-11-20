import { useState, useCallback } from 'react'
import { Upload, Video } from 'lucide-react'

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

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        w-full max-w-2xl p-12 rounded-2xl border-2 border-dashed
        transition-all duration-300 cursor-pointer
        ${isDragging
          ? 'border-primary-400 bg-primary-900/20 scale-105'
          : 'border-slate-600 bg-slate-800/50 hover:border-slate-500 hover:bg-slate-800'
        }
      `}
      onClick={handleBrowse}
    >
      <div className="flex flex-col items-center gap-6 text-center">
        <div className={`
          p-6 rounded-full transition-colors
          ${isDragging ? 'bg-primary-600' : 'bg-slate-700'}
        `}>
          {isDragging ? (
            <Video className="w-12 h-12 animate-pulse" />
          ) : (
            <Upload className="w-12 h-12" />
          )}
        </div>

        <div>
          <h3 className="text-2xl font-bold mb-2">
            {isDragging ? 'Drop your video here' : 'Drop a video to start'}
          </h3>
          <p className="text-slate-400 mb-4">
            or click to browse your files
          </p>
          <div className="flex flex-wrap justify-center gap-2 text-sm text-slate-500">
            <span className="px-2 py-1 bg-slate-700 rounded">MP4</span>
            <span className="px-2 py-1 bg-slate-700 rounded">MOV</span>
            <span className="px-2 py-1 bg-slate-700 rounded">AVI</span>
            <span className="px-2 py-1 bg-slate-700 rounded">MKV</span>
            <span className="px-2 py-1 bg-slate-700 rounded">WEBM</span>
          </div>
        </div>

        <div className="w-full max-w-md p-4 bg-slate-900/50 rounded-lg border border-slate-700">
          <p className="text-sm text-slate-300">
            <span className="font-semibold text-primary-400">Tip:</span> The configurable clipper
            uses AI to detect comedians by face and pose detection. Enable debug mode to see
            detection frames!
          </p>
        </div>
      </div>
    </div>
  )
}

export default DropZone
