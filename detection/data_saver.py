import os
import time
import json
import logging
from typing import List

import cv2
import numpy as np

from config import Config
from utils import Utils

logger = logging.getLogger(__name__)


class DataSaver:

    ACTION_PRIORITY = ["打架", "跌倒", "离岗", "人员聚集"]
    MAX_RETRY = 3  # 最大重试次数，超过则丢弃

    def __init__(self, config: Config):
        self.config = config
        os.makedirs(os.path.dirname(config.RESULT_VIDEO_PATH), exist_ok=True)
        os.makedirs(config.DATASET_DIR, exist_ok=True)
        self._pending_detections = []  # [(timestamp, data, retry_count), ...]
        self._last_flush_time = time.time()
        self._flush_interval = 5.0

    def save_detection_data(self, actions: List[str], person_count: int, fps: float, frame_count: int,
                            camera_name: str = None, camera_id: str = None) -> str:
        """保存检测数据，返回时间戳"""
        timestamp = Utils.generate_timestamp()
        detection_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "person_count": person_count,
            "actions": actions or [],
            "frame_count": frame_count,
            "fps": fps,
            "image_filename": f"frame_{timestamp}.jpg" if actions else None,
            "camera_name": camera_name,
            "camera_id": camera_id
        }
        self._pending_detections.append((timestamp, detection_data, 0))
        now = time.time()
        if now - self._last_flush_time >= self._flush_interval:
            self._flush()
        return timestamp

    def _get_target_dir(self, actions: List[str]) -> str:
        """按 ACTION_PRIORITY 优先级确定目标子文件夹"""
        for action in self.ACTION_PRIORITY:
            if action in actions:
                target = os.path.join(self.config.DATASET_DIR, action)
                os.makedirs(target, exist_ok=True)
                return target
        return self.config.DATASET_DIR

    def _flush(self):
        """批量写入待处理的检测数据，失败条目保留重试"""
        if not self._pending_detections:
            return
        still_pending = []
        for timestamp, data, retry_count in self._pending_detections:
            try:
                target_dir = self._get_target_dir(data.get("actions", []))
                json_path = os.path.join(target_dir, f"detection_{timestamp}.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except OSError as e:
                if retry_count + 1 >= self.MAX_RETRY:
                    logger.warning("检测数据写入失败超过 %d 次，丢弃: %s (%s)", self.MAX_RETRY, timestamp, e)
                else:
                    logger.error("保存检测数据失败 (重试 %d/%d): %s", retry_count + 1, self.MAX_RETRY, e)
                    still_pending.append((timestamp, data, retry_count + 1))
        self._pending_detections = still_pending
        self._last_flush_time = time.time()

    def save_frame_image(self, frame: np.ndarray, actions: List[str], timestamp: str) -> None:
        """保存帧图像（仅当检测到行为时）"""
        if actions and self.config.SAVE_IMAGE_ON_ACTION:
            try:
                target_dir = self._get_target_dir(actions)
                frame_path = os.path.join(target_dir, f"frame_{timestamp}.jpg")
                cv2.imwrite(frame_path, frame)
            except OSError as e:
                logger.error("保存帧图像失败: %s", e)

    def flush_remaining(self):
        """进程退出前刷新所有待写数据"""
        self._flush()
