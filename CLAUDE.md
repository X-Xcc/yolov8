# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

监狱智能行为分析系统 (Prison Intelligent Behavior Analysis System) — real-time security monitoring using YOLOv8 pose estimation. Detects falls, fighting, fatigue, eye fatigue, guard absence, and crowd gathering in prison environments.

## Architecture

Two-component system with dual Python→Java communication paths:

### 1. Python AI Detection (`ai-models/yolov8_security.py`)
- YOLOv8n-pose model for real-time pose estimation
- Detects: 跌倒 (fall), 打架 (fighting), 疲劳 (fatigue/posture), 眼疲劳 (eye fatigue via EAR), 离岗 (leave post), 人员聚集 (crowd gathering)
- OpenCV-based video processing with UI overlay (OpenCV window)
- **Dual communication to Java backend**:
  - (a) Saves detection JSON (`detection_*.json`) + frame images (`frame_*.jpg`) to `backend/data/` directory for Java to scan
  - (b) HTTP POST frames to `/api/update_frame` for real-time MJPEG stream
- Modules: `DetectionModule` (behavior detection), `DataSaver`, `AlertManager`, `UIManager`
- Optional Qwen2.5-VL service (`ai-models/qwen_vl_service.py`, port 5001) for LLM-based scene analysis

### 2. Java Spring Boot Backend (`backend/`)
- Spring Boot 3.x, Java 17, Maven (WAR packaging)
- Serves web dashboard (Thymeleaf template at `src/main/resources/templates/index.html`, ~2200 lines with Chart.js)
- REST API endpoints under `/yolov8-security/`:
  - `GET /api/stats` — detection statistics + behavior counts (polled every 2s by dashboard)
  - `GET /api/images` + `GET /api/images/{name}` — screenshot listing/serving
  - `DELETE /api/delete_all_images` — bulk delete detection data + invalidate cache
  - `GET /api/model_info` — YOLO model quantization info
  - `GET /api/ai/status` — Qwen2.5-VL service health check
  - `POST /api/open_folder` — open screenshots/videos folder on server via `java.awt.Desktop`
  - `GET /video_feed` — MJPEG video stream (`multipart/x-mixed-replace`)
- Services: `DetectionService` (cached file scanning), `ModelInfoService`, `PythonScriptService`, `QwenVLService`
- Filters: `AuthFilter` (token-based API auth), `RateLimitFilter`, `CorsConfig`
- Nginx reverse proxy (`nginx/nginx.conf`): HTTPS redirect, WebSocket/SSE proxying for video feed, SPA fallback

### Communication Flow
```
Camera/video file → YOLOv8 Pose (Python)
                              → writes JSON + images to backend/data/  ←──┐
                              → HTTP POST frames to Java backend           │
                                                                         │
                              ←── Java scans data/ directory ────────────┘
                              ←── Java serves REST API + MJPEG stream
                              ←── Web dashboard polls /api/stats every 2s
```

## Key Commands

### Python Detection
```bash
cd ai-models && python yolov8_security.py
```

### Tests
```bash
# Python tests
cd tests && python -m pytest test_detection.py -v
cd tests && python -m pytest test_detection.py -v -k "test_name"

# Java tests
cd backend && .\mvnw test
```

### Java Backend
```bash
cd backend && .\mvnw clean package -DskipTests     # Build WAR
cd backend && .\mvnw spring-boot:run               # Run dev server
cd backend && .\mvnw test                           # Run tests
```

### Docker
```bash
docker-compose up -d
docker-compose down
docker-compose logs -f
```

## Key Implementation Details

- **Flat-file data exchange (no database)** — Python writes `detection_*.json` and `frame_*.jpg` to `backend/data/`, Java's `DetectionService` scans and parses them via Jackson. This is the primary data flow.
- **DetectionService caching** — `DirScan` cache with 2-second TTL (`SCAN_CACHE_TTL_MS = 2000L`). After `DELETE /api/delete_all_images`, `invalidateScanCache()` must be called or deletes won't be visible immediately.
- **StatsResponse aggregation** — `BehaviorCounts` POJO tracks fall, fight, absent, fatigue, gather. Recent detections capped at 50, all detections at 200.
- **Video streaming** — `VideoStreamController` serves MJPEG via `multipart/x-mixed-replace`; frames are read from disk (written by Python), not generated on-the-fly. Nginx proxies this with `proxy_buffering off` and `proxy_cache off`.
- **Auth** — `AuthFilter` checks `Authorization` header against `app.auth.token` (default from `.env` `API_KEY`). Token mismatch returns 401.
- **Rate limiting** — `RateLimitFilter` uses token bucket per IP.
- **Python Config class** (`ai-models/yolov8_security.py`, line 56) centralizes all parameters: model path, detection thresholds, alert cooldown, UI colors, save intervals, EAR threshold for eye fatigue.

## Config

- Python: `Config` class in `ai-models/yolov8_security.py` (line 56)
- Java: `application.properties` + `AppConfig.java`
  - `app.auth.token=${API_KEY:default-dev-token}` — API auth token
  - `server.port=5000` — backend port
  - `file.upload-dir=../data` — where DetectionService scans for data
- Nginx: `nginx/nginx.conf` — SSL certs, reverse proxy, SPA fallback
- Web server URL: env var `WEB_SERVER_URL` (default: `http://127.0.0.1:5000/yolov8-security`)

## Model Files

- YOLOv8n-pose: `models/yolov8n-pose.pt` (pose estimation, ~5MB ONNX/PyTorch)
- Qwen2.5-VL-7B: Optional multimodal model for advanced scene analysis (~14GB)

## Important Notes

- No database — all detection data is stored as flat JSON files in `backend/data/`
- The Python script reads from a video file (`videos/test_video.mp4`) by default; change `Config.SOURCE` to `0` for live camera
- Java tests use JUnit 5 with `@TempDir` for isolated file I/O testing — no mocking framework
- The web UI is a single Thymeleaf template with embedded CSS/JS using Chart.js (no separate frontend build)
- `open_folder` endpoint uses `java.awt.Desktop.open()` — will fail in headless/Docker environments without X11
- Qwen VL service (port 5001) is entirely optional; the system works without it

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. The
skill has multi-step workflows, checklists, and quality gates that produce better
results than an ad-hoc answer. When in doubt, invoke the skill. A false positive is
cheaper than a false negative.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke /office-hours
- Strategy, scope, "think bigger", "what should we build" → invoke /plan-ceo-review
- Architecture, "does this design make sense" → invoke /plan-eng-review
- Design system, brand, "how should this look" → invoke /design-consultation
- Design review of a plan → invoke /plan-design-review
- Developer experience of a plan → invoke /plan-devex-review
- "Review everything", full review pipeline → invoke /autoplan
- Bugs, errors, "why is this broken", "wtf", "this doesn't work" → invoke /investigate
- Test the site, find bugs, "does this work" → invoke /qa (or /qa-only for report only)
- Code review, check the diff, "look at my changes" → invoke /review
- Visual polish, design audit, "this looks off" → invoke /design-review
- Developer experience audit, try onboarding → invoke /devex-review
- Ship, deploy, create a PR, "send it" → invoke /ship
- Merge + deploy + verify → invoke /land-and-deploy
- Configure deployment → invoke /setup-deploy
- Post-deploy monitoring → invoke /canary
- Update docs after shipping → invoke /document-release
- Weekly retro, "how'd we do" → invoke /retro
- Second opinion, codex review → invoke /codex
- Safety mode, careful mode, lock it down → invoke /careful or /guard
- Restrict edits to a directory → invoke /freeze or /unfreeze
- Upgrade gstack → invoke /gstack-upgrade
- Save progress, "save my work" → invoke /context-save
- Resume, restore, "where was I" → invoke /context-restore
- Security audit, OWASP, "is this secure" → invoke /cso
- Make a PDF, document, publication → invoke /make-pdf
- Launch real browser for QA → invoke /open-gstack-browser
- Import cookies for authenticated testing → invoke /setup-browser-cookies
- Performance regression, page speed, benchmarks → invoke /benchmark
- Review what gstack has learned → invoke /learn
- Tune question sensitivity → invoke /plan-tune
- Code quality dashboard → invoke /health