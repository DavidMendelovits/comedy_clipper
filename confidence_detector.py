#!/usr/bin/env python3
"""
Confidence-based detection system that combines multiple signals.
Provides probabilistic exit detection with confidence scores.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
from dataclasses import dataclass
import time


@dataclass
class DetectionSignal:
    """A single detection signal with confidence."""
    signal_type: str  # "position", "velocity", "zone", "appearance", "context"
    value: float  # Signal value
    confidence: float  # Confidence in this signal (0-1)
    timestamp: float
    metadata: Dict = None


class ConfidenceBasedDetector:
    """
    Combines multiple detection signals to provide confident exit detection.
    """

    def __init__(self):
        """Initialize confidence-based detector."""
        # Signal weights (can be tuned)
        self.signal_weights = {
            'position': 0.15,
            'velocity': 0.25,
            'zone': 0.20,
            'appearance': 0.20,
            'context': 0.20
        }

        # Signal history
        self.signal_history = deque(maxlen=100)

        # Detection thresholds
        self.exit_threshold = 0.7
        self.enter_threshold = 0.7
        self.confidence_decay = 0.95  # Per frame

        # Tracking
        self.person_states = {}  # person_id -> state_info
        self.exit_events = []
        self.enter_events = []

    def add_signal(self, person_id: int, signal: DetectionSignal):
        """
        Add a detection signal for a person.

        Args:
            person_id: Person identifier
            signal: Detection signal to add
        """
        if person_id not in self.person_states:
            self.person_states[person_id] = {
                'signals': deque(maxlen=30),
                'exit_confidence': 0.0,
                'enter_confidence': 0.0,
                'stage_confidence': 1.0,
                'last_update': signal.timestamp
            }

        self.person_states[person_id]['signals'].append(signal)
        self.person_states[person_id]['last_update'] = signal.timestamp
        self.signal_history.append((person_id, signal))

    def update_position_signal(self, person_id: int, x: float, y: float,
                               frame_width: int, frame_height: int, timestamp: float):
        """
        Update position-based signal.

        Args:
            person_id: Person identifier
            x, y: Position coordinates
            frame_width, frame_height: Frame dimensions
            timestamp: Current timestamp
        """
        # Normalize position
        norm_x = x / frame_width
        norm_y = y / frame_height

        # Calculate distance to edges
        edge_distances = [
            norm_x,  # Left edge
            1 - norm_x,  # Right edge
            norm_y,  # Top edge
            1 - norm_y  # Bottom edge
        ]
        min_edge_distance = min(edge_distances)

        # Position signal: closer to edge = higher signal
        position_value = 1.0 - min_edge_distance

        # Confidence based on stability
        confidence = 0.8  # Base confidence for position

        signal = DetectionSignal(
            signal_type='position',
            value=position_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata={'x': norm_x, 'y': norm_y, 'edge_distance': min_edge_distance}
        )

        self.add_signal(person_id, signal)

    def update_velocity_signal(self, person_id: int, vx: float, vy: float,
                               x: float, y: float, frame_width: int, frame_height: int,
                               timestamp: float):
        """
        Update velocity-based signal.

        Args:
            person_id: Person identifier
            vx, vy: Velocity components
            x, y: Current position
            frame_width, frame_height: Frame dimensions
            timestamp: Current timestamp
        """
        # Normalize position
        norm_x = x / frame_width
        norm_y = y / frame_height

        # Check which edge person is moving toward
        velocity_magnitude = np.sqrt(vx**2 + vy**2)

        # Determine if moving toward nearest edge
        moving_toward_edge = False
        edge_velocity = 0

        if norm_x < 0.2 and vx < 0:  # Near left, moving left
            edge_velocity = abs(vx)
            moving_toward_edge = True
        elif norm_x > 0.8 and vx > 0:  # Near right, moving right
            edge_velocity = abs(vx)
            moving_toward_edge = True
        elif norm_y < 0.2 and vy < 0:  # Near top, moving up
            edge_velocity = abs(vy)
            moving_toward_edge = True
        elif norm_y > 0.8 and vy > 0:  # Near bottom, moving down
            edge_velocity = abs(vy)
            moving_toward_edge = True

        # Velocity signal
        if moving_toward_edge:
            velocity_value = min(1.0, edge_velocity / 30.0)  # Normalize by typical exit speed
            confidence = min(1.0, velocity_magnitude / 20.0)
        else:
            velocity_value = 0.0
            confidence = 0.5

        signal = DetectionSignal(
            signal_type='velocity',
            value=velocity_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata={'vx': vx, 'vy': vy, 'magnitude': velocity_magnitude}
        )

        self.add_signal(person_id, signal)

    def update_zone_signal(self, person_id: int, zone_state: str,
                           zone_confidence: float, timestamp: float):
        """
        Update zone-based signal.

        Args:
            person_id: Person identifier
            zone_state: "inside", "outside", "boundary"
            zone_confidence: Confidence in zone state
            timestamp: Current timestamp
        """
        # Zone signal
        if zone_state == "outside":
            zone_value = 1.0
        elif zone_state == "boundary":
            zone_value = 0.5
        else:  # inside
            zone_value = 0.0

        signal = DetectionSignal(
            signal_type='zone',
            value=zone_value,
            confidence=zone_confidence,
            timestamp=timestamp,
            metadata={'zone_state': zone_state}
        )

        self.add_signal(person_id, signal)

    def update_appearance_signal(self, person_id: int, visibility: float,
                                 size_change: float, timestamp: float):
        """
        Update appearance-based signal.

        Args:
            person_id: Person identifier
            visibility: Visibility score (0-1)
            size_change: Relative size change (negative = shrinking)
            timestamp: Current timestamp
        """
        # Appearance signal: low visibility or shrinking = likely exiting
        if visibility < 0.3:
            appearance_value = 0.8
        elif size_change < -0.2:  # Shrinking significantly
            appearance_value = 0.6
        else:
            appearance_value = 0.0

        confidence = 0.7  # Moderate confidence for appearance

        signal = DetectionSignal(
            signal_type='appearance',
            value=appearance_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata={'visibility': visibility, 'size_change': size_change}
        )

        self.add_signal(person_id, signal)

    def update_context_signal(self, person_id: int, performance_state: str,
                             role: str, stage_time: float, timestamp: float):
        """
        Update context-based signal.

        Args:
            person_id: Person identifier
            performance_state: Current performance state
            role: "host" or "comedian"
            stage_time: Time on stage in seconds
            timestamp: Current timestamp
        """
        # Context signal based on role and timing
        context_value = 0.0
        confidence = 0.5

        if role == "host":
            if stage_time > 15:  # Host on stage too long
                context_value = 0.7
                confidence = 0.8
        elif role == "comedian":
            if performance_state == "host_outro":
                context_value = 0.6
                confidence = 0.7
            elif stage_time > 300:  # 5+ minutes
                context_value = 0.3
                confidence = 0.6

        signal = DetectionSignal(
            signal_type='context',
            value=context_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata={'performance_state': performance_state, 'role': role, 'stage_time': stage_time}
        )

        self.add_signal(person_id, signal)

    def calculate_exit_confidence(self, person_id: int) -> float:
        """
        Calculate overall exit confidence for a person.

        Args:
            person_id: Person identifier

        Returns:
            Exit confidence (0-1)
        """
        if person_id not in self.person_states:
            return 0.0

        signals = list(self.person_states[person_id]['signals'])
        if not signals:
            return 0.0

        # Group signals by type
        signal_groups = {}
        for signal in signals:
            if signal.signal_type not in signal_groups:
                signal_groups[signal.signal_type] = []
            signal_groups[signal.signal_type].append(signal)

        # Calculate weighted average for each signal type
        weighted_scores = {}
        total_weight = 0

        for signal_type, weight in self.signal_weights.items():
            if signal_type in signal_groups:
                # Get recent signals of this type
                recent_signals = signal_groups[signal_type][-5:]

                # Calculate weighted average value
                if recent_signals:
                    values = [s.value * s.confidence for s in recent_signals]
                    confidences = [s.confidence for s in recent_signals]

                    avg_value = np.mean(values)
                    avg_confidence = np.mean(confidences)

                    weighted_scores[signal_type] = avg_value * avg_confidence * weight
                    total_weight += weight

        # Calculate overall confidence
        if total_weight > 0:
            exit_confidence = sum(weighted_scores.values()) / total_weight
        else:
            exit_confidence = 0.0

        # Apply temporal smoothing
        old_confidence = self.person_states[person_id]['exit_confidence']
        smoothed_confidence = 0.7 * exit_confidence + 0.3 * old_confidence

        self.person_states[person_id]['exit_confidence'] = smoothed_confidence

        return smoothed_confidence

    def calculate_stage_presence_confidence(self, person_id: int) -> float:
        """
        Calculate confidence that person is still on stage.

        Args:
            person_id: Person identifier

        Returns:
            Stage presence confidence (0-1)
        """
        exit_confidence = self.calculate_exit_confidence(person_id)
        stage_confidence = 1.0 - exit_confidence

        # Apply decay if no recent updates
        if person_id in self.person_states:
            last_update = self.person_states[person_id]['last_update']
            current_time = time.time()
            time_since_update = current_time - last_update

            if time_since_update > 1.0:  # More than 1 second
                decay_factor = self.confidence_decay ** time_since_update
                stage_confidence *= decay_factor

        self.person_states[person_id]['stage_confidence'] = stage_confidence
        return stage_confidence

    def detect_exits(self, timestamp: float) -> List[Tuple[int, float]]:
        """
        Detect exit events based on confidence thresholds.

        Args:
            timestamp: Current timestamp

        Returns:
            List of (person_id, confidence) tuples for detected exits
        """
        exits = []

        for person_id, state in self.person_states.items():
            exit_confidence = self.calculate_exit_confidence(person_id)

            if exit_confidence > self.exit_threshold:
                exits.append((person_id, exit_confidence))

                # Record exit event
                self.exit_events.append({
                    'person_id': person_id,
                    'timestamp': timestamp,
                    'confidence': exit_confidence,
                    'signals': list(state['signals'])
                })

        return exits

    def detect_entries(self, timestamp: float) -> List[Tuple[int, float]]:
        """
        Detect entry events based on confidence thresholds.

        Args:
            timestamp: Current timestamp

        Returns:
            List of (person_id, confidence) tuples for detected entries
        """
        entries = []

        for person_id, state in self.person_states.items():
            # Entry detection logic (inverse of exit)
            enter_confidence = state.get('enter_confidence', 0.0)

            if enter_confidence > self.enter_threshold:
                entries.append((person_id, enter_confidence))

                # Record entry event
                self.enter_events.append({
                    'person_id': person_id,
                    'timestamp': timestamp,
                    'confidence': enter_confidence,
                    'signals': list(state['signals'])
                })

        return entries

    def get_person_status(self, person_id: int) -> Dict:
        """
        Get detailed status for a person.

        Args:
            person_id: Person identifier

        Returns:
            Dictionary with person status
        """
        if person_id not in self.person_states:
            return {
                'person_id': person_id,
                'status': 'unknown',
                'exit_confidence': 0.0,
                'stage_confidence': 0.0,
                'signals': []
            }

        state = self.person_states[person_id]

        # Determine status based on confidences
        exit_conf = state['exit_confidence']
        stage_conf = state['stage_confidence']

        if exit_conf > 0.8:
            status = 'exiting'
        elif exit_conf > 0.5:
            status = 'likely_exiting'
        elif stage_conf > 0.8:
            status = 'on_stage'
        elif stage_conf > 0.5:
            status = 'likely_on_stage'
        else:
            status = 'uncertain'

        # Get recent signals
        recent_signals = list(state['signals'])[-10:]

        return {
            'person_id': person_id,
            'status': status,
            'exit_confidence': exit_conf,
            'stage_confidence': stage_conf,
            'enter_confidence': state.get('enter_confidence', 0.0),
            'last_update': state['last_update'],
            'recent_signals': recent_signals,
            'signal_summary': self._summarize_signals(recent_signals)
        }

    def _summarize_signals(self, signals: List[DetectionSignal]) -> Dict:
        """
        Summarize a list of signals.

        Args:
            signals: List of detection signals

        Returns:
            Summary dictionary
        """
        if not signals:
            return {}

        summary = {}

        # Group by type
        by_type = {}
        for signal in signals:
            if signal.signal_type not in by_type:
                by_type[signal.signal_type] = []
            by_type[signal.signal_type].append(signal)

        # Summarize each type
        for signal_type, type_signals in by_type.items():
            values = [s.value for s in type_signals]
            confidences = [s.confidence for s in type_signals]

            summary[signal_type] = {
                'avg_value': np.mean(values),
                'max_value': np.max(values),
                'avg_confidence': np.mean(confidences),
                'count': len(type_signals)
            }

        return summary

    def reset_person(self, person_id: int):
        """Reset tracking for a person."""
        if person_id in self.person_states:
            del self.person_states[person_id]

    def get_all_statuses(self) -> List[Dict]:
        """Get status for all tracked persons."""
        return [self.get_person_status(pid) for pid in self.person_states.keys()]