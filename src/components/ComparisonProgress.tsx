import React from 'react';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface ModelProgress {
  modelId: string;
  modelName: string;
  progress: number;
  status: 'pending' | 'running' | 'completed' | 'error';
  message?: string;
}

interface ComparisonProgressProps {
  modelProgress: ModelProgress[];
}

export function ComparisonProgress({ modelProgress }: ComparisonProgressProps) {
  if (modelProgress.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
        Model Comparison Progress
      </h3>

      <div className="space-y-3">
        {modelProgress.map((model) => (
          <div
            key={model.modelId}
            className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {model.status === 'running' && (
                  <Loader2 size={16} className="text-[var(--color-primary)] animate-spin" />
                )}
                {model.status === 'completed' && (
                  <CheckCircle2 size={16} className="text-[var(--color-accent)]" />
                )}
                {model.status === 'error' && (
                  <XCircle size={16} className="text-[var(--color-error)]" />
                )}
                {model.status === 'pending' && (
                  <div className="w-4 h-4 rounded-full border-2 border-[var(--color-border)]" />
                )}

                <span className="font-medium text-[var(--color-text-primary)]">
                  {model.modelName}
                </span>
              </div>

              <span className="text-sm text-[var(--color-text-muted)]">
                {model.status === 'completed' ? '100%' : `${Math.round(model.progress)}%`}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 rounded-full ${
                  model.status === 'error'
                    ? 'bg-[var(--color-error)]'
                    : model.status === 'completed'
                    ? 'bg-[var(--color-accent)]'
                    : 'bg-[var(--color-primary)]'
                }`}
                style={{
                  width: `${model.status === 'completed' ? 100 : model.progress}%`,
                }}
              />
            </div>

            {/* Message */}
            {model.message && (
              <p className="text-xs text-[var(--color-text-muted)] mt-2">
                {model.message}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
