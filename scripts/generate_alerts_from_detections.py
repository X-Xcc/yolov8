#!/usr/bin/env python3
"""Generate alerts.json from detection files with actions (matching trend data)."""
import json
import os
import random
import glob as globmod
from datetime import datetime

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "server", "data"))

LEVEL_MAP = {
    "打架": "high",
    "跌倒": "medium",
    "离岗": "medium",
    "人员聚集": "low",
}

def main():
    files = globmod.glob(os.path.join(DATA_DIR, "detection_*.json"))
    alerts = []
    alert_id = 1

    for fpath in sorted(files):
        with open(fpath, encoding="utf-8") as f:
            det = json.load(f)
        actions = det.get("actions", [])
        if not actions:
            continue
        for action in actions:
            alert = {
                "id": f"alert_{alert_id:06d}",
                "cameraId": det["camera_id"],
                "cameraName": det["camera_name"],
                "type": action,
                "level": LEVEL_MAP.get(action, "low"),
                "time": det["timestamp"],
                "snapshotUrl": det.get("image_filename", ""),
                "status": "pending",
                "confidence": round(random.uniform(72, 98), 1),
                "message": f"{det['camera_name']} 检测到{action}行为",
                "simulated": True,
            }
            alerts.append(alert)
            alert_id += 1

    alerts.sort(key=lambda a: a["time"], reverse=True)

    alert_path = os.path.join(DATA_DIR, "alerts.json")
    with open(alert_path, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(alerts)} alerts from {len(files)} detection files")

    # Stats
    by_type = {}
    for a in alerts:
        by_type[a["type"]] = by_type.get(a["type"], 0) + 1
    print("Alert distribution:")
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
