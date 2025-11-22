import { CheckCircle2, Circle, Loader2, FileText, PartyPopper } from 'lucide-react'
import { useState, useEffect } from 'react'
import Card from './ui/Card'
import Button from './ui/Button'

interface PhaseProgress {
  phase: string
  percent: number
  message?: string
  current?: number
  total?: number
}

interface ProcessState {
  running: boolean
  progress: number
  currentFrame: number
  totalFrames: number
  output: string[]
  steps: string[]
  currentStep: string
  logFile?: string
  phaseProgress?: PhaseProgress
}

interface ProgressPanelProps {
  processState: ProcessState
}

const ProgressPanel: React.FC<ProgressPanelProps> = ({ processState }) => {
  const [showLog, setShowLog] = useState(false)
  const [showCelebration, setShowCelebration] = useState(false)
  const [prevRunning, setPrevRunning] = useState(processState.running)

  // Define expected steps for visual progress
  const allSteps = [
    'Starting video processing',
    'Detecting segments',
    'Loading video',
    'Processing video frames',
    'Analyzing video',
    'Extracting audio for diarization',
    'Running speaker diarization model',
    'Filtering segments',
    'Creating video clips',
    'Processing complete'
  ]

  // Show celebration when processing completes
  useEffect(() => {
    if (prevRunning && !processState.running) {
      setShowCelebration(true)
      setTimeout(() => setShowCelebration(false), 3000)
    }
    setPrevRunning(processState.running)
  }, [processState.running, prevRunning])

  // Determine step status based on processState.steps
  const getStepStatus = (step: string): 'completed' | 'in-progress' | 'pending' => {
    if (processState.steps.includes(step)) {
      if (processState.currentStep === step && processState.running) {
        return 'in-progress'
      }
      return 'completed'
    }
    return 'pending'
  }

  // Get only relevant steps that have been started
  const relevantSteps = allSteps.filter(step => {
    const status = getStepStatus(step)
    return status !== 'pending' || processState.currentStep === step
  })

  return (
    <div className="flex-1 flex flex-col p-8 gap-6 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            {processState.running ? (
              <div className="p-3 bg-primary-500/20 rounded-xl animate-pulse">
                <Loader2 className="w-7 h-7 animate-spin text-primary-400" />
              </div>
            ) : (
              <div className="p-3 bg-emerald-500/20 rounded-xl">
                <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                {showCelebration && (
                  <div className="absolute -top-2 -right-2">
                    <PartyPopper className="w-6 h-6 text-yellow-400 animate-bounce-subtle" />
                  </div>
                )}
              </div>
            )}
          </div>
          <div>
            <h2 className={`text-2xl font-bold ${!processState.running && showCelebration ? 'text-gradient' : ''}`}>
              {processState.running ? 'Processing Video' : 'Processing Complete!'}
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {processState.running ? 'Please wait while we process your video' : 'Your video has been successfully processed'}
            </p>
          </div>
        </div>

        {processState.logFile && (
          <Button
            variant="secondary"
            size="sm"
            icon={<FileText size={16} />}
            onClick={() => setShowLog(!showLog)}
          >
            {showLog ? 'Hide' : 'View'} Log
          </Button>
        )}
      </div>

      {/* Phase-specific progress bars */}
      {processState.running && processState.phaseProgress && (
        <Card variant="gradient-border" padding="md">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-100 capitalize">
                  {processState.phaseProgress.phase} Phase
                </h3>
                {processState.phaseProgress.message && (
                  <p className="text-sm text-slate-400 mt-1">
                    {processState.phaseProgress.message}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-mono font-bold text-gradient">
                  {processState.phaseProgress.percent}%
                </span>
              </div>
            </div>

            <div className="space-y-2">
              {processState.phaseProgress.current && processState.phaseProgress.total && (
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Progress</span>
                  <span className="font-mono">
                    {processState.phaseProgress.current} / {processState.phaseProgress.total}
                  </span>
                </div>
              )}
              <div className="relative w-full h-4 bg-slate-700 rounded-full overflow-hidden shadow-inner">
                <div
                  className="absolute inset-0 bg-gradient-to-r from-primary-600 via-primary-500 to-primary-400 transition-all duration-500 ease-out shadow-glow-sm"
                  style={{ width: `${processState.phaseProgress.percent}%` }}
                >
                  <div className="absolute inset-0 shimmer" style={{ opacity: 0.3 }} />
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Step-based progress */}
      <Card variant="elevated" padding="md" className="flex-1 flex flex-col gap-4 overflow-hidden">
        <h3 className="text-lg font-semibold text-slate-100">Progress Steps</h3>

        <div className="flex-1 overflow-y-auto space-y-2 pr-2">
          {relevantSteps.map((step, index) => {
            const status = getStepStatus(step)

            return (
              <div
                key={index}
                className={`
                  flex items-center gap-3 p-4 rounded-xl transition-all duration-300
                  ${
                    status === 'in-progress'
                      ? 'bg-gradient-to-r from-primary-900/40 to-primary-800/30 border border-primary-600/50 shadow-glow-sm scale-[1.02]'
                      : status === 'completed'
                      ? 'bg-slate-700/30 border border-emerald-600/30'
                      : 'bg-slate-900/30 border border-slate-700/30'
                  }
                `}
              >
                <div className={`
                  flex-shrink-0 p-1.5 rounded-lg
                  ${status === 'in-progress' ? 'bg-primary-500/20' : status === 'completed' ? 'bg-emerald-500/20' : 'bg-slate-700/20'}
                `}>
                  {status === 'completed' && (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 animate-scale-in" />
                  )}
                  {status === 'in-progress' && (
                    <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
                  )}
                  {status === 'pending' && (
                    <Circle className="w-5 h-5 text-slate-500" />
                  )}
                </div>

                <span
                  className={`text-sm flex-1 ${
                    status === 'in-progress'
                      ? 'text-primary-200 font-semibold'
                      : status === 'completed'
                      ? 'text-slate-300'
                      : 'text-slate-500'
                  }`}
                >
                  {step}
                </span>

                {status === 'completed' && (
                  <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                )}
              </div>
            )
          })}
        </div>
      </Card>

      {/* Log file path */}
      {showLog && processState.logFile && (
        <Card variant="glass" padding="md">
          <div className="space-y-3">
            <div>
              <p className="text-xs font-medium text-slate-400 mb-2">Log file location:</p>
              <p className="text-xs font-mono text-slate-200 break-all bg-slate-950/50 p-3 rounded-lg border border-slate-700">
                {processState.logFile}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="primary"
                size="sm"
                fullWidth
                onClick={async () => {
                  await (window as any).electron.openFile(processState.logFile)
                }}
              >
                Open Log File
              </Button>
              <Button
                variant="secondary"
                size="sm"
                fullWidth
                onClick={async () => {
                  await (window as any).electron.openInFinder(processState.logFile)
                }}
              >
                Show in Finder
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Status message */}
      {processState.running && (
        <Card variant="glass" padding="md" className="border border-primary-600/30 bg-primary-900/10">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 relative">
              <div className="w-3 h-3 bg-primary-400 rounded-full animate-pulse" />
              <div className="absolute inset-0 w-3 h-3 bg-primary-400 rounded-full animate-ping opacity-75" />
            </div>
            <p className="text-sm text-primary-200 font-medium">
              {processState.currentStep || 'Processing in progress...'}
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}

export default ProgressPanel
