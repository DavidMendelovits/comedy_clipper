/**
 * PipelineConfigForm Component
 *
 * Main form component that orchestrates presets, parameter groups, and config state.
 * Automatically generates UI from pipeline schemas.
 */

import React, { useState, useEffect } from 'react'
import { PipelineSchema, getDefaultConfig } from '../../schemas'
import { PresetSelector } from './PresetSelector'
import { ParameterGroup } from './ParameterGroup'

interface PipelineConfigFormProps {
  schema: PipelineSchema
  onConfigChange: (config: Record<string, any>) => void
  disabled?: boolean
  className?: string
}

export function PipelineConfigForm({
  schema,
  onConfigChange,
  disabled = false,
  className = ''
}: PipelineConfigFormProps) {
  // Initialize with default config from schema
  const [config, setConfig] = useState<Record<string, any>>(() =>
    getDefaultConfig(schema.pipelineType)
  )

  // Initialize with balanced preset (2nd preset) if available
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(() =>
    schema.presets?.[1]?.id || null
  )

  // Apply preset configuration when selected
  useEffect(() => {
    if (selectedPresetId && schema.presets) {
      const preset = schema.presets.find(p => p.id === selectedPresetId)
      if (preset) {
        setConfig(preset.config)
      }
    }
  }, [selectedPresetId, schema.presets])

  // Notify parent of config changes
  useEffect(() => {
    onConfigChange(config)
  }, [config, onConfigChange])

  // Handle preset selection
  const handlePresetSelect = (presetId: string) => {
    setSelectedPresetId(presetId)
  }

  // Handle individual parameter changes
  const handleParameterChange = (key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
    }))
    // Clear preset selection when manually changing parameters
    setSelectedPresetId(null)
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Pipeline Info */}
      <div className="text-center">
        <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">
          {schema.displayName}
        </h3>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          {schema.description}
        </p>
      </div>

      {/* Preset Selector (if presets are defined) */}
      {schema.presets && schema.presets.length > 0 && (
        <PresetSelector
          presets={schema.presets}
          selectedPresetId={selectedPresetId}
          onPresetSelect={handlePresetSelect}
          disabled={disabled}
        />
      )}

      {/* Parameter Groups */}
      <div className="space-y-4">
        {schema.groups.map(group => (
          <ParameterGroup
            key={group.id}
            group={group}
            config={config}
            onChange={handleParameterChange}
            disabled={disabled}
          />
        ))}
      </div>

      {/* Custom Parameters Warning (when not using preset) */}
      {!selectedPresetId && schema.presets && schema.presets.length > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <p className="text-sm text-yellow-200">
            <strong>Custom Configuration:</strong> You've modified parameters manually.
            Select a preset to restore optimized defaults.
          </p>
        </div>
      )}
    </div>
  )
}
