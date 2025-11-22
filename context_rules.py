#!/usr/bin/env python3
"""
Context-aware transition rules for intelligent segment detection.
Uses performance history, timing patterns, and probabilistic state machines.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
from enum import Enum
import time


class PerformanceState(Enum):
    """States in a comedy performance."""
    EMPTY_STAGE = "empty_stage"
    HOST_INTRO = "host_intro"
    COMEDIAN_ENTERING = "comedian_entering"
    COMEDIAN_PERFORMING = "comedian_performing"
    HOST_OUTRO = "host_outro"
    TRANSITION = "transition"
    APPLAUSE = "applause"


class ContextualTransitionRules:
    """
    Smart transition detection using context and history.
    """

    def __init__(self):
        """Initialize context-aware rules engine."""
        # State tracking
        self.current_state = PerformanceState.EMPTY_STAGE
        self.state_history = deque(maxlen=100)
        self.state_start_time = 0
        self.state_duration = 0

        # Performance tracking
        self.performance_segments = []
        self.current_segment = None

        # Pattern recognition
        self.typical_intro_duration = 10  # seconds
        self.typical_outro_duration = 5  # seconds
        self.min_performance_duration = 30  # seconds
        self.max_gap_between_segments = 20  # seconds

        # Confidence tracking
        self.state_confidence = 0.5
        self.transition_confidence = {}

        # Identity tracking
        self.person_durations = {}  # person_id -> list of durations
        self.person_roles = {}  # person_id -> "host" or "comedian"

    def update_state(self, person_count: int, identities: List[int], timestamp: float) -> Tuple[PerformanceState, float]:
        """
        Update performance state based on context.

        Args:
            person_count: Number of people on stage
            identities: List of identity IDs currently on stage
            timestamp: Current timestamp in seconds

        Returns:
            (new_state, confidence) tuple
        """
        # Track state duration
        if self.current_state != PerformanceState.EMPTY_STAGE:
            self.state_duration = timestamp - self.state_start_time

        # Store previous state
        prev_state = self.current_state

        # Determine new state based on context
        new_state, confidence = self._determine_state(
            person_count, identities, timestamp, prev_state
        )

        # Update state if changed
        if new_state != self.current_state:
            self.state_history.append({
                'state': self.current_state,
                'duration': self.state_duration,
                'timestamp': timestamp
            })

            self.current_state = new_state
            self.state_start_time = timestamp
            self.state_duration = 0
            self.state_confidence = confidence

            # Check for segment boundaries
            self._check_segment_boundary(prev_state, new_state, timestamp)

        return new_state, confidence

    def _determine_state(self, person_count: int, identities: List[int],
                         timestamp: float, prev_state: PerformanceState) -> Tuple[PerformanceState, float]:
        """
        Determine the most likely state based on context.

        Returns:
            (state, confidence) tuple
        """
        # Empty stage
        if person_count == 0:
            return PerformanceState.EMPTY_STAGE, 1.0

        # Single person on stage
        elif person_count == 1:
            person_id = identities[0] if identities else None

            # Check if this is a known host or comedian
            role = self.person_roles.get(person_id, None)

            # Use timing context
            if prev_state == PerformanceState.EMPTY_STAGE:
                # Someone just entered empty stage
                if role == "host":
                    return PerformanceState.HOST_INTRO, 0.8
                elif role == "comedian":
                    return PerformanceState.COMEDIAN_PERFORMING, 0.8
                else:
                    # Unknown person - guess based on timing
                    if self.state_duration < self.typical_intro_duration:
                        return PerformanceState.HOST_INTRO, 0.6
                    else:
                        return PerformanceState.COMEDIAN_PERFORMING, 0.6

            elif prev_state == PerformanceState.HOST_INTRO:
                # Host was introducing, still alone
                if self.state_duration > self.typical_intro_duration * 2:
                    # Too long for intro, probably comedian
                    return PerformanceState.COMEDIAN_PERFORMING, 0.7
                else:
                    return PerformanceState.HOST_INTRO, 0.9

            elif prev_state == PerformanceState.COMEDIAN_PERFORMING:
                # Comedian was performing, still alone
                return PerformanceState.COMEDIAN_PERFORMING, 0.95

            else:
                # Default to performing
                return PerformanceState.COMEDIAN_PERFORMING, 0.6

        # Two people on stage
        elif person_count == 2:
            # Check identities and roles
            roles = [self.person_roles.get(id, "unknown") for id in identities]

            if "host" in roles and "comedian" in roles:
                # Host and comedian together
                if prev_state == PerformanceState.COMEDIAN_PERFORMING:
                    # Host joining comedian - likely outro
                    return PerformanceState.HOST_OUTRO, 0.85
                elif prev_state == PerformanceState.EMPTY_STAGE:
                    # Both entering together
                    return PerformanceState.COMEDIAN_ENTERING, 0.7
                else:
                    return PerformanceState.TRANSITION, 0.7

            elif prev_state == PerformanceState.HOST_INTRO:
                # Host was alone, someone joined - comedian entering
                return PerformanceState.COMEDIAN_ENTERING, 0.8

            elif prev_state == PerformanceState.COMEDIAN_PERFORMING:
                # Comedian was alone, someone joined - host outro
                return PerformanceState.HOST_OUTRO, 0.8

            else:
                return PerformanceState.TRANSITION, 0.6

        # More than 2 people
        else:
            # Multiple people - likely transition or applause
            if prev_state == PerformanceState.COMEDIAN_PERFORMING:
                return PerformanceState.APPLAUSE, 0.7
            else:
                return PerformanceState.TRANSITION, 0.6

    def _check_segment_boundary(self, old_state: PerformanceState,
                                new_state: PerformanceState, timestamp: float):
        """
        Check if state transition indicates segment boundary.

        Args:
            old_state: Previous state
            new_state: New state
            timestamp: Current timestamp
        """
        # Start segment conditions
        start_conditions = [
            # Host exits, comedian alone
            (old_state == PerformanceState.COMEDIAN_ENTERING and
             new_state == PerformanceState.COMEDIAN_PERFORMING),

            # Comedian enters empty stage
            (old_state == PerformanceState.EMPTY_STAGE and
             new_state == PerformanceState.COMEDIAN_PERFORMING),

            # Transition to comedian performing
            (old_state == PerformanceState.TRANSITION and
             new_state == PerformanceState.COMEDIAN_PERFORMING),
        ]

        # End segment conditions
        end_conditions = [
            # Comedian performing to host outro
            (old_state == PerformanceState.COMEDIAN_PERFORMING and
             new_state == PerformanceState.HOST_OUTRO),

            # Comedian exits
            (old_state == PerformanceState.COMEDIAN_PERFORMING and
             new_state == PerformanceState.EMPTY_STAGE),

            # Applause after performance
            (old_state == PerformanceState.COMEDIAN_PERFORMING and
             new_state == PerformanceState.APPLAUSE),
        ]

        # Check for segment start
        if any(start_conditions):
            if self.current_segment is None:
                self.current_segment = {
                    'start_time': timestamp,
                    'start_state': new_state,
                    'events': []
                }
                print(f"Segment started at {timestamp:.2f}s")

        # Check for segment end
        elif any(end_conditions):
            if self.current_segment is not None:
                self.current_segment['end_time'] = timestamp
                self.current_segment['end_state'] = old_state
                self.current_segment['duration'] = timestamp - self.current_segment['start_time']

                # Validate segment
                if self.current_segment['duration'] >= self.min_performance_duration:
                    self.performance_segments.append(self.current_segment)
                    print(f"Segment ended at {timestamp:.2f}s (duration: {self.current_segment['duration']:.2f}s)")
                else:
                    print(f"Segment too short ({self.current_segment['duration']:.2f}s), discarding")

                self.current_segment = None

    def learn_person_role(self, person_id: int, duration_on_stage: float,
                          entry_count: int, avg_duration: float):
        """
        Learn whether a person is likely host or comedian based on behavior.

        Args:
            person_id: Person identifier
            duration_on_stage: Current duration on stage
            entry_count: Number of times person has entered stage
            avg_duration: Average duration per appearance
        """
        # Store duration history
        if person_id not in self.person_durations:
            self.person_durations[person_id] = []
        self.person_durations[person_id].append(duration_on_stage)

        # Classify based on patterns
        if entry_count > 2 and avg_duration < 30:
            # Multiple short appearances - likely host
            self.person_roles[person_id] = "host"

        elif entry_count <= 2 and avg_duration > 60:
            # Few long appearances - likely comedian
            self.person_roles[person_id] = "comedian"

        elif duration_on_stage > 120:
            # Very long single appearance - definitely comedian
            self.person_roles[person_id] = "comedian"

        elif duration_on_stage < 15 and entry_count > 1:
            # Very short repeated appearances - definitely host
            self.person_roles[person_id] = "host"

    def get_segment_confidence(self) -> float:
        """
        Get confidence in current segment detection.

        Returns:
            Confidence score (0-1)
        """
        if self.current_segment is None:
            return 0.0

        # Base confidence on state confidence
        confidence = self.state_confidence

        # Adjust based on duration
        if self.state_duration > self.min_performance_duration:
            confidence += 0.1
        elif self.state_duration < 10:
            confidence -= 0.2

        # Adjust based on state
        if self.current_state == PerformanceState.COMEDIAN_PERFORMING:
            confidence += 0.1
        elif self.current_state == PerformanceState.TRANSITION:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def predict_next_state(self) -> Tuple[PerformanceState, float]:
        """
        Predict the most likely next state.

        Returns:
            (predicted_state, probability) tuple
        """
        predictions = {}

        # Based on current state and duration
        if self.current_state == PerformanceState.EMPTY_STAGE:
            predictions[PerformanceState.HOST_INTRO] = 0.6
            predictions[PerformanceState.COMEDIAN_PERFORMING] = 0.3
            predictions[PerformanceState.EMPTY_STAGE] = 0.1

        elif self.current_state == PerformanceState.HOST_INTRO:
            if self.state_duration > self.typical_intro_duration:
                predictions[PerformanceState.COMEDIAN_ENTERING] = 0.8
                predictions[PerformanceState.COMEDIAN_PERFORMING] = 0.1
            else:
                predictions[PerformanceState.COMEDIAN_ENTERING] = 0.5
                predictions[PerformanceState.HOST_INTRO] = 0.5

        elif self.current_state == PerformanceState.COMEDIAN_PERFORMING:
            if self.state_duration > 180:  # 3 minutes
                predictions[PerformanceState.HOST_OUTRO] = 0.4
                predictions[PerformanceState.APPLAUSE] = 0.3
                predictions[PerformanceState.COMEDIAN_PERFORMING] = 0.3
            else:
                predictions[PerformanceState.COMEDIAN_PERFORMING] = 0.8
                predictions[PerformanceState.HOST_OUTRO] = 0.2

        elif self.current_state == PerformanceState.HOST_OUTRO:
            predictions[PerformanceState.EMPTY_STAGE] = 0.4
            predictions[PerformanceState.HOST_INTRO] = 0.3
            predictions[PerformanceState.APPLAUSE] = 0.3

        else:
            # Default predictions
            predictions[PerformanceState.COMEDIAN_PERFORMING] = 0.3
            predictions[PerformanceState.TRANSITION] = 0.3
            predictions[PerformanceState.EMPTY_STAGE] = 0.2
            predictions[PerformanceState.HOST_INTRO] = 0.2

        # Find most likely
        if predictions:
            best_state = max(predictions.keys(), key=lambda k: predictions[k])
            return best_state, predictions[best_state]
        else:
            return PerformanceState.TRANSITION, 0.5

    def get_segments(self) -> List[Dict]:
        """
        Get all detected performance segments.

        Returns:
            List of segment dictionaries
        """
        segments = self.performance_segments.copy()

        # Add current segment if active
        if self.current_segment is not None:
            current = self.current_segment.copy()
            current['active'] = True
            current['confidence'] = self.get_segment_confidence()
            segments.append(current)

        return segments

    def reset(self):
        """Reset all state tracking."""
        self.current_state = PerformanceState.EMPTY_STAGE
        self.state_history.clear()
        self.state_start_time = 0
        self.state_duration = 0
        self.performance_segments.clear()
        self.current_segment = None
        self.person_durations.clear()
        self.person_roles.clear()


class ProbabilisticStateMachine:
    """
    Probabilistic state machine for robust transition detection.
    """

    def __init__(self):
        """Initialize probabilistic state machine."""
        # State transition probabilities
        self.transition_matrix = self._init_transition_matrix()

        # Observation likelihoods
        self.observation_likelihoods = self._init_observation_likelihoods()

        # Current state distribution
        self.state_distribution = {
            PerformanceState.EMPTY_STAGE: 0.9,
            PerformanceState.HOST_INTRO: 0.05,
            PerformanceState.COMEDIAN_PERFORMING: 0.05
        }

    def _init_transition_matrix(self) -> Dict:
        """Initialize state transition probabilities."""
        matrix = {}

        # From EMPTY_STAGE
        matrix[PerformanceState.EMPTY_STAGE] = {
            PerformanceState.EMPTY_STAGE: 0.7,
            PerformanceState.HOST_INTRO: 0.25,
            PerformanceState.COMEDIAN_PERFORMING: 0.05
        }

        # From HOST_INTRO
        matrix[PerformanceState.HOST_INTRO] = {
            PerformanceState.HOST_INTRO: 0.3,
            PerformanceState.COMEDIAN_ENTERING: 0.5,
            PerformanceState.COMEDIAN_PERFORMING: 0.2
        }

        # From COMEDIAN_PERFORMING
        matrix[PerformanceState.COMEDIAN_PERFORMING] = {
            PerformanceState.COMEDIAN_PERFORMING: 0.8,
            PerformanceState.HOST_OUTRO: 0.1,
            PerformanceState.APPLAUSE: 0.05,
            PerformanceState.EMPTY_STAGE: 0.05
        }

        # Add other states...

        return matrix

    def _init_observation_likelihoods(self) -> Dict:
        """Initialize observation likelihoods."""
        likelihoods = {}

        # Likelihood of observing N people in each state
        likelihoods[0] = {  # 0 people
            PerformanceState.EMPTY_STAGE: 0.99,
            PerformanceState.HOST_INTRO: 0.01,
            PerformanceState.COMEDIAN_PERFORMING: 0.01
        }

        likelihoods[1] = {  # 1 person
            PerformanceState.EMPTY_STAGE: 0.01,
            PerformanceState.HOST_INTRO: 0.4,
            PerformanceState.COMEDIAN_PERFORMING: 0.8
        }

        likelihoods[2] = {  # 2 people
            PerformanceState.EMPTY_STAGE: 0.01,
            PerformanceState.HOST_INTRO: 0.1,
            PerformanceState.COMEDIAN_ENTERING: 0.8,
            PerformanceState.HOST_OUTRO: 0.8
        }

        return likelihoods

    def update(self, observation: int) -> PerformanceState:
        """
        Update state distribution based on observation.

        Args:
            observation: Number of people observed

        Returns:
            Most likely current state
        """
        # Predict step (apply transition model)
        predicted_distribution = {}

        for next_state in PerformanceState:
            prob = 0
            for current_state in self.state_distribution:
                if current_state in self.transition_matrix:
                    transitions = self.transition_matrix[current_state]
                    if next_state in transitions:
                        prob += self.state_distribution[current_state] * transitions[next_state]

            predicted_distribution[next_state] = prob

        # Update step (apply observation model)
        updated_distribution = {}

        if observation in self.observation_likelihoods:
            likelihoods = self.observation_likelihoods[observation]

            # Bayes rule
            total_likelihood = 0
            for state in predicted_distribution:
                if state in likelihoods:
                    likelihood = likelihoods[state] * predicted_distribution[state]
                    updated_distribution[state] = likelihood
                    total_likelihood += likelihood

            # Normalize
            if total_likelihood > 0:
                for state in updated_distribution:
                    updated_distribution[state] /= total_likelihood
            else:
                updated_distribution = predicted_distribution
        else:
            updated_distribution = predicted_distribution

        self.state_distribution = updated_distribution

        # Return most likely state
        if updated_distribution:
            return max(updated_distribution.keys(), key=lambda k: updated_distribution[k])
        else:
            return PerformanceState.EMPTY_STAGE