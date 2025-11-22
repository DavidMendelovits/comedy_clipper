"""
Background Subtraction for Stage Exit Detection

Uses background modeling to detect when people enter/exit the stage area
by analyzing foreground motion patterns.
"""

import cv2
import numpy as np
from collections import deque
from typing import Tuple, List, Optional, Dict


class StageExitDetector:
    """
    Detects people entering/exiting stage using background subtraction.

    Advantages over person counting:
    - Detects motion/trajectory rather than counting
    - Less sensitive to brief detection failures
    - Can track partial exits (person moving toward edge)
    - Works even when face/pose detection fails
    """

    def __init__(
        self,
        stage_zone: Tuple[int, int, int, int],
        history_frames: int = 500,
        var_threshold: int = 16,
        detect_shadows: bool = True,
        min_contour_area: int = 2000,
        exit_zone_margin: float = 0.15
    ):
        """
        Initialize background subtraction detector.

        Args:
            stage_zone: (x, y, w, h) defining the stage area
            history_frames: Number of frames for background learning
            var_threshold: Variance threshold for background/foreground classification
            detect_shadows: Whether to detect and suppress shadows
            min_contour_area: Minimum contour area to consider as a person
            exit_zone_margin: Margin from stage edge to define exit zones (0-1)
        """
        # Create background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history_frames,
            varThreshold=var_threshold,
            detectShadows=detect_shadows
        )

        self.stage_zone = stage_zone
        self.min_contour_area = min_contour_area
        self.exit_zone_margin = exit_zone_margin

        # Track active objects
        self.active_objects: Dict[int, dict] = {}
        self.next_object_id = 0

        # Exit detection
        self.exit_events: List[Tuple[int, float, str]] = []  # (object_id, timestamp, direction)
        self.enter_events: List[Tuple[int, float, str]] = []

        # Motion history for trajectory analysis
        self.motion_history = deque(maxlen=30)

        # Stage presence tracking
        self.stage_occupied_frames = 0
        self.stage_empty_frames = 0
        self.presence_threshold = 5  # Frames before confirming presence change

    def process_frame(self, frame: np.ndarray, frame_num: int, timestamp: float) -> dict:
        """
        Process a frame and detect stage entry/exit events.

        Args:
            frame: Input video frame
            frame_num: Frame number
            timestamp: Timestamp in seconds

        Returns:
            Dictionary with detection results:
                - stage_occupied: bool
                - num_people_on_stage: int
                - exit_events: list of (object_id, direction)
                - enter_events: list of (object_id, direction)
                - foreground_mask: binary mask
                - contours: detected contours
        """
        x, y, w, h = self.stage_zone
        stage_roi = frame[y:y+h, x:x+w]

        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(stage_roi)

        # Remove shadows (if enabled)
        if self.bg_subtractor.getDetectShadows():
            # Shadows are labeled as 127, foreground as 255
            fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)[1]

        # Morphological operations to reduce noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by area
        valid_contours = [c for c in contours if cv2.contourArea(c) > self.min_contour_area]

        # Detect people on stage
        people_on_stage = []
        for contour in valid_contours:
            # Get bounding box
            cx, cy, cw, ch = cv2.boundingRect(contour)

            # Calculate centroid
            M = cv2.moments(contour)
            if M["m00"] > 0:
                centroid_x = int(M["m10"] / M["m00"])
                centroid_y = int(M["m01"] / M["m00"])
            else:
                centroid_x = cx + cw // 2
                centroid_y = cy + ch // 2

            # Convert to absolute coordinates
            abs_centroid_x = x + centroid_x
            abs_centroid_y = y + centroid_y

            people_on_stage.append({
                'bbox': (cx, cy, cw, ch),
                'centroid': (centroid_x, centroid_y),
                'abs_centroid': (abs_centroid_x, abs_centroid_y),
                'area': cv2.contourArea(contour),
                'contour': contour
            })

        # Track objects and detect exits/entries
        exit_events, enter_events = self._track_and_detect_events(
            people_on_stage, frame_num, timestamp, w, h
        )

        # Update stage occupancy
        stage_occupied = len(people_on_stage) > 0
        if stage_occupied:
            self.stage_occupied_frames += 1
            self.stage_empty_frames = 0
        else:
            self.stage_empty_frames += 1
            self.stage_occupied_frames = 0

        # Motion analysis
        motion_score = np.sum(fg_mask > 0) / (w * h)
        self.motion_history.append(motion_score)

        return {
            'stage_occupied': stage_occupied,
            'num_people_on_stage': len(people_on_stage),
            'people': people_on_stage,
            'exit_events': exit_events,
            'enter_events': enter_events,
            'foreground_mask': fg_mask,
            'contours': valid_contours,
            'motion_score': motion_score,
            'stable_occupancy': stage_occupied if self.stage_occupied_frames >= self.presence_threshold else None
        }

    def _track_and_detect_events(
        self,
        people: List[dict],
        frame_num: int,
        timestamp: float,
        stage_width: int,
        stage_height: int
    ) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
        """
        Track people across frames and detect exit/entry events.

        Returns:
            (exit_events, enter_events) where each is list of (object_id, direction)
        """
        exit_events = []
        enter_events = []

        # Define exit zones (edges of stage)
        left_exit = int(stage_width * self.exit_zone_margin)
        right_exit = int(stage_width * (1 - self.exit_zone_margin))
        top_exit = int(stage_height * self.exit_zone_margin)
        bottom_exit = int(stage_height * (1 - self.exit_zone_margin))

        # Match current detections to tracked objects
        matched_ids = set()
        for person in people:
            cx, cy = person['centroid']

            # Find closest tracked object
            best_match_id = None
            best_distance = float('inf')

            for obj_id, obj_data in self.active_objects.items():
                if obj_id in matched_ids:
                    continue

                last_pos = obj_data['positions'][-1]
                distance = np.sqrt((cx - last_pos[0])**2 + (cy - last_pos[1])**2)

                # Match if within reasonable distance (100 pixels)
                if distance < 100 and distance < best_distance:
                    best_distance = distance
                    best_match_id = obj_id

            if best_match_id is not None:
                # Update existing object
                self.active_objects[best_match_id]['positions'].append((cx, cy))
                self.active_objects[best_match_id]['last_seen'] = frame_num
                self.active_objects[best_match_id]['bbox'] = person['bbox']
                matched_ids.add(best_match_id)
            else:
                # New object - entering stage
                new_id = self.next_object_id
                self.next_object_id += 1

                self.active_objects[new_id] = {
                    'id': new_id,
                    'positions': deque([(cx, cy)], maxlen=30),
                    'first_seen': frame_num,
                    'last_seen': frame_num,
                    'bbox': person['bbox']
                }

                # Determine entry direction
                entry_dir = self._get_direction(cx, cy, left_exit, right_exit, top_exit, bottom_exit)
                if entry_dir:
                    enter_events.append((new_id, entry_dir))
                    self.enter_events.append((new_id, timestamp, entry_dir))

                matched_ids.add(new_id)

        # Check for objects that disappeared (potential exits)
        disappeared_ids = []
        for obj_id, obj_data in list(self.active_objects.items()):
            if obj_id not in matched_ids:
                frames_missing = frame_num - obj_data['last_seen']

                # If missing for 5 frames, consider it an exit
                if frames_missing >= 5:
                    # Analyze trajectory to determine exit direction
                    if len(obj_data['positions']) >= 2:
                        # Get last known position and direction
                        last_pos = obj_data['positions'][-1]
                        prev_pos = obj_data['positions'][-2] if len(obj_data['positions']) >= 2 else last_pos

                        # Calculate movement direction
                        dx = last_pos[0] - prev_pos[0]
                        dy = last_pos[1] - prev_pos[1]

                        # Determine exit direction based on position and movement
                        exit_dir = self._get_exit_direction(
                            last_pos[0], last_pos[1], dx, dy,
                            left_exit, right_exit, top_exit, bottom_exit,
                            stage_width, stage_height
                        )

                        if exit_dir:
                            exit_events.append((obj_id, exit_dir))
                            self.exit_events.append((obj_id, timestamp, exit_dir))

                    disappeared_ids.append(obj_id)

        # Remove disappeared objects
        for obj_id in disappeared_ids:
            del self.active_objects[obj_id]

        return exit_events, enter_events

    def _get_direction(self, x: int, y: int, left: int, right: int, top: int, bottom: int) -> Optional[str]:
        """Determine which edge of stage a position is near."""
        if x < left:
            return "left"
        elif x > right:
            return "right"
        elif y < top:
            return "top"
        elif y > bottom:
            return "bottom"
        return None

    def _get_exit_direction(
        self,
        x: int, y: int, dx: float, dy: float,
        left: int, right: int, top: int, bottom: int,
        width: int, height: int
    ) -> Optional[str]:
        """
        Determine exit direction based on position and movement.

        Combines last known position with movement trajectory.
        """
        # Position-based exit detection
        if x < left or (dx < 0 and x < width * 0.3):
            return "left"
        elif x > right or (dx > 0 and x > width * 0.7):
            return "right"
        elif y < top or (dy < 0 and y < height * 0.3):
            return "top"
        elif y > bottom or (dy > 0 and y > height * 0.7):
            return "bottom"

        return None

    def get_stage_state(self) -> str:
        """
        Get stable stage state.

        Returns:
            "occupied", "empty", or "changing"
        """
        if self.stage_occupied_frames >= self.presence_threshold:
            return "occupied"
        elif self.stage_empty_frames >= self.presence_threshold:
            return "empty"
        else:
            return "changing"

    def reset(self):
        """Reset the detector state."""
        self.active_objects.clear()
        self.exit_events.clear()
        self.enter_events.clear()
        self.motion_history.clear()
        self.stage_occupied_frames = 0
        self.stage_empty_frames = 0


def visualize_detection(frame: np.ndarray, result: dict, stage_zone: Tuple[int, int, int, int]) -> np.ndarray:
    """
    Visualize background subtraction detection results on frame.

    Args:
        frame: Input frame
        result: Detection result dictionary
        stage_zone: (x, y, w, h) of stage area

    Returns:
        Annotated frame
    """
    vis_frame = frame.copy()
    x, y, w, h = stage_zone

    # Draw stage zone
    cv2.rectangle(vis_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Draw detected people
    for person in result['people']:
        px, py, pw, ph = person['bbox']
        # Convert to absolute coordinates
        abs_x = x + px
        abs_y = y + py

        cv2.rectangle(vis_frame, (abs_x, abs_y), (abs_x+pw, abs_y+ph), (255, 0, 0), 2)

        # Draw centroid
        cx, cy = person['abs_centroid']
        cv2.circle(vis_frame, (cx, cy), 5, (0, 0, 255), -1)

    # Draw exit/entry events
    for obj_id, direction in result['exit_events']:
        cv2.putText(vis_frame, f"EXIT {direction}", (x + 10, y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    for obj_id, direction in result['enter_events']:
        cv2.putText(vis_frame, f"ENTER {direction}", (x + 10, y + 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Draw stage state
    state = result.get('stable_occupancy')
    if state is not None:
        state_text = "OCCUPIED" if state else "EMPTY"
        color = (0, 255, 0) if state else (0, 0, 255)
        cv2.putText(vis_frame, state_text, (x + 10, y + h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    # Show motion score
    motion_text = f"Motion: {result['motion_score']:.3f}"
    cv2.putText(vis_frame, motion_text, (x + w - 200, y + 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return vis_frame
