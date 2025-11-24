import React, { useState } from 'react';
import { Film, FileVideo, Image, Download, FolderOpen, Play, Trash2 } from 'lucide-react';
import { OverlayVideoPlayer } from '../OverlayVideoPlayer';
import DebugFrameViewer from '../DebugFrameViewer';
import { useResultsStore } from '../../stores/resultsStore';
import { useComparisonStore } from '../../stores/comparisonStore';
import { useUIStore } from '../../stores/uiStore';

type ViewMode = 'clips' | 'overlays' | 'debug';

export function ResultsTab() {
  const clips = useResultsStore((state) => state.clips);
  const debugFrames = useResultsStore((state) => state.debugFrames);
  const debugVideos = useResultsStore((state) => state.debugVideos);

  const overlayVideos = useComparisonStore((state) => state.overlayVideos);

  const showToast = useUIStore((state) => state.showToast);
  const setShowDebugFrameViewer = useUIStore((state) => state.setShowDebugFrameViewer);

  const [viewMode, setViewMode] = useState<ViewMode>('clips');
  const [selectedOverlay, setSelectedOverlay] = useState<string | null>(null);

  const hasClips = clips.length > 0;
  const hasOverlays = Object.keys(overlayVideos).length > 0;
  const hasDebug = debugFrames.length > 0 || debugVideos.length > 0;

  const handleOpenClip = async (clipPath: string) => {
    try {
      await window.electron?.openVideo(clipPath);
    } catch (error) {
      showToast('Failed to open clip', 'error');
    }
  };

  const handleOpenOutputDir = async () => {
    try {
      await window.electron?.openOutputDir();
    } catch (error) {
      showToast('Failed to open output directory', 'error');
    }
  };

  const handleExportAll = async () => {
    showToast('Export all feature coming soon!', 'info');
  };

  if (!hasClips && !hasOverlays && !hasDebug) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-[var(--color-bg-secondary)] rounded-full mb-4">
            <Film size={48} className="text-[var(--color-text-muted)]" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">No Results Yet</h2>
          <p className="text-[var(--color-text-muted)] max-w-md">
            Process a video or run a model comparison to see results here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">Results</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={handleOpenOutputDir}
              className="flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg transition-colors"
            >
              <FolderOpen size={16} />
              Open Output Folder
            </button>
            <button
              onClick={handleExportAll}
              className="flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg transition-colors"
            >
              <Download size={16} />
              Export All
            </button>
          </div>
        </div>

        {/* View Mode Tabs */}
        <div className="flex gap-2 border-b border-[var(--color-border)]">
          <button
            onClick={() => setViewMode('clips')}
            className={`px-6 py-3 text-sm font-medium transition-colors relative ${
              viewMode === 'clips'
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <div className="flex items-center gap-2">
              <Film size={16} />
              Clips ({clips.length})
            </div>
            {viewMode === 'clips' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
            )}
          </button>

          <button
            onClick={() => setViewMode('overlays')}
            className={`px-6 py-3 text-sm font-medium transition-colors relative ${
              viewMode === 'overlays'
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
            disabled={!hasOverlays}
          >
            <div className="flex items-center gap-2">
              <FileVideo size={16} />
              Overlay Videos ({Object.keys(overlayVideos).length})
            </div>
            {viewMode === 'overlays' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
            )}
          </button>

          <button
            onClick={() => setViewMode('debug')}
            className={`px-6 py-3 text-sm font-medium transition-colors relative ${
              viewMode === 'debug'
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
            disabled={!hasDebug}
          >
            <div className="flex items-center gap-2">
              <Image size={16} />
              Debug Frames ({debugFrames.length})
            </div>
            {viewMode === 'debug' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
            )}
          </button>
        </div>

        {/* Clips View */}
        {viewMode === 'clips' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
                Generated Clips
              </h2>
              <p className="text-sm text-[var(--color-text-muted)]">
                {clips.length} clip{clips.length !== 1 ? 's' : ''} found
              </p>
            </div>

            {clips.length === 0 ? (
              <div className="text-center py-12 text-[var(--color-text-muted)]">
                No clips generated yet
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {clips.map((clip, index) => (
                  <div
                    key={clip.path}
                    className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden hover:border-[var(--color-primary)] transition-colors group"
                  >
                    {/* Thumbnail/Preview */}
                    <div className="aspect-video bg-[var(--color-bg-tertiary)] flex items-center justify-center">
                      <Film size={48} className="text-[var(--color-text-muted)]" />
                    </div>

                    {/* Info */}
                    <div className="p-4 space-y-3">
                      <div>
                        <h3 className="font-medium text-[var(--color-text-primary)] truncate">
                          {clip.name}
                        </h3>
                        {clip.size && (
                          <p className="text-xs text-[var(--color-text-muted)]">
                            {(clip.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleOpenClip(clip.path)}
                          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded text-sm transition-colors"
                        >
                          <Play size={14} />
                          Play
                        </button>
                        <button
                          className="p-2 hover:bg-[var(--color-bg-tertiary)] rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} className="text-[var(--color-text-muted)]" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Overlay Videos View */}
        {viewMode === 'overlays' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
                Overlay Videos
              </h2>
              <p className="text-sm text-[var(--color-text-muted)]">
                Full videos with pose detection overlays
              </p>
            </div>

            {/* Selected Overlay Player */}
            {selectedOverlay && overlayVideos[selectedOverlay] && (
              <div className="mb-6">
                <OverlayVideoPlayer
                  videoPath={overlayVideos[selectedOverlay]}
                  title={`${selectedOverlay} - Overlay Video`}
                  onClose={() => setSelectedOverlay(null)}
                />
              </div>
            )}

            {/* Overlay List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(overlayVideos).map(([modelId, videoPath]) => (
                <button
                  key={modelId}
                  onClick={() => setSelectedOverlay(modelId)}
                  className={`bg-[var(--color-bg-secondary)] border rounded-lg p-6 text-left transition-all ${
                    selectedOverlay === modelId
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary-light)]'
                      : 'border-[var(--color-border)] hover:border-[var(--color-border-light)]'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-[var(--color-bg-tertiary)] rounded">
                      <FileVideo size={24} className="text-[var(--color-primary)]" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-[var(--color-text-primary)]">
                        {modelId}
                      </h3>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        Overlay Video
                      </p>
                    </div>
                  </div>
                  <div className="text-sm text-[var(--color-text-muted)] truncate">
                    {videoPath.split('/').pop()}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Debug Frames View */}
        {viewMode === 'debug' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
                Debug Frames
              </h2>
              <button
                onClick={() => setShowDebugFrameViewer(true)}
                className="text-sm text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors"
              >
                Open Frame Viewer
              </button>
            </div>

            {debugFrames.length === 0 ? (
              <div className="text-center py-12 text-[var(--color-text-muted)]">
                No debug frames available
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {debugFrames.slice(0, 24).map((frame, index) => (
                  <div
                    key={index}
                    className="aspect-video bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden hover:border-[var(--color-primary)] transition-colors cursor-pointer"
                    onClick={() => setShowDebugFrameViewer(true)}
                  >
                    {frame.data && (
                      <img
                        src={`data:image/jpeg;base64,${frame.data}`}
                        alt={`Debug frame ${index}`}
                        className="w-full h-full object-cover"
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {debugFrames.length > 24 && (
              <button
                onClick={() => setShowDebugFrameViewer(true)}
                className="w-full py-3 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-lg hover:border-[var(--color-primary)] transition-colors"
              >
                View all {debugFrames.length} frames
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
