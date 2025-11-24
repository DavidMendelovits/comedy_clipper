import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Square } from 'lucide-react';
import DropZone from '../DropZone';
import { ModelCard, type ModelInfo } from '../ModelCard';
import ProgressPanel from '../ProgressPanel';
import VideoPreview from '../VideoPreview';
import { AdvancedParameters } from '../AdvancedParameters';
import { useVideoStore } from '../../stores/videoStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useProcessingStore } from '../../stores/processingStore';
import { useResultsStore } from '../../stores/resultsStore';
import { useUIStore } from '../../stores/uiStore';
import { useJobsStore } from '../../stores/jobsStore';

const AVAILABLE_MODELS: ModelInfo[] = [
  {
    id: 'yolo_pose',
    name: 'YOLO Pose',
    description: 'Latest YOLO11 pose detection with multi-person tracking',
    speed: 'fast',
    accuracy: 'excellent',
    recommended: true,
  },
  {
    id: 'pose',
    name: 'MediaPipe Pose',
    description: 'Google MediaPipe pose estimation, fast and lightweight',
    speed: 'fast',
    accuracy: 'high',
  },
  {
    id: 'multimodal',
    name: 'Multimodal',
    description: 'Combined face + pose detection for best accuracy',
    speed: 'moderate',
    accuracy: 'excellent',
  },
  {
    id: 'face',
    name: 'Face Detection',
    description: 'MediaPipe face detection only',
    speed: 'fast',
    accuracy: 'good',
  },
  {
    id: 'mediapipe',
    name: 'MediaPipe Tracking',
    description: 'Position-based tracking with entry/exit detection',
    speed: 'fast',
    accuracy: 'high',
  },
  {
    id: 'scene',
    name: 'Scene Detection',
    description: 'FFmpeg scene detection for camera cuts',
    speed: 'moderate',
    accuracy: 'good',
  },
  {
    id: 'diarization',
    name: 'Diarization',
    description: 'Speaker diarization (requires HF_TOKEN)',
    speed: 'slow',
    accuracy: 'high',
  },
];

export function ProcessTab() {
  const navigate = useNavigate();

  const selectedVideo = useVideoStore((state) => state.selectedVideo);
  const setVideo = useVideoStore((state) => state.setVideo);

  const config = useSettingsStore((state) => state.config);
  const setConfig = useSettingsStore((state) => state.setConfig);
  const overlayConfig = useSettingsStore((state) => state.overlayConfig);

  const isProcessing = useProcessingStore((state) => state.isProcessing);
  const progress = useProcessingStore((state) => state.progress);

  const clips = useResultsStore((state) => state.clips);

  const showToast = useUIStore((state) => state.showToast);
  const setShowSettings = useUIStore((state) => state.setShowSettings);

  // Job store
  const activeJobId = useJobsStore((state) => state.activeJobId);

  const handleVideoSelect = async (path: string) => {
    try {
      const duration = await window.electron?.getVideoDuration(path);
      setVideo(path, duration || 0);
      showToast('Video loaded successfully', 'success');
    } catch (error) {
      showToast('Failed to load video', 'error');
    }
  };

  const handleModelSelect = (modelId: string) => {
    setConfig({
      clipperType: modelId as any,
    });
  };

  const handleProcess = async () => {
    if (!selectedVideo) {
      showToast('Please select a video first', 'error');
      return;
    }

    console.log('[ProcessTab] Starting job creation...');

    try {
      const jobsStore = useJobsStore.getState();

      // Create a new job
      console.log('[ProcessTab] Creating job with config:', config, 'overlayConfig:', overlayConfig);
      const jobId = await jobsStore.createJob({
        type: 'clipper',
        videoPath: selectedVideo,
        config: {
          clipperType: config.clipperType,
          minDuration: config.minDuration,
          maxDuration: config.maxDuration,
          outputDir: config.outputDir,
          debug: config.debug,
          exitThreshold: config.exitThreshold,
          exitStabilityFrames: config.exitStabilityFrames,
          yoloModel: config.yoloModel,
          yoloEnabled: config.yoloEnabled,
          personCountMethod: config.personCountMethod,
          zoneCrossingEnabled: config.zoneCrossingEnabled,
          configFile: config.configFile,
          // Advanced parameters
          mergeThreshold: config.mergeThreshold,
          bufferBefore: config.bufferBefore,
          bufferAfter: config.bufferAfter,
          blurDetectionEnabled: config.blurDetectionEnabled,
          // Overlay video settings
          exportOverlayVideo: overlayConfig.exportFullVideo,
          overlayIncludeSkeletons: overlayConfig.includeSkeletons,
          overlayIncludeBoundingBoxes: overlayConfig.includeBoundingBoxes,
          overlayShowInfo: overlayConfig.includeInfoOverlay,
        },
      });

      console.log('[ProcessTab] Job created with ID:', jobId);

      if (!jobId) {
        console.error('[ProcessTab] Job creation failed - no jobId returned');
        showToast('Failed to create job', 'error');
        return;
      }

      // Start the job
      console.log('[ProcessTab] Starting job:', jobId);
      const success = await jobsStore.startJob(jobId);
      console.log('[ProcessTab] Job start result:', success);

      if (success) {
        showToast('Job started successfully', 'success');
        // Navigate to jobs list page to show all ongoing jobs
        console.log('[ProcessTab] Navigating to jobs list page');
        navigate('/jobs');
        console.log('[ProcessTab] Navigation called');
      } else {
        console.error('[ProcessTab] Job start failed');
        showToast('Failed to start job', 'error');
      }
    } catch (error) {
      console.error('[ProcessTab] Error processing video:', error);
      showToast('Failed to start processing', 'error');
    }
  };

  const handleStop = async () => {
    if (!activeJobId) {
      // Fallback to legacy stop if no active job
      try {
        await window.electron?.stopClipper();
      } catch (error) {
        showToast('Failed to stop processing', 'error');
      }
      return;
    }

    try {
      const success = await useJobsStore.getState().cancelJob(activeJobId);
      if (success) {
        showToast('Job cancelled', 'success');
      } else {
        showToast('Failed to cancel job', 'error');
      }
    } catch (error) {
      showToast('Failed to stop processing', 'error');
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-8">
        {/* Video Selection */}
        {!selectedVideo ? (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">
              Select Video
            </h2>
            <DropZone onVideoSelect={handleVideoSelect} />
          </div>
        ) : (
          <>
            {/* Video Preview */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">
                  Video Preview
                </h2>
                <button
                  onClick={() => setVideo(null)}
                  className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Change Video
                </button>
              </div>
              <VideoPreview
                videoPath={selectedVideo}
                onStartProcessing={handleProcess}
                isProcessing={isProcessing}
                onSelectNewVideo={() => setVideo(null)}
              />
            </div>

            {/* Model Selection */}
            {!isProcessing && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">
                  Select Detection Method
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {AVAILABLE_MODELS.map((model) => (
                    <ModelCard
                      key={model.id}
                      model={model}
                      selected={config.clipperType === model.id}
                      onToggle={handleModelSelect}
                      multiSelect={false}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Advanced Parameters */}
            {!isProcessing && (
              <AdvancedParameters config={config} setConfig={setConfig} />
            )}

            {/* Process Button */}
            {!isProcessing && (
              <button
                onClick={handleProcess}
                className="w-full flex items-center justify-center gap-3 px-8 py-4 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg text-lg font-semibold transition-colors"
              >
                <Play size={24} />
                Process Video
              </button>
            )}

            {/* Progress Panel */}
            {isProcessing && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">
                    Processing...
                  </h2>
                  <button
                    onClick={handleStop}
                    className="flex items-center gap-2 px-4 py-2 bg-[var(--color-error)] hover:bg-red-600 text-white rounded-lg transition-colors"
                  >
                    <Square size={16} />
                    Stop
                  </button>
                </div>
                <ProgressPanel />
              </div>
            )}

            {/* Results Summary */}
            {!isProcessing && clips.length > 0 && (
              <div className="bg-[var(--color-accent-light)] border border-[var(--color-accent)] rounded-lg p-6">
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
                  Processing Complete!
                </h3>
                <p className="text-[var(--color-text-secondary)]">
                  Found {clips.length} clip{clips.length !== 1 ? 's' : ''}.
                  Go to the <button
                    onClick={() => useUIStore.getState().setActiveTab('results')}
                    className="text-[var(--color-accent)] hover:underline font-medium"
                  >
                    Results
                  </button> tab to view and export them.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
