import React from 'react';
import { Play, FileVideo, Download, Eye } from 'lucide-react';
import type { ModelResult } from '../stores/comparisonStore';

interface ComparisonResultsProps {
  results: Record<string, ModelResult>;
  modelNames: Record<string, string>;
  onViewOverlay?: (modelId: string) => void;
  onViewClips?: (modelId: string) => void;
  onExportReport?: () => void;
}

export function ComparisonResults({
  results,
  modelNames,
  onViewOverlay,
  onViewClips,
  onExportReport,
}: ComparisonResultsProps) {
  const modelIds = Object.keys(results);

  if (modelIds.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Comparison Results
        </h3>

        {onExportReport && (
          <button
            onClick={onExportReport}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg transition-colors"
          >
            <Download size={16} />
            Export Report
          </button>
        )}
      </div>

      {/* Stats Table */}
      <div className="overflow-x-auto">
        <table className="w-full border border-[var(--color-border)] rounded-lg overflow-hidden">
          <thead className="bg-[var(--color-bg-tertiary)]">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-[var(--color-text-secondary)]">
                Model
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-[var(--color-text-secondary)]">
                Clips
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-[var(--color-text-secondary)]">
                Detection Rate
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-[var(--color-text-secondary)]">
                Avg FPS
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-[var(--color-text-secondary)]">
                Total Time
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-[var(--color-text-secondary)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-[var(--color-bg-secondary)]">
            {modelIds.map((modelId, index) => {
              const result = results[modelId];
              const modelName = modelNames[modelId] || modelId;

              return (
                <tr
                  key={modelId}
                  className={`${
                    index !== modelIds.length - 1 ? 'border-b border-[var(--color-border)]' : ''
                  }`}
                >
                  {/* Model Name */}
                  <td className="px-4 py-3 text-sm font-medium text-[var(--color-text-primary)]">
                    {modelName}
                  </td>

                  {/* Clips Count */}
                  <td className="px-4 py-3 text-sm text-right text-[var(--color-text-primary)]">
                    {result.clips?.length || 0}
                  </td>

                  {/* Detection Rate */}
                  <td className="px-4 py-3 text-sm text-right">
                    {result.stats?.detectionRate !== undefined ? (
                      <span
                        className={`font-medium ${
                          result.stats.detectionRate > 90
                            ? 'text-[var(--color-accent)]'
                            : result.stats.detectionRate > 70
                            ? 'text-[var(--color-warning)]'
                            : 'text-[var(--color-text-muted)]'
                        }`}
                      >
                        {result.stats.detectionRate.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">N/A</span>
                    )}
                  </td>

                  {/* Avg FPS */}
                  <td className="px-4 py-3 text-sm text-right text-[var(--color-text-primary)]">
                    {result.stats?.avgFps !== undefined
                      ? result.stats.avgFps.toFixed(1)
                      : 'N/A'}
                  </td>

                  {/* Total Time */}
                  <td className="px-4 py-3 text-sm text-right text-[var(--color-text-primary)]">
                    {result.stats?.totalTime !== undefined
                      ? `${Math.floor(result.stats.totalTime / 60)}:${String(
                          Math.floor(result.stats.totalTime % 60)
                        ).padStart(2, '0')}`
                      : 'N/A'}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {result.overlayVideo && onViewOverlay && (
                        <button
                          onClick={() => onViewOverlay(modelId)}
                          className="p-1.5 hover:bg-[var(--color-bg-tertiary)] rounded transition-colors"
                          title="View Overlay Video"
                        >
                          <FileVideo size={16} className="text-[var(--color-primary)]" />
                        </button>
                      )}

                      {result.clips && result.clips.length > 0 && onViewClips && (
                        <button
                          onClick={() => onViewClips(modelId)}
                          className="p-1.5 hover:bg-[var(--color-bg-tertiary)] rounded transition-colors"
                          title="View Clips"
                        >
                          <Play size={16} className="text-[var(--color-accent)]" />
                        </button>
                      )}

                      {result.debugFrames && result.debugFrames.length > 0 && (
                        <button
                          className="p-1.5 hover:bg-[var(--color-bg-tertiary)] rounded transition-colors"
                          title="View Debug Frames"
                        >
                          <Eye size={16} className="text-[var(--color-text-muted)]" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4">
          <div className="text-sm text-[var(--color-text-muted)] mb-1">Models Compared</div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)]">
            {modelIds.length}
          </div>
        </div>

        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4">
          <div className="text-sm text-[var(--color-text-muted)] mb-1">Total Clips</div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)]">
            {modelIds.reduce((sum, id) => sum + (results[id].clips?.length || 0), 0)}
          </div>
        </div>

        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4">
          <div className="text-sm text-[var(--color-text-muted)] mb-1">Avg Detection Rate</div>
          <div className="text-2xl font-bold text-[var(--color-accent)]">
            {modelIds.length > 0
              ? (
                  modelIds.reduce((sum, id) => sum + (results[id].stats?.detectionRate || 0), 0) /
                  modelIds.length
                ).toFixed(1)
              : 0}
            %
          </div>
        </div>
      </div>
    </div>
  );
}
