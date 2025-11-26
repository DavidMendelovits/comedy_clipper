/**
 * Pipeline Schema Registry
 *
 * Central registry for all pipeline schemas with helper functions.
 * Add new pipelines here as they're developed.
 */

import { PipelineSchema } from './parameterTypes'
import { POSE_DETECTION_SCHEMA } from './poseDetectionSchema'

// Registry of all available pipeline schemas
export const PIPELINE_SCHEMAS: Record<string, PipelineSchema> = {
  pose_detection: POSE_DETECTION_SCHEMA,
  // Future pipelines will be added here:
  // face_detection: FACE_DETECTION_SCHEMA,
  // scene_detection: SCENE_DETECTION_SCHEMA,
  // multimodal: MULTIMODAL_SCHEMA,
}

/**
 * Get a pipeline schema by type
 * @param pipelineType - The pipeline type identifier (e.g., 'pose_detection')
 * @returns The pipeline schema or null if not found
 */
export function getPipelineSchema(pipelineType: string): PipelineSchema | null {
  return PIPELINE_SCHEMAS[pipelineType] || null
}

/**
 * Get all available pipeline types
 * @returns Array of pipeline type identifiers
 */
export function getAvailablePipelines(): string[] {
  return Object.keys(PIPELINE_SCHEMAS)
}

/**
 * Get default configuration for a pipeline
 * Combines all parameter default values into a config object
 * @param pipelineType - The pipeline type identifier
 * @returns Config object with default values, or empty object if schema not found
 */
export function getDefaultConfig(pipelineType: string): Record<string, any> {
  const schema = getPipelineSchema(pipelineType)
  if (!schema) return {}

  const config: Record<string, any> = {}

  // Iterate through all groups and parameters
  schema.groups.forEach(group => {
    group.parameters.forEach(param => {
      config[param.key] = param.defaultValue
    })
  })

  return config
}

/**
 * Get preset configuration by ID
 * @param pipelineType - The pipeline type identifier
 * @param presetId - The preset ID (e.g., 'fast', 'balanced', 'accurate')
 * @returns Config object for the preset, or null if not found
 */
export function getPresetConfig(
  pipelineType: string,
  presetId: string
): Record<string, any> | null {
  const schema = getPipelineSchema(pipelineType)
  if (!schema || !schema.presets) return null

  const preset = schema.presets.find(p => p.id === presetId)
  return preset ? preset.config : null
}

/**
 * Validate a configuration against a schema
 * Checks that all required parameters are present
 * @param pipelineType - The pipeline type identifier
 * @param config - The configuration object to validate
 * @returns Object with isValid flag and array of missing required parameters
 */
export function validateConfig(
  pipelineType: string,
  config: Record<string, any>
): { isValid: boolean; missingParams: string[] } {
  const schema = getPipelineSchema(pipelineType)
  if (!schema) {
    return { isValid: false, missingParams: [] }
  }

  const missingParams: string[] = []

  schema.groups.forEach(group => {
    group.parameters.forEach(param => {
      if (param.required && !(param.key in config)) {
        missingParams.push(param.key)
      }
    })
  })

  return {
    isValid: missingParams.length === 0,
    missingParams
  }
}
