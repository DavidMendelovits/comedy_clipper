import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import LogViewer from './components/LogViewer';
import SegmentReviewModal from './components/SegmentReviewModal';
import DebugFrameViewer from './components/DebugFrameViewer';
import Toast from './components/Toast';
import {
  useVideoStore,
  useProcessingStore,
  useResultsStore,
  useUIStore,
  useSettingsStore,
  useComparisonStore,
  setupJobEventListeners,
} from './stores';

function App() {
  // UI state
  const showLogs = useUIStore((state) => state.showLogs);
  const setShowLogs = useUIStore((state) => state.setShowLogs);
  const showReviewModal = useUIStore((state) => state.showReviewModal);
  const setShowReviewModal = useUIStore((state) => state.setShowReviewModal);
  const showDebugFrameViewer = useUIStore((state) => state.showDebugFrameViewer);
  const setShowDebugFrameViewer = useUIStore((state) => state.setShowDebugFrameViewer);
  const toast = useUIStore((state) => state.toast);
  const clearToast = useUIStore((state) => state.clearToast);

  // Video state
  const selectedVideo = useVideoStore((state) => state.selectedVideo);
  const duration = useVideoStore((state) => state.duration);
  const setDuration = useVideoStore((state) => state.setDuration);

  // Processing state (kept for backward compatibility with existing components)
  const addLog = useProcessingStore((state) => state.addLog);
  const setProgress = useProcessingStore((state) => state.setProgress);
  const setFrameProgress = useProcessingStore((state) => state.setFrameProgress);
  const addStep = useProcessingStore((state) => state.addStep);
  const setPhaseProgress = useProcessingStore((state) => state.setPhaseProgress);
  const setProcessing = useProcessingStore((state) => state.setProcessing);
  const setLogFile = useProcessingStore((state) => state.setLogFile);

  // Results state
  const setClips = useResultsStore((state) => state.setClips);
  const detectedSegments = useResultsStore((state) => state.detectedSegments);
  const filteredSegments = useResultsStore((state) => state.filteredSegments);

  // Settings
  const config = useSettingsStore((state) => state.config);

  // Comparison state
  const setModelProgress = useComparisonStore((state) => state.setModelProgress);
  const setModelResult = useComparisonStore((state) => state.setModelResult);

  // Set up job event listeners (only once on mount)
  useEffect(() => {
    if (!window.electron) {
      console.error('Electron API not available! Preload script may not have loaded.');
      return;
    }

    console.log('Electron API available:', Object.keys(window.electron));

    // Initialize job event listeners
    setupJobEventListeners();

    // Legacy IPC listeners (maintained for backward compatibility)
    window.electron.onClipperOutput?.((data: any) => {
      addLog(`[${data.type}] ${data.message}`);
    });

    window.electron.onClipperProgress?.((data: any) => {
      setProgress(data.percent);
      setFrameProgress(data.current, data.total);

      if (data.phase) {
        setPhaseProgress({
          phase: data.phase,
          percent: data.percent,
          message: data.message,
          current: data.current,
          total: data.total,
        });
      }
    });

    window.electron.onClipperStep?.((data: any) => {
      addStep(data.step);
    });

    window.electron.onPoseComparisonProgress?.((data: any) => {
      if (data.type === 'progress') {
        setModelProgress(data.modelId, data.percent);
      } else if (data.type === 'complete') {
        setModelResult(data.modelId, data.result);
      } else if (data.type === 'error') {
        setModelResult(data.modelId, { modelId: data.modelId, error: data.error });
      }
    });
  }, []);

  // Fetch video duration when video changes
  useEffect(() => {
    if (selectedVideo) {
      window.electron.getVideoDuration?.(selectedVideo).then((dur) => {
        if (dur) setDuration(dur);
      });
    }
  }, [selectedVideo, setDuration]);

  // Handle segment review approval
  const handleSegmentsApproved = async (selectedSegments: { start: number; end: number }[]) => {
    if (!selectedVideo) return;

    setShowReviewModal(false);
    setShowLogs(true);
    setProcessing(true);

    try {
      const result = await window.electron?.reclipSegments({
        videoPath: selectedVideo,
        segments: selectedSegments,
        outputDir: config.outputDir,
        debug: config.debug,
      });

      if (result?.success) {
        setClips(result.clips || []);
        setProcessing(false);
        setProgress(100);
        if (result.log_file) {
          setLogFile(result.log_file);
        }

        useUIStore.getState().showToast(
          `Successfully created ${result.clips?.length || 0} clip${result.clips?.length !== 1 ? 's' : ''}!`,
          'success'
        );
      }
    } catch (error: any) {
      console.error('Re-clipping error:', error);
      setProcessing(false);
      addLog(`[ERROR] ${error.error || error.message}`);
      useUIStore.getState().showToast(
        `Re-clipping failed: ${error.error || error.message}`,
        'error'
      );
    }
  };

  return (
    <>
      {/* Router Provider - Main App */}
      <RouterProvider router={router} />

      {/* Global Modals and Overlays */}
      {/* Log Viewer Panel */}
      <LogViewer isOpen={showLogs} onClose={() => setShowLogs(false)} />

      {/* Segment Review Modal */}
      {selectedVideo && (
        <SegmentReviewModal
          isOpen={showReviewModal}
          segments={filteredSegments.length > 0 ? filteredSegments : detectedSegments}
          videoPath={selectedVideo}
          videoDuration={duration}
          onApprove={handleSegmentsApproved}
          onCancel={() => setShowReviewModal(false)}
        />
      )}

      {/* Debug Frame Viewer */}
      {showDebugFrameViewer && (
        <DebugFrameViewer frames={[]} onClose={() => setShowDebugFrameViewer(false)} />
      )}

      {/* Toast Notification */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={clearToast} />}
    </>
  );
}

export default App;
