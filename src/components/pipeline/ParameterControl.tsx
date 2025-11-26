/**
 * ParameterControl Component
 *
 * Renders individual parameter inputs based on parameter type.
 * Supports: range, select, number, boolean, string
 */

import React from 'react'
import { Parameter } from '../../schemas'

interface ParameterControlProps {
  parameter: Parameter
  value: any
  onChange: (value: any) => void
  disabled?: boolean
}

export function ParameterControl({
  parameter,
  value,
  onChange,
  disabled = false
}: ParameterControlProps) {
  const baseInputClasses = "w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)] disabled:opacity-50 disabled:cursor-not-allowed"

  const renderControl = () => {
    switch (parameter.type) {
      case 'range': {
        const rangeParam = parameter
        const displayValue = rangeParam.unit
          ? `${value}${rangeParam.unit}`
          : value

        return (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--color-text-secondary)]">
                {displayValue}
              </span>
              <span className="text-xs text-[var(--color-text-muted)]">
                {rangeParam.min} - {rangeParam.max}
              </span>
            </div>
            <input
              type="range"
              min={rangeParam.min}
              max={rangeParam.max}
              step={rangeParam.step}
              value={value}
              onChange={(e) => onChange(parseFloat(e.target.value))}
              disabled={disabled}
              className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-lg appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-[var(--color-primary)]
                       [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-moz-range-thumb]:w-4
                       [&::-moz-range-thumb]:h-4
                       [&::-moz-range-thumb]:rounded-full
                       [&::-moz-range-thumb]:bg-[var(--color-primary)]
                       [&::-moz-range-thumb]:border-0
                       [&::-moz-range-thumb]:cursor-pointer
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        )
      }

      case 'select': {
        const selectParam = parameter
        return (
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={baseInputClasses}
          >
            {selectParam.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )
      }

      case 'number': {
        const numberParam = parameter
        return (
          <input
            type="number"
            min={numberParam.min}
            max={numberParam.max}
            step={numberParam.step}
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            disabled={disabled}
            className={baseInputClasses}
          />
        )
      }

      case 'boolean': {
        return (
          <div className="flex items-center">
            <input
              type="checkbox"
              id={parameter.key}
              checked={value}
              onChange={(e) => onChange(e.target.checked)}
              disabled={disabled}
              className="w-4 h-4 text-[var(--color-primary)] bg-[var(--color-bg-tertiary)] border-[var(--color-border)] rounded focus:ring-[var(--color-primary)] disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <label
              htmlFor={parameter.key}
              className="ml-2 text-sm text-[var(--color-text-secondary)]"
            >
              {parameter.label}
            </label>
          </div>
        )
      }

      case 'string': {
        const stringParam = parameter
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={stringParam.placeholder}
            disabled={disabled}
            className={baseInputClasses}
          />
        )
      }

      default:
        return (
          <div className="text-[var(--color-text-muted)] text-sm">
            Unsupported parameter type: {(parameter as any).type}
          </div>
        )
    }
  }

  // Boolean type renders its own label inline
  if (parameter.type === 'boolean') {
    return (
      <div className="space-y-1">
        {renderControl()}
        {parameter.description && (
          <p className="text-xs text-[var(--color-text-muted)] ml-6">
            {parameter.description}
          </p>
        )}
      </div>
    )
  }

  // All other types get a label above the control
  return (
    <div className="space-y-2">
      <label className="block">
        <span className="text-sm font-medium text-[var(--color-text-secondary)]">
          {parameter.label}
          {parameter.required && (
            <span className="text-red-500 ml-1">*</span>
          )}
        </span>
      </label>
      {renderControl()}
      {parameter.description && (
        <p className="text-xs text-[var(--color-text-muted)]">
          {parameter.description}
        </p>
      )}
    </div>
  )
}
