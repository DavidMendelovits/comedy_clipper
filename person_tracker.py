#!/usr/bin/env python3
"""
Simple centroid-based person tracker for multi-object tracking
Based on PyImageSearch centroid tracking algorithm
"""

import numpy as np
from scipy.spatial import distance as dist
from collections import OrderedDict


class CentroidTracker:
    """
    Tracks objects across frames using centroid distances.

    Maintains object IDs and handles object registration, deregistration,
    and matching across frames.
    """

    def __init__(self, max_disappeared=30):
        """
        Initialize the centroid tracker.

        Args:
            max_disappeared: Maximum frames an object can disappear before deregistration
        """
        self.next_object_id = 0
        self.objects = OrderedDict()  # object_id -> centroid
        self.disappeared = OrderedDict()  # object_id -> frames_disappeared
        self.max_disappeared = max_disappeared

        # Track zone crossings
        self.zone_states = OrderedDict()  # object_id -> "inside" or "outside"

    def register(self, centroid, zone_state="unknown"):
        """
        Register a new object with the next available ID.

        Args:
            centroid: (x, y) tuple of object center
            zone_state: "inside", "outside", or "unknown"
        """
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.zone_states[self.next_object_id] = zone_state
        self.next_object_id += 1

    def deregister(self, object_id):
        """Remove an object that has disappeared for too long."""
        del self.objects[object_id]
        del self.disappeared[object_id]
        if object_id in self.zone_states:
            del self.zone_states[object_id]

    def update(self, detections, zone_checker=None):
        """
        Update tracked objects with new detections.

        Args:
            detections: List of (x, y, w, h) bounding boxes or (x, y) centroids
            zone_checker: Optional function(centroid) -> "inside"|"outside"

        Returns:
            OrderedDict of object_id -> centroid
            List of zone crossing events: [(object_id, from_state, to_state), ...]
        """
        zone_crossings = []

        # If no detections, mark all objects as disappeared
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1

                # Deregister if disappeared too long
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            return self.objects, zone_crossings

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

                self.objects[object_id] = new_centroid
                self.disappeared[object_id] = 0

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

        return self.objects, zone_crossings

    def get_count_inside_zone(self):
        """Get count of objects currently inside the zone."""
        return sum(1 for state in self.zone_states.values() if state == "inside")

    def get_count_outside_zone(self):
        """Get count of objects currently outside the zone."""
        return sum(1 for state in self.zone_states.values() if state == "outside")
