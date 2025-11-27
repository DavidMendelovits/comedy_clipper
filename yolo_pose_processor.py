#!/usr/bin/env python3
"""
YOLO Pose Video Processor
Detects pose entry/exit events in parallel video chunks
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("ERROR: OpenCV not installed. Run: pip install opencv-python", file=sys.stderr)
    sys.exit(1)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("ERROR: Ultralytics not installed. Run: pip install ultralytics", file=sys.stderr)
    sys.exit(1)


@dataclass
class PoseEvent:
    """Represents a pose enter/exit event"""
    timestamp: float
    event_type: str  # 'enter' or 'exit'
    person_id: int
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    keypoints: List[Tuple[float, float, float]]  # [(x, y, conf), ...]


@dataclass
class VideoChunk:
    """Represents a video chunk to process"""
    index: int
    start_time: float
    end_time: float
    duration: float
    file_path: str


class TrackedPerson:
    """Represents a tracked person with state management for ID stability"""

    def __init__(self, person_id: int, bbox: Tuple[float, float, float, float],
                 keypoints: List[Tuple[float, float, float]], timestamp: float,
                 entry_edge: str = None):
        self.person_id = person_id
        self.last_bbox = bbox
        self.last_keypoints = keypoints
        self.frames_missing = 0
        self.state = 'pending'  # 'pending', 'active', 'dormant', 'exited'
        self.last_seen_timestamp = timestamp
        self.first_seen_timestamp = timestamp
        self.consecutive_detections = 1  # Count of consecutive frames detected
        self.entry_edge = entry_edge  # 'left', 'right', 'top', 'bottom', or None
        self.enter_event_emitted = False  # Has the enter event been emitted?
        self.last_confidence = 0.0  # Track detection confidence

    def update(self, bbox: Tuple[float, float, float, float],
               keypoints: List[Tuple[float, float, float]], timestamp: float,
               confidence: float = 0.0):
        """Update person with new detection"""
        self.last_bbox = bbox
        self.last_keypoints = keypoints
        self.frames_missing = 0
        self.consecutive_detections += 1
        self.last_seen_timestamp = timestamp
        self.last_confidence = confidence
        # Transition from pending to active handled externally based on time

    def mark_missing(self):
        """Increment missing frame counter and reset consecutive detections"""
        self.frames_missing += 1
        self.consecutive_detections = 0

    def get_center(self) -> Tuple[float, float]:
        """Get center point of last known bounding box"""
        x1, y1, x2, y2 = self.last_bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def get_bbox_area(self) -> float:
        """Get bounding box area"""
        x1, y1, x2, y2 = self.last_bbox
        return (x2 - x1) * (y2 - y1)


class YOLOPoseProcessor:
    """Process video with YOLO pose detection in parallel chunks"""

    CHUNK_DURATION = 30.0  # 30 seconds per chunk
    CONFIDENCE_THRESHOLD = 0.5  # Detection confidence threshold (relaxed from 0.6)
    NMS_IOU_THRESHOLD = 0.45  # Non-Maximum Suppression IOU threshold
    MIN_VISIBLE_KEYPOINTS = 7  # Minimum visible keypoints required (was 6)
    MIN_DETECTION_CONFIDENCE = 0.50  # Minimum per-detection box confidence (relaxed from 0.65)
    KEYPOINT_CONFIDENCE_THRESHOLD = 0.30  # Keypoint confidence threshold (relaxed from 0.45)
    MIN_ASPECT_RATIO = 1.3  # Minimum bbox height/width ratio (relaxed from 1.5)
    MAX_ASPECT_RATIO = 3.2  # Maximum bbox height/width ratio (relaxed from 2.8)
    MIN_KEYPOINT_COVERAGE = 0.30  # Minimum keypoint coverage fraction (was 0.20)
    MIN_VERTICAL_KEYPOINT_SPAN = 0.50  # Keypoints must span 50% of bbox height (filters head-only detections)
    SAMPLE_RATE = 10  # Process every 10th frame (3 fps at 30fps video, was 30)
    EXIT_STABILITY_FRAMES = 5  # Require person absent for N frames before exit (was 3)
    EXIT_EDGE_THRESHOLD = 0.20  # Person must be within 20% of frame edge to confirm exit (was 15%)
    DORMANT_TIMEOUT_SECONDS = 10.0  # Keep dormant persons for 10 seconds before cleanup (was 30s)

    # Smart tracking for static camera comedy shows
    AUDIENCE_ZONE_THRESHOLD = 0.25  # Ignore detections in bottom 25% of frame (audience heads)
    PRIMARY_PERFORMER_ONLY = True  # Only track the largest detection (the comedian)
    ENTER_STABILITY_SECONDS = 1.5  # Require presence for 1.5s before emitting enter event
    EXIT_STABILITY_SECONDS = 2.0  # Require absence for 2.0s before emitting exit event
    VALID_ENTRY_EDGES = ['left', 'right']  # Valid entry directions (stage wings, not audience)

    def __init__(self, video_path: str, model_name: str = "yolo11m-pose.pt",
                 confidence_threshold: float = None, nms_iou_threshold: float = None,
                 min_visible_keypoints: int = None, exit_stability_frames: int = None,
                 min_detection_conf: float = None, keypoint_conf: float = None,
                 min_aspect_ratio: float = None, max_aspect_ratio: float = None,
                 min_keypoint_coverage: float = None):
        """
        Initialize processor

        Args:
            video_path: Path to input video
            model_name: YOLO pose model to use
            confidence_threshold: Override default confidence threshold
            nms_iou_threshold: Override default NMS IOU threshold
            min_visible_keypoints: Override default minimum visible keypoints
            exit_stability_frames: Override default exit stability frames
            min_detection_conf: Override default minimum detection box confidence
            keypoint_conf: Override default keypoint confidence threshold
            min_aspect_ratio: Override default minimum aspect ratio
            max_aspect_ratio: Override default maximum aspect ratio
            min_keypoint_coverage: Override default minimum keypoint coverage
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        self.video_path = video_path
        self.model_name = model_name
        self.video_name = Path(video_path).stem

        # Override class constants if provided
        if confidence_threshold is not None:
            self.CONFIDENCE_THRESHOLD = confidence_threshold
        if nms_iou_threshold is not None:
            self.NMS_IOU_THRESHOLD = nms_iou_threshold
        if min_visible_keypoints is not None:
            self.MIN_VISIBLE_KEYPOINTS = min_visible_keypoints
        if exit_stability_frames is not None:
            self.EXIT_STABILITY_FRAMES = exit_stability_frames
        if min_detection_conf is not None:
            self.MIN_DETECTION_CONFIDENCE = min_detection_conf
        if keypoint_conf is not None:
            self.KEYPOINT_CONFIDENCE_THRESHOLD = keypoint_conf
        if min_aspect_ratio is not None:
            self.MIN_ASPECT_RATIO = min_aspect_ratio
        if max_aspect_ratio is not None:
            self.MAX_ASPECT_RATIO = max_aspect_ratio
        if min_keypoint_coverage is not None:
            self.MIN_KEYPOINT_COVERAGE = min_keypoint_coverage

        # Get video metadata
        self.fps, self.total_frames, self.duration, self.width, self.height = self._get_video_info()

        # Calculate chunks
        self.num_chunks = int(np.ceil(self.duration / self.CHUNK_DURATION))

        # Create temp directory for chunks and cache
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"pose_processing_{self.video_name}_"))
        self.cache_dir = self.temp_dir / "pose_cache"
        self.cache_dir.mkdir(exist_ok=True)

        print(f"Video: {self.video_name}", flush=True)
        print(f"  Duration: {self.duration:.1f}s", flush=True)
        print(f"  Resolution: {self.width}x{self.height}", flush=True)
        print(f"  FPS: {self.fps:.1f}", flush=True)
        print(f"  Total frames: {self.total_frames}", flush=True)
        print(f"  Chunks: {self.num_chunks} x {self.CHUNK_DURATION}s", flush=True)
        print(f"  Temp directory: {self.temp_dir}", flush=True)

    def _get_video_info(self) -> Tuple[float, int, float, int, int]:
        """Extract video metadata using OpenCV"""
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return fps, total_frames, duration, width, height

    def _emit_progress(self, phase: str, percent: int, message: str = None,
                      current: int = None, total: int = None):
        """Emit structured progress JSON for IPC"""
        progress_data = {
            "type": "progress",
            "phase": phase,
            "percent": percent
        }
        if message:
            progress_data["message"] = message
        if current is not None:
            progress_data["current"] = current
        if total is not None:
            progress_data["total"] = total

        print(f"[PROGRESS] {json.dumps(progress_data)}", flush=True)

    def _split_video_into_chunks(self) -> List[VideoChunk]:
        """Split video into 30-second chunks using FFmpeg"""
        print("\n[STEP] Splitting video into chunks...", flush=True)
        self._emit_progress("chunking", 0, "Splitting video into chunks")

        chunks = []
        chunks_dir = self.temp_dir / "chunks"
        chunks_dir.mkdir(exist_ok=True)

        for i in range(self.num_chunks):
            start_time = i * self.CHUNK_DURATION
            end_time = min((i + 1) * self.CHUNK_DURATION, self.duration)
            duration = end_time - start_time

            chunk_path = chunks_dir / f"chunk_{i:04d}.mp4"

            # FFmpeg command to extract chunk
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', self.video_path,
                '-t', str(duration),
                '-c', 'copy',  # Fast copy, no re-encoding
                '-avoid_negative_ts', 'make_zero',
                str(chunk_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Warning: Failed to create chunk {i}: {result.stderr}", file=sys.stderr)
                continue

            chunks.append(VideoChunk(
                index=i,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                file_path=str(chunk_path)
            ))

            progress = int(((i + 1) / self.num_chunks) * 100)
            self._emit_progress("chunking", progress, f"Created chunk {i+1}/{self.num_chunks}",
                              i+1, self.num_chunks)

        print(f"  Created {len(chunks)} chunks", flush=True)
        return chunks

    def _process_chunk(self, chunk: VideoChunk, model_name: str) -> Tuple[int, List[PoseEvent], Dict]:
        """
        Process a single chunk with YOLO pose detection

        Args:
            chunk: Video chunk to process
            model_name: YOLO model name

        Returns:
            Tuple of (chunk_index, events, pose_metadata)
        """
        # Load YOLO model (each process gets its own instance)
        model = YOLO(model_name)

        cap = cv2.VideoCapture(chunk.file_path)
        chunk_fps = cap.get(cv2.CAP_PROP_FPS)

        events = []
        pose_metadata = {}

        # Track persons with state management (active, dormant, exited)
        tracked_persons: Dict[int, TrackedPerson] = {}  # person_id -> TrackedPerson
        next_person_id = 0

        frame_num = 0
        checked_frames = 0

        # Get frame dimensions for exit validation
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames (every SAMPLE_RATE frames)
            if frame_num % self.SAMPLE_RATE == 0:
                # Global timestamp in video
                global_timestamp = chunk.start_time + (frame_num / chunk_fps)

                # Run YOLO pose detection with NMS filtering
                results = model(frame, conf=self.CONFIDENCE_THRESHOLD, iou=self.NMS_IOU_THRESHOLD, verbose=False)

                detected_persons = []

                if len(results) > 0 and hasattr(results[0], 'keypoints') and results[0].keypoints is not None:
                    keypoints = results[0].keypoints
                    boxes = results[0].boxes

                    if keypoints.xy is not None and boxes is not None:
                        num_detections = len(keypoints.xy)

                        for det_idx in range(num_detections):
                            # Get bounding box
                            bbox_tensor = boxes.xyxy[det_idx]
                            bbox = (
                                float(bbox_tensor[0]),
                                float(bbox_tensor[1]),
                                float(bbox_tensor[2]),
                                float(bbox_tensor[3])
                            )

                            # Get keypoints
                            kpts = keypoints.xy[det_idx]
                            kpts_conf = keypoints.conf[det_idx] if keypoints.conf is not None else None

                            # Convert keypoints to list format
                            kpts_list = []
                            for kpt_idx in range(len(kpts)):
                                x, y = float(kpts[kpt_idx][0]), float(kpts[kpt_idx][1])
                                conf = float(kpts_conf[kpt_idx]) if kpts_conf is not None else 1.0
                                kpts_list.append((x, y, conf))

                            # Average confidence from keypoints
                            avg_conf = np.mean([kp[2] for kp in kpts_list if kp[0] > 0 and kp[1] > 0])

                            # FILTERING: Validate detection quality to reduce false positives

                            # 0. Extract and validate detection box confidence (NEW)
                            det_conf = boxes.conf[det_idx].item() if hasattr(boxes, 'conf') and boxes.conf is not None else 1.0
                            if det_conf < self.MIN_DETECTION_CONFIDENCE:
                                continue  # Skip low-confidence detections

                            # 1. Filter by visible keypoints (must have enough keypoints with good confidence)
                            # UPDATED: Use configurable threshold instead of hardcoded 0.3
                            visible_kpts = sum(1 for kp in kpts_list if kp[0] > 0 and kp[1] > 0 and kp[2] > self.KEYPOINT_CONFIDENCE_THRESHOLD)
                            if visible_kpts < self.MIN_VISIBLE_KEYPOINTS:
                                continue  # Skip detections with too few visible keypoints

                            # 2. Filter by bounding box size and aspect ratio
                            bbox_width = bbox[2] - bbox[0]
                            bbox_height = bbox[3] - bbox[1]
                            bbox_area = bbox_width * bbox_height
                            frame_area = frame.shape[0] * frame.shape[1]

                            # Skip tiny detections (< 2% of frame area) - likely noise or audience heads
                            if bbox_area < (frame_area * 0.02):
                                continue

                            # Skip unrealistic aspect ratios (UPDATED: tightened range 1.5-2.8)
                            aspect_ratio = bbox_height / bbox_width if bbox_width > 0 else 0
                            if aspect_ratio < self.MIN_ASPECT_RATIO or aspect_ratio > self.MAX_ASPECT_RATIO:
                                continue  # Skip if too wide or impossibly tall

                            # 3. Keypoint clustering check - ensure keypoints are spatially grouped
                            valid_keypoints = [(x, y) for x, y, c in kpts_list if c > self.KEYPOINT_CONFIDENCE_THRESHOLD]
                            if len(valid_keypoints) >= 2:
                                kp_xs = [x for x, y in valid_keypoints]
                                kp_ys = [y for x, y in valid_keypoints]
                                kp_width = max(kp_xs) - min(kp_xs)
                                kp_height = max(kp_ys) - min(kp_ys)
                                kp_coverage = (kp_width * kp_height) / (bbox_width * bbox_height) if bbox_width > 0 and bbox_height > 0 else 0
                                if kp_coverage < self.MIN_KEYPOINT_COVERAGE:
                                    continue  # Skip if keypoints don't cover enough of the bounding box

                                # 4. Vertical keypoint span check - filter out head-only detections
                                # Heads have keypoints clustered at top (~30-40% span)
                                # Bodies (even with feet cut off) have keypoints spanning head to hips (~70-90%)
                                vertical_span = kp_height / bbox_height if bbox_height > 0 else 0
                                if vertical_span < self.MIN_VERTICAL_KEYPOINT_SPAN:
                                    continue  # Skip - likely just a head (audience member)

                            detected_persons.append({
                                'bbox': bbox,
                                'keypoints': kpts_list,
                                'confidence': float(avg_conf),
                                'bbox_area': bbox_area
                            })

                # SMART FILTERING: Audience zone and primary performer selection

                # 1. Filter out detections in audience zone (bottom of frame)
                detected_persons = [
                    p for p in detected_persons
                    if not self._is_in_audience_zone(p['bbox'], frame_height)
                ]

                # 2. Primary performer selection: only keep the largest detection
                if self.PRIMARY_PERFORMER_ONLY and len(detected_persons) > 1:
                    # Sort by bbox area descending, keep only the largest
                    detected_persons.sort(key=lambda p: p['bbox_area'], reverse=True)
                    detected_persons = detected_persons[:1]
                    # Log that we're filtering to primary
                    if len(detected_persons) == 1:
                        print(f"    [Primary] Selected largest detection (area={detected_persons[0]['bbox_area']:.0f})", flush=True)

                # Match detected persons to tracked persons (including dormant)
                current_frame_persons = set()  # Set of person_ids detected this frame

                for detection in detected_persons:
                    bbox = detection['bbox']
                    keypoints = detection['keypoints']

                    # Try to match with existing person (active or dormant)
                    matched_id = self._match_detection_to_person(bbox, tracked_persons, frame_width)

                    if matched_id is not None:
                        # Update existing person
                        person = tracked_persons[matched_id]
                        was_dormant = person.state == 'dormant'
                        was_pending = person.state == 'pending'
                        person.update(bbox, keypoints, global_timestamp, detection['confidence'])
                        current_frame_persons.add(matched_id)

                        # If re-activated from dormant, reset to pending
                        if was_dormant:
                            person.state = 'pending'
                            person.first_seen_timestamp = global_timestamp
                            print(f"  [Re-activated] Person {matched_id} at {global_timestamp:.2f}s (back to pending)", flush=True)

                        # Check if pending person should transition to active (temporal hysteresis)
                        if person.state == 'pending' and not person.enter_event_emitted:
                            presence_duration = global_timestamp - person.first_seen_timestamp
                            if presence_duration >= self.ENTER_STABILITY_SECONDS:
                                # Person has been present long enough - emit enter event
                                person.state = 'active'
                                person.enter_event_emitted = True

                                events.append(PoseEvent(
                                    timestamp=person.first_seen_timestamp,  # Use first seen time
                                    event_type='enter',
                                    person_id=matched_id,
                                    confidence=person.last_confidence,
                                    bbox=person.last_bbox,
                                    keypoints=person.last_keypoints
                                ))
                                print(f"  [ENTER confirmed] Person {matched_id} at {person.first_seen_timestamp:.2f}s (stable for {presence_duration:.1f}s)", flush=True)
                    else:
                        # New person detected - determine entry edge
                        entry_edge = self._get_entry_edge(bbox, frame_width, frame_height)

                        # Validate entry direction (must be from valid edges, not audience)
                        if entry_edge is not None and entry_edge not in self.VALID_ENTRY_EDGES:
                            print(f"    [Ignored] Detection entered from '{entry_edge}' (invalid entry direction)", flush=True)
                            continue  # Skip this detection

                        # Create new TrackedPerson in pending state
                        person_id = next_person_id
                        next_person_id += 1

                        new_person = TrackedPerson(person_id, bbox, keypoints, global_timestamp, entry_edge)
                        new_person.last_confidence = detection['confidence']
                        tracked_persons[person_id] = new_person
                        current_frame_persons.add(person_id)

                        print(f"  [Pending] New person {person_id} at {global_timestamp:.2f}s (entry_edge={entry_edge})", flush=True)
                        # Don't emit ENTER event yet - wait for temporal hysteresis

                # Check for persons who weren't detected this frame
                for person_id, person in tracked_persons.items():
                    if person_id not in current_frame_persons and person.state != 'exited':
                        # Person not detected - increment missing counter
                        person.mark_missing()

                        # Calculate how long they've been missing
                        missing_duration = global_timestamp - person.last_seen_timestamp

                        # For pending persons (enter not yet emitted), just drop them
                        if person.state == 'pending' and not person.enter_event_emitted:
                            if missing_duration > self.ENTER_STABILITY_SECONDS:
                                # Pending person disappeared before stabilizing - just remove
                                person.state = 'exited'
                                print(f"  [Dropped] Pending person {person_id} never stabilized (missing {missing_duration:.1f}s)", flush=True)
                            continue

                        # For active persons, use temporal hysteresis for exits
                        if missing_duration >= self.EXIT_STABILITY_SECONDS:
                            # Check if this is a valid exit (near frame edge)
                            if self._is_valid_exit(person.last_bbox, frame_width, frame_height):
                                # Valid exit - person was near edge
                                person.state = 'exited'
                                events.append(PoseEvent(
                                    timestamp=person.last_seen_timestamp,  # Use last seen time
                                    event_type='exit',
                                    person_id=person_id,
                                    confidence=1.0,
                                    bbox=person.last_bbox,
                                    keypoints=[]
                                ))
                                print(f"  [EXIT confirmed] Person {person_id} at {person.last_seen_timestamp:.2f}s (absent for {missing_duration:.1f}s)", flush=True)
                            else:
                                # Invalid exit - person disappeared mid-frame
                                # Mark as dormant, don't emit exit event
                                person.state = 'dormant'
                                print(f"  [Dormant] Person {person_id} - not near edge after {missing_duration:.1f}s, keeping for re-match", flush=True)

                # Cleanup old dormant persons - emit exit events for timed-out dormant persons
                for person_id in list(tracked_persons.keys()):
                    person = tracked_persons[person_id]
                    if person.state == 'dormant':
                        dormant_duration = global_timestamp - person.last_seen_timestamp
                        if dormant_duration > self.DORMANT_TIMEOUT_SECONDS:
                            # Person has been dormant too long, assume they actually left
                            person.state = 'exited'
                            # Only emit exit if enter was emitted
                            if person.enter_event_emitted:
                                events.append(PoseEvent(
                                    timestamp=person.last_seen_timestamp,  # Use last seen time as exit time
                                    event_type='exit',
                                    person_id=person_id,
                                    confidence=0.7,  # Lower confidence for timeout-based exit
                                    bbox=person.last_bbox,
                                    keypoints=[]
                                ))
                                print(f"  [Exit from dormant] Person {person_id} timed out at {person.last_seen_timestamp:.2f}s", flush=True)
                            else:
                                print(f"  [Dropped dormant] Person {person_id} never confirmed, removing", flush=True)

                # Store pose metadata for this frame (active and pending persons for visualization)
                active_persons_for_metadata = {
                    pid: p for pid, p in tracked_persons.items()
                    if p.state in ('active', 'pending')
                }
                pose_metadata[global_timestamp] = {
                    'frame_num': frame_num,
                    'detections': [
                        {
                            'person_id': pid,
                            'bbox': person.last_bbox,
                            'keypoints': person.last_keypoints
                        }
                        for pid, person in active_persons_for_metadata.items()
                    ]
                }

                checked_frames += 1

            frame_num += 1

        cap.release()

        # Handle persons still tracked at end of chunk
        # Only emit exit events for CONFIRMED persons (enter_event_emitted=True)
        # Skip pending persons and persons who never stabilized
        for person_id, person in tracked_persons.items():
            # Only emit exits for persons whose enter was confirmed
            if not person.enter_event_emitted:
                if person.state != 'exited':
                    print(f"  [End of chunk - dropped] Pending person {person_id} never confirmed", flush=True)
                continue

            if person.state == 'dormant':
                # Dormant person - emit exit at last seen time
                is_near_edge = self._is_valid_exit(person.last_bbox, frame_width, frame_height)
                exit_confidence = 0.8 if is_near_edge else 0.5
                events.append(PoseEvent(
                    timestamp=person.last_seen_timestamp,
                    event_type='exit',
                    person_id=person_id,
                    confidence=exit_confidence,
                    bbox=person.last_bbox,
                    keypoints=[]
                ))
                print(f"  [End of chunk - dormant exit] Person {person_id} at {person.last_seen_timestamp:.2f}s", flush=True)
            elif person.state == 'active' and person.frames_missing > 0:
                # Active but has been missing - likely exiting
                is_near_edge = self._is_valid_exit(person.last_bbox, frame_width, frame_height)
                exit_confidence = 0.7 if is_near_edge else 0.4
                events.append(PoseEvent(
                    timestamp=person.last_seen_timestamp,
                    event_type='exit',
                    person_id=person_id,
                    confidence=exit_confidence,
                    bbox=person.last_bbox,
                    keypoints=[]
                ))
                print(f"  [End of chunk - missing exit] Person {person_id} at {person.last_seen_timestamp:.2f}s (missing {person.frames_missing} frames)", flush=True)

        return chunk.index, events, pose_metadata

    def _calculate_iou(self, bbox1: Tuple[float, float, float, float],
                      bbox2: Tuple[float, float, float, float]) -> float:
        """Calculate Intersection over Union between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i < x1_i or y2_i < y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _calculate_center_distance(self, bbox1: Tuple[float, float, float, float],
                                   bbox2: Tuple[float, float, float, float]) -> float:
        """Calculate Euclidean distance between bbox centers"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        center1 = ((x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2)
        center2 = ((x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2)

        return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

    def _get_entry_edge(self, bbox: Tuple[float, float, float, float],
                        frame_width: float, frame_height: float) -> Optional[str]:
        """
        Determine which edge a detection entered from based on bbox position.
        Returns 'left', 'right', 'top', 'bottom', or None if not near edge.
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        threshold = self.EXIT_EDGE_THRESHOLD  # Use same threshold for entry

        # Check edges in priority order (sides first for stage wings)
        if center_x < frame_width * threshold:
            return 'left'
        elif center_x > frame_width * (1 - threshold):
            return 'right'
        elif center_y < frame_height * threshold:
            return 'top'
        elif center_y > frame_height * (1 - threshold):
            return 'bottom'

        return None

    def _is_in_audience_zone(self, bbox: Tuple[float, float, float, float],
                             frame_height: float) -> bool:
        """
        Check if detection is in the audience zone (bottom portion of frame).
        Audience heads typically appear at the very bottom of the frame.
        """
        x1, y1, x2, y2 = bbox
        center_y = (y1 + y2) / 2

        # Detection is in audience zone if center is in bottom portion
        return center_y > frame_height * (1 - self.AUDIENCE_ZONE_THRESHOLD)

    def _is_valid_exit(self, last_bbox: Tuple[float, float, float, float],
                       frame_width: float, frame_height: float = None) -> bool:
        """
        Validate that exit is plausible based on last known position.
        Person must be within EXIT_EDGE_THRESHOLD of any frame edge.

        Args:
            last_bbox: Last known bounding box (x1, y1, x2, y2)
            frame_width: Width of the frame
            frame_height: Height of the frame (optional, defaults to frame_width for aspect ratio)
        """
        x1, y1, x2, y2 = last_bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        # Use frame_height if provided, otherwise estimate from frame_width
        if frame_height is None:
            frame_height = frame_width * 9 / 16  # Assume 16:9 aspect ratio

        # Check if person was near any edge (left, right, top, or bottom)
        near_left = center_x < frame_width * self.EXIT_EDGE_THRESHOLD
        near_right = center_x > frame_width * (1 - self.EXIT_EDGE_THRESHOLD)
        near_top = center_y < frame_height * self.EXIT_EDGE_THRESHOLD
        near_bottom = center_y > frame_height * (1 - self.EXIT_EDGE_THRESHOLD)

        return near_left or near_right or near_top or near_bottom

    def _match_detection_to_person(self, detection_bbox: Tuple[float, float, float, float],
                                   tracked_persons: Dict[int, 'TrackedPerson'],
                                   frame_width: float) -> Optional[int]:
        """
        Match detection to existing person (pending, active, OR dormant).
        Returns person_id if matched, None if new person.
        """
        best_match_id = None
        best_score = 0.0

        for person_id, person in tracked_persons.items():
            if person.state == 'exited':
                continue  # Skip confirmed exits

            # Calculate IOU with last known position
            iou = self._calculate_iou(detection_bbox, person.last_bbox)

            # Calculate center distance for proximity scoring
            center_dist = self._calculate_center_distance(detection_bbox, person.last_bbox)

            # For dormant persons, use different matching criteria
            if person.state == 'dormant':
                # Dormant matching: lower IOU threshold but check center proximity
                if center_dist < frame_width * 0.3:  # Within 30% of frame width
                    score = max(iou, 0.2)  # Boost score for nearby dormant
                else:
                    score = iou * 0.5  # Penalize far dormant matches
            elif person.state == 'pending':
                # Pending: use IOU but with a slight boost (we want to track new persons)
                score = iou * 1.1  # Slight boost for pending matches
            else:
                # Active person: use IOU directly
                score = iou

            # Lower threshold for re-matching (was 0.3)
            if score > best_score and score > 0.15:
                best_score = score
                best_match_id = person_id

        return best_match_id

    def process_video(self) -> Dict:
        """
        Process entire video: chunk, detect poses in parallel, consolidate events

        Returns:
            Result dictionary with events and metadata
        """
        print("\n[STEP] Starting YOLO pose processing", flush=True)
        self._emit_progress("initialization", 0, "Initializing processor")

        result = {
            'success': False,
            'events': [],
            'pose_metadata_cache': None,
            'video_info': {
                'duration': self.duration,
                'fps': self.fps,
                'resolution': [self.width, self.height],
                'chunks': self.num_chunks
            },
            'error': None
        }

        try:
            # Step 1: Split video into chunks
            chunks = self._split_video_into_chunks()

            if not chunks:
                result['error'] = 'Failed to create video chunks'
                return result

            # Step 2: Process chunks in parallel
            print(f"\n[STEP] Processing {len(chunks)} chunks in parallel...", flush=True)
            self._emit_progress("detection", 0, f"Processing chunks in parallel", 0, len(chunks))

            # Determine number of workers (CPU cores - 1, minimum 1)
            num_workers = max(1, mp.cpu_count() - 1)
            print(f"  Using {num_workers} parallel workers", flush=True)

            all_events = []
            all_pose_metadata = {}
            chunks_completed = 0

            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                # Submit all chunks for processing
                future_to_chunk = {
                    executor.submit(self._process_chunk, chunk, self.model_name): chunk
                    for chunk in chunks
                }

                # Collect results as they complete
                for future in as_completed(future_to_chunk):
                    chunk = future_to_chunk[future]
                    try:
                        chunk_idx, events, pose_metadata = future.result()

                        # Consolidate results
                        all_events.extend(events)
                        all_pose_metadata.update(pose_metadata)

                        chunks_completed += 1
                        progress = int((chunks_completed / len(chunks)) * 100)
                        self._emit_progress("detection", progress,
                                          f"Completed chunk {chunks_completed}/{len(chunks)}",
                                          chunks_completed, len(chunks))

                        print(f"  Chunk {chunk_idx} complete: {len(events)} events detected", flush=True)

                        # Emit chunk completion event for real-time UI updates
                        chunk_event = {
                            "type": "chunk_complete",
                            "chunk_index": chunk_idx,
                            "events_count": len(events),
                            "chunks_completed": chunks_completed,
                            "total_chunks": len(chunks)
                        }
                        print(f"[CHUNK_COMPLETE] {json.dumps(chunk_event)}", flush=True)

                    except Exception as e:
                        print(f"  Error processing chunk {chunk.index}: {e}", file=sys.stderr)

            # Step 3: Sort events by timestamp
            all_events.sort(key=lambda e: e.timestamp)

            # Step 4: Cache pose metadata
            cache_file = self.cache_dir / "pose_metadata.json"
            with open(cache_file, 'w') as f:
                # Convert pose metadata to JSON-serializable format
                json_metadata = {
                    str(ts): data for ts, data in all_pose_metadata.items()
                }
                json.dump(json_metadata, f, indent=2)

            print(f"\n[STEP] Processing complete", flush=True)
            print(f"  Total events detected: {len(all_events)}", flush=True)
            print(f"    - Enter events: {sum(1 for e in all_events if e.event_type == 'enter')}", flush=True)
            print(f"    - Exit events: {sum(1 for e in all_events if e.event_type == 'exit')}", flush=True)
            print(f"  Pose metadata cached: {cache_file}", flush=True)

            # Step 5: Build result
            result['success'] = True
            result['events'] = [
                {
                    'timestamp': e.timestamp,
                    'event_type': e.event_type,
                    'person_id': e.person_id,
                    'confidence': e.confidence,
                    'bbox': e.bbox,
                    'keypoints': e.keypoints
                }
                for e in all_events
            ]
            result['pose_metadata_cache'] = str(cache_file)

            self._emit_progress("complete", 100, "Processing complete")

            return result

        except Exception as e:
            result['error'] = str(e)
            print(f"\nError: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return result

        finally:
            # Cleanup: Remove chunk files (keep pose cache)
            print("\n[STEP] Cleaning up temporary files...", flush=True)
            chunks_dir = self.temp_dir / "chunks"
            if chunks_dir.exists():
                import shutil
                shutil.rmtree(chunks_dir)


def main():
    parser = argparse.ArgumentParser(
        description="YOLO Pose Video Processor - Detect pose events in parallel chunks"
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('--model', default=None,
                       help='YOLO pose model file (overrides --model-size if provided)')
    parser.add_argument('--model-size', choices=['nano', 'small', 'medium', 'large'], default='medium',
                       help='YOLO model size: nano (fastest, least accurate), small, medium (default, balanced), large (slowest, most accurate)')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON (for IPC)')

    # Detection quality parameters
    parser.add_argument('--confidence-threshold', type=float, default=0.6,
                       help='Detection confidence threshold (default: 0.6)')
    parser.add_argument('--nms-iou', type=float, default=0.45,
                       help='NMS IoU threshold for suppressing overlaps (default: 0.45)')
    parser.add_argument('--min-visible-keypoints', type=int, default=9,
                       help='Minimum visible keypoints required (default: 9, balanced for medium model)')
    parser.add_argument('--exit-stability-frames', type=int, default=3,
                       help='Frames person must be absent before exit event (default: 3)')
    parser.add_argument('--min-detection-conf', type=float, default=0.65,
                       help='Minimum per-detection box confidence (default: 0.65)')
    parser.add_argument('--keypoint-conf', type=float, default=0.45,
                       help='Minimum keypoint confidence threshold (default: 0.45, balanced for medium model)')
    parser.add_argument('--min-aspect-ratio', type=float, default=1.5,
                       help='Minimum bbox aspect ratio (height/width) (default: 1.5)')
    parser.add_argument('--max-aspect-ratio', type=float, default=2.8,
                       help='Maximum bbox aspect ratio (height/width) (default: 2.8)')
    parser.add_argument('--min-keypoint-coverage', type=float, default=0.35,
                       help='Minimum fraction of bbox that keypoints must cover (default: 0.35, balanced for medium model)')

    args = parser.parse_args()

    # Map model size to model file if --model not explicitly provided
    model_size_map = {
        'nano': 'yolo11n-pose.pt',
        'small': 'yolo11s-pose.pt',
        'medium': 'yolo11m-pose.pt',
        'large': 'yolo11l-pose.pt'
    }

    model_name = args.model if args.model else model_size_map[args.model_size]

    try:
        processor = YOLOPoseProcessor(
            args.video,
            model_name=model_name,
            confidence_threshold=args.confidence_threshold,
            nms_iou_threshold=args.nms_iou,
            min_visible_keypoints=args.min_visible_keypoints,
            exit_stability_frames=args.exit_stability_frames,
            min_detection_conf=args.min_detection_conf,
            keypoint_conf=args.keypoint_conf,
            min_aspect_ratio=args.min_aspect_ratio,
            max_aspect_ratio=args.max_aspect_ratio,
            min_keypoint_coverage=args.min_keypoint_coverage
        )
        result = processor.process_video()

        if args.json:
            print(json.dumps(result, indent=2))

        if not result['success']:
            sys.exit(1)

    except Exception as e:
        error_msg = str(e)
        if args.json:
            print(json.dumps({'success': False, 'error': error_msg}))
        else:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
