"""
Visual Detector - MediaPipe Face and Pose Detection
Handles face detection, pose detection, and multi-modal detection
"""

from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None


class VisualDetector:
    """MediaPipe-based face and pose detector"""

    def __init__(self, config: Any, mode: str = "multimodal"):
        """
        Initialize visual detector.

        Args:
            config: Configuration object
            mode: Detection mode ("face", "pose", "multimodal", "mediapipe")
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe not installed. Run: pip install mediapipe")

        self.config = config
        self.mode = mode
        self.face_detection = None
        self.pose = None
        self.mp_drawing = None
        self.mp_drawing_styles = None

        # Initialize detectors based on mode
        self._init_detectors()

    def _init_detectors(self):
        """Initialize MediaPipe detectors based on mode"""
        print("Initializing MediaPipe detectors...")

        # Face detection
        if self.mode in ["multimodal", "face"]:
            self.mp_face = mp.solutions.face_detection
            face_conf = self.config.get("confidence.face_detection.min_detection_confidence", 0.5)
            face_model = self.config.get("confidence.face_detection.model_selection", 1)
            self.face_detection = self.mp_face.FaceDetection(
                model_selection=face_model,
                min_detection_confidence=face_conf
            )
            print(f"  Face detection initialized (confidence={face_conf})")

        # Pose detection
        if self.mode in ["multimodal", "pose", "mediapipe"]:
            self.mp_pose = mp.solutions.pose
            pose_det_conf = self.config.get("confidence.pose_detection.min_detection_confidence", 0.5)
            pose_track_conf = self.config.get("confidence.pose_detection.min_tracking_confidence", 0.5)
            pose_complexity = self.config.get("confidence.pose_detection.model_complexity", 1)
            pose_smooth = self.config.get("confidence.pose_detection.smooth_landmarks", True)

            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=pose_complexity,
                smooth_landmarks=pose_smooth,
                min_detection_confidence=pose_det_conf,
                min_tracking_confidence=pose_track_conf
            )
            print(f"  Pose detection initialized (confidence={pose_det_conf})")

        # Drawing utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def detect_frame(
        self,
        frame: np.ndarray,
        frame_width: int,
        frame_height: int
    ) -> Tuple[int, int, List[float], List[float], Any, Any]:
        """
        Detect faces and poses in a single frame.

        Args:
            frame: BGR image from OpenCV
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels

        Returns:
            Tuple of:
                - num_faces: Number of detected faces
                - num_poses: Number of detected poses
                - face_positions: List of face X positions (pixels)
                - pose_positions: List of pose X positions (pixels)
                - face_detections: Raw MediaPipe face detections (for visualization)
                - pose_landmarks: Raw MediaPipe pose landmarks (for visualization)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        num_faces = 0
        face_positions = []
        face_detections_list = []

        num_poses = 0
        pose_positions = []
        pose_landmarks_list = []

        # Face detection
        if self.face_detection is not None:
            face_results = self.face_detection.process(rgb_frame)
            if face_results.detections:
                for detection in face_results.detections:
                    num_faces += 1
                    bbox = detection.location_data.relative_bounding_box
                    center_x = (bbox.xmin + bbox.width / 2) * frame_width
                    face_positions.append(center_x)
                    face_detections_list.append(detection)

        # Pose detection
        if self.pose is not None:
            pose_results = self.pose.process(rgb_frame)
            if pose_results.pose_landmarks:
                num_poses = 1
                landmarks = pose_results.pose_landmarks.landmark

                # Calculate torso center position
                left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
                right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]

                torso_x = (left_shoulder.x + right_shoulder.x + left_hip.x + right_hip.x) / 4
                pose_positions.append(torso_x * frame_width)
                pose_landmarks_list.append(pose_results.pose_landmarks)

        return (
            num_faces,
            num_poses,
            face_positions,
            pose_positions,
            face_detections_list,
            pose_landmarks_list
        )

    def draw_detections(
        self,
        frame: np.ndarray,
        face_detections: List[Any],
        pose_landmarks: List[Any],
        draw_face_boxes: bool = True,
        draw_pose_landmarks: bool = True
    ) -> np.ndarray:
        """
        Draw detection visualizations on frame.

        Args:
            frame: BGR image from OpenCV
            face_detections: List of MediaPipe face detections
            pose_landmarks: List of MediaPipe pose landmarks
            draw_face_boxes: Whether to draw face bounding boxes
            draw_pose_landmarks: Whether to draw pose skeleton

        Returns:
            Annotated frame
        """
        annotated = frame.copy()

        # Draw pose landmarks
        if draw_pose_landmarks and pose_landmarks:
            for landmarks in pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated,
                    landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )

        # Draw face boxes
        if draw_face_boxes and face_detections:
            for detection in face_detections:
                bbox = detection.location_data.relative_bounding_box
                h, w = annotated.shape[:2]
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                cv2.rectangle(annotated, (x, y), (x + width, y + height), (0, 255, 0), 2)

        return annotated

    def cleanup(self):
        """Release MediaPipe resources"""
        if self.face_detection is not None:
            self.face_detection.close()
        if self.pose is not None:
            self.pose.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
