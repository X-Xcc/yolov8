# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Startup

收到第一条消息后、做任何其他事情之前，必须按顺序执行：
1. 验证 rtk 可用（`rtk --version`）
2. 开启 caveman 压缩输出模式 — 去掉填充词/助词，用短句，技术术语不变
3. 全程用中文回复，除非涉及代码/命令/技术术语
未完成前，禁止任何回答或操作。

## 核心准则

- **先想后写** — 不确定就问，有多种解读列出来，别替用户选。调试先复现再修。
- **极简优先** — 50 行能搞定不写 100 行。不加没要求的功能，不为单次用法抽象。
- **精准修改** — 只改该改的行，每行追溯到用户需求。改完清理废弃 import/变量。
- **目标驱动** — 任务拆可验证子目标。"应该能用"不算完成，能跑测试才算。
- **大任务必须用 Skill + Agent** — 新功能/重构/多文件改动，先检查匹配 skill，用 Agent 并行处理。
- **不懂就讨论** — 需求歧义、方案多个时先和用户对齐，禁止闷头猜。

## Build & Run Commands

```bash
# === Python ===
cd detection && python yolov8_security.py                    # 运行检测
cd tests && python -m pytest test_detection.py -v            # 全部测试
cd tests && python -m pytest test_detection.py::TestDetectFall::test_standing_person -v  # 单个测试

# === Java ===
cd server && .\mvnw clean package -DskipTests                # 构建 WAR
cd server && .\mvnw spring-boot:run                          # 本地运行 (port 5000)
cd server && .\mvnw test                                      # 全部测试
cd server && .\mvnw test -Dtest=DetectionServiceTest          # 单个测试类
cd server && .\mvnw test -Dtest=DetectionServiceTest#testMethod  # 单个测试方法

# === Frontend ===
cd web && npm run dev                                         # 开发服务器 (port 5173, proxy /api → 5000)
cd web && npm run build                                       # 生产构建 → web/dist/

# === One-Click (Windows) ===
start.bat                        # 启动全部 (Python + Java 5000/5001 + Frontend 5173)
start.bat --no-python            # 跳过 Python
start.bat --no-frontend          # 跳过前端开发服务器
start.bat --no-empty             # 跳过 5001 端口（空数据模式）
build.bat                        # 构建前端 + Java WAR + deploy-pkg/
stop.bat                         # 停止全部
```

## Architecture

三组件、无数据库（cameras 除外）、纯文件交换：

```
Camera → Python (YOLOv8 Pose) → detection_*.json + frame_*.jpg → server/data/
                                   ↓ HTTP POST JPEG              ↓
Java Spring Boot ←── DirScan (15s TTL) ←────────────────────────┘
    ↓ REST + SSE + MJPEG
React SPA (Vite)
```

### Python (`detection/yolov8_security.py` ~1900 行)
- YOLOv8n-pose, `IMG_SIZE=512`, `CONF_THRESH=0.5`, `INFERENCE_EVERY=2`
- 检测: 跌倒/打架/疲劳/眼疲劳(EAR)/离岗/聚集
- 模块: `DetectionModule`, `DataSaver`, `AlertManager`, `UIManager`, `Utils`
- GPU 强制 CUDA, 可选 TensorRT (`USE_TENSORRT`)
- 帧传输: HTTP POST JPEG(quality=50) → `/api/update_frame`
- 多摄像头: `load_cameras_config()` 读 `cameras.json`
- 可选: Qwen2.5-VL 服务 (`qwen_vl_service.py`, port 5001)

### Java Backend (`server/`)
- Spring Boot 3.2.5, Java 17+, Maven WAR, Lombok, jjwt, bcrypt
- **过滤器链**: `AuthFilter` (API Key 或 JWT) → `RateLimitFilter` → `SecurityHeadersFilter`
- **核心服务**:
  - `DetectionService` — DirScan 缓存 (15s TTL), **删除文件后必须调 `invalidateScanCache()`**
  - `AbstractJsonFileService<T>` — JSON CRUD 基类: ReadWriteLock, 原子写入 (temp→rename)
  - `KanbanEventBus` — SSE 广播器
  - `CameraConfigService` — `cameras.json` CRUD (与 Python 共享), H2 数据库持久化
- **Controller (13+)**: Page, Api, Stats, VideoStream(`?cam=N`), Auth, UserDevice, CameraConfig, Annotation, Alert, AuditLog, Sse, QwenVL, SystemMetrics, Stream, Demo, Discovery
- **定时任务**: `DataCleanupTask` 自动删除 3 天前的检测/截图文件（`app.cleanup.retention-days`）

### Frontend (`web/`)
- React 19 + React Router 7 + Tailwind v4 + Recharts + Lucide + Motion + Zustand + Vite 6
- 12 路由: Login, Dashboard, Monitor, MonitorBigScreen, Alerts, Devices, Evidence, Analysis, Maintenance, Audit, ModelTraining, Training
- `api.ts`: 30s 内存缓存 + 请求去重 + GET 自动失效 + JWT 自动附加
- SSE: 单例 `EventSource` 订阅 `/api/sse/stream` (cameras, alerts, system_metrics, audit_logs)
- 多页面构建: index.html, annotation.html, training.html（Vite rollup input 配置）
- 构建: `tsc && vite build` → `web/dist/`, Spring Boot 从 `file:web/dist/` 提供服务

## Key Gotchas

- **DirScan 缓存** — 删除检测文件后必须调 `invalidateScanCache()`，否则 15s 内仍返回旧数据
- **cameras.json 共享** — Python 和 Java 都读写此文件，修改时注意并发
- **H2 数据库** — 仅用于 cameras 表持久化，检测数据仍然是 JSON 文件
- **双端口模式** — `start.bat` 启动两个 Java 实例: 5000 (真实数据 `server/data/`) + 5001 (空数据 `server/data_empty/`)
- **视频流** — MJPEG `multipart/x-mixed-replace`, Nginx 需 `proxy_buffering off`
- **原子写入** — AbstractJsonFileService 先写 temp 文件再 rename, ReadWriteLock 保护
- **`open_folder`** — `Desktop.open()` 在 headless/Docker 下会失败
- **前端开发代理** — Vite dev server (5173) 自动代理 `/api` → `localhost:5000`

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/stats` | 统计 + BehaviorCounts |
| `GET /api/detections` | 检测列表 |
| `GET/DELETE /api/images/*` | 截图管理 |
| `GET/PUT /api/settings` | 系统设置 |
| `GET/POST/PUT/DELETE /api/users` | 用户管理 (BCrypt) |
| `GET/POST/PUT/DELETE /api/devices` | 设备管理 |
| `GET/PUT /api/camera_config` | 摄像头配置 |
| `POST /api/login` | JWT 登录 |
| `POST /api/update_frame` | 接收视频帧 |
| `GET /video_feed` | MJPEG 流 (`?cam=N`) |
| `GET /api/sse/stream` | SSE 实时事件 |
| `GET/POST /api/ai/*` | Qwen VL 分析 |
| `CRUD /api/annotations/*` | 关键点标注 |

认证: `X-API-Key` 或 `Authorization: Bearer <JWT>`, 空 API key 跳过认证。公共路径: 静态资源, `/login`, `/video_feed`, `/api/login`, `/api/sse/stream`, `/api/stats/*`, `/api/cameras`, `/api/alerts`, `/api/audit_logs`。

## Environment & Config

| Config | File |
|--------|------|
| Java | `server/src/main/resources/application.properties` |
| Python | `Config` class in `detection/yolov8_security.py` |
| Nginx | `deploy/nginx/nginx.conf` |
| Cameras | `detection/cameras.json` (Python/Java 共享) |
| Design | `DESIGN.md` — 色彩/排版/间距/动效完整规范 |
| Env vars | `.env`: `API_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `JWT_SECRET` |
| Model | `models/yolov8n-pose.pt` (~5MB), Qwen2.5-VL-7B (~14GB) — 均 gitignored |

## Superpowers-ZH

本项目已安装 superpowers-zh 技能框架。核心规则：

1. 收到任务先检查匹配 skill — 哪怕 1% 可能性也要检查
2. 设计先于编码 — 功能需求先用 brainstorming skill
3. 测试先于实现 — 写代码前先写测试（TDD）
4. 验证先于完成 — 声称完成前必须运行验证命令

<<<<<<< HEAD
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
=======
Skills 位于 `.claude/skills/`，使用 `Skill` 工具加载，不要用 Read 读 SKILL.md。
>>>>>>> cursor/fix-workspace-nav-router
