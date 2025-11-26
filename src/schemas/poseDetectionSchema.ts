/**
 * Pose Detection Pipeline Schema
 *
 * Defines all parameters, presets, and configuration for the YOLO pose detection pipeline.
 */

import {
  PipelineSchema,
  ParameterGroup,
  Preset,
  SelectParameter,
  RangeParameter,
  NumberParameter
} from './parameterTypes'

// Model Selection Parameter
const YOLO_MODEL_PARAM: SelectParameter = {
  key: 'yoloModel',
  label: 'YOLO Model',
  description: 'Choose model size - larger models are more accurate but slower',
  type: 'select',
  defaultValue: 'yolo11m-pose.pt',
  cliArg: '--model',
  required: true,
  options: [
    {
      value: 'yolo11n-pose.pt',
      label: 'Nano (fastest)',
      description: '~50% mAP, 2-3x faster than Medium'
    },
    {
      value: 'yolo11s-pose.pt',
      label: 'Small',
      description: '~60% mAP, balanced speed/accuracy'
    },
    {
      value: 'yolo11m-pose.pt',
      label: 'Medium (recommended)',
      description: '~75% mAP, best balance for most videos'
    },
    {
      value: 'yolo11l-pose.pt',
      label: 'Large',
      description: '~78% mAP, high accuracy'
    },
    {
      value: 'yolo11x-pose.pt',
      label: 'XLarge (slowest)',
      description: '~80% mAP, maximum accuracy'
    }
  ]
}

// Detection Parameters
const CONFIDENCE_THRESHOLD_PARAM: RangeParameter = {
  key: 'confidenceThreshold',
  label: 'Detection Confidence',
  description: 'Minimum confidence for initial pose detection',
  type: 'range',
  defaultValue: 0.6,
  min: 0.1,
  max: 0.95,
  step: 0.05,
  cliArg: '--confidence-threshold',
  unit: ''
}

const MIN_DETECTION_CONF_PARAM: RangeParameter = {
  key: 'minDetectionConf',
  label: 'Minimum Detection Confidence',
  description: 'Minimum confidence for accepting detections after NMS',
  type: 'range',
  defaultValue: 0.65,
  min: 0.1,
  max: 0.95,
  step: 0.05,
  cliArg: '--min-detection-conf',
  unit: ''
}

const KEYPOINT_CONF_PARAM: RangeParameter = {
  key: 'keypointConf',
  label: 'Keypoint Confidence',
  description: 'Minimum confidence for individual keypoints to be considered valid',
  type: 'range',
  defaultValue: 0.5,
  min: 0.1,
  max: 0.9,
  step: 0.05,
  cliArg: '--keypoint-conf',
  unit: ''
}

const NMS_IOU_PARAM: RangeParameter = {
  key: 'nmsIou',
  label: 'NMS IOU Threshold',
  description: 'Non-maximum suppression overlap threshold - lower = fewer overlapping detections',
  type: 'range',
  defaultValue: 0.45,
  min: 0.1,
  max: 0.9,
  step: 0.05,
  cliArg: '--nms-iou',
  unit: ''
}

const MIN_VISIBLE_KEYPOINTS_PARAM: NumberParameter = {
  key: 'minVisibleKeypoints',
  label: 'Minimum Visible Keypoints',
  description: 'Minimum number of keypoints required for valid detection (out of 17)',
  type: 'number',
  defaultValue: 10,
  min: 5,
  max: 17,
  step: 1,
  cliArg: '--min-visible-keypoints'
}

// Filtering Parameters
const MIN_ASPECT_RATIO_PARAM: RangeParameter = {
  key: 'minAspectRatio',
  label: 'Minimum Aspect Ratio',
  description: 'Minimum height/width ratio for valid human detection',
  type: 'range',
  defaultValue: 1.5,
  min: 1.0,
  max: 2.5,
  step: 0.1,
  cliArg: '--min-aspect-ratio',
  unit: ''
}

const MAX_ASPECT_RATIO_PARAM: RangeParameter = {
  key: 'maxAspectRatio',
  label: 'Maximum Aspect Ratio',
  description: 'Maximum height/width ratio for valid human detection',
  type: 'range',
  defaultValue: 2.8,
  min: 2.0,
  max: 5.0,
  step: 0.1,
  cliArg: '--max-aspect-ratio',
  unit: ''
}

const MIN_KEYPOINT_COVERAGE_PARAM: RangeParameter = {
  key: 'minKeypointCoverage',
  label: 'Minimum Keypoint Coverage',
  description: 'Minimum percentage of bounding box that keypoints must cover',
  type: 'range',
  defaultValue: 0.4,
  min: 0.1,
  max: 0.9,
  step: 0.05,
  cliArg: '--min-keypoint-coverage',
  unit: ''
}

const EXIT_STABILITY_FRAMES_PARAM: NumberParameter = {
  key: 'exitStabilityFrames',
  label: 'Exit Stability Frames',
  description: 'Number of consecutive frames required to confirm comedian exit',
  type: 'number',
  defaultValue: 2,
  min: 1,
  max: 10,
  step: 1,
  cliArg: '--exit-stability-frames'
}

// Parameter Groups
const POSE_DETECTION_GROUPS: ParameterGroup[] = [
  {
    id: 'model',
    label: 'Model Settings',
    description: 'Choose YOLO model size and performance characteristics',
    collapsible: false,
    parameters: [YOLO_MODEL_PARAM]
  },
  {
    id: 'detection',
    label: 'Detection Parameters',
    description: 'Fine-tune detection sensitivity and filtering',
    collapsible: true,
    defaultCollapsed: false,
    parameters: [
      CONFIDENCE_THRESHOLD_PARAM,
      MIN_DETECTION_CONF_PARAM,
      KEYPOINT_CONF_PARAM,
      NMS_IOU_PARAM,
      MIN_VISIBLE_KEYPOINTS_PARAM
    ]
  },
  {
    id: 'filtering',
    label: 'Advanced Filtering',
    description: 'Additional filters to reduce false positives',
    collapsible: true,
    defaultCollapsed: true,
    parameters: [
      MIN_ASPECT_RATIO_PARAM,
      MAX_ASPECT_RATIO_PARAM,
      MIN_KEYPOINT_COVERAGE_PARAM,
      EXIT_STABILITY_FRAMES_PARAM
    ]
  }
]

// Presets
const POSE_DETECTION_PRESETS: Preset[] = [
  {
    id: 'fast',
    label: 'Fast',
    description: 'Fastest processing with Nano model - good for quick previews',
    speedRating: 5,
    qualityRating: 2,
    icon: 'Zap',
    config: {
      yoloModel: 'yolo11n-pose.pt',
      confidenceThreshold: 0.5,
      minDetectionConf: 0.6,
      keypointConf: 0.4,
      nmsIou: 0.5,
      minVisibleKeypoints: 8,
      minAspectRatio: 1.2,
      maxAspectRatio: 3.5,
      minKeypointCoverage: 0.3,
      exitStabilityFrames: 1
    }
  },
  {
    id: 'balanced',
    label: 'Balanced',
    description: 'Medium model with optimized filtering - recommended for most videos',
    speedRating: 3,
    qualityRating: 4,
    icon: 'Target',
    config: {
      yoloModel: 'yolo11m-pose.pt',
      confidenceThreshold: 0.6,
      minDetectionConf: 0.65,
      keypointConf: 0.5,
      nmsIou: 0.45,
      minVisibleKeypoints: 10,
      minAspectRatio: 1.5,
      maxAspectRatio: 2.8,
      minKeypointCoverage: 0.4,
      exitStabilityFrames: 2
    }
  },
  {
    id: 'accurate',
    label: 'Accurate',
    description: 'Large model with strict filtering - best quality, slower processing',
    speedRating: 1,
    qualityRating: 5,
    icon: 'Award',
    config: {
      yoloModel: 'yolo11l-pose.pt',
      confidenceThreshold: 0.65,
      minDetectionConf: 0.7,
      keypointConf: 0.55,
      nmsIou: 0.4,
      minVisibleKeypoints: 11,
      minAspectRatio: 1.5,
      maxAspectRatio: 2.6,
      minKeypointCoverage: 0.45,
      exitStabilityFrames: 3
    }
  }
]

// Complete Pose Detection Schema
export const POSE_DETECTION_SCHEMA: PipelineSchema = {
  pipelineType: 'pose_detection',
  displayName: 'Pose Detection',
  description: 'Detect comedian poses and track stage presence using YOLO11 pose estimation',
  groups: POSE_DETECTION_GROUPS,
  presets: POSE_DETECTION_PRESETS,
  cliCommand: 'yolo_pose_processor.py'
}
