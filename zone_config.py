#!/usr/bin/env python3
"""
Flexible zone boundary configuration system for stage detection.
Supports multiple zone shapes and adaptive boundary learning.
"""

import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
from collections import defaultdict


class FlexibleZoneConfig:
    """
    Flexible zone configuration supporting multiple shapes and adaptive learning.

    Supports:
    - Rectangle boundaries
    - Polygon boundaries
    - Elliptical boundaries
    - Adaptive boundary learning from performer positions
    - Multiple zone layers (stage, safe zone, danger zone)
    """

    def __init__(self):
        """Initialize the zone configuration."""
        self.zone_type = "rectangle"
        self.stage_bounds = None
        self.safe_zone = None
        self.danger_zone = None

        # Adaptive learning
        self.position_history = []
        self.heatmap = None
        self.auto_calibrated = False

        # Zone definitions
        self.zones = {}

    def set_rectangle_zone(self, left: float, right: float, top: float, bottom: float):
        """
        Set a rectangular stage zone.

        Args:
            left: Left boundary (0-1)
            right: Right boundary (0-1)
            top: Top boundary (0-1)
            bottom: Bottom boundary (0-1)
        """
        self.zone_type = "rectangle"
        self.stage_bounds = {
            'left': left,
            'right': right,
            'top': top,
            'bottom': bottom
        }

        # Create safe and danger zones
        margin = 0.05
        self.safe_zone = {
            'left': left + margin,
            'right': right - margin,
            'top': top + margin,
            'bottom': bottom - margin
        }

        self.danger_zone = {
            'left': left - margin,
            'right': right + margin,
            'top': top - margin,
            'bottom': bottom + margin
        }

    def set_polygon_zone(self, points: List[Tuple[float, float]]):
        """
        Set a polygon-shaped stage zone.

        Args:
            points: List of (x, y) coordinates defining the polygon (normalized 0-1)
        """
        self.zone_type = "polygon"
        self.stage_bounds = np.array(points)

        # Create safe zone (shrink polygon)
        center = np.mean(self.stage_bounds, axis=0)
        self.safe_zone = center + 0.9 * (self.stage_bounds - center)

        # Create danger zone (expand polygon)
        self.danger_zone = center + 1.1 * (self.stage_bounds - center)

    def set_elliptical_zone(self, center_x: float, center_y: float, width: float, height: float):
        """
        Set an elliptical stage zone.

        Args:
            center_x: X coordinate of center (0-1)
            center_y: Y coordinate of center (0-1)
            width: Width of ellipse (0-1)
            height: Height of ellipse (0-1)
        """
        self.zone_type = "ellipse"
        self.stage_bounds = {
            'center': (center_x, center_y),
            'width': width,
            'height': height
        }

        # Safe zone (smaller ellipse)
        self.safe_zone = {
            'center': (center_x, center_y),
            'width': width * 0.9,
            'height': height * 0.9
        }

        # Danger zone (larger ellipse)
        self.danger_zone = {
            'center': (center_x, center_y),
            'width': width * 1.1,
            'height': height * 1.1
        }

    def is_in_zone(self, x: float, y: float, zone_name: str = "stage") -> bool:
        """
        Check if a point is within a specified zone.

        Args:
            x: X coordinate (normalized 0-1)
            y: Y coordinate (normalized 0-1)
            zone_name: "stage", "safe", or "danger"

        Returns:
            True if point is in zone
        """
        if zone_name == "safe":
            bounds = self.safe_zone
        elif zone_name == "danger":
            bounds = self.danger_zone
        else:
            bounds = self.stage_bounds

        if bounds is None:
            return True  # No zone defined, consider all points in zone

        if self.zone_type == "rectangle":
            return (bounds['left'] <= x <= bounds['right'] and
                    bounds['top'] <= y <= bounds['bottom'])

        elif self.zone_type == "polygon":
            # Point-in-polygon test
            point = np.array([x, y])
            return cv2.pointPolygonTest(bounds.astype(np.float32), tuple(point), False) >= 0

        elif self.zone_type == "ellipse":
            cx, cy = bounds['center']
            wx, wy = bounds['width'] / 2, bounds['height'] / 2

            # Ellipse equation: ((x-cx)/wx)^2 + ((y-cy)/wy)^2 <= 1
            return ((x - cx) / wx) ** 2 + ((y - cy) / wy) ** 2 <= 1

        return True

    def get_distance_to_edge(self, x: float, y: float) -> float:
        """
        Calculate minimum distance from point to zone edge.

        Args:
            x: X coordinate (normalized 0-1)
            y: Y coordinate (normalized 0-1)

        Returns:
            Distance to nearest edge (negative if outside zone)
        """
        if self.stage_bounds is None:
            return 0.5  # Default distance if no zone defined

        if self.zone_type == "rectangle":
            bounds = self.stage_bounds
            distances = [
                x - bounds['left'],    # Distance to left edge
                bounds['right'] - x,   # Distance to right edge
                y - bounds['top'],     # Distance to top edge
                bounds['bottom'] - y   # Distance to bottom edge
            ]
            return min(distances)

        elif self.zone_type == "polygon":
            point = np.array([x, y])
            return cv2.pointPolygonTest(
                self.stage_bounds.astype(np.float32),
                tuple(point),
                True  # Return signed distance
            )

        elif self.zone_type == "ellipse":
            cx, cy = self.stage_bounds['center']
            wx, wy = self.stage_bounds['width'] / 2, self.stage_bounds['height'] / 2

            # Distance from ellipse center
            ellipse_value = ((x - cx) / wx) ** 2 + ((y - cy) / wy) ** 2

            if ellipse_value <= 1:
                # Inside ellipse - return approximate distance to edge
                return (1 - ellipse_value) * min(wx, wy)
            else:
                # Outside ellipse
                return -(ellipse_value - 1) * min(wx, wy)

        return 0.0

    def add_position_sample(self, x: float, y: float, frame_num: int):
        """
        Add a position sample for adaptive learning.

        Args:
            x: X coordinate (normalized 0-1)
            y: Y coordinate (normalized 0-1)
            frame_num: Frame number for temporal tracking
        """
        self.position_history.append({
            'x': x,
            'y': y,
            'frame': frame_num
        })

    def auto_calibrate_zones(self, min_samples: int = 100):
        """
        Automatically calibrate zones based on position history.

        Args:
            min_samples: Minimum samples needed for calibration

        Returns:
            True if calibration successful
        """
        if len(self.position_history) < min_samples:
            return False

        # Extract positions
        positions = np.array([(p['x'], p['y']) for p in self.position_history])

        # Calculate bounding box of positions
        min_x, min_y = np.min(positions, axis=0)
        max_x, max_y = np.max(positions, axis=0)

        # Add margin around detected area
        margin = 0.1
        self.set_rectangle_zone(
            max(0, min_x - margin),
            min(1, max_x + margin),
            max(0, min_y - margin),
            min(1, max_y + margin)
        )

        self.auto_calibrated = True
        return True

    def generate_heatmap(self, width: int = 100, height: int = 100) -> np.ndarray:
        """
        Generate a heatmap of position history.

        Args:
            width: Width of heatmap
            height: Height of heatmap

        Returns:
            Heatmap array
        """
        heatmap = np.zeros((height, width))

        for pos in self.position_history:
            x = int(pos['x'] * width)
            y = int(pos['y'] * height)

            if 0 <= x < width and 0 <= y < height:
                heatmap[y, x] += 1

        # Apply Gaussian blur for smoothing
        if cv2 is not None:
            heatmap = cv2.GaussianBlur(heatmap, (15, 15), 0)

        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        self.heatmap = heatmap
        return heatmap

    def get_zone_confidence(self, x: float, y: float) -> float:
        """
        Get confidence that a position is within the performance zone.

        Args:
            x: X coordinate (normalized 0-1)
            y: Y coordinate (normalized 0-1)

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from zone boundaries
        if not self.is_in_zone(x, y, "stage"):
            base_confidence = 0.0
        elif self.is_in_zone(x, y, "safe"):
            base_confidence = 1.0
        else:
            # In danger zone - calculate gradient
            distance = self.get_distance_to_edge(x, y)
            base_confidence = max(0, min(1, distance * 2))

        # Adjust based on heatmap if available
        if self.heatmap is not None:
            hm_height, hm_width = self.heatmap.shape
            hm_x = int(x * hm_width)
            hm_y = int(y * hm_height)

            if 0 <= hm_x < hm_width and 0 <= hm_y < hm_height:
                heatmap_confidence = self.heatmap[hm_y, hm_x]
                # Weighted average of base and heatmap confidence
                return 0.7 * base_confidence + 0.3 * heatmap_confidence

        return base_confidence

    def visualize_zones(self, frame: np.ndarray, alpha: float = 0.3) -> np.ndarray:
        """
        Visualize zones on a frame.

        Args:
            frame: Input frame
            alpha: Transparency for overlays

        Returns:
            Frame with zone overlays
        """
        height, width = frame.shape[:2]
        overlay = frame.copy()

        if self.zone_type == "rectangle" and self.stage_bounds:
            # Draw stage zone (green)
            pt1 = (int(self.stage_bounds['left'] * width),
                   int(self.stage_bounds['top'] * height))
            pt2 = (int(self.stage_bounds['right'] * width),
                   int(self.stage_bounds['bottom'] * height))
            cv2.rectangle(overlay, pt1, pt2, (0, 255, 0), 2)

            # Draw safe zone (blue)
            if self.safe_zone:
                pt1 = (int(self.safe_zone['left'] * width),
                       int(self.safe_zone['top'] * height))
                pt2 = (int(self.safe_zone['right'] * width),
                       int(self.safe_zone['bottom'] * height))
                cv2.rectangle(overlay, pt1, pt2, (255, 0, 0), 1)

            # Draw danger zone (red)
            if self.danger_zone:
                pt1 = (int(self.danger_zone['left'] * width),
                       int(self.danger_zone['top'] * height))
                pt2 = (int(self.danger_zone['right'] * width),
                       int(self.danger_zone['bottom'] * height))
                cv2.rectangle(overlay, pt1, pt2, (0, 0, 255), 1)

        elif self.zone_type == "polygon" and self.stage_bounds is not None:
            # Scale polygon points to frame size
            points = (self.stage_bounds * [width, height]).astype(np.int32)
            cv2.polylines(overlay, [points], True, (0, 255, 0), 2)

            if self.safe_zone is not None:
                safe_points = (self.safe_zone * [width, height]).astype(np.int32)
                cv2.polylines(overlay, [safe_points], True, (255, 0, 0), 1)

            if self.danger_zone is not None:
                danger_points = (self.danger_zone * [width, height]).astype(np.int32)
                cv2.polylines(overlay, [danger_points], True, (0, 0, 255), 1)

        elif self.zone_type == "ellipse" and self.stage_bounds:
            cx, cy = self.stage_bounds['center']
            wx, wy = self.stage_bounds['width'] / 2, self.stage_bounds['height'] / 2

            # Draw stage ellipse
            cv2.ellipse(overlay,
                        (int(cx * width), int(cy * height)),
                        (int(wx * width), int(wy * height)),
                        0, 0, 360, (0, 255, 0), 2)

            # Draw safe zone
            if self.safe_zone:
                sx, sy = self.safe_zone['width'] / 2, self.safe_zone['height'] / 2
                cv2.ellipse(overlay,
                            (int(cx * width), int(cy * height)),
                            (int(sx * width), int(sy * height)),
                            0, 0, 360, (255, 0, 0), 1)

            # Draw danger zone
            if self.danger_zone:
                dx, dy = self.danger_zone['width'] / 2, self.danger_zone['height'] / 2
                cv2.ellipse(overlay,
                            (int(cx * width), int(cy * height)),
                            (int(dx * width), int(dy * height)),
                            0, 0, 360, (0, 0, 255), 1)

        # Blend overlay with original
        result = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # Add heatmap if available
        if self.heatmap is not None:
            # Resize heatmap to frame size
            heatmap_resized = cv2.resize(self.heatmap, (width, height))

            # Convert to color
            heatmap_color = cv2.applyColorMap(
                (heatmap_resized * 255).astype(np.uint8),
                cv2.COLORMAP_JET
            )

            # Blend with result
            result = cv2.addWeighted(result, 0.7, heatmap_color, 0.3, 0)

        return result

    def save_config(self, filepath: str):
        """Save zone configuration to file."""
        import json

        config = {
            'zone_type': self.zone_type,
            'stage_bounds': self.stage_bounds,
            'auto_calibrated': self.auto_calibrated
        }

        # Convert numpy arrays to lists for JSON serialization
        if isinstance(config['stage_bounds'], np.ndarray):
            config['stage_bounds'] = config['stage_bounds'].tolist()

        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)

    def load_config(self, filepath: str):
        """Load zone configuration from file."""
        import json

        with open(filepath, 'r') as f:
            config = json.load(f)

        self.zone_type = config['zone_type']
        self.auto_calibrated = config.get('auto_calibrated', False)

        if self.zone_type == "rectangle":
            self.set_rectangle_zone(
                config['stage_bounds']['left'],
                config['stage_bounds']['right'],
                config['stage_bounds']['top'],
                config['stage_bounds']['bottom']
            )
        elif self.zone_type == "polygon":
            self.set_polygon_zone(config['stage_bounds'])
        elif self.zone_type == "ellipse":
            cx, cy = config['stage_bounds']['center']
            self.set_elliptical_zone(
                cx, cy,
                config['stage_bounds']['width'],
                config['stage_bounds']['height']
            )