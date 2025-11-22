#!/usr/bin/env python3
"""
Scan video for person count transitions to find segment boundaries.
"""

import cv2
import yaml
from pathlib import Path
from ultralytics import YOLO
import numpy as np

def load_config():
    with open('clipper_rules.yaml', 'r') as f:
        return yaml.safe_load(f)

def count_people_in_zone(frame, model, config):
    """Count people in the stage zone."""
    h, w = frame.shape[:2]

    zone = config['zone_crossing']['stage_boundary']
    left = int(zone['left'] * w)
    right = int(zone['right'] * w)
    top = int(zone['top'] * h)
    bottom = int(zone['bottom'] * h)

    results = model(frame, conf=config['yolo_detection']['confidence'], verbose=False)

    count = 0
    for result in results:
        boxes = result.boxes
        for box in boxes:
            if int(box.cls[0]) == 0:  # person class
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                if left <= cx <= right and top <= cy <= bottom:
                    count += 1

    return count

def main():
    config = load_config()
    model = YOLO(config['yolo_detection']['model'])

    video_path = 'test_vid.mov'
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Scanning {video_path} for person count transitions...")
    print(f"FPS: {fps:.2f}, Duration: {total_frames/fps:.2f}s")
    print(f"Sampling every 30 frames (~1 second)")
    print()

    # Scan video
    frame_num = 0
    prev_count = None
    transitions = []

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            break

        count = count_people_in_zone(frame, model, config)
        timestamp = frame_num / fps

        # Apply smoothing window
        if prev_count is not None and prev_count != count:
            transitions.append({
                'frame': frame_num,
                'timestamp': timestamp,
                'from': prev_count,
                'to': count
            })
            print(f"{timestamp:7.1f}s ({int(timestamp)//60:2d}:{int(timestamp)%60:02d}) - "
                  f"Count: {prev_count} → {count}")

        prev_count = count
        frame_num += 30  # Sample every second

        # Progress indicator
        if frame_num % 900 == 0:  # Every 30 seconds
            print(f"  ... scanned {timestamp:.0f}s / {total_frames/fps:.0f}s")

    cap.release()

    print()
    print("="*60)
    print(f"Found {len(transitions)} transitions")
    print("="*60)

    if transitions:
        # Group transitions to find potential segments
        print("\nPotential segment boundaries:")
        for t in transitions:
            ts = t['timestamp']
            action = ""
            if t['from'] == 0 and t['to'] == 1:
                action = "→ START (comedian enters empty stage)"
            elif t['from'] == 1 and t['to'] == 0:
                action = "→ END (comedian exits)"
            elif t['from'] == 2 and t['to'] == 1:
                action = "→ START (host exits, comedian alone)"
            elif t['from'] == 1 and t['to'] == 2:
                action = "→ END (host enters)"

            print(f"{ts:7.1f}s ({int(ts)//60:2d}:{int(ts)%60:02d}) - {t['from']}→{t['to']} {action}")
    else:
        print("\n⚠️  NO TRANSITIONS FOUND!")
        print("The person count never changes throughout the video.")
        print("\nThis means your current transition-based detection won't work.")
        print("\nRecommendations:")
        print("1. Switch to scene detection mode (detection_mode: scene)")
        print("2. Or add sustained-presence logic (create segments when count=1 for 10+ seconds)")

if __name__ == '__main__':
    main()
