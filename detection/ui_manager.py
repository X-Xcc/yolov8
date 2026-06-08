import logging
from typing import List, Tuple

import cv2
import numpy as np

from config import Config
from utils import Utils

logger = logging.getLogger(__name__)


class UIManager:

    def __init__(self, config: Config):
        self.config = config

    def draw_header(self, img: np.ndarray, is_alarm: bool, draw=None) -> np.ndarray:
        """绘制顶部标题栏"""
        header_height = self.config.HEADER_HEIGHT
        header = np.full((header_height, img.shape[1], 3), self.config.COLORS['panel'], dtype=np.uint8)
        header = Utils.draw_text_cn(header, "AI SECURITY SYSTEM", (20, 15), 24, self.config.COLORS['text'])
        live_color = self.config.COLORS['live_red'] if is_alarm else self.config.COLORS['live_green']
        cv2.circle(header, (img.shape[1] - 120, 30), 8, live_color, -1)
        header = Utils.draw_text_cn(header, "LIVE", (img.shape[1] - 100, 15), 20, self.config.COLORS['text'])
        return np.vstack((header, img))

    def draw_card(self, img: np.ndarray, title: str, content: List, pos: Tuple[int, int],
                  width: int, height: int) -> np.ndarray:
        """绘制卡片UI"""
        x, y = pos
        cv2.rectangle(img, (x, y), (x + width, y + height), self.config.COLORS['card_bg'], -1)
        cv2.rectangle(img, (x, y), (x + width, y + height), self.config.COLORS['card_border'], 2)
        img = Utils.draw_text_cn(img, title, (x + 10, y + 20), 18, self.config.COLORS['text'])
        for i, line in enumerate(content):
            if isinstance(line, tuple):
                text, color = line
                img = Utils.draw_text_cn(img, text, (x + 15, y + 50 + i * 30), 14, color)
            else:
                img = Utils.draw_text_cn(img, line, (x + 15, y + 50 + i * 30), 14, self.config.COLORS['text'])
        return img

    def draw_behavior_badge(self, img: np.ndarray, behavior: str, confidence: float, pos: Tuple[int, int]) -> Tuple[np.ndarray, int]:
        """绘制行为标签"""
        if behavior == "跌倒":
            color = self.config.COLORS['danger']
        elif behavior == "打架":
            color = self.config.COLORS['warning']
        elif behavior == "离岗":
            color = self.config.COLORS['leave']
        else:
            color = self.config.COLORS['normal']

        text = f"  {behavior} {confidence:.2f}  "
        text_width, _ = Utils.measure_text_size(text, 16)
        x, y = pos
        rect_height = 30
        cv2.rectangle(img, (x, y), (x + text_width + 10, y + rect_height), color, -1)
        cv2.rectangle(img, (x, y), (x + text_width + 10, y + rect_height), (0, 0, 0), 1)
        img = Utils.draw_text_cn(img, text, (x + 5, y + 5), 16, self.config.COLORS['bg'])
        return img, text_width + 20

    def draw_fps(self, img: np.ndarray, fps: float) -> np.ndarray:
        """绘制FPS卡片"""
        card_width = 120
        card_height = 40
        x = img.shape[1] - card_width - 10
        y = 10
        cv2.rectangle(img, (x, y), (x + card_width, y + card_height), self.config.COLORS['panel'], -1)
        cv2.rectangle(img, (x, y), (x + card_width, y + card_height), self.config.COLORS['card_border'], 1)
        fps_text = f"{fps:.1f} FPS"
        cv2.putText(img, fps_text, (x + 10, y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.config.COLORS['text'], 2)
        return img

    def draw_left_panel(self, img: np.ndarray, person_count: int, actions: List[str], logs: List[str], action_confidences: dict) -> np.ndarray:
        """绘制左侧状态面板"""
        panel_width = self.config.PANEL_WIDTH
        panel_height = img.shape[0]
        panel = np.full((panel_height, panel_width, 3), self.config.COLORS['panel'], dtype=np.uint8)

        # OpenCV 画矩形
        cv2.rectangle(panel, (10, 50), (panel_width - 10, 170), self.config.COLORS['card_bg'], -1)
        cv2.rectangle(panel, (10, 50), (panel_width - 10, 170), self.config.COLORS['card_border'], 2)
        cv2.rectangle(panel, (10, 180), (panel_width - 10, 330), self.config.COLORS['card_bg'], -1)
        cv2.rectangle(panel, (10, 180), (panel_width - 10, 330), self.config.COLORS['card_border'], 2)
        cv2.rectangle(panel, (10, 340), (panel_width - 10, 590), self.config.COLORS['card_bg'], -1)
        cv2.rectangle(panel, (10, 340), (panel_width - 10, 590), self.config.COLORS['card_border'], 2)

        # 行为标签矩形
        behavior_x = 20
        behavior_y = 230
        for action in actions:
            confidence = action_confidences.get(action, 0.0)
            color = self.config.COLORS.get('normal', (0, 255, 0))
            if action == "跌倒": color = self.config.COLORS['danger']
            elif action == "打架": color = self.config.COLORS['warning']
            elif action == "离岗": color = self.config.COLORS['leave']
            text = f"  {action} {confidence:.2f}  "
            tw, _ = Utils.measure_text_size(text, 16)
            cv2.rectangle(panel, (behavior_x, behavior_y), (behavior_x + tw + 10, behavior_y + 30), color, -1)
            cv2.rectangle(panel, (behavior_x, behavior_y), (behavior_x + tw + 10, behavior_y + 30), (0, 0, 0), 1)
            behavior_x += tw + 20
            if behavior_x > panel_width - 120:
                behavior_x = 20
                behavior_y += 40

        # 批量文字渲染
        draw = Utils.begin_text_batch(panel)
        Utils.draw_text_cn_batch(draw, "SYSTEM STATUS", (20, 20), 20, self.config.COLORS['text'])

        status = "正常"
        status_color = self.config.COLORS['normal']
        if "跌倒" in actions or "打架" in actions:
            status = "警告"
            status_color = self.config.COLORS['warning']
        Utils.draw_text_cn_batch(draw, "状态信息", (20, 70), 18, self.config.COLORS['text'])
        Utils.draw_text_cn_batch(draw, f"People: {person_count}", (25, 100), 14, self.config.COLORS['text'])
        Utils.draw_text_cn_batch(draw, f"状态: {status}", (25, 130), 14, status_color)

        Utils.draw_text_cn_batch(draw, "行为检测", (20, 200), 18, self.config.COLORS['text'])
        bx = 25
        by = 235
        for action in actions:
            confidence = action_confidences.get(action, 0.0)
            Utils.draw_text_cn_batch(draw, f"  {action} {confidence:.2f}  ", (bx + 5, by + 5), 16, self.config.COLORS['bg'])
            tw, _ = Utils.measure_text_size(f"  {action} {confidence:.2f}  ", 16)
            bx += tw + 20
            if bx > panel_width - 120:
                bx = 25
                by += 40

        Utils.draw_text_cn_batch(draw, "最近日志", (20, 360), 18, self.config.COLORS['text'])
        log_y = 390
        for log in list(logs)[-5:]:
            Utils.draw_text_cn_batch(draw, log, (25, log_y - 5), 14, self.config.COLORS['text'])
            log_y += 30

        panel = Utils.end_text_batch(panel)
        return np.hstack((panel, img))

    def draw_exit_hint(self, img: np.ndarray) -> np.ndarray:
        """绘制退出提示"""
        return Utils.draw_text_cn(
            img,
            "按 Enter 退出系统",
            (img.shape[1] - 250, img.shape[0] - 30),
            20,
            self.config.COLORS['text']
        )
