import { useRef, useEffect } from 'react'
import { Activity, Terminal } from 'lucide-react'

interface ProcessState {
  running: boolean
  progress: number
  currentFrame: number
  totalFrames: number
  output: string[]
}

interface ProgressPanelProps {
  processState: ProcessState
}

const ProgressPanel: React.FC<ProgressPanelProps> = ({ processState }) => {
  const outputRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [processState.output])

  return (
    <div className="flex-1 flex flex-col p-8 gap-6 overflow-hidden">
      <div className="flex items-center gap-3">
        <Activity className={`w-6 h-6 ${processState.running ? 'animate-pulse text-primary-400' : 'text-slate-400'}`} />
        <h2 className="text-2xl font-bold">
          {processState.running ? 'Processing Video...' : 'Processing Complete'}
        </h2>
      </div>

      {processState.totalFrames > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">
              Frame {processState.currentFrame} of {processState.totalFrames}
            </span>
            <span className="font-mono text-primary-400">
              {processState.progress.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary-600 to-primary-400 transition-all duration-300 ease-out"
              style={{ width: `${processState.progress}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col bg-slate-950 rounded-lg border border-slate-800 overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 bg-slate-900 border-b border-slate-800">
          <Terminal className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Console Output</span>
        </div>

        <div
          ref={outputRef}
          className="flex-1 p-4 font-mono text-xs text-slate-300 overflow-y-auto space-y-1"
        >
          {processState.output.length === 0 ? (
            <div className="text-slate-500 italic">Waiting for output...</div>
          ) : (
            processState.output.map((line, index) => {
              const isError = line.includes('[stderr]') || line.includes('[ERROR]')
              const isStdout = line.includes('[stdout]')

              return (
                <div
                  key={index}
                  className={`
                    ${isError ? 'text-red-400' : ''}
                    ${isStdout ? 'text-slate-300' : ''}
                    ${!isError && !isStdout ? 'text-slate-400' : ''}
                  `}
                >
                  {line}
                </div>
              )
            })
          )}
        </div>
      </div>

      {processState.running && (
        <div className="flex items-center gap-3 px-4 py-3 bg-primary-900/20 border border-primary-700/50 rounded-lg">
          <div className="w-2 h-2 bg-primary-400 rounded-full animate-pulse" />
          <p className="text-sm text-primary-300">
            Processing in progress... This may take a while depending on video length.
          </p>
        </div>
      )}
    </div>
  )
}

export default ProgressPanel
