#!/usr/bin/env python3
"""Generate detection_*.json files spread across today for trend chart testing."""
import json
import os
import random
import shutil
import time
from datetime import datetime, timedelta, date

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "server", "data")
DATA_DIR = os.path.normpath(DATA_DIR)

CAMERAS = [
    ("cam0", "A区监舍1号"), ("cam1", "A区监舍2号"), ("cam2", "A区监舍3号"), ("cam3", "A区监舍4号"),
    ("cam4", "B区走廊1号"), ("cam5", "B区走廊2号"), ("cam6", "B区走廊3号"), ("cam7", "B区走廊4号"),
    ("cam8", "C区工场1号"), ("cam9", "C区工场2号"), ("cam10", "C区工场3号"), ("cam11", "C区工场4号"),
    ("cam12", "D区放风场1号"), ("cam13", "D区放风场2号"), ("cam14", "D区放风场3号"), ("cam15", "D区放风场4号"),
]

# Weighted action distribution: (action_list, weight)
# Each entry is a list of actions (can have multiple behaviors in one detection)
ACTION_POOL = [
    ([],                        45),   # normal - no anomaly
    (["人员聚集"],               20),   # crowd
    (["跌倒"],                   18),   # fall
    (["离岗"],                   12),   # absence
    (["打架"],                    5),   # fight
]

def pick_action():
    r = random.randint(0, 99)
    cumulative = 0
    for actions, weight in ACTION_POOL:
        cumulative += weight
        if r < cumulative:
            return actions
    return []

def generate_detection(epoch_ms, cam_id, cam_name, det_id):
    actions = pick_action()
    person_count = random.randint(1, 7) if actions else random.randint(1, 4)
    ts = datetime.fromtimestamp(epoch_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

    boxes = []
    for _ in range(len(actions) if actions else random.randint(0, 2)):
        boxes.append({
            "x": random.randint(50, 500),
            "y": random.randint(50, 350),
            "width": random.randint(80, 200),
            "height": random.randint(120, 300),
            "confidence": round(random.uniform(0.5, 0.98), 2),
            "class": "person",
        })

    return {
        "id": f"det_demo_{epoch_ms}_{det_id}",
        "timestamp": ts,
        "actions": actions,
        "filename": f"detection_{epoch_ms}_{cam_id}.json",
        "fps": round(random.uniform(25, 32), 1),
        "boxes": boxes,
        "person_count": person_count,
        "image_filename": f"frame_{epoch_ms}_{cam_id}.jpg",
        "frame_count": random.randint(1000, 99999),
        "camera_name": cam_name,
        "camera_id": cam_id,
    }

def main():
    today = date.today()
    now = datetime.now()
    today_start = datetime(today.year, today.month, today.day, 0, 0, 0)
    now_ts = now.timestamp()

    # Clean old detection files
    removed = 0
    for f in os.listdir(DATA_DIR):
        if f.startswith("detection_") and f.endswith(".json"):
            os.remove(os.path.join(DATA_DIR, f))
            removed += 1
    print(f"Removed {removed} old detection files")

    # Generate 200 detections spread from 00:00 to now
    count = 200
    start_ts = today_start.timestamp()
    timestamps = sorted(random.uniform(start_ts, now_ts) for _ in range(count))

    for i, ts_float in enumerate(timestamps):
        epoch_ms = int(ts_float * 1000)
        cam_id, cam_name = random.choice(CAMERAS)
        det_id = f"{random.randint(1000, 9999):04x}"
        det = generate_detection(epoch_ms, cam_id, cam_name, det_id)

        fname = f"detection_{epoch_ms}_{cam_id}.json"
        fpath = os.path.join(DATA_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(det, f, ensure_ascii=False, indent=2)

    print(f"Generated {count} detection files from {today_start} to {now}")

    # Stats
    by_hour = {}
    for ts_float in timestamps:
        h = datetime.fromtimestamp(ts_float).hour
        by_hour[h] = by_hour.get(h, 0) + 1
    print("Per-hour distribution:")
    for h in sorted(by_hour):
        print(f"  {h:02d}:00 - {by_hour[h]} detections")

if __name__ == "__main__":
    main()
