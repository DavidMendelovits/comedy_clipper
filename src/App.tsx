import { useEffect, useState } from 'react'
import { Film, Play, Pause, FolderOpen, Terminal, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAppStore } from './store'
import DropZone from './components/DropZone'
import ProgressPanel from './components/ProgressPanel'
import OutputViewer from './components/OutputViewer'
import VideoPreview from './components/VideoPreview'
import LogViewer from './components/LogViewer'
import SegmentReviewModal from './components/SegmentReviewModal'
import Toast from './components/Toast'
import { Button, Card, Tooltip } from './components/ui'

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const {
    selectedVideo,
    config,
    processState,
    clips,
    detectedSegments,
    filteredSegments,
    debugFrames,
    keyframeMarkers,
    showLogs,
    showReviewModal,
    videoDuration,
    toast,
    setSelectedVideo,
    setConfig,
    setProcessState,
    setClips,
    setDetectedSegments,
    setFilteredSegments,
    setDebugFrames,
    setShowLogs,
    setShowReviewModal,
    setVideoDuration,
    setToast,
    resetProcessing,
  } = useAppStore()

  useEffect(() => {
    // Check if electron API is available
    if (!(window as any).electron) {
      console.error('Electron API not available! Preload script may not have loaded.')
      return
    }

    console.log('Electron API available:', Object.keys((window as any).electron))

    // Listen for clipper output
    ;(window as any).electron?.onClipperOutput((data: any) => {
      setProcessState({
        output: [...processState.output, `[${data.type}] ${data.message}`],
      })
    })

    // Listen for progress updates
    ;(window as any).electron?.onClipperProgress((data: any) => {
      setProcessState({
        progress: data.percent,
        currentFrame: data.current,
        totalFrames: data.total,
        phaseProgress: data.phase ? {
          phase: data.phase,
          percent: data.percent,
          message: data.message,
          current: data.current,
          total: data.total,
        } : processState.phaseProgress,
      })
    })

    // Listen for step updates
    ;(window as any).electron?.onClipperStep((data: any) => {
      setProcessState({
        currentStep: data.step,
        steps: [...processState.steps, data.step],
      })
    })
  }, [])

  const handleVideoSelect = async (videoPath: string) => {
    setSelectedVideo(videoPath)
    // Auto-set output directory to video's directory
    const videoDir = videoPath.substring(0, videoPath.lastIndexOf('/'))
    // Set optimal defaults for enhanced detection
    setConfig({
      outputDir: videoDir,
      clipperType: 'multimodal',
      yoloEnabled: true,
      zoneCrossingEnabled: true,
      personCountMethod: 'yolo_zone',
      minDuration: 15,
      debug: false,
      configFile: 'clipper_rules.yaml'
    })
  }

  const handleRunClipper = async () => {
    if (!selectedVideo) return

    if (!(window as any).electron) {
      console.error('Electron API not available!')
      alert('Electron API not loaded. Please restart the app.')
      return
    }

    // Auto-open logs when processing starts
    setShowLogs(true)

    // Reset processing state
    resetProcessing()
    setProcessState({
      running: true,
      progress: 0,
      currentFrame: 0,
      totalFrames: 0,
      output: [],
      steps: [],
      currentStep: '',
      logFile: undefined,
      phaseProgress: undefined,
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
          yoloEnabled: config.yoloEnabled,
          personCountMethod: config.personCountMethod,
          zoneCrossingEnabled: config.zoneCrossingEnabled,
          stageBoundary: config.stageBoundary,
        },
      })

      if (result.success) {
        setClips(result.clips || [])
        setProcessState({
          running: false,
          progress: 100,
          logFile: result.log_file
        })

        // Store segment timestamps
        if (result.segments_detected) {
          setDetectedSegments(result.segments_detected.map((seg: [number, number]) => ({
            start: seg[0],
            end: seg[1]
          })))
        }
        if (result.segments_filtered) {
          setFilteredSegments(result.segments_filtered.map((seg: [number, number]) => ({
            start: seg[0],
            end: seg[1]
          })))
        }

        // Load debug frames if available
        if (config.debug && result.debug_dir) {
          const debugData = await (window as any).electron.getDebugFrames(result.debug_dir)
          setDebugFrames(debugData.frames || [])
          if (debugData.csv_path) {
            console.log('CSV data available at:', debugData.csv_path)
          }
        }

        // Show success toast
        setToast({
          message: `Successfully processed video! Found ${result.clips?.length || 0} clip${result.clips?.length !== 1 ? 's' : ''}`,
          type: 'success'
        })
      }
    } catch (error: any) {
      console.error('Clipper error:', error)
      setProcessState({
        running: false,
        output: [...processState.output, `[ERROR] ${error.error || error.message}`],
        logFile: error.log_file || processState.logFile,
      })
      setToast({
        message: `Processing failed: ${error.error || error.message}`,
        type: 'error'
      })
    }
  }

  const handleStopClipper = async () => {
    await (window as any).electron.stopClipper()
    setProcessState({ running: false })
  }

  const handleSelectOutputDir = async () => {
    const dir = await (window as any).electron.selectOutputDirectory()
    if (dir) {
      setConfig({ outputDir: dir })
    }
  }

  const handleReviewSegments = () => {
    setShowReviewModal(true)
  }

  const handleSegmentsApproved = async (selectedSegments: { start: number; end: number }[]) => {
    if (!selectedVideo) return

    setShowReviewModal(false)
    setShowLogs(true)

    // Reset process state for re-clipping
    setProcessState({
      running: true,
      progress: 0,
      steps: [],
      currentStep: 'Re-clipping selected segments...',
    })

    try {
      const result = await (window as any).electron.reclipSegments({
        videoPath: selectedVideo,
        segments: selectedSegments,
        outputDir: config.outputDir,
        debug: config.debug,
      })

      if (result.success) {
        // Update clips with new results
        setClips(result.clips || [])
        setProcessState({
          running: false,
          progress: 100,
          currentStep: `Successfully created ${result.clips?.length || 0} clips`,
          logFile: result.log_file,
        })

        // Show success toast
        setToast({
          message: `Successfully created ${result.clips?.length || 0} clip${result.clips?.length !== 1 ? 's' : ''}!`,
          type: 'success',
        })

        console.log('Re-clipping complete:', result)
      }
    } catch (error: any) {
      console.error('Re-clipping error:', error)
      setProcessState({
        running: false,
        output: [...processState.output, `[ERROR] ${error.error || error.message}`],
        logFile: error.log_file || processState.logFile,
      })
      setToast({
        message: `Re-clipping failed: ${error.error || error.message}`,
        type: 'error'
      })
    }
  }

  return (
    <div className="flex flex-col h-screen bg-slate-900 text-white relative">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-5 pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(to right, #475569 1px, transparent 1px),
            linear-gradient(to bottom, #475569 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px'
        }} />
      </div>

      <div className="flex flex-1 overflow-hidden relative z-10">
        {/* Sidebar */}
        <div className={`
          ${sidebarCollapsed ? 'w-20' : 'w-96'}
          transition-all duration-300 ease-in-out
          flex flex-col relative border-r border-slate-700/50 bg-slate-800/50 backdrop-blur-sm
        `}>
          {/* Collapse Toggle */}
          <Tooltip content={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'} position="right">
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="absolute -right-3 top-6 z-50 p-1.5 bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded-lg shadow-lg transition-all hover:scale-110"
            >
              {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </Tooltip>

          {/* Header */}
          <div className="p-6 border-b border-slate-700/50">
            {!sidebarCollapsed ? (
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-gradient-to-br from-primary-600 to-primary-500 rounded-xl shadow-glow-sm">
                  <Film className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gradient">Comedy Clipper</h1>
                  <p className="text-xs text-slate-400">AI-Powered Video Clipping</p>
                </div>
              </div>
            ) : (
              <div className="flex justify-center">
                <div className="p-2.5 bg-gradient-to-br from-primary-600 to-primary-500 rounded-xl shadow-glow-sm">
                  <Film className="w-6 h-6" />
                </div>
              </div>
            )}
          </div>

          {/* Sidebar Content */}
          {!sidebarCollapsed ? (
            <div className="flex-1 flex flex-col p-6 gap-4 overflow-y-auto">
              {/* Video File */}
              <Card variant="elevated" padding="sm">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Video File
                </label>
                {selectedVideo ? (
                  <div className="p-3 bg-slate-950/50 rounded-lg text-sm break-all border border-slate-700">
                    {selectedVideo.split('/').pop()}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 italic">No video selected</p>
                )}
              </Card>

              {/* Output Directory */}
              <Card variant="elevated" padding="sm">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Output Directory
                </label>
                <Button
                  variant="secondary"
                  size="sm"
                  fullWidth
                  icon={<FolderOpen size={16} />}
                  onClick={handleSelectOutputDir}
                  className="justify-start"
                >
                  <span className="truncate">{config.outputDir || 'Select directory...'}</span>
                </Button>
              </Card>

              {/* Enhanced Detection Info */}
              <Card variant="elevated" padding="sm">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium text-green-400">Enhanced Detection Enabled</span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Using advanced multi-signal detection with velocity tracking, appearance analysis, and confidence scoring for reliable comic exit detection.
                  </p>
                </div>
              </Card>

              <div className="flex-1" />

              {/* Action Buttons */}
              <div className="space-y-3">
                <Button
                  variant="primary"
                  size="lg"
                  fullWidth
                  icon={<Play size={20} />}
                  onClick={handleRunClipper}
                  disabled={!selectedVideo || processState.running}
                >
                  Start Processing
                </Button>

                {processState.running && (
                  <Button
                    variant="danger"
                    size="lg"
                    fullWidth
                    icon={<Pause size={20} />}
                    onClick={handleStopClipper}
                  >
                    Stop Processing
                  </Button>
                )}
              </div>

              {/* Log Viewer Toggle */}
              <div className="border-t border-slate-700/50 pt-4">
                <Button
                  variant={showLogs ? 'primary' : 'secondary'}
                  size="md"
                  fullWidth
                  icon={<Terminal size={16} />}
                  onClick={() => setShowLogs(!showLogs)}
                >
                  {showLogs ? 'Hide' : 'Show'} Live Logs
                </Button>
              </div>
            </div>
          ) : (
            /* Collapsed Sidebar */
            <div className="flex-1 flex flex-col items-center py-6 gap-4">
              <Tooltip content="Start Processing" position="right">
                <Button
                  variant="primary"
                  size="icon"
                  icon={<Play size={20} />}
                  onClick={handleRunClipper}
                  disabled={!selectedVideo || processState.running}
                />
              </Tooltip>

              {processState.running && (
                <Tooltip content="Stop Processing" position="right">
                  <Button
                    variant="danger"
                    size="icon"
                    icon={<Pause size={20} />}
                    onClick={handleStopClipper}
                  />
                </Tooltip>
              )}

              <div className="flex-1" />

              <Tooltip content={showLogs ? 'Hide Live Logs' : 'Show Live Logs'} position="right">
                <Button
                  variant={showLogs ? 'primary' : 'secondary'}
                  size="icon"
                  icon={<Terminal size={16} />}
                  onClick={() => setShowLogs(!showLogs)}
                />
              </Tooltip>
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
            // Show video preview ALONGSIDE progress during processing
            selectedVideo ? (
              <div className="flex-1 flex overflow-hidden">
                <div className="flex-1">
                  <VideoPreview
                    videoPath={selectedVideo}
                    onStartProcessing={handleRunClipper}
                    isProcessing={processState.running}
                    segments={filteredSegments.length > 0 ? filteredSegments : detectedSegments}
                    keyframeMarkers={keyframeMarkers}
                    onDurationChange={setVideoDuration}
                    onReviewSegments={clips.length > 0 && filteredSegments.length > 0 ? handleReviewSegments : undefined}
                  />
                </div>
                <div className="w-96 border-l border-slate-700">
                  <ProgressPanel processState={processState} />
                </div>
              </div>
            ) : (
              <ProgressPanel processState={processState} />
            )
          ) : clips.length > 0 ? (
            <OutputViewer clips={clips} debugFrames={debugFrames} />
          ) : selectedVideo ? (
            <VideoPreview
              videoPath={selectedVideo}
              onStartProcessing={handleRunClipper}
              isProcessing={processState.running}
              segments={filteredSegments.length > 0 ? filteredSegments : detectedSegments}
              keyframeMarkers={keyframeMarkers}
              onDurationChange={setVideoDuration}
              onReviewSegments={clips.length > 0 && filteredSegments.length > 0 ? handleReviewSegments : undefined}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center p-8">
              <DropZone onVideoSelect={handleVideoSelect} />
            </div>
          )}
        </div>
      </div>

      {/* Log Viewer Panel */}
      <LogViewer isOpen={showLogs} onClose={() => setShowLogs(false)} />

      {/* Segment Review Modal */}
      {selectedVideo && (
        <SegmentReviewModal
          isOpen={showReviewModal}
          segments={filteredSegments.length > 0 ? filteredSegments : detectedSegments}
          videoPath={selectedVideo}
          videoDuration={videoDuration}
          onApprove={handleSegmentsApproved}
          onCancel={() => setShowReviewModal(false)}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}

export default App
