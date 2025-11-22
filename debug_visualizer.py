#!/usr/bin/env python3
"""
Debug visualization system for comedy clipper detection.
Provides visual overlays and debug information for analysis.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
import time


class DebugVisualizer:
    """
    Comprehensive debug visualization for detection analysis.
    """

    def __init__(self):
        """Initialize debug visualizer."""
        # Display options
        self.show_zones = True
        self.show_tracking = True
        self.show_velocity = True
        self.show_confidence = True
        self.show_state = True
        self.show_heatmap = False
        self.show_timeline = True

        # Color scheme
        self.colors = {
            'zone_stage': (0, 255, 0),      # Green
            'zone_safe': (255, 255, 0),     # Cyan
            'zone_danger': (0, 0, 255),     # Red
            'person_host': (255, 128, 0),   # Orange
            'person_comedian': (0, 255, 255), # Yellow
            'person_unknown': (128, 128, 128), # Gray
            'velocity': (255, 0, 255),      # Magenta
            'exit_path': (0, 128, 255),     # Blue
            'confidence_high': (0, 255, 0),  # Green
            'confidence_med': (0, 255, 255), # Yellow
            'confidence_low': (0, 0, 255),   # Red
        }

        # History tracking for trails
        self.position_history = {}  # person_id -> deque of positions
        self.max_trail_length = 30

        # Performance metrics
        self.fps_history = deque(maxlen=30)
        self.detection_times = deque(maxlen=100)

        # Timeline data
        self.timeline_events = deque(maxlen=500)

    def visualize_frame(self, frame: np.ndarray, detection_data: Dict) -> np.ndarray:
        """
        Add debug visualizations to frame.

        Args:
            frame: Input frame
            detection_data: Dictionary containing all detection data

        Returns:
            Frame with debug overlays
        """
        output = frame.copy()
        height, width = frame.shape[:2]

        # Draw zones
        if self.show_zones and 'zones' in detection_data:
            output = self._draw_zones(output, detection_data['zones'])

        # Draw person tracking
        if self.show_tracking and 'persons' in detection_data:
            output = self._draw_person_tracking(output, detection_data['persons'])

        # Draw velocity vectors
        if self.show_velocity and 'velocities' in detection_data:
            output = self._draw_velocity_vectors(output, detection_data['velocities'])

        # Draw confidence bars
        if self.show_confidence and 'confidences' in detection_data:
            output = self._draw_confidence_bars(output, detection_data['confidences'])

        # Draw state information
        if self.show_state and 'state' in detection_data:
            output = self._draw_state_info(output, detection_data['state'])

        # Draw heatmap
        if self.show_heatmap and 'heatmap' in detection_data:
            output = self._draw_heatmap(output, detection_data['heatmap'])

        # Draw timeline
        if self.show_timeline:
            output = self._draw_timeline(output)

        # Draw performance metrics
        output = self._draw_performance_metrics(output)

        return output

    def _draw_zones(self, frame: np.ndarray, zones: Dict) -> np.ndarray:
        """Draw detection zones on frame."""
        height, width = frame.shape[:2]
        overlay = frame.copy()

        # Draw stage zone
        if 'stage' in zones:
            stage = zones['stage']
            if stage['type'] == 'rectangle':
                pt1 = (int(stage['left'] * width), int(stage['top'] * height))
                pt2 = (int(stage['right'] * width), int(stage['bottom'] * height))
                cv2.rectangle(overlay, pt1, pt2, self.colors['zone_stage'], 2)
                cv2.putText(overlay, "STAGE", (pt1[0] + 5, pt1[1] + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['zone_stage'], 2)

        # Draw safe zone
        if 'safe' in zones:
            safe = zones['safe']
            pt1 = (int(safe['left'] * width), int(safe['top'] * height))
            pt2 = (int(safe['right'] * width), int(safe['bottom'] * height))
            cv2.rectangle(overlay, pt1, pt2, self.colors['zone_safe'], 1)

        # Draw danger zone
        if 'danger' in zones:
            danger = zones['danger']
            pt1 = (int(danger['left'] * width), int(danger['top'] * height))
            pt2 = (int(danger['right'] * width), int(danger['bottom'] * height))
            cv2.rectangle(overlay, pt1, pt2, self.colors['zone_danger'], 1, cv2.LINE_AA)

        # Blend overlay
        return cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    def _draw_person_tracking(self, frame: np.ndarray, persons: List[Dict]) -> np.ndarray:
        """Draw person tracking information."""
        height, width = frame.shape[:2]

        for person in persons:
            person_id = person.get('id', 0)
            bbox = person.get('bbox', None)
            role = person.get('role', 'unknown')
            identity_id = person.get('identity_id', None)
            confidence = person.get('confidence', 0.0)

            if bbox:
                x, y, w, h = bbox

                # Choose color based on role
                if role == 'host':
                    color = self.colors['person_host']
                elif role == 'comedian':
                    color = self.colors['person_comedian']
                else:
                    color = self.colors['person_unknown']

                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                # Draw person info
                info_text = f"P{person_id}"
                if identity_id is not None:
                    info_text += f" (ID:{identity_id})"
                if role != 'unknown':
                    info_text += f" [{role}]"

                cv2.putText(frame, info_text, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Draw confidence
                if confidence > 0:
                    conf_text = f"{confidence:.2f}"
                    cv2.putText(frame, conf_text, (x, y + h + 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                # Update position history
                center_x = x + w // 2
                center_y = y + h // 2

                if person_id not in self.position_history:
                    self.position_history[person_id] = deque(maxlen=self.max_trail_length)
                self.position_history[person_id].append((center_x, center_y))

                # Draw trail
                if len(self.position_history[person_id]) > 1:
                    points = np.array(list(self.position_history[person_id]), np.int32)
                    cv2.polylines(frame, [points], False, color, 1, cv2.LINE_AA)

        return frame

    def _draw_velocity_vectors(self, frame: np.ndarray, velocities: List[Dict]) -> np.ndarray:
        """Draw velocity vectors for tracked persons."""
        scale = 5  # Scale factor for velocity visualization

        for vel_data in velocities:
            person_id = vel_data.get('person_id', 0)
            position = vel_data.get('position', None)
            velocity = vel_data.get('velocity', None)

            if position and velocity:
                x, y = position
                vx, vy = velocity

                # Calculate arrow endpoint
                end_x = int(x + vx * scale)
                end_y = int(y + vy * scale)

                # Draw velocity vector
                cv2.arrowedLine(frame, (int(x), int(y)), (end_x, end_y),
                               self.colors['velocity'], 2, cv2.LINE_AA)

                # Draw velocity magnitude
                magnitude = np.sqrt(vx**2 + vy**2)
                vel_text = f"v:{magnitude:.1f}"
                cv2.putText(frame, vel_text, (int(x) + 10, int(y) - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['velocity'], 1)

        return frame

    def _draw_confidence_bars(self, frame: np.ndarray, confidences: List[Dict]) -> np.ndarray:
        """Draw confidence bars for each person."""
        height, width = frame.shape[:2]
        bar_width = 150
        bar_height = 20
        start_x = width - bar_width - 20
        start_y = 20

        for i, conf_data in enumerate(confidences):
            person_id = conf_data.get('person_id', 0)
            exit_conf = conf_data.get('exit_confidence', 0.0)
            stage_conf = conf_data.get('stage_confidence', 1.0)
            role = conf_data.get('role', 'unknown')

            y_pos = start_y + i * (bar_height + 10)

            # Draw background
            cv2.rectangle(frame, (start_x, y_pos),
                         (start_x + bar_width, y_pos + bar_height),
                         (50, 50, 50), -1)

            # Draw exit confidence bar
            exit_width = int(bar_width * exit_conf)
            if exit_conf > 0.7:
                color = self.colors['confidence_high']
            elif exit_conf > 0.4:
                color = self.colors['confidence_med']
            else:
                color = self.colors['confidence_low']

            cv2.rectangle(frame, (start_x, y_pos),
                         (start_x + exit_width, y_pos + bar_height),
                         color, -1)

            # Draw text
            text = f"P{person_id} ({role}) Exit: {exit_conf:.2f}"
            cv2.putText(frame, text, (start_x, y_pos - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        return frame

    def _draw_state_info(self, frame: np.ndarray, state: Dict) -> np.ndarray:
        """Draw current state information."""
        height, width = frame.shape[:2]

        # State info box
        info_lines = []

        if 'performance_state' in state:
            info_lines.append(f"State: {state['performance_state']}")

        if 'person_count' in state:
            info_lines.append(f"People: {state['person_count']}")

        if 'segment_active' in state:
            if state['segment_active']:
                info_lines.append("RECORDING")
                duration = state.get('segment_duration', 0)
                info_lines.append(f"Duration: {duration:.1f}s")

        if 'transitions_detected' in state:
            info_lines.append(f"Transitions: {state['transitions_detected']}")

        # Draw info box
        y_pos = 20
        for line in info_lines:
            cv2.putText(frame, line, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 25

        # Draw recording indicator
        if state.get('segment_active', False):
            cv2.circle(frame, (width - 30, 30), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (width - 70, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        return frame

    def _draw_heatmap(self, frame: np.ndarray, heatmap: np.ndarray) -> np.ndarray:
        """Overlay heatmap on frame."""
        if heatmap is None or heatmap.size == 0:
            return frame

        height, width = frame.shape[:2]

        # Resize heatmap to frame size
        heatmap_resized = cv2.resize(heatmap, (width, height))

        # Normalize and convert to color
        heatmap_norm = (heatmap_resized * 255).astype(np.uint8)
        heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)

        # Blend with frame
        return cv2.addWeighted(frame, 0.6, heatmap_color, 0.4, 0)

    def _draw_timeline(self, frame: np.ndarray) -> np.ndarray:
        """Draw event timeline at bottom of frame."""
        height, width = frame.shape[:2]
        timeline_height = 60
        timeline_y = height - timeline_height

        # Draw timeline background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, timeline_y), (width, height),
                     (30, 30, 30), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Draw timeline events
        if self.timeline_events:
            # Calculate time range
            current_time = time.time()
            time_window = 30  # Show last 30 seconds

            for event in self.timeline_events:
                event_time = event.get('timestamp', 0)
                time_ago = current_time - event_time

                if time_ago < time_window:
                    # Calculate x position
                    x_pos = int(width * (1 - time_ago / time_window))

                    # Draw event marker
                    event_type = event.get('type', 'unknown')
                    if event_type == 'exit':
                        color = (0, 0, 255)
                    elif event_type == 'enter':
                        color = (0, 255, 0)
                    elif event_type == 'transition':
                        color = (255, 255, 0)
                    else:
                        color = (128, 128, 128)

                    cv2.line(frame, (x_pos, timeline_y),
                            (x_pos, height - 10), color, 2)

                    # Draw event label
                    if 'label' in event:
                        cv2.putText(frame, event['label'],
                                   (x_pos - 20, height - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                                   color, 1)

        # Draw timeline labels
        cv2.putText(frame, "Timeline (30s)", (10, timeline_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def _draw_performance_metrics(self, frame: np.ndarray) -> np.ndarray:
        """Draw performance metrics overlay."""
        height, width = frame.shape[:2]

        # Calculate FPS
        if self.fps_history:
            avg_fps = np.mean(list(self.fps_history))
            fps_text = f"FPS: {avg_fps:.1f}"
        else:
            fps_text = "FPS: --"

        # Calculate detection time
        if self.detection_times:
            avg_time = np.mean(list(self.detection_times)) * 1000
            time_text = f"Det: {avg_time:.1f}ms"
        else:
            time_text = "Det: --ms"

        # Draw metrics
        cv2.putText(frame, fps_text, (width - 100, height - 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, time_text, (width - 100, height - 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return frame

    def add_timeline_event(self, event_type: str, label: str, timestamp: float = None):
        """
        Add an event to the timeline.

        Args:
            event_type: Type of event ("exit", "enter", "transition", etc.)
            label: Event label
            timestamp: Event timestamp (current time if None)
        """
        if timestamp is None:
            timestamp = time.time()

        self.timeline_events.append({
            'type': event_type,
            'label': label,
            'timestamp': timestamp
        })

    def update_fps(self, fps: float):
        """Update FPS tracking."""
        self.fps_history.append(fps)

    def update_detection_time(self, detection_time: float):
        """Update detection time tracking."""
        self.detection_times.append(detection_time)

    def save_debug_frame(self, frame: np.ndarray, output_path: str, frame_num: int):
        """
        Save debug frame to file.

        Args:
            frame: Frame with debug overlays
            output_path: Output directory path
            frame_num: Frame number
        """
        filename = f"{output_path}/debug_frame_{frame_num:06d}.jpg"
        cv2.imwrite(filename, frame)

    def create_debug_video(self, frames: List[np.ndarray], output_path: str, fps: int = 30):
        """
        Create debug video from frames.

        Args:
            frames: List of debug frames
            output_path: Output video path
            fps: Video frame rate
        """
        if not frames:
            return

        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for frame in frames:
            out.write(frame)

        out.release()