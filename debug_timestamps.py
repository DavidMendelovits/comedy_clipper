#!/usr/bin/env python3
"""
Debug script to analyze person detection at specific timestamps.
Tests YOLO detection, zone filtering, and person counting.
"""

import cv2
import yaml
import sys
from pathlib import Path
from ultralytics import YOLO
import numpy as np

# Timestamps to check (in seconds)
TIMESTAMPS = [
    125,   # 2:05
    372,   # 6:12
    540,   # 9:00
    719,   # 11:59
]

def load_config():
    """Load clipper configuration."""
    with open('clipper_rules.yaml', 'r') as f:
        return yaml.safe_load(f)

def analyze_frame(frame, model, config, timestamp):
    """Analyze a single frame for person detection."""
    h, w = frame.shape[:2]

    # Get zone boundaries
    zone = config['zone_crossing']['stage_boundary']
    left = int(zone['left'] * w)
    right = int(zone['right'] * w)
    top = int(zone['top'] * h)
    bottom = int(zone['bottom'] * h)

    # Run YOLO detection
    results = model(frame, conf=config['yolo_detection']['confidence'], verbose=False)

    # Count people
    total_people = 0
    people_in_zone = 0
    people_outside_zone = 0

    detections = []

    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls = int(box.cls[0])
            # Class 0 is 'person' in COCO dataset
            if cls == 0:
                total_people += 1
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                # Calculate centroid
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2

                # Check if in zone
                in_zone = (left <= cx <= right and top <= cy <= bottom)

                if in_zone:
                    people_in_zone += 1
                else:
                    people_outside_zone += 1

                detections.append({
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'centroid': (int(cx), int(cy)),
                    'confidence': conf,
                    'in_zone': in_zone
                })

    # Draw detections
    debug_frame = frame.copy()

    # Draw zone boundary
    cv2.rectangle(debug_frame, (left, top), (right, bottom), (255, 255, 0), 2)
    cv2.putText(debug_frame, "STAGE ZONE", (left + 10, top + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # Draw detections
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cx, cy = det['centroid']
        color = (0, 255, 0) if det['in_zone'] else (0, 0, 255)
        label = "IN ZONE" if det['in_zone'] else "AUDIENCE"

        # Draw bounding box
        cv2.rectangle(debug_frame, (x1, y1), (x2, y2), color, 2)

        # Draw centroid
        cv2.circle(debug_frame, (cx, cy), 5, color, -1)

        # Draw label
        cv2.putText(debug_frame, f"{label} {det['confidence']:.2f}",
                   (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Add info text
    info_lines = [
        f"Timestamp: {timestamp}s ({timestamp//60}:{timestamp%60:02d})",
        f"Total People: {total_people}",
        f"In Zone (Stage): {people_in_zone}",
        f"Outside Zone (Audience): {people_outside_zone}",
        f"Zone Bottom: {zone['bottom']*100:.0f}% ({bottom}px of {h}px)",
    ]

    y_pos = 30
    for line in info_lines:
        cv2.putText(debug_frame, line, (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_pos += 30

    return debug_frame, {
        'timestamp': timestamp,
        'total_people': total_people,
        'people_in_zone': people_in_zone,
        'people_outside_zone': people_outside_zone,
        'detections': detections
    }

def main():
    # Load config
    config = load_config()

    # Load YOLO model
    print(f"Loading YOLO model: {config['yolo_detection']['model']}")
    model = YOLO(config['yolo_detection']['model'])

    # Open video
    video_path = 'test_vid.mov'
    if not Path(video_path).exists():
        print(f"Error: Video not found at {video_path}")
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    print(f"Video: {video_path}")
    print(f"FPS: {fps:.2f}, Total Frames: {total_frames}, Duration: {duration:.2f}s")
    print(f"YOLO Confidence: {config['yolo_detection']['confidence']}")
    print(f"Zone Bottom: {config['zone_crossing']['stage_boundary']['bottom']*100:.0f}%")
    print()

    # Create output directory
    output_dir = Path('debug_analysis')
    output_dir.mkdir(exist_ok=True)

    # Analyze each timestamp
    results = []
    for ts in TIMESTAMPS:
        frame_num = int(ts * fps)

        if frame_num >= total_frames:
            print(f"Timestamp {ts}s ({ts//60}:{ts%60:02d}) is beyond video duration")
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()

        if not ret:
            print(f"Failed to read frame at {ts}s")
            continue

        print(f"Analyzing timestamp {ts}s ({ts//60}:{ts%60:02d})...")
        debug_frame, info = analyze_frame(frame, model, config, ts)
        results.append(info)

        # Save debug frame
        output_path = output_dir / f'timestamp_{ts:04d}s.jpg'
        cv2.imwrite(str(output_path), debug_frame)
        print(f"  Total: {info['total_people']}, In Zone: {info['people_in_zone']}, Outside: {info['people_outside_zone']}")
        print(f"  Saved: {output_path}")
        print()

    cap.release()

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for info in results:
        ts = info['timestamp']
        print(f"{ts:4d}s ({ts//60}:{ts%60:02d}) - Total: {info['total_people']}, "
              f"In Zone: {info['people_in_zone']}, Outside: {info['people_outside_zone']}")

    print("\nRecommendations:")
    print("-" * 60)

    # Check if zone is catching people
    max_in_zone = max((r['people_in_zone'] for r in results), default=0)
    max_total = max((r['total_people'] for r in results), default=0)

    if max_in_zone == 0 and max_total > 0:
        print("⚠️  NO people detected in zone, but people detected outside!")
        print("   → Zone boundary might be too restrictive")
        print("   → Try increasing 'bottom' from 0.85 to 0.90 or 0.95")
    elif max_in_zone < 4:
        print(f"⚠️  Only {max_in_zone} person(s) detected in zone (expected 4 comedians)")
        print("   → YOLO might be missing detections")
        print("   → Try lowering confidence from 0.5 to 0.3 or 0.4")
    else:
        print(f"✓ Detected {max_in_zone} people in zone at some timestamps")

    print("\nDebug frames saved to:", output_dir.absolute())

if __name__ == '__main__':
    main()
