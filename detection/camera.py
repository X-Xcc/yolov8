import os
import json
import logging

import cv2

logger = logging.getLogger(__name__)

# requests 可选
try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


def detect_cameras(max_index=5):
    """扫描USB设备索引0~max_index，返回可用摄像头列表"""
    available = []
    logger.info("正在扫描可用摄像头...")
    backend = cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else cv2.CAP_ANY
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
                logger.info("  摄像头 %d 可用", i)
            cap.release()
        else:
            cap.release()
    if not available:
        logger.warning("  未检测到任何摄像头")
    else:
        logger.info("共检测到 %d 个摄像头: %s", len(available), available)
    return available


def load_cameras_config(api_base=None):
    """从 Java 后端 API 获取摄像头列表，回退到本地 cameras.json"""
    if api_base is None:
        api_base = os.environ.get("WEB_SERVER_URL", "http://127.0.0.1:5000")

    rtsp_host = os.environ.get("GO2RTC_RTSP_HOST", "rtsp://127.0.0.1:8554")

    if not _HAS_REQUESTS:
        logger.warning("requests 库不可用，回退到本地 cameras.json")
        return _load_cameras_config_fallback()

    try:
        resp = requests.get(f"{api_base}/api/camera_config", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        cameras_data = data.get("data", data) if isinstance(data, dict) else data

        cameras = []
        for cam in cameras_data:
            if cam.get("type") == "usb":
                cameras.append({
                    "id": cam["id"],
                    "type": "usb",
                    "address": int(cam.get("address", cam.get("port", 0))),
                    "name": cam.get("name", f"Camera {cam['id']}"),
                    "go2rtc_id": cam.get("go2rtcId"),
                })
            elif cam.get("type") == "rtsp":
                go2rtc_id = cam.get("go2rtcId", f"cam_{cam['id']}")
                original_rtsp = _replace_cam_password(cam.get("address", ""))
                cameras.append({
                    "id": cam["id"],
                    "type": "rtsp",
                    "address": original_rtsp if original_rtsp else f"{rtsp_host}/{go2rtc_id}",
                    "name": cam.get("name", f"Camera {cam['id']}"),
                    "go2rtc_id": go2rtc_id,
                })
            elif cam.get("type") == "http_snapshot":
                cameras.append({
                    "id": cam["id"],
                    "type": "http_snapshot",
                    "address": _replace_cam_password(cam.get("address", cam.get("httpUrl", ""))),
                    "name": cam.get("name", f"Camera {cam['id']}"),
                    "go2rtc_id": cam.get("go2rtcId"),
                })

        logger.info("从 API 加载了 %d 个摄像头", len(cameras))
        return cameras

    except Exception as e:
        logger.warning("从 API 获取摄像头列表失败: %s", e)
        return _load_cameras_config_fallback()


def _replace_cam_password(value):
    """将字符串中的 ${CAM_PASSWORD} 替换为环境变量值"""
    if not isinstance(value, str):
        return value
    if "${CAM_PASSWORD}" not in value:
        return value
    password = os.environ.get("CAM_PASSWORD", "")
    if not password:
        logger.warning("环境变量 CAM_PASSWORD 未设置，摄像头密码为空")
    return value.replace("${CAM_PASSWORD}", password)


def _load_cameras_config_fallback():
    """回退方案：读本地 cameras.json"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cameras.json")
    if not os.path.exists(config_path):
        return []
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cameras = []
        for cam in data.get("cameras", []):
            address = _replace_cam_password(cam.get("address", ""))
            if cam.get("type") == "rtsp":
                continue  # fallback 时跳过 RTSP
            cameras.append({
                "id": cam.get("id", ""),
                "type": cam.get("type", "usb"),
                "address": cam.get("address", 0),
                "name": cam.get("name", ""),
                "go2rtc_id": cam.get("go2rtcId"),
            })
        return cameras
    except Exception as e:
        logger.error("读取 cameras.json 失败: %s", e)
        return []
