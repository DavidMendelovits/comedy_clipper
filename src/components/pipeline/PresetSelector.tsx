/**
 * PresetSelector Component
 *
 * Renders preset buttons (Fast, Balanced, Accurate) with icons and ratings.
 * Allows users to quickly select common configurations.
 */

import React from 'react'
import * as LucideIcons from 'lucide-react'
import { Preset } from '../../schemas'
import { RatingIndicator } from '../ui/RatingIndicator'

interface PresetSelectorProps {
  presets: Preset[]
  selectedPresetId: string | null
  onPresetSelect: (presetId: string) => void
  disabled?: boolean
}

export function PresetSelector({
  presets,
  selectedPresetId,
  onPresetSelect,
  disabled = false
}: PresetSelectorProps) {
  // Helper to get Lucide icon component by name
  const getIcon = (iconName?: string) => {
    if (!iconName) return null
    const Icon = (LucideIcons as any)[iconName]
    return Icon ? <Icon className="w-5 h-5" /> : null
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">
        Quick Presets
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {presets.map((preset) => {
          const isSelected = selectedPresetId === preset.id

          return (
            <button
              key={preset.id}
              onClick={() => onPresetSelect(preset.id)}
              disabled={disabled}
              className={`
                relative p-4 rounded-lg border-2 text-left transition-all
                ${isSelected
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                  : 'border-[var(--color-border)] bg-[var(--color-bg-secondary)] hover:border-[var(--color-primary)]/50'
                }
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
            >
              {/* Icon and Title */}
              <div className="flex items-center gap-3 mb-2">
                <div className={`${isSelected ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {getIcon(preset.icon)}
                </div>
                <span className={`font-semibold ${isSelected ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-primary)]'}`}>
                  {preset.label}
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-[var(--color-text-muted)] mb-3">
                {preset.description}
              </p>

              {/* Ratings */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">Speed</span>
                  <RatingIndicator rating={preset.speedRating} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">Quality</span>
                  <RatingIndicator rating={preset.qualityRating} />
                </div>
              </div>

              {/* Selected indicator */}
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 rounded-full bg-[var(--color-primary)]"></div>
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
