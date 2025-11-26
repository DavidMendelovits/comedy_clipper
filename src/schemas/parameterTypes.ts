/**
 * Parameter Type Definitions for Schema-Driven Pipeline Configuration
 *
 * This module defines the core type system for all pipeline parameters.
 * Each pipeline (pose, face, scene, etc.) will define its parameters using these types.
 */

// Supported parameter input types
export type ParameterType = 'number' | 'string' | 'boolean' | 'select' | 'range'

// Base parameter definition shared by all parameter types
export interface BaseParameter {
  key: string              // Config object key (e.g., 'yoloModel', 'confidenceThreshold')
  label: string            // Display label in UI
  description: string      // Help text / tooltip
  type: ParameterType
  defaultValue: any
  cliArg: string           // Python CLI argument name (e.g., '--yolo-model', '--conf')
  required?: boolean       // Whether parameter is required (default: false)
}

// Number input (integer or float)
export interface NumberParameter extends BaseParameter {
  type: 'number'
  defaultValue: number
  min?: number
  max?: number
  step?: number
}

// String input (text field)
export interface StringParameter extends BaseParameter {
  type: 'string'
  defaultValue: string
  placeholder?: string
}

// Boolean input (checkbox)
export interface BooleanParameter extends BaseParameter {
  type: 'boolean'
  defaultValue: boolean
}

// Select dropdown
export interface SelectParameter extends BaseParameter {
  type: 'select'
  defaultValue: string
  options: Array<{
    value: string
    label: string
    description?: string
  }>
}

// Range slider (numeric with visual feedback)
export interface RangeParameter extends BaseParameter {
  type: 'range'
  defaultValue: number
  min: number
  max: number
  step: number
  unit?: string  // Display unit (e.g., '%', 's', 'px')
}

// Union type for all parameter types
export type Parameter =
  | NumberParameter
  | StringParameter
  | BooleanParameter
  | SelectParameter
  | RangeParameter

// Parameter group for organizing related parameters
export interface ParameterGroup {
  id: string
  label: string
  description?: string
  collapsible?: boolean    // Whether group can be collapsed
  defaultCollapsed?: boolean  // Default collapsed state
  parameters: Parameter[]
}

// Preset configuration (e.g., Fast, Balanced, Accurate)
export interface Preset {
  id: string
  label: string
  description: string
  speedRating: number      // 1-5: Higher = faster processing
  qualityRating: number    // 1-5: Higher = better quality
  icon?: string            // Lucide icon name
  config: Record<string, any>  // Parameter values for this preset
}

// Complete pipeline schema
export interface PipelineSchema {
  pipelineType: string     // Unique identifier (e.g., 'pose_detection', 'face_detection')
  displayName: string      // Human-readable name
  description: string      // Pipeline description
  groups: ParameterGroup[]
  presets?: Preset[]
  cliCommand: string       // Python script name (e.g., 'yolo_pose_processor.py')
}
