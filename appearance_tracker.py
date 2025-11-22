#!/usr/bin/env python3
"""
Appearance-based person tracking for distinguishing individuals.
Uses color histograms, size features, and temporal consistency.
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from collections import deque, OrderedDict
import time


class AppearanceFeatures:
    """
    Extract and compare appearance features for person identification.
    """

    def __init__(self):
        """Initialize feature extractor."""
        self.histogram_bins = 32
        self.feature_weights = {
            'color_histogram': 0.4,
            'size': 0.2,
            'aspect_ratio': 0.2,
            'position': 0.2
        }

    def extract_color_histogram(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Extract color histogram from person bounding box.

        Args:
            image: Frame image
            bbox: (x, y, w, h) bounding box

        Returns:
            Normalized color histogram
        """
        x, y, w, h = bbox

        # Ensure bbox is within image bounds
        x = max(0, x)
        y = max(0, y)
        x_end = min(image.shape[1], x + w)
        y_end = min(image.shape[0], y + h)

        # Extract region of interest
        roi = image[y:y_end, x:x_end]

        if roi.size == 0:
            return np.zeros(self.histogram_bins * 3)

        # Calculate histograms for each channel
        hist_features = []

        for channel in range(3):
            hist = cv2.calcHist(
                [roi],
                [channel],
                None,
                [self.histogram_bins],
                [0, 256]
            )
            hist = cv2.normalize(hist, hist).flatten()
            hist_features.extend(hist)

        return np.array(hist_features)

    def extract_size_features(self, bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Extract size-based features.

        Args:
            bbox: (x, y, w, h) bounding box

        Returns:
            Dictionary of size features
        """
        x, y, w, h = bbox

        return {
            'width': w,
            'height': h,
            'area': w * h,
            'aspect_ratio': w / h if h > 0 else 1.0,
            'center_x': x + w / 2,
            'center_y': y + h / 2
        }

    def extract_all_features(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Extract all appearance features.

        Args:
            image: Frame image
            bbox: (x, y, w, h) bounding box

        Returns:
            Dictionary of all features
        """
        color_hist = self.extract_color_histogram(image, bbox)
        size_features = self.extract_size_features(bbox)

        return {
            'color_histogram': color_hist,
            'size_features': size_features,
            'timestamp': time.time()
        }

    def compare_histograms(self, hist1: np.ndarray, hist2: np.ndarray) -> float:
        """
        Compare two color histograms.

        Args:
            hist1: First histogram
            hist2: Second histogram

        Returns:
            Similarity score (0-1)
        """
        if hist1.size == 0 or hist2.size == 0:
            return 0.0

        # Use correlation coefficient
        correlation = cv2.compareHist(
            hist1.reshape(-1, 1),
            hist2.reshape(-1, 1),
            cv2.HISTCMP_CORREL
        )

        # Convert to 0-1 range
        return max(0, min(1, correlation))

    def compare_features(self, features1: Dict, features2: Dict) -> float:
        """
        Compare two feature sets.

        Args:
            features1: First feature set
            features2: Second feature set

        Returns:
            Overall similarity score (0-1)
        """
        scores = {}

        # Compare color histograms
        if 'color_histogram' in features1 and 'color_histogram' in features2:
            scores['color_histogram'] = self.compare_histograms(
                features1['color_histogram'],
                features2['color_histogram']
            )

        # Compare sizes
        if 'size_features' in features1 and 'size_features' in features2:
            size1 = features1['size_features']
            size2 = features2['size_features']

            # Normalized size difference
            size_diff = abs(size1['area'] - size2['area']) / max(size1['area'], size2['area'])
            scores['size'] = max(0, 1 - size_diff)

            # Aspect ratio similarity
            ar_diff = abs(size1['aspect_ratio'] - size2['aspect_ratio'])
            scores['aspect_ratio'] = max(0, 1 - ar_diff / 2)

            # Position proximity (normalized by image size)
            pos_dist = np.sqrt(
                (size1['center_x'] - size2['center_x']) ** 2 +
                (size1['center_y'] - size2['center_y']) ** 2
            )
            scores['position'] = max(0, 1 - pos_dist / 1000)  # Normalize by typical image width

        # Weighted average of scores
        total_score = 0
        total_weight = 0

        for feature, score in scores.items():
            weight = self.feature_weights.get(feature, 0.25)
            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0


class PersonIdentityTracker:
    """
    Track person identities using appearance features.
    Helps distinguish between host and comedian.
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize identity tracker.

        Args:
            similarity_threshold: Minimum similarity to consider same person
        """
        self.feature_extractor = AppearanceFeatures()
        self.similarity_threshold = similarity_threshold

        # Track identities
        self.identities = OrderedDict()  # identity_id -> feature_history
        self.object_to_identity = {}  # object_id -> identity_id
        self.next_identity_id = 0

        # Track role assignments
        self.identity_roles = {}  # identity_id -> "host" or "comedian"
        self.role_confidence = {}  # identity_id -> confidence

        # Performance tracking
        self.stage_time = {}  # identity_id -> total_time_on_stage
        self.last_seen = {}  # identity_id -> last_frame_seen

    def update_identity(self, object_id: int, image: np.ndarray, bbox: Tuple[int, int, int, int], frame_num: int):
        """
        Update identity tracking for an object.

        Args:
            object_id: Tracker object ID
            image: Current frame
            bbox: Bounding box (x, y, w, h)
            frame_num: Current frame number

        Returns:
            identity_id assigned to this object
        """
        # Extract features
        features = self.feature_extractor.extract_all_features(image, bbox)

        # Check if object already has an identity
        if object_id in self.object_to_identity:
            identity_id = self.object_to_identity[object_id]

            # Update feature history
            if identity_id not in self.identities:
                self.identities[identity_id] = deque(maxlen=30)

            self.identities[identity_id].append(features)
            self.last_seen[identity_id] = frame_num

            # Update stage time
            if identity_id not in self.stage_time:
                self.stage_time[identity_id] = 0
            self.stage_time[identity_id] += 1

            return identity_id

        # Try to match with existing identities
        best_match_id = None
        best_match_score = 0

        for identity_id, feature_history in self.identities.items():
            if not feature_history:
                continue

            # Compare with recent features
            recent_features = list(feature_history)[-5:]
            scores = []

            for hist_features in recent_features:
                score = self.feature_extractor.compare_features(features, hist_features)
                scores.append(score)

            avg_score = np.mean(scores)

            if avg_score > best_match_score:
                best_match_score = avg_score
                best_match_id = identity_id

        # Assign identity
        if best_match_score > self.similarity_threshold:
            # Match found - assign existing identity
            identity_id = best_match_id
            self.object_to_identity[object_id] = identity_id

            # Update feature history
            self.identities[identity_id].append(features)
            self.last_seen[identity_id] = frame_num

        else:
            # No match - create new identity
            identity_id = self.next_identity_id
            self.next_identity_id += 1

            self.identities[identity_id] = deque(maxlen=30)
            self.identities[identity_id].append(features)
            self.object_to_identity[object_id] = identity_id
            self.stage_time[identity_id] = 0
            self.last_seen[identity_id] = frame_num

        return identity_id

    def infer_roles(self, frame_num: int):
        """
        Infer host vs comedian roles based on behavior patterns.

        Args:
            frame_num: Current frame number

        Returns:
            Dictionary of identity_id -> role
        """
        # Analyze patterns to determine roles
        for identity_id in self.identities:
            if identity_id in self.identity_roles:
                continue  # Role already assigned

            # Get stage time for this identity
            stage_time = self.stage_time.get(identity_id, 0)
            last_seen_frame = self.last_seen.get(identity_id, 0)

            # Heuristics for role assignment
            confidence = 0.5  # Default neutral confidence

            # Comedian typically stays on stage longer
            if stage_time > 100:  # More than ~3 seconds at 30fps
                confidence += 0.2

            # Host typically appears briefly
            if stage_time < 30:  # Less than 1 second
                confidence -= 0.2

            # Check appearance frequency
            appearances = self.count_appearances(identity_id)
            if appearances > 2:  # Multiple appearances suggests host
                role = "host"
                confidence += 0.1
            else:
                role = "comedian"
                confidence += 0.1

            # Assign role with confidence
            if abs(confidence - 0.5) > 0.2:  # Sufficient confidence
                self.identity_roles[identity_id] = role
                self.role_confidence[identity_id] = abs(confidence)

        return self.identity_roles

    def count_appearances(self, identity_id: int) -> int:
        """
        Count how many times an identity appears and disappears.

        Args:
            identity_id: Identity to check

        Returns:
            Number of appearances
        """
        # This is simplified - a more sophisticated version would
        # track actual entry/exit events
        return 1  # Placeholder

    def get_identity_info(self, identity_id: int) -> Dict:
        """
        Get detailed information about an identity.

        Args:
            identity_id: Identity to query

        Returns:
            Dictionary with identity information
        """
        if identity_id not in self.identities:
            return None

        # Get average features
        feature_history = list(self.identities[identity_id])
        if not feature_history:
            return None

        # Calculate average color histogram
        color_hists = [f['color_histogram'] for f in feature_history if 'color_histogram' in f]
        avg_color_hist = np.mean(color_hists, axis=0) if color_hists else None

        # Get average size
        size_features = [f['size_features'] for f in feature_history if 'size_features' in f]
        if size_features:
            avg_width = np.mean([s['width'] for s in size_features])
            avg_height = np.mean([s['height'] for s in size_features])
            avg_area = np.mean([s['area'] for s in size_features])
        else:
            avg_width = avg_height = avg_area = 0

        return {
            'identity_id': identity_id,
            'role': self.identity_roles.get(identity_id, 'unknown'),
            'role_confidence': self.role_confidence.get(identity_id, 0.0),
            'stage_time': self.stage_time.get(identity_id, 0),
            'last_seen': self.last_seen.get(identity_id, 0),
            'avg_color_histogram': avg_color_hist,
            'avg_size': {
                'width': avg_width,
                'height': avg_height,
                'area': avg_area
            },
            'feature_count': len(feature_history)
        }

    def cleanup_old_identities(self, current_frame: int, max_age: int = 300):
        """
        Remove identities that haven't been seen recently.

        Args:
            current_frame: Current frame number
            max_age: Maximum frames since last seen
        """
        identities_to_remove = []

        for identity_id, last_frame in self.last_seen.items():
            if current_frame - last_frame > max_age:
                identities_to_remove.append(identity_id)

        for identity_id in identities_to_remove:
            if identity_id in self.identities:
                del self.identities[identity_id]
            if identity_id in self.stage_time:
                del self.stage_time[identity_id]
            if identity_id in self.last_seen:
                del self.last_seen[identity_id]
            if identity_id in self.identity_roles:
                del self.identity_roles[identity_id]
            if identity_id in self.role_confidence:
                del self.role_confidence[identity_id]

            # Remove object mappings
            objects_to_remove = [
                obj_id for obj_id, id_val in self.object_to_identity.items()
                if id_val == identity_id
            ]
            for obj_id in objects_to_remove:
                del self.object_to_identity[obj_id]

    def get_exit_likelihood(self, identity_id: int) -> float:
        """
        Calculate likelihood that this identity is about to exit.

        Args:
            identity_id: Identity to check

        Returns:
            Exit likelihood (0-1)
        """
        role = self.identity_roles.get(identity_id, 'unknown')
        stage_time = self.stage_time.get(identity_id, 0)

        # Base likelihood on role and time
        if role == "host":
            # Hosts typically exit quickly
            if stage_time > 60:  # More than 2 seconds at 30fps
                return 0.8
            else:
                return 0.3

        elif role == "comedian":
            # Comedians typically stay longer
            if stage_time > 300:  # More than 10 seconds
                return 0.3
            else:
                return 0.1

        else:
            # Unknown role - use neutral estimate
            return 0.2