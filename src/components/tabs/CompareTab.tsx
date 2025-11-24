import React, { useState } from 'react';
import { Play, FileVideo, ChevronDown, ChevronRight } from 'lucide-react';
import DropZone from '../DropZone';
import { ModelCard, type ModelInfo } from '../ModelCard';
import { ComparisonProgress } from '../ComparisonProgress';
import { ComparisonResults } from '../ComparisonResults';
import VideoPreview from '../VideoPreview';
import Toggle from '../ui/Toggle';
import { useVideoStore } from '../../stores/videoStore';
import { useComparisonStore } from '../../stores/comparisonStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useUIStore } from '../../stores/uiStore';

// All available models for comparison including OpenPose
const COMPARISON_MODELS: ModelInfo[] = [
  {
    id: 'yolo',
    name: 'YOLO Pose',
    description: 'YOLO11 pose detection, 17 keypoints, multi-person',
    speed: 'fast',
    accuracy: 'excellent',
    recommended: true,
  },
  {
    id: 'mediapipe',
    name: 'MediaPipe Pose',
    description: 'Google MediaPipe, 33 keypoints, single-person',
    speed: 'fast',
    accuracy: 'high',
  },
  {
    id: 'openpose_coco',
    name: 'OpenPose COCO',
    description: 'CMU OpenPose, 18 keypoints, multi-person',
    speed: 'slow',
    accuracy: 'excellent',
  },
  {
    id: 'openpose_mpi',
    name: 'OpenPose MPI',
    description: 'CMU OpenPose, 15 keypoints, multi-person',
    speed: 'moderate',
    accuracy: 'high',
  },
  {
    id: 'movenet_lightning',
    name: 'MoveNet Lightning',
    description: 'TensorFlow MoveNet, fast variant, 17 keypoints',
    speed: 'fast',
    accuracy: 'good',
  },
  {
    id: 'movenet_thunder',
    name: 'MoveNet Thunder',
    description: 'TensorFlow MoveNet, accurate variant, 17 keypoints',
    speed: 'moderate',
    accuracy: 'high',
  },
  {
    id: 'mmpose_rtmpose_m',
    name: 'MMPose RTMPose-M',
    description: 'OpenMMLab RTMPose medium, real-time performance',
    speed: 'fast',
    accuracy: 'high',
  },
  {
    id: 'mmpose_hrnet_w48',
    name: 'MMPose HRNet-W48',
    description: 'OpenMMLab HRNet, highest accuracy',
    speed: 'slow',
    accuracy: 'excellent',
  },
];

const MODEL_NAMES: Record<string, string> = Object.fromEntries(
  COMPARISON_MODELS.map((m) => [m.id, m.name])
);

export function CompareTab() {
  const selectedVideo = useVideoStore((state) => state.selectedVideo);
  const setVideo = useVideoStore((state) => state.setVideo);

  const overlayConfig = useSettingsStore((state) => state.overlayConfig);
  const setOverlayConfig = useSettingsStore((state) => state.setOverlayConfig);

  const isRunning = useComparisonStore((state) => state.isRunning);
  const selectedModels = useComparisonStore((state) => state.selectedModels);
  const toggleModel = useComparisonStore((state) => state.toggleModel);
  const modelProgress = useComparisonStore((state) => state.modelProgress);
  const modelResults = useComparisonStore((state) => state.modelResults);

  const showToast = useUIStore((state) => state.showToast);

  const [showOverlaySettings, setShowOverlaySettings] = useState(false);

  const handleVideoSelect = async (path: string) => {
    try {
      const duration = await window.electron?.getVideoDuration(path);
      setVideo(path, duration || 0);
      showToast('Video loaded successfully', 'success');
    } catch (error) {
      showToast('Failed to load video', 'error');
    }
  };

  const handleRunComparison = async () => {
    if (!selectedVideo) {
      showToast('Please select a video first', 'error');
      return;
    }

    if (selectedModels.length === 0) {
      showToast('Please select at least one model', 'error');
      return;
    }

    try {
      // TODO: Call the pose comparison runner with overlay export
      await window.electron?.runPoseComparison({
        videoPath: selectedVideo,
        modelIds: selectedModels,
        overlayConfig,
      });
    } catch (error) {
      showToast('Failed to start comparison', 'error');
    }
  };

  const handleExportReport = () => {
    // Export comparison results as JSON
    const report = {
      video: selectedVideo,
      timestamp: new Date().toISOString(),
      models: selectedModels,
      results: modelResults,
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);

    showToast('Report exported successfully', 'success');
  };

  const handleViewOverlay = async (modelId: string) => {
    const overlayPath = modelResults[modelId]?.overlayVideo;
    if (overlayPath) {
      await window.electron?.openVideo(overlayPath);
    }
  };

  const handleViewClips = (modelId: string) => {
    // Switch to results tab with filter for this model
    useUIStore.getState().setActiveTab('results');
    showToast(`Viewing clips from ${MODEL_NAMES[modelId]}`, 'info');
  };

  // Build progress array for ComparisonProgress component
  const progressArray = selectedModels.map((modelId) => ({
    modelId,
    modelName: MODEL_NAMES[modelId] || modelId,
    progress: modelProgress[modelId] || 0,
    status: modelResults[modelId]?.error
      ? ('error' as const)
      : modelProgress[modelId] === 100
      ? ('completed' as const)
      : modelProgress[modelId] > 0
      ? ('running' as const)
      : ('pending' as const),
    message: modelResults[modelId]?.error,
  }));

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-8">
        {/* Video Selection */}
        {!selectedVideo ? (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">
              Select Video to Compare
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
                onStartProcessing={handleRunComparison}
                isProcessing={isRunning}
                onSelectNewVideo={() => setVideo(null)}
              />
            </div>

            {/* Model Selection */}
            {!isRunning && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">
                  Select Models to Compare
                </h2>
                <p className="text-[var(--color-text-muted)]">
                  Select multiple models to run in parallel and compare results
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {COMPARISON_MODELS.map((model) => (
                    <ModelCard
                      key={model.id}
                      model={model}
                      selected={selectedModels.includes(model.id)}
                      onToggle={toggleModel}
                      multiSelect={true}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Overlay Export Settings */}
            {!isRunning && selectedModels.length > 0 && (
              <div className="space-y-4">
                <button
                  onClick={() => setShowOverlaySettings(!showOverlaySettings)}
                  className="flex items-center gap-2 text-lg font-semibold text-[var(--color-text-primary)] hover:text-[var(--color-primary)] transition-colors"
                >
                  {showOverlaySettings ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                  Overlay Export Settings
                </button>

                {showOverlaySettings && (
                  <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Toggle
                        label="Export Full Video with Overlays"
                        checked={overlayConfig.exportFullVideo}
                        onChange={(checked) => setOverlayConfig({ exportFullVideo: checked })}
                      />

                      <Toggle
                        label="Include Pose Skeletons"
                        checked={overlayConfig.includeSkeletons}
                        onChange={(checked) => setOverlayConfig({ includeSkeletons: checked })}
                      />

                      <Toggle
                        label="Include Bounding Boxes"
                        checked={overlayConfig.includeBoundingBoxes}
                        onChange={(checked) => setOverlayConfig({ includeBoundingBoxes: checked })}
                      />

                      <Toggle
                        label="Include Info Overlay"
                        checked={overlayConfig.includeInfoOverlay}
                        onChange={(checked) => setOverlayConfig({ includeInfoOverlay: checked })}
                      />

                      <Toggle
                        label="Include Stage Markers"
                        checked={overlayConfig.includeStageMarkers}
                        onChange={(checked) => setOverlayConfig({ includeStageMarkers: checked })}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                        Overlay Opacity: {Math.round(overlayConfig.opacity * 100)}%
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={overlayConfig.opacity}
                        onChange={(e) => setOverlayConfig({ opacity: parseFloat(e.target.value) })}
                        className="w-full"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Run Comparison Button */}
            {!isRunning && selectedModels.length > 0 && (
              <button
                onClick={handleRunComparison}
                className="w-full flex items-center justify-center gap-3 px-8 py-4 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg text-lg font-semibold transition-colors"
              >
                <Play size={24} />
                Run Comparison ({selectedModels.length} model{selectedModels.length !== 1 ? 's' : ''})
              </button>
            )}

            {/* Progress */}
            {isRunning && <ComparisonProgress modelProgress={progressArray} />}

            {/* Results */}
            {Object.keys(modelResults).length > 0 && (
              <ComparisonResults
                results={modelResults}
                modelNames={MODEL_NAMES}
                onViewOverlay={handleViewOverlay}
                onViewClips={handleViewClips}
                onExportReport={handleExportReport}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
