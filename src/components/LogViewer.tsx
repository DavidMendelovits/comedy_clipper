import { useState, useEffect, useRef } from 'react'
import { Terminal, X, Search, Copy, Trash2, ChevronDown, ChevronUp } from 'lucide-react'

interface LogEntry {
  level: string
  message: string
  timestamp: string
}

interface LogViewerProps {
  isOpen: boolean
  onClose: () => void
}

export default function LogViewer({ isOpen, onClose }: LogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filter, setFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState<'all' | 'info' | 'error'>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!(window as any).electron?.onClipperLog) return

    const cleanup = (window as any).electron.onClipperLog((data: LogEntry) => {
      setLogs(prev => [...prev, data])
    })

    return cleanup
  }, [])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const filteredLogs = logs.filter(log => {
    // Filter by level
    if (levelFilter !== 'all' && log.level !== levelFilter) return false

    // Filter by search text
    if (filter && !log.message.toLowerCase().includes(filter.toLowerCase())) return false

    return true
  })

  const handleCopyLogs = () => {
    const logText = filteredLogs
      .map(log => `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}`)
      .join('\n')
    navigator.clipboard.writeText(logText)
  }

  const handleClearLogs = () => {
    setLogs([])
  }

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'text-red-400'
      case 'warn': return 'text-yellow-400'
      case 'info': return 'text-blue-400'
      default: return 'text-slate-300'
    }
  }

  if (!isOpen) return null

  return (
    <div className="h-80 border-t border-slate-700 bg-slate-900 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary-400" />
          <span className="font-semibold text-sm">Live Logs</span>
          <span className="text-xs text-slate-400">({filteredLogs.length} entries)</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Level Filter */}
          <select
            value={levelFilter}
            onChange={e => setLevelFilter(e.target.value as any)}
            className="px-2 py-1 text-xs bg-slate-700 border border-slate-600 rounded"
          >
            <option value="all">All Levels</option>
            <option value="info">Info</option>
            <option value="error">Errors</option>
          </select>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400" />
            <input
              type="text"
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Filter logs..."
              className="pl-7 pr-2 py-1 text-xs bg-slate-700 border border-slate-600 rounded w-40 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          {/* Auto-scroll toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-1 text-xs rounded ${
              autoScroll
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-300'
            }`}
          >
            {autoScroll ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
          </button>

          {/* Copy logs */}
          <button
            onClick={handleCopyLogs}
            className="p-1 hover:bg-slate-700 rounded transition-colors"
            title="Copy logs"
          >
            <Copy className="w-4 h-4" />
          </button>

          {/* Clear logs */}
          <button
            onClick={handleClearLogs}
            className="p-1 hover:bg-slate-700 rounded transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-700 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Log Content */}
      <div
        ref={logContainerRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-0.5"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 text-center py-8">
            No logs yet. Start processing to see live output.
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} className="flex gap-2">
              <span className="text-slate-500 text-[10px] shrink-0">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`shrink-0 font-bold ${getLogLevelColor(log.level)}`}>
                [{log.level.toUpperCase()}]
              </span>
              <span className="text-slate-300 whitespace-pre-wrap break-all">
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
