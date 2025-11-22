#!/usr/bin/env python3
"""
Enhanced person tracker with velocity-based exit detection.
Extends CentroidTracker with velocity tracking and movement pattern analysis.
"""

import numpy as np
from scipy.spatial import distance as dist
from collections import OrderedDict, deque
import time


class EnhancedPersonTracker:
    """
    Enhanced tracker with velocity and movement pattern analysis.

    Features:
    - Velocity tracking for each person
    - Exit pattern detection (consistent movement toward edges)
    - Acceleration-based sudden exit detection
    - Movement history for pattern analysis
    """

    def __init__(self, max_disappeared=30, velocity_window=5, exit_velocity_threshold=20.0):
        """
        Initialize the enhanced tracker.

        Args:
            max_disappeared: Maximum frames an object can disappear before deregistration
            velocity_window: Number of frames to use for velocity calculation
            exit_velocity_threshold: Minimum velocity (pixels/frame) toward edge for exit detection
        """
        self.next_object_id = 0
        self.objects = OrderedDict()  # object_id -> centroid
        self.disappeared = OrderedDict()  # object_id -> frames_disappeared
        self.max_disappeared = max_disappeared

        # Zone tracking
        self.zone_states = OrderedDict()  # object_id -> "inside" or "outside"

        # Velocity tracking
        self.position_history = OrderedDict()  # object_id -> deque of positions
        self.velocities = OrderedDict()  # object_id -> (vx, vy)
        self.accelerations = OrderedDict()  # object_id -> (ax, ay)
        self.velocity_window = velocity_window
        self.exit_velocity_threshold = exit_velocity_threshold

        # Movement pattern tracking
        self.movement_patterns = OrderedDict()  # object_id -> "stationary", "moving", "exiting"
        self.exit_confidence = OrderedDict()  # object_id -> confidence score (0-1)

        # Stage boundaries (will be set externally)
        self.stage_left = 0.1
        self.stage_right = 0.9
        self.stage_top = 0.1
        self.stage_bottom = 0.9

    def set_stage_boundaries(self, left, right, top, bottom):
        """Set the stage boundary percentages."""
        self.stage_left = left
        self.stage_right = right
        self.stage_top = top
        self.stage_bottom = bottom

    def register(self, centroid, zone_state="unknown"):
        """
        Register a new object with velocity tracking.

        Args:
            centroid: (x, y) tuple of object center
            zone_state: "inside", "outside", or "unknown"
        """
        object_id = self.next_object_id
        self.objects[object_id] = centroid
        self.disappeared[object_id] = 0
        self.zone_states[object_id] = zone_state

        # Initialize velocity tracking
        self.position_history[object_id] = deque(maxlen=self.velocity_window)
        self.position_history[object_id].append(centroid)
        self.velocities[object_id] = (0, 0)
        self.accelerations[object_id] = (0, 0)
        self.movement_patterns[object_id] = "stationary"
        self.exit_confidence[object_id] = 0.0

        self.next_object_id += 1

    def deregister(self, object_id):
        """Remove an object and its tracking data."""
        del self.objects[object_id]
        del self.disappeared[object_id]
        if object_id in self.zone_states:
            del self.zone_states[object_id]
        if object_id in self.position_history:
            del self.position_history[object_id]
        if object_id in self.velocities:
            del self.velocities[object_id]
        if object_id in self.accelerations:
            del self.accelerations[object_id]
        if object_id in self.movement_patterns:
            del self.movement_patterns[object_id]
        if object_id in self.exit_confidence:
            del self.exit_confidence[object_id]

    def calculate_velocity(self, object_id):
        """
        Calculate velocity for an object based on position history.

        Returns:
            (vx, vy) tuple of velocity components
        """
        history = self.position_history[object_id]
        if len(history) < 2:
            return (0, 0)

        # Calculate average velocity over the window
        if len(history) >= 2:
            # Get first and last positions
            old_pos = history[0]
            new_pos = history[-1]
            time_diff = len(history) - 1

            if time_diff > 0:
                vx = (new_pos[0] - old_pos[0]) / time_diff
                vy = (new_pos[1] - old_pos[1]) / time_diff
                return (vx, vy)

        return (0, 0)

    def calculate_acceleration(self, object_id):
        """
        Calculate acceleration based on velocity changes.

        Returns:
            (ax, ay) tuple of acceleration components
        """
        if object_id not in self.velocities:
            return (0, 0)

        old_velocity = self.velocities[object_id]
        new_velocity = self.calculate_velocity(object_id)

        # Simple acceleration calculation
        ax = new_velocity[0] - old_velocity[0]
        ay = new_velocity[1] - old_velocity[1]

        return (ax, ay)

    def analyze_movement_pattern(self, object_id, frame_width, frame_height):
        """
        Analyze movement pattern to detect exits.

        Args:
            object_id: ID of the object to analyze
            frame_width: Width of the video frame
            frame_height: Height of the video frame

        Returns:
            Movement pattern: "stationary", "moving", "exiting", "entering"
        """
        if object_id not in self.objects:
            return "unknown"

        centroid = self.objects[object_id]
        vx, vy = self.velocities[object_id]

        # Convert to normalized coordinates
        norm_x = centroid[0] / frame_width
        norm_y = centroid[1] / frame_height

        # Calculate speed
        speed = np.sqrt(vx**2 + vy**2)

        # Check if near edges
        near_left = norm_x < self.stage_left
        near_right = norm_x > self.stage_right
        near_top = norm_y < self.stage_top
        near_bottom = norm_y > self.stage_bottom
        near_edge = near_left or near_right or near_top or near_bottom

        # Analyze movement direction
        moving_left = vx < -self.exit_velocity_threshold
        moving_right = vx > self.exit_velocity_threshold
        moving_up = vy < -self.exit_velocity_threshold
        moving_down = vy > self.exit_velocity_threshold

        # Exit detection logic
        exit_confidence = 0.0

        # Check for exit patterns
        if near_left and moving_left:
            exit_confidence = min(1.0, abs(vx) / (self.exit_velocity_threshold * 2))
        elif near_right and moving_right:
            exit_confidence = min(1.0, abs(vx) / (self.exit_velocity_threshold * 2))
        elif near_top and moving_up:
            exit_confidence = min(1.0, abs(vy) / (self.exit_velocity_threshold * 2))
        elif near_bottom and moving_down:
            exit_confidence = min(1.0, abs(vy) / (self.exit_velocity_threshold * 2))

        # Check for entering patterns (opposite of exit)
        enter_confidence = 0.0
        if near_left and moving_right:
            enter_confidence = min(1.0, abs(vx) / (self.exit_velocity_threshold * 2))
        elif near_right and moving_left:
            enter_confidence = min(1.0, abs(vx) / (self.exit_velocity_threshold * 2))
        elif near_top and moving_down:
            enter_confidence = min(1.0, abs(vy) / (self.exit_velocity_threshold * 2))
        elif near_bottom and moving_up:
            enter_confidence = min(1.0, abs(vy) / (self.exit_velocity_threshold * 2))

        self.exit_confidence[object_id] = exit_confidence

        # Determine pattern
        if exit_confidence > 0.6:
            return "exiting"
        elif enter_confidence > 0.6:
            return "entering"
        elif speed > 5:  # Moving but not exiting
            return "moving"
        else:
            return "stationary"

    def detect_exit_events(self, frame_width, frame_height):
        """
        Detect potential exit events based on movement patterns.

        Args:
            frame_width: Width of the video frame
            frame_height: Height of the video frame

        Returns:
            List of (object_id, confidence) tuples for potential exits
        """
        exit_events = []

        for object_id in self.objects:
            pattern = self.analyze_movement_pattern(object_id, frame_width, frame_height)
            self.movement_patterns[object_id] = pattern

            if pattern == "exiting" and self.exit_confidence[object_id] > 0.7:
                exit_events.append((object_id, self.exit_confidence[object_id]))

        return exit_events

    def update(self, detections, zone_checker=None, frame_width=1920, frame_height=1080):
        """
        Update tracked objects with velocity tracking.

        Args:
            detections: List of (x, y, w, h) bounding boxes or (x, y) centroids
            zone_checker: Optional function(centroid) -> "inside"|"outside"
            frame_width: Width of the video frame
            frame_height: Height of the video frame

        Returns:
            OrderedDict of object_id -> centroid
            List of zone crossing events: [(object_id, from_state, to_state), ...]
            List of exit events: [(object_id, confidence), ...]
        """
        zone_crossings = []

        # If no detections, mark all objects as disappeared
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1

                # Check if object was exiting before disappearing
                if object_id in self.movement_patterns:
                    if self.movement_patterns[object_id] == "exiting":
                        # Likely completed exit
                        self.exit_confidence[object_id] = 1.0

                # Deregister if disappeared too long
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            exit_events = self.detect_exit_events(frame_width, frame_height)
            return self.objects, zone_crossings, exit_events

        # Convert bounding boxes to centroids if needed
        input_centroids = np.zeros((len(detections), 2), dtype="float")
        for (i, detection) in enumerate(detections):
            if len(detection) == 4:  # Bounding box (x, y, w, h)
                x, y, w, h = detection
                cx = x + w / 2
                cy = y + h / 2
                input_centroids[i] = (cx, cy)
            else:  # Already a centroid (x, y)
                input_centroids[i] = detection

        # If we're not currently tracking any objects, register all
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                zone_state = "unknown"
                if zone_checker:
                    zone_state = zone_checker(input_centroids[i])
                self.register(input_centroids[i], zone_state)

        # Otherwise, match existing objects to new detections
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Compute distances between existing and new centroids
            D = dist.cdist(np.array(object_centroids), input_centroids)

            # Find minimum distance for each existing object
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            # Match objects to detections
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue

                # Update the object with new centroid
                object_id = object_ids[row]
                old_centroid = self.objects[object_id]
                new_centroid = input_centroids[col]

                # Update position and calculate velocity
                self.objects[object_id] = new_centroid
                self.position_history[object_id].append(new_centroid)
                self.disappeared[object_id] = 0

                # Calculate velocity and acceleration
                old_velocity = self.velocities[object_id]
                new_velocity = self.calculate_velocity(object_id)
                self.velocities[object_id] = new_velocity
                self.accelerations[object_id] = self.calculate_acceleration(object_id)

                # Check for zone crossing
                if zone_checker:
                    old_zone = self.zone_states.get(object_id, "unknown")
                    new_zone = zone_checker(new_centroid)

                    if old_zone != "unknown" and new_zone != "unknown" and old_zone != new_zone:
                        zone_crossings.append((object_id, old_zone, new_zone))

                    self.zone_states[object_id] = new_zone

                used_rows.add(row)
                used_cols.add(col)

            # Handle unmatched objects (disappeared)
            unused_rows = set(range(D.shape[0])) - used_rows
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1

                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # Register new objects (unmatched detections)
            unused_cols = set(range(D.shape[1])) - used_cols
            for col in unused_cols:
                zone_state = "unknown"
                if zone_checker:
                    zone_state = zone_checker(input_centroids[col])
                self.register(input_centroids[col], zone_state)

        # Detect exit events
        exit_events = self.detect_exit_events(frame_width, frame_height)

        return self.objects, zone_crossings, exit_events

    def get_count_inside_zone(self):
        """Get count of objects currently inside the zone."""
        return sum(1 for state in self.zone_states.values() if state == "inside")

    def get_count_outside_zone(self):
        """Get count of objects currently outside the zone."""
        return sum(1 for state in self.zone_states.values() if state == "outside")

    def get_object_info(self, object_id):
        """
        Get detailed information about a tracked object.

        Returns:
            Dictionary with object information
        """
        if object_id not in self.objects:
            return None

        return {
            'position': self.objects[object_id],
            'velocity': self.velocities.get(object_id, (0, 0)),
            'acceleration': self.accelerations.get(object_id, (0, 0)),
            'zone_state': self.zone_states.get(object_id, 'unknown'),
            'movement_pattern': self.movement_patterns.get(object_id, 'unknown'),
            'exit_confidence': self.exit_confidence.get(object_id, 0.0),
            'disappeared_frames': self.disappeared.get(object_id, 0)
        }