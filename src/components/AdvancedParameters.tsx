/**
 * Advanced Parameters Component
 * Comprehensive parameter tuning UI for clipping configuration
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, RotateCcw, Sliders } from 'lucide-react';

interface AdvancedParametersProps {
  config: any;
  setConfig: (config: Partial<any>) => void;
}

const PRESETS = {
  conservative: {
    name: 'Conservative',
    description: 'Strict filtering, fewer clips with high confidence',
    minDuration: 240, // 4 minutes
    maxDuration: 1200, // 20 minutes
    mergeThreshold: 5,
    bufferBefore: 5,
    bufferAfter: 5,
  },
  balanced: {
    name: 'Balanced',
    description: 'Standard settings for most comedy sets',
    minDuration: 180, // 3 minutes
    maxDuration: 1800, // 30 minutes
    mergeThreshold: 10,
    bufferBefore: 10,
    bufferAfter: 10,
  },
  aggressive: {
    name: 'Aggressive',
    description: 'Capture more clips, including shorter sets',
    minDuration: 120, // 2 minutes
    maxDuration: 2400, // 40 minutes
    mergeThreshold: 15,
    bufferBefore: 15,
    bufferAfter: 15,
  },
};

export function AdvancedParameters({ config, setConfig }: AdvancedParametersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handlePresetSelect = (presetKey: keyof typeof PRESETS) => {
    const preset = PRESETS[presetKey];
    setConfig({
      minDuration: preset.minDuration,
      maxDuration: preset.maxDuration,
      mergeThreshold: preset.mergeThreshold,
      bufferBefore: preset.bufferBefore,
      bufferAfter: preset.bufferAfter,
    });
  };

  const handleReset = () => {
    handlePresetSelect('balanced');
  };

  // Validation
  const minDuration = config.minDuration || 180;
  const maxDuration = config.maxDuration || 1800;
  const hasValidationError = minDuration >= maxDuration;

  return (
    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden">
      {/* Header - Always Visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-[var(--color-bg-tertiary)] transition-colors"
      >
        <div className="flex items-center gap-3">
          <Sliders size={20} className="text-[var(--color-primary)]" />
          <div className="text-left">
            <h3 className="font-semibold text-[var(--color-text-primary)]">
              Advanced Parameters
            </h3>
            <p className="text-sm text-[var(--color-text-muted)]">
              Fine-tune clipping behavior and filters
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp size={20} className="text-[var(--color-text-muted)]" />
        ) : (
          <ChevronDown size={20} className="text-[var(--color-text-muted)]" />
        )}
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="p-4 pt-0 space-y-6 border-t border-[var(--color-border)]">
          {/* Validation Warning */}
          {hasValidationError && (
            <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <AlertTriangle size={20} className="text-[var(--color-warning)] flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-[var(--color-warning)]">Invalid Parameters</p>
                <p className="text-[var(--color-text-secondary)] mt-1">
                  Min duration must be less than max duration
                </p>
              </div>
            </div>
          )}

          {/* Preset Selector */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-3">
              Parameter Presets
            </label>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => handlePresetSelect(key as keyof typeof PRESETS)}
                  className="p-3 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] rounded-lg text-left transition-colors group"
                >
                  <p className="font-medium text-[var(--color-text-primary)] group-hover:text-[var(--color-primary)] transition-colors">
                    {preset.name}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {preset.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Duration Filters */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                Duration Filters
              </label>
              <button
                onClick={handleReset}
                className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors"
              >
                <RotateCcw size={12} />
                Reset
              </button>
            </div>

            {/* Min Duration Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-[var(--color-text-secondary)]">
                  Minimum Duration
                </label>
                <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">
                  {minDuration}s ({Math.floor(minDuration / 60)}m {minDuration % 60}s)
                </span>
              </div>
              <input
                type="range"
                min="30"
                max="600"
                step="30"
                value={minDuration}
                onChange={(e) => setConfig({ minDuration: parseInt(e.target.value) })}
                className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
                <span>30s</span>
                <span>10m</span>
              </div>
            </div>

            {/* Max Duration Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-[var(--color-text-secondary)]">
                  Maximum Duration
                </label>
                <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">
                  {maxDuration}s ({Math.floor(maxDuration / 60)}m {maxDuration % 60}s)
                </span>
              </div>
              <input
                type="range"
                min="300"
                max="3600"
                step="60"
                value={maxDuration}
                onChange={(e) => setConfig({ maxDuration: parseInt(e.target.value) })}
                className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
                <span>5m</span>
                <span>60m</span>
              </div>
            </div>
          </div>

          {/* Segment Merging */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <div>
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Merge Threshold
                </label>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Merge segments if gap is less than this value
                </p>
              </div>
              <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">
                {config.mergeThreshold || 10}s
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              step="5"
              value={config.mergeThreshold || 10}
              onChange={(e) => setConfig({ mergeThreshold: parseInt(e.target.value) })}
              className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
            />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0s (no merge)</span>
              <span>30s</span>
            </div>
          </div>

          {/* Buffer Controls */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-[var(--color-text-secondary)]">
                  Buffer Before
                </label>
                <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">
                  {config.bufferBefore || 10}s
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="5"
                value={config.bufferBefore || 10}
                onChange={(e) => setConfig({ bufferBefore: parseInt(e.target.value) })}
                className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-[var(--color-text-secondary)]">
                  Buffer After
                </label>
                <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">
                  {config.bufferAfter || 10}s
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="5"
                value={config.bufferAfter || 10}
                onChange={(e) => setConfig({ bufferAfter: parseInt(e.target.value) })}
                className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
              />
            </div>
          </div>

          {/* Position Detection */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <div>
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Stage Exit Threshold
                </label>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Distance from edge to trigger exit detection (0-50%)
                </p>
              </div>
              <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">
                {((config.exitThreshold || 0.15) * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="0.5"
              step="0.05"
              value={config.exitThreshold || 0.15}
              onChange={(e) => setConfig({ exitThreshold: parseFloat(e.target.value) })}
              className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer slider"
            />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)] mt-1">
              <span>0% (edge only)</span>
              <span>50% (center)</span>
            </div>
          </div>

          {/* Advanced Toggles */}
          <div className="space-y-3 pt-3 border-t border-[var(--color-border)]">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Blur Detection
                </label>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Find sharp frame boundaries to avoid blurry clips
                </p>
              </div>
              <input
                type="checkbox"
                checked={config.blurDetectionEnabled !== false}
                onChange={(e) => setConfig({ blurDetectionEnabled: e.target.checked })}
                className="w-4 h-4 text-[var(--color-primary)] bg-[var(--color-bg-tertiary)] border-[var(--color-border)] rounded focus:ring-[var(--color-primary)]"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Zone Crossing Detection
                </label>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Detect when performer crosses stage boundaries
                </p>
              </div>
              <input
                type="checkbox"
                checked={config.zoneCrossingEnabled || false}
                onChange={(e) => setConfig({ zoneCrossingEnabled: e.target.checked })}
                className="w-4 h-4 text-[var(--color-primary)] bg-[var(--color-bg-tertiary)] border-[var(--color-border)] rounded focus:ring-[var(--color-primary)]"
              />
            </div>
          </div>

          {/* Info Box */}
          <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <p className="text-sm text-[var(--color-text-secondary)]">
              💡 <strong>Tip:</strong> After processing, you can fine-tune these parameters
              instantly using cached detection data without re-running pose detection.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
