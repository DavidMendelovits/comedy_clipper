"""
YOLO Detector - YOLO-based person detection and tracking
Handles person detection, tracking, and zone crossing detection
"""

from typing import List, Tuple, Optional, Dict, Any
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None

try:
    from enhanced_person_tracker import EnhancedPersonTracker
    TRACKER_AVAILABLE = True
except ImportError:
    try:
        # Fallback to original tracker if enhanced not available
        from person_tracker import CentroidTracker as EnhancedPersonTracker
        TRACKER_AVAILABLE = True
    except ImportError:
        TRACKER_AVAILABLE = False
        EnhancedPersonTracker = None


class YOLODetector:
    """YOLO-based person detector with tracking"""

    def __init__(self, config: Any):
        """
        Initialize YOLO detector.

        Args:
            config: Configuration object
        """
        if not YOLO_AVAILABLE:
            raise ImportError("Ultralytics not installed. Run: pip install ultralytics")
        if not TRACKER_AVAILABLE:
            raise ImportError("Person tracker not found. Ensure person_tracker.py exists")

        self.config = config

        # Load YOLO model
        model_name = config.get("yolo_detection.model", "yolov8n.pt")
        self.yolo = YOLO(model_name)
        print(f"  YOLO model loaded: {model_name}")

        # Initialize person tracker with velocity detection
        max_disappeared = config.get("yolo_detection.max_disappeared_frames", 30)
        velocity_window = config.get("yolo_detection.velocity_window", 5)
        exit_velocity_threshold = config.get("yolo_detection.exit_velocity_threshold", 20.0)

        self.person_tracker = EnhancedPersonTracker(
            max_disappeared=max_disappeared,
            velocity_window=velocity_window,
            exit_velocity_threshold=exit_velocity_threshold
        )
        print(f"  Tracker initialized (max_disappeared={max_disappeared})")

        # Detection confidence threshold
        self.confidence = config.get("yolo_detection.confidence", 0.5)

    def detect_frame(
        self,
        frame: np.ndarray,
        zone_checker: Optional[callable] = None,
        frame_width: int = None,
        frame_height: int = None
    ) -> Tuple[int, List[Tuple], int, int, List[Tuple]]:
        """
        Detect people in a single frame.

        Args:
            frame: BGR image from OpenCV
            zone_checker: Optional function to check if position is in zone
            frame_width: Frame width for velocity calculation
            frame_height: Frame height for velocity calculation

        Returns:
            Tuple of:
                - num_persons: Total number of detected persons
                - detections: List of (x1, y1, w, h) tuples
                - count_inside: Number of people inside zone (if zone_checker provided)
                - count_outside: Number of people outside zone (if zone_checker provided)
                - zone_crossings: List of (obj_id, from_zone, to_zone) tuples
        """
        # Run YOLO detection (class 0 = person)
        results = self.yolo(frame, classes=[0], conf=self.confidence, verbose=False)

        detections = []
        if len(results) > 0 and len(results[0].boxes) > 0:
            # Extract bounding boxes
            boxes = results[0].boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]

            for box in boxes:
                x1, y1, x2, y2 = box
                w = x2 - x1
                h = y2 - y1
                detections.append((x1, y1, w, h))

        num_persons = len(detections)

        # Update tracker with detections
        zone_crossings = []
        count_inside = 0
        count_outside = 0

        if hasattr(self.person_tracker, 'detect_exit_events'):
            # Enhanced tracker with exit detection
            tracked_objects, zone_crossings, exit_events = self.person_tracker.update(
                detections,
                zone_checker=zone_checker,
                frame_width=frame_width,
                frame_height=frame_height
            )
        else:
            # Original tracker
            tracked_objects, zone_crossings = self.person_tracker.update(
                detections,
                zone_checker=zone_checker
            )

        # Count people inside/outside zone
        if zone_checker:
            count_inside = self.person_tracker.get_count_inside_zone()
            count_outside = self.person_tracker.get_count_outside_zone()

        return num_persons, detections, count_inside, count_outside, zone_crossings

    def set_stage_boundaries(
        self,
        left: float = 0.05,
        right: float = 0.95,
        top: float = 0.0,
        bottom: float = 0.85
    ):
        """
        Set stage boundaries for zone crossing detection.

        Args:
            left: Left boundary (fraction or pixels)
            right: Right boundary (fraction or pixels)
            top: Top boundary (fraction or pixels)
            bottom: Bottom boundary (fraction or pixels)
        """
        if hasattr(self.person_tracker, 'set_stage_boundaries'):
            self.person_tracker.set_stage_boundaries(left, right, top, bottom)

    def get_tracked_objects(self) -> Dict[int, Any]:
        """Get currently tracked objects"""
        return self.person_tracker.objects if hasattr(self.person_tracker, 'objects') else {}

    def reset(self):
        """Reset tracker state"""
        if hasattr(self.person_tracker, 'reset'):
            self.person_tracker.reset()
