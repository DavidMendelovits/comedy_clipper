/**
 * ParameterGroup Component
 *
 * Renders a collapsible group of related parameters.
 * Handles expand/collapse state and renders ParameterControl for each parameter.
 */

import React, { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { ParameterGroup as ParameterGroupType } from '../../schemas'
import { ParameterControl } from './ParameterControl'

interface ParameterGroupProps {
  group: ParameterGroupType
  config: Record<string, any>
  onChange: (key: string, value: any) => void
  disabled?: boolean
}

export function ParameterGroup({
  group,
  config,
  onChange,
  disabled = false
}: ParameterGroupProps) {
  const [isCollapsed, setIsCollapsed] = useState(
    group.defaultCollapsed ?? false
  )

  const toggleCollapsed = () => {
    if (group.collapsible) {
      setIsCollapsed(!isCollapsed)
    }
  }

  return (
    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden">
      {/* Group Header */}
      <div
        className={`
          px-6 py-4 border-b border-[var(--color-border)]
          ${group.collapsible ? 'cursor-pointer hover:bg-[var(--color-bg-tertiary)] transition-colors' : ''}
        `}
        onClick={toggleCollapsed}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-[var(--color-text-primary)]">
              {group.label}
            </h4>
            {group.description && (
              <p className="text-sm text-[var(--color-text-muted)] mt-1">
                {group.description}
              </p>
            )}
          </div>
          {group.collapsible && (
            <div className="ml-4 text-[var(--color-text-muted)]">
              {isCollapsed ? (
                <ChevronRight className="w-5 h-5" />
              ) : (
                <ChevronDown className="w-5 h-5" />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Group Parameters */}
      {!isCollapsed && (
        <div className="p-6 space-y-6">
          {group.parameters.map((parameter) => (
            <ParameterControl
              key={parameter.key}
              parameter={parameter}
              value={config[parameter.key] ?? parameter.defaultValue}
              onChange={(value) => onChange(parameter.key, value)}
              disabled={disabled}
            />
          ))}
        </div>
      )}
    </div>
  )
}
