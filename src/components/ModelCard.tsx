import React from 'react';
import { Zap, Target, Clock, CheckCircle2 } from 'lucide-react';

export interface ModelInfo {
  id: string;
  name: string;
  description: string;
  speed: 'fast' | 'moderate' | 'slow';
  accuracy: 'good' | 'high' | 'excellent';
  recommended?: boolean;
}

interface ModelCardProps {
  model: ModelInfo;
  selected: boolean;
  onToggle: (id: string) => void;
  multiSelect?: boolean;
}

const speedConfig = {
  fast: { icon: Zap, label: 'Fast', color: 'text-[var(--color-accent)]' },
  moderate: { icon: Clock, label: 'Moderate', color: 'text-[var(--color-warning)]' },
  slow: { icon: Clock, label: 'Slow', color: 'text-[var(--color-text-muted)]' },
};

const accuracyConfig = {
  good: { icon: Target, label: 'Good', color: 'text-[var(--color-text-muted)]' },
  high: { icon: Target, label: 'High', color: 'text-[var(--color-warning)]' },
  excellent: { icon: Target, label: 'Excellent', color: 'text-[var(--color-accent)]' },
};

export function ModelCard({ model, selected, onToggle, multiSelect = false }: ModelCardProps) {
  const SpeedIcon = speedConfig[model.speed].icon;
  const AccuracyIcon = accuracyConfig[model.accuracy].icon;

  return (
    <button
      onClick={() => onToggle(model.id)}
      className={`
        relative flex flex-col p-4 rounded-lg border-2 transition-all duration-200
        ${selected
          ? 'border-[var(--color-primary)] bg-[var(--color-primary-light)]'
          : 'border-[var(--color-border)] bg-[var(--color-bg-secondary)] hover:border-[var(--color-border-light)] hover:bg-[var(--color-bg-tertiary)]'
        }
      `}
    >
      {/* Selection Indicator */}
      <div className="absolute top-3 right-3">
        {multiSelect ? (
          <div
            className={`
              w-5 h-5 rounded border-2 flex items-center justify-center
              ${selected
                ? 'bg-[var(--color-primary)] border-[var(--color-primary)]'
                : 'border-[var(--color-border)]'
              }
            `}
          >
            {selected && <CheckCircle2 size={14} className="text-white" />}
          </div>
        ) : (
          <div
            className={`
              w-5 h-5 rounded-full border-2 flex items-center justify-center
              ${selected
                ? 'bg-[var(--color-primary)] border-[var(--color-primary)]'
                : 'border-[var(--color-border)]'
              }
            `}
          >
            {selected && <div className="w-2 h-2 bg-white rounded-full" />}
          </div>
        )}
      </div>

      {/* Recommended Badge */}
      {model.recommended && (
        <div className="absolute top-3 left-3">
          <span className="px-2 py-0.5 text-xs font-medium bg-[var(--color-accent)] text-white rounded-full">
            Recommended
          </span>
        </div>
      )}

      {/* Model Name */}
      <h3
        className={`
          text-lg font-semibold text-left mb-2
          ${model.recommended ? 'mt-6' : ''}
          ${selected ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-primary)]'}
        `}
      >
        {model.name}
      </h3>

      {/* Description */}
      <p className="text-sm text-[var(--color-text-muted)] text-left mb-4 flex-1">
        {model.description}
      </p>

      {/* Badges */}
      <div className="flex gap-3 mt-auto">
        <div className="flex items-center gap-1">
          <SpeedIcon size={14} className={speedConfig[model.speed].color} />
          <span className="text-xs text-[var(--color-text-muted)]">
            {speedConfig[model.speed].label}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <AccuracyIcon size={14} className={accuracyConfig[model.accuracy].color} />
          <span className="text-xs text-[var(--color-text-muted)]">
            {accuracyConfig[model.accuracy].label}
          </span>
        </div>
      </div>
    </button>
  );
}
