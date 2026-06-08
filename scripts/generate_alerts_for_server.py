#!/usr/bin/env python3
"""Generate realistic prison alerts spanning 30 days for trend chart testing."""
import json
import os
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "server", "data"))

LEVEL_MAP = {"打架": "high", "跌倒": "medium", "离岗": "medium", "人员聚集": "low"}

CAMERAS = [
    ("cam0", "A区监舍1号"), ("cam1", "A区监舍2号"), ("cam2", "A区监舍3号"), ("cam3", "A区监舍4号"),
    ("cam4", "B区走廊1号"), ("cam5", "B区走廊2号"), ("cam6", "B区走廊3号"), ("cam7", "B区走廊4号"),
    ("cam8", "C区工场1号"), ("cam9", "C区工场2号"), ("cam10", "C区工场3号"), ("cam11", "C区工场4号"),
    ("cam12", "D区放风场1号"), ("cam13", "D区放风场2号"), ("cam14", "D区放风场3号"), ("cam15", "D区放风场4号"),
]

# 每个小时事件密度倍率
def hour_profile(hour):
    if 0 <= hour < 6:   return 0.15
    if 6 <= hour < 8:   return 0.5
    if 8 <= hour < 12:  return 1.2
    if 12 <= hour < 14: return 0.7
    if 14 <= hour < 18: return 1.3
    if 18 <= hour < 21: return 0.9
    return 0.25

# 每种行为的基础频率 (每小时期望值)
BASE_RATE = {
    "人员聚集": 0.8,
    "离岗":     0.5,
    "跌倒":     0.3,
    "打架":     0.1,
}

# 星期几的密度倍率 (0=周一, 6=周日) — 周末工场关闭
def weekday_mult(weekday):
    if weekday < 5:  # 周一~五
        return 1.0
    return 0.4  # 周末少很多

def main():
    now = datetime.now()
    days = 30
    start = now - timedelta(days=days)
    start = start.replace(minute=0, second=0, microsecond=0)

    alerts = []
    alert_id = 1

    total_hours = days * 24
    for hour_offset in range(total_hours):
        hour_time = start + timedelta(hours=hour_offset)
        if hour_time > now:
            break
        hour = hour_time.hour
        weekday = hour_time.weekday()
        density = hour_profile(hour) * weekday_mult(weekday)

        hour_event_count = 0
        for action, base_rate in BASE_RATE.items():
            rate = base_rate * density
            count = max(0, int(rate + random.uniform(-0.3, 0.8)))
            if action == "打架" and random.random() > 0.6:
                count = 0

            for _ in range(count):
                minute = random.randint(0, 59)
                ts = hour_time.replace(minute=minute, second=random.randint(0, 59))
                cam_id, cam_name = random.choice(CAMERAS)

                conf_base = {"打架": 85, "跌倒": 80, "离岗": 70, "人员聚集": 65}[action]
                conf = round(conf_base + random.uniform(0, 13), 1)

                alerts.append({
                    "id": f"alert_{alert_id:06d}",
                    "cameraId": cam_id,
                    "cameraName": cam_name,
                    "type": action,
                    "level": LEVEL_MAP[action],
                    "time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "snapshotUrl": f"frame_{int(ts.timestamp()*1000)}_{cam_id}.jpg",
                    "status": random.choice(["pending", "pending", "confirmed"]),
                    "confidence": conf,
                    "message": f"{cam_name} 检测到{action}行为",
                    "simulated": True,
                })
                alert_id += 1
                hour_event_count += 1

        # 每小时保底至少 1 条 (白天)
        if hour_event_count == 0 and 7 <= hour <= 22:
            action = random.choice(["人员聚集", "离岗", "跌倒"])
            cam_id, cam_name = random.choice(CAMERAS)
            ts = hour_time.replace(minute=random.randint(0, 59), second=random.randint(0, 59))
            conf_base = {"跌倒": 80, "离岗": 70, "人员聚集": 65}[action]
            alerts.append({
                "id": f"alert_{alert_id:06d}",
                "cameraId": cam_id,
                "cameraName": cam_name,
                "type": action,
                "level": LEVEL_MAP[action],
                "time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "snapshotUrl": f"frame_{int(ts.timestamp()*1000)}_{cam_id}.jpg",
                "status": "pending",
                "confidence": round(conf_base + random.uniform(0, 10), 1),
                "message": f"{cam_name} 检测到{action}行为",
                "simulated": True,
            })
            alert_id += 1

    alerts.sort(key=lambda a: a["time"], reverse=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    alert_path = os.path.join(DATA_DIR, "alerts.json")
    with open(alert_path, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(alerts)} alerts across {days} days")
    print(f"Window: {start.strftime('%Y-%m-%d %H:%M')} -> {now.strftime('%Y-%m-%d %H:%M')}")

    # 每天分布
    by_day = {}
    for a in alerts:
        d = a["time"][:10]
        by_day[d] = by_day.get(d, 0) + 1
    print("Per-day (last 10):")
    for d in sorted(by_day)[-10:]:
        print(f"  {d}: {by_day[d]}")

    # 每种行为
    by_type = {}
    for a in alerts:
        by_type[a["type"]] = by_type.get(a["type"], 0) + 1
    print("Per-type:")
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
