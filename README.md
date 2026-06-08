# YOLOv8 Security

> 一套围绕「实时监控、异常检测、告警闭环、证据留存、设备接入、数据分析」构建的智能视频安防平台。

YOLOv8 Security 将 **Python 检测引擎**、**Spring Boot 后端服务** 与 **React 管理前端** 整合在一个仓库中，适合用于监区、园区、值守室、厂区等需要持续视频巡检与事件留痕的场景。

如果你想找的是一个：

- 能直接本地跑起来的完整工程
- 具备前后端和检测链路的可二开项目
- 支持摄像头接入、告警联动、证据管理和运维页面的系统原型

那这个仓库就是为这类目标准备的。

---

## 效果预览

### 登录页

> 已完成登录页实机截图采集。为避免提交本机临时绝对路径到仓库，当前 README 先保留截图位说明；待截图文件落到仓库目录后，可直接替换为仓库内相对路径图片。

---

## 特性亮点

- **完整链路**：覆盖检测、告警、截图、证据、统计、设备和运维管理
- **多端协同**：Python 做检测，Java 做服务，React 做控制台
- **多种视频源接入**：支持 USB、RTSP、HTTP 快照摄像头
- **设备生态扩展**：支持 ONVIF 自动发现和 go2rtc 流转发
- **双实例运行模式**：同时提供实时数据实例和空数据演示实例
- **可扩展 AI 能力**：已预留并接入 `Qwen2.5-VL` 图像分析服务
- **适合演示与二开**：既能快速启动，也方便继续拆模块重构

---

## 系统能力

### 检测与告警

- 跌倒检测
- 打架 / 肢体冲突检测
- 异常聚集检测
- 离岗 / 区域无人检测
- 疲劳 / 长时间静止检测
- 检测结果落盘、截图保存、告警生成

### 业务管理

- 实时监控与摄像头联动
- 告警中心与详情跳转
- 证据中心与截图浏览
- 审计日志与导出
- 数据分析与趋势图表
- 设备管理与连通性校验
- 模型信息与运维中心

### 页面路由

当前前端已包含以下核心页面：

- `/dashboard`：控制面板
- `/monitor`：实时监控
- `/alerts`：告警中心
- `/evidence`：视频证据
- `/devices`：设备管理
- `/analysis`：数据分析
- `/audit`：审计日志
- `/model-training`：模型微调
- `/training`：算法对比
- `/maintenance`：运维中心

---

## 技术栈

### 前端

- React 19
- Vite 6
- TypeScript 5
- React Router 7
- Zustand
- Recharts
- Three.js / React Three Fiber

### 后端

- Spring Boot 3.2.5
- Java 17
- Thymeleaf
- JWT 鉴权
- H2 Database
- Spring JDBC
- WebSocket

### 检测与 AI

- Python 3.10+
- YOLOv8 / Ultralytics
- PyTorch
- OpenCV
- Qwen2.5-VL（可选增强）

### 流媒体与设备

- go2rtc
- ONVIF 自动发现
- RTSP / USB / HTTP Snapshot

---

## 项目结构

```text
.
├─ detection/          # Python 检测端：行为识别、截图、结果落盘
├─ server/             # Spring Boot 后端：API、鉴权、统计、设备管理
├─ web/                # React 前端：监控、告警、证据、分析、运维
├─ models/             # 模型文件目录
├─ videos/             # 本地测试视频
├─ start.bat           # Windows 一键启动
├─ stop.bat            # Windows 一键停止
├─ build.bat           # 一键构建与打包
└─ README.md
```

---

## 架构总览

```text
摄像头 / RTSP / 本地视频
          │
          ▼
Python 检测端（detection/）
  - YOLOv8 行为识别
  - 帧处理、截图保存、结果写入
  - 调用后端接口同步状态
          │
          ▼
Spring Boot 后端（server/）
  - 认证与 API
  - 告警 / 证据 / 审计 / 统计
  - H2 数据库存储
  - go2rtc / ONVIF 联动
          │
          ├─ http://localhost:5000   实时数据实例
          └─ http://localhost:5001   空数据演示实例
          │
          ▼
React 前端（web/）
  - 开发模式：Vite Dev Server（5173）
  - 生产模式：由后端托管静态资源
```

---

## 快速开始

### 环境要求

- Windows 10 / 11（当前脚本体验最佳）
- Java 17+
- Python 3.10+
- Node.js 18+
- Maven 3.9+（或可用 Maven Wrapper）

推荐机器配置：

- 内存：8 GB+
- 硬盘：5 GB+
- 显卡：有 NVIDIA GPU 更佳，无 GPU 也可运行

### 一键启动

如果你只是想快速跑起来，直接执行：

```bash
start.bat
```

默认会完成：

1. 检查 Java / Python / Maven / Node 环境
2. 构建后端 WAR 包
3. 启动 Python 检测模块
4. 启动 `5000` 实时数据实例
5. 启动 `5001` 空数据实例
6. 启动前端开发服务器 `5173`

启动后可访问：

- 前端开发环境：`http://localhost:5173`
- 后端实时实例：`http://localhost:5000`
- 后端空数据实例：`http://localhost:5001`

停止全部服务：

```bash
stop.bat
```

### 启动参数

```bash
start.bat --no-python
start.bat --no-frontend
start.bat --no-empty
start.bat --no-build
start.bat --prod
```

参数说明：

- `--no-python`：跳过 Python 检测模块
- `--no-frontend`：跳过前端开发服务器
- `--no-empty`：不启动 `5001` 演示实例
- `--no-build`：跳过 Maven 构建
- `--prod`：生产模式，由后端托管前端静态资源

---

## 分模块运行

### 1. 启动检测端

```bash
pip install -r detection/requirements.txt
cd detection
python yolov8_security.py
```

### 2. 启动前端

```bash
cd web
npm install
npm run dev
```

### 3. 启动后端

```bash
cd server
mvn clean package -DskipTests
java -jar target/yolov8-security.war --server.port=5000
```

启动空数据实例：

```bash
java -DDATA_DIR=./data_empty -jar target/yolov8-security.war --server.port=5001
```

---

## 构建与打包

### 一键构建

```bash
build.bat
```

该脚本会完成：

1. 构建前端 `web/dist`
2. 同步前端静态资源到 `server/web/dist`
3. 打包后端 `server/target/yolov8-security.war`
4. 生成部署目录 `deploy-pkg/`

### 手动构建

前端构建：

```bash
cd web
npm install
npm run build
```

后端构建：

```bash
cd server
mvn clean package -Dmaven.test.skip=true
```

---

## 配置说明

### 关键配置文件

- `server/src/main/resources/application.properties`
- `server/src/main/resources/application-docker.properties`

### 当前默认关键项

- 后端端口：`5000`
- 数据目录：`${DATA_DIR:./data}`
- H2 数据库：`${DATA_DIR:./data}/db/cameras`
- Qwen2.5-VL 服务：`http://127.0.0.1:5002`
- go2rtc API：`http://127.0.0.1:1984`
- go2rtc RTSP：`rtsp://127.0.0.1:8554`

### 建议配置的环境变量

- `JWT_SECRET`：生产环境必须修改
- `H2_PASSWORD`：数据库密码
- `DATA_DIR`：数据目录
- `WEB_SERVER_URL`：检测端访问后端的地址
- `GO2RTC_RTSP_HOST`：RTSP 中转地址

### 模型文件目录

将模型文件放在 `models/` 下，例如：

- `models/yolov8n-pose.pt`
- `models/Qwen2.5-VL-7B-Instruct/`

---

## 摄像头接入

系统当前支持以下类型：

- USB 摄像头
- RTSP 摄像头
- HTTP 快照摄像头
- ONVIF 自动发现设备

后端维护摄像头配置；对于 RTSP 摄像头，会自动联动 go2rtc 维护流配置。检测端优先从后端接口读取摄像头清单，失败时回退本地配置。

---

## API 能力概览

后端已经具备以下主要接口族：

- 认证：`/api/login`、`/api/me`
- 告警：`/api/alerts`
- 审计：`/api/audit_logs`
- 统计：`/api/stats`、`/api/stats/summary`、`/api/stats/trend`
- 证据：`/api/evidence/list`、`/api/evidence/stats`
- 截图：`/api/screenshot`、`/api/screenshot/upload`
- 检测控制：`/api/detection/start`、`/api/detection/stop`、`/api/detection/status`
- 标注：`/api/annotations/*`
- AI 分析：`/api/ai/status`、`/api/ai/analyze`
- 设备发现：`/api/discover`

如果你准备接入其他系统、补 API 文档或拆 SDK，这些接口可以作为起点。

---

## 适合什么用途

这个仓库比较适合以下几类目标：

- 做视频安防 / 行为识别类项目原型
- 演示一套前后端联动的智能监控系统
- 基于现有页面和接口继续做企业内部系统
- 将检测、流媒体、设备管理拆分成独立服务继续演进
- 作为毕设、项目展示或行业 PoC 的基础代码

---

## 开发建议

### 前端

```bash
cd web
npm run dev
npm run test
npm run build
```

### 后端

```bash
cd server
mvn test
mvn spring-boot:run
```

### 检测端

```bash
cd detection
python yolov8_security.py
```

---

## 注意事项

- 生产环境请务必修改 `JWT_SECRET` 和数据库密码
- 如果 `5000 / 5001 / 5173` 端口被占用，启动脚本会发出提示
- 首次运行前端若缺少 `node_modules`，启动脚本会自动安装依赖
- Python 检测端依赖摄像头、模型和本地运行环境，建议先单独验证
- `Qwen2.5-VL` 和 `go2rtc` 属于增强能力，未配置时也可以先跑通基础流程

---

## Roadmap 建议

如果你准备把这个仓库继续打磨成更正式的展示项目，下一步建议补齐：

- 首页截图 / GIF 演示
- 默认账号与权限说明
- 更完整的 API 文档
- Docker / Linux 部署文档
- 常见问题与排障指南
- 数据目录、日志目录与备份策略说明

---

## 许可证

当前仓库未显式声明 License。

如果你准备对外开源，建议补充 `LICENSE` 文件；如果只用于内部交付，建议在此处写明使用范围与限制。