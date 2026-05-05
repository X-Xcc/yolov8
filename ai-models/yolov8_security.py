# 依赖：
# ultralytics
# opencv-python
# numpy
# pillow

# 导入必要的库
import os
import threading
from itertools import combinations

# 直接导入，减少不必要的检查
from ultralytics import YOLO
import cv2
import time
import numpy as np
import json
import torch
from typing import List, Tuple, Optional
from PIL import ImageFont, ImageDraw, Image

# 快速忽略警告，不进行复杂配置
import warnings

warnings.filterwarnings("ignore")

# ===================== GPU/CPU 检测 =====================
print("\n" + "=" * 60)
print("PyTorch 版本:", torch.__version__)
print("CUDA 可用:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("使用设备: 👉 GPU -", torch.cuda.get_device_name(0))
    print("GPU 显存:", torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024, "GB")
else:
    print("使用设备: 🖥 CPU")
    print("警告: GPU 不可用，将使用 CPU（性能会降低）")
print("=" * 60 + "\n") 
# =====================
# ==================================

# 尝试导入 requests，用于发送视频帧到 web 服务器
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("警告: 未安装 requests 库，无法发送视频流到 web 面板")

# Web 服务器配置
WEB_SERVER_URL = os.environ.get("WEB_SERVER_URL", "http://127.0.0.1:5000/yolov8-security")
SEND_FRAME_INTERVAL = 1  # 每1帧发送一次（实时）
JPEG_QUALITY = 50  # 降低JPEG质量以减少传输时间（极致性能）


# ===================== 配置区 =====================
class Config:
    """系统配置类，集中管理所有参数"""
    # 路径配置 - 简化，直接使用固定路径结构
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "yolov8n-pose.pt")
    # 多摄像头支持 - 启动时自动检测可用摄像头
    SOURCES = []  # 启动时由 detect_cameras() 填充
    RESULT_VIDEO_PATH = os.path.join(PROJECT_ROOT, "results", "security_result.mp4")
    DATASET_DIR = os.path.join(PROJECT_ROOT, "backend", "data")

    # 模型参数
    IMG_SIZE = 512
    CONF_THRESH = 0.5
    # 强制使用GPU（如果可用）
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # 检测参数
    FATIGUE_THRESHOLD = 0.05  # 归一化坐标下的移动阈值
    FATIGUE_DURATION = 3
    FIGHTING_THRESHOLD = 0.3
    # 眼疲劳参数
    EYE_AR_THRESHOLD = 0.2  # EAR阈值，低于此值认为是闭眼
    EYE_FATIGUE_FRAMES = 30  # 连续多少帧EAR过低判定为疲劳
    # 人员聚集参数（讲稿要求：阈值3人、聚集半径<1.5m、持续≥3s）
    GATHER_THRESHOLD = 3        # 聚集人数阈值
    GATHER_RADIUS = 0.08       # 归一化聚集半径（约占画面8%，实际按像素换算）
    GATHER_DURATION = 3.0       # 聚集持续秒数

    # 报警参数
    ALERT_COOLDOWN = 5.0

    # 数据保存参数
    SAVE_INTERVAL = 5
    SAVE_IMAGE_ON_ACTION = True

    # UI参数
    PANEL_WIDTH = 300
    HEADER_HEIGHT = 60
    BANNER_HEIGHT = 40

    # 颜色配置 - 直接定义，减少注释
    COLORS = {
        'bg': (30, 30, 30),
        'panel': (45, 45, 45),
        'text': (220, 220, 220),
        'normal': (0, 255, 0),
        'warning': (0, 165, 255),
        'danger': (0, 0, 255),
        'fatigue': (0, 255, 255),
        'leave': (150, 150, 150),
        'live_green': (0, 255, 0),
        'live_red': (0, 0, 255),
        'card_bg': (50, 50, 50),
        'card_border': (60, 60, 60)
    }


# ===================== 摄像头自动检测 =====================
def detect_cameras(max_index=5):
    """扫描USB设备索引0~max_index，返回可用摄像头列表"""
    available = []
    print("正在扫描可用摄像头...")
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
                print(f"  ✓ 摄像头 {i} 可用")
            cap.release()
        else:
            cap.release()
    if not available:
        print("  ✗ 未检测到USB摄像头，将使用默认索引0")
        available = [0]
    else:
        print(f"共检测到 {len(available)} 个摄像头: {available}")
    return available


# ===================== 工具函数 =====================
class Utils:
    """工具函数类"""
    # 静态变量：缓存可用字体路径，避免重复IO操作
    _AVAILABLE_FONT_PATH = None
    # 缓存字体对象（key = font size），避免每次 draw 都重新加载字体文件
    _FONT_CACHE = {}

    # YOLOv8 Pose 关键点索引
    KEYPOINT_NAMES = {
        0: 'nose', 1: 'left_eye', 2: 'right_eye', 3: 'left_ear', 4: 'right_ear',
        5: 'left_shoulder', 6: 'right_shoulder', 7: 'left_elbow', 8: 'right_elbow',
        9: 'left_wrist', 10: 'right_wrist', 11: 'left_hip', 12: 'right_hip',
        13: 'left_knee', 14: 'right_knee', 15: 'left_ankle', 16: 'right_ankle'
    }

    @classmethod
    def _get_available_font_path(cls) -> str:
        """获取可用的字体路径，缓存结果"""
        if cls._AVAILABLE_FONT_PATH is None:
            # 兼容不同系统的字体路径
            font_paths = [
                r"C:\Windows\Fonts\simhei.ttf",  # 黑体
                r"C:\Windows\Fonts\simsun.ttc",  # 宋体
                r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
                r"C:\Windows\Fonts\msyhbd.ttc",  # 微软雅黑粗体
                r"C:\Windows\Fonts\simkai.ttf",  # 楷体
                r"C:\Windows\Fonts\simli.ttf",  # 隶书
                r"C:\Windows\Fonts\simfang.ttf",  # 仿宋
                r"C:\Windows\Fonts\STXINGKA.TTF",  # 行楷
                r"C:\Windows\Fonts\STKAITI.TTF",  # 楷体
                r"C:\Windows\Fonts\STSONG.TTF",  # 宋体
                r"C:\Windows\Fonts\STZHONGS.TTF",  # 黑体
                r"C:\Windows\Fonts\microsoftyahei.ttf",  # 微软雅黑
                r"C:\Windows\Fonts\yahei.ttf",  # 雅黑
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux中文
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # Linux中文
            ]

            # 寻找可用的字体
            for path in font_paths:
                if os.path.exists(path):
                    cls._AVAILABLE_FONT_PATH = path
                    break
        return cls._AVAILABLE_FONT_PATH

    @staticmethod
    def _get_cached_font(size: int):
        """Get or create a cached font for the given size"""
        if size not in Utils._FONT_CACHE:
            font_path = Utils._get_available_font_path()
            if font_path is None:
                Utils._FONT_CACHE[size] = ImageFont.load_default()
            else:
                try:
                    Utils._FONT_CACHE[size] = ImageFont.truetype(font_path, size, encoding="utf-8")
                except (OSError, IOError):
                    Utils._FONT_CACHE[size] = ImageFont.load_default()
        return Utils._FONT_CACHE[size]

    @staticmethod
    def draw_text_cn(img: np.ndarray, text: str, pos: Tuple[int, int],
                     size: int = 30, color: Tuple[int, int, int] = (255, 255, 255)) -> np.ndarray:
        """绘制中文文本，确保正确显示"""
        try:
            # 转换BGR为RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(img_pil)

            # 使用缓存字体
            font = Utils._get_cached_font(size)

            # 绘制文本
            draw.text(pos, text, font=font, fill=color)

            # 转换回BGR
            img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            return img_bgr
        except (OSError, IOError, ValueError) as e:
            print(f"中文绘制失败: {e}")
            return img

    @staticmethod
    def calculate_distance(p1: np.ndarray, p2: np.ndarray) -> float:
        """计算两个关键点之间的欧氏距离"""
        dx = float(p1[0]) - float(p2[0])
        dy = float(p1[1]) - float(p2[1])
        return np.sqrt(dx * dx + dy * dy)

    @staticmethod
    def calculate_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """计算三个点形成的夹角（p2为顶点）"""
        # 转换为向量
        v1 = np.array([float(p1[0]) - float(p2[0]), float(p1[1]) - float(p2[1])])
        v2 = np.array([float(p3[0]) - float(p2[0]), float(p3[1]) - float(p2[1])])

        # 计算夹角余弦值
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
        return np.arccos(np.clip(cos_angle, -1.0, 1.0)) * 180 / np.pi

    @staticmethod
    def get_body_center(keypoints: np.ndarray) -> Optional[np.ndarray]:
        """获取人体躯干中心（胸部位置）"""
        if len(keypoints) >= 13:
            # 基于胸部/肩部关键点计算中心
            return np.mean(keypoints[[5, 6, 11, 12], :2], axis=0)
        return None

    @staticmethod
    def calculate_overlap(bbox1: List[float], bbox2: List[float], img_shape: Tuple[int, int]) -> float:
        """计算两个人体框的重叠度"""
        # 转换为像素坐标
        h, w = img_shape[:2]
        bbox1_pixel = [bbox1[0] * w, bbox1[1] * h, bbox1[2] * w, bbox1[3] * h]
        bbox2_pixel = [bbox2[0] * w, bbox2[1] * h, bbox2[2] * w, bbox2[3] * h]

        # 计算交集
        x1 = max(bbox1_pixel[0], bbox2_pixel[0])
        y1 = max(bbox1_pixel[1], bbox2_pixel[1])
        x2 = min(bbox1_pixel[2], bbox2_pixel[2])
        y2 = min(bbox1_pixel[3], bbox2_pixel[3])

        if x2 < x1 or y2 < y1:
            return 0.0

        # 计算交集面积
        intersection = (x2 - x1) * (y2 - y1)
        # 计算并集面积
        area1 = (bbox1_pixel[2] - bbox1_pixel[0]) * (bbox1_pixel[3] - bbox1_pixel[1])
        area2 = (bbox2_pixel[2] - bbox2_pixel[0]) * (bbox2_pixel[3] - bbox2_pixel[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def generate_timestamp() -> str:
        """生成带毫秒的时间戳"""
        ms = int(time.time() * 1000) % 1000
        return f"{time.strftime('%Y%m%d_%H%M%S')}_{ms:03d}"

    @staticmethod
    def measure_text_size(text: str, font_size: int) -> Tuple[int, int]:
        """测量文本尺寸，避免重复代码"""
        try:
            temp_img = Image.new('RGB', (100, 100))
            temp_draw = ImageDraw.Draw(temp_img)
            font = Utils._get_cached_font(font_size)
            text_bbox = temp_draw.textbbox((0, 0), text, font=font)
            return int(text_bbox[2] - text_bbox[0]), int(text_bbox[3] - text_bbox[1])
        except (OSError, IOError, AttributeError):
            return 80, 20

    @staticmethod
    def calculate_eye_aspect_ratio(keypoints: np.ndarray) -> Tuple[float, bool]:
        """计算双眼高度与宽度的比例（Eye Aspect Ratio - EAR）
        Returns:
            (ear值, 是否有效)
        """
        if len(keypoints) < 17:
            return 0.0, False

        left_eye = keypoints[1]
        right_eye = keypoints[2]
        left_ear = keypoints[3]
        right_ear = keypoints[4]

        left_eye_valid = left_eye[2] > 0.5 and left_ear[2] > 0.5
        right_eye_valid = right_eye[2] > 0.5 and right_ear[2] > 0.5

        if not (left_eye_valid and right_eye_valid):
            return 0.0, False

        eye_width = Utils.calculate_distance(left_eye, right_eye)
        if eye_width == 0:
            return 0.0, False

        left_eye_height = Utils.calculate_distance(left_eye, left_ear)
        right_eye_height = Utils.calculate_distance(right_eye, right_ear)
        avg_eye_height = (left_eye_height + right_eye_height) / 2.0

        ear = avg_eye_height / eye_width
        return ear, True


# ===================== 检测模块 =====================
class DetectionModule:
    """行为检测模块"""

    def __init__(self, config: Config):
        self.config = config

    @staticmethod
    def detect_fall(keypoints: np.ndarray) -> Tuple[bool, float]:
        """基于多维度特征检测跌倒行为 - 优化版本，返回检测结果和置信度"""
        if len(keypoints) < 17:
            return False, 0.0

        # 1. 计算人体包围框的长宽比（跌倒时宽>高）
        valid_kp = keypoints[keypoints[:, 2] > 0.5]  # 只使用置信度>0.5的关键点
        if len(valid_kp) < 5:
            return False, 0.0

        min_x, max_x = valid_kp[:, 0].min(), valid_kp[:, 0].max()
        min_y, max_y = valid_kp[:, 1].min(), valid_kp[:, 1].max()

        height = max_y - min_y
        if height == 0:
            return False, 0.0

        aspect_ratio = (max_x - min_x) / height

        # 2. 头部与臀部的相对位置（跌倒时头部可能低于臀部）
        head_y = keypoints[0][1]  # 鼻子Y坐标
        hip_y = (keypoints[11][1] + keypoints[12][1]) / 2  # 髋部Y坐标
        head_hip_ratio = (head_y - hip_y) / height

        # 3. 腿部角度分析（跌倒时腿部弯曲角度异常）
        left_knee_angle = Utils.calculate_angle(keypoints[11], keypoints[13], keypoints[15])
        right_knee_angle = Utils.calculate_angle(keypoints[12], keypoints[14], keypoints[16])

        # 4. 躯干垂直度（跌倒时躯干水平）
        shoulder_y = (keypoints[5][1] + keypoints[6][1]) / 2
        verticality_ratio = abs(hip_y - shoulder_y) / height

        # 5. 脚踝与髋部的相对位置
        hip_ankle_diff = hip_y - (keypoints[15][1] + keypoints[16][1]) / 2

        # 6. 计算躯干倾斜角度（更准确的姿态判断）
        shoulder_center = (keypoints[5][:2] + keypoints[6][:2]) / 2
        hip_center = (keypoints[11][:2] + keypoints[12][:2]) / 2
        trunk_vector = shoulder_center - hip_center

        trunk_norm = np.linalg.norm(trunk_vector)
        trunk_angle = np.arccos(
            np.clip(-trunk_vector[1] / trunk_norm, -1.0, 1.0)) * 180 / np.pi if trunk_norm > 0 else 0

        # 7. 头部与地面的相对位置（新增特征）
        head_ground_ratio = head_y / max_y

        # 8. 关键点置信度加权（新增特征）
        confidence_score = np.mean(keypoints[:, 2])

        # 综合评分（各项特征加权 - 调整阈值以提高检测率）
        fall_score = 0
        required_features = 0

        # 特征1：长宽比（调整为更合理的值）
        if aspect_ratio > 1.0:
            fall_score += 0.25
            required_features += 1
        elif aspect_ratio > 0.8:
            fall_score += 0.1

        # 特征2：头部低于臀部（调整阈值）
        if head_hip_ratio < -0.05:
            fall_score += 0.2
            required_features += 1

        # 特征3：腿部角度（放松一点，坐着时也可能弯曲）
        if (left_knee_angle < 60 or left_knee_angle > 170) and \
                (right_knee_angle < 60 or right_knee_angle > 170):
            fall_score += 0.15

        # 特征4：躯干垂直度（调整阈值）
        if verticality_ratio < 0.25:
            fall_score += 0.15
            required_features += 1

        # 特征5：脚踝位置
        if hip_ankle_diff > 0.03:
            fall_score += 0.1

        # 特征6：躯干倾斜角度（新增，关键特征）
        if trunk_angle > 40:
            fall_score += 0.15
            required_features += 1

        # 特征7：头部接近地面
        if head_ground_ratio > 0.7:
            fall_score += 0.1

        # 特征8：关键点置信度
        fall_score *= confidence_score

        # 综合判定：必须满足多个条件才判定为跌倒
        is_fall = fall_score > 0.5 and required_features >= 2
        return is_fall, fall_score

    @staticmethod
    def _is_arm_raised(keypoints: np.ndarray) -> bool:
        """检测手臂是否抬起"""
        if len(keypoints) < 10:
            return False
        shoulder_y = (keypoints[5][1] + keypoints[6][1]) / 2
        elbow_y = (keypoints[7][1] + keypoints[8][1]) / 2
        wrist_y = (keypoints[9][1] + keypoints[10][1]) / 2
        return (elbow_y < shoulder_y - 0.05) or (wrist_y < shoulder_y - 0.1)

    def detect_fighting(self, keypoints_list: List[np.ndarray], bboxes: List[List[float]],
                        img_shape: Tuple[int, int]) -> Tuple[bool, List[int]]:
        """基于躯干数据检测打架行为"""
        if len(keypoints_list) < 2:
            return False, []

        h, w = img_shape[:2]
        max_dim = max(w, h)
        fighting_persons = set()

        # 遍历每对人体
        for (i, kp1), (j, kp2) in combinations(enumerate(keypoints_list), 2):
            # 获取躯干中心
            center1 = Utils.get_body_center(kp1)
            center2 = Utils.get_body_center(kp2)

            if center1 is None or center2 is None:
                continue

            # 综合判定
            fight_score = 0

            # 1. 计算躯干中心距离（归一化）
            if Utils.calculate_distance(center1, center2) / max_dim < 0.15:
                fight_score += 0.4

            # 2. 计算人体框重叠度
            if Utils.calculate_overlap(bboxes[i], bboxes[j], img_shape) > 0.1:
                fight_score += 0.3

            # 3. 检测手臂是否抬起（打架时通常手臂抬起）
            if DetectionModule._is_arm_raised(kp1) and DetectionModule._is_arm_raised(kp2):
                fight_score += 0.3

            if fight_score > self.config.FIGHTING_THRESHOLD:
                # 记录打架人员的索引
                fighting_persons.add(i)
                fighting_persons.add(j)

        return len(fighting_persons) > 0, list(fighting_persons)

    def detect_gathering(self, keypoints_list: List[np.ndarray],
                         img_shape: Tuple[int, int],
                         gather_start_times: Optional[dict]) -> Tuple[bool, int, float]:
        """检测人员聚集行为
        讲稿标准：聚集半径<1.5m、持续≥3s、人数阈值≥3人
        返回：(是否聚集, 聚集人数, 聚集置信度)
        """
        n = len(keypoints_list)
        if n < self.config.GATHER_THRESHOLD:
            return False, 0, 0.0

        h, w = img_shape[:2]
        max_dim = max(w, h)

        # 聚类：找出彼此距离在阈值内的人员
        in_gather = [False] * n
        clusters = []

        for i, kp_i in enumerate(keypoints_list):
            center_i = Utils.get_body_center(kp_i)
            if center_i is None:
                continue
            cluster = [i]
            for j, kp_j in enumerate(keypoints_list):
                if j <= i:
                    continue
                center_j = Utils.get_body_center(kp_j)
                if center_j is None:
                    continue
                # 归一化距离
                dist = Utils.calculate_distance(center_i, center_j) / max_dim
                if dist < self.config.GATHER_RADIUS:
                    cluster.append(j)
            clusters.append(cluster)

        # 取最大聚集簇
        best_cluster = max(clusters, key=len)
        gather_count = len(best_cluster)

        if gather_count < self.config.GATHER_THRESHOLD:
            return False, 0, 0.0

        # 计算聚集持续时间
        current_time = time.time()
        cluster_key = tuple(sorted(best_cluster))
        if gather_start_times is None:
            gather_start_times = {}

        if all(in_gather[i] for i in best_cluster):
            # 之前就在聚集中
            pass
        else:
            # 新聚集，记录开始时间
            gather_start_times[cluster_key] = current_time

        start_time = gather_start_times.get(cluster_key, current_time)
        duration = current_time - start_time

        confidence = min(gather_count / 8.0, 1.0)  # 人数越多置信度越高

        is_gathering = duration >= self.config.GATHER_DURATION
        return is_gathering, gather_count, confidence

    def detect_fatigue(self, keypoints: np.ndarray, prev_center: Optional[np.ndarray],
                       last_move_time: float) -> Tuple[bool, float, np.ndarray, float]:
        """检测疲劳状态，返回检测结果、置信度、新的中心和时间"""
        current_time = time.time()
        center = Utils.get_body_center(keypoints)

        if center is None:
            return False, 0.0, prev_center, last_move_time

        if prev_center is not None:
            distance = Utils.calculate_distance(center, prev_center)

            if distance > self.config.FATIGUE_THRESHOLD:
                last_move_time = current_time
                return False, 0.0, center, last_move_time
            else:
                static_duration = current_time - last_move_time
                static_ratio = min(static_duration / self.config.FATIGUE_DURATION, 1.0)

                if static_duration > self.config.FATIGUE_DURATION:
                    return True, static_ratio, center, last_move_time
                else:
                    return False, static_ratio, center, last_move_time
        else:
            last_move_time = current_time
            return False, 0.0, center, last_move_time

    def detect_eye_fatigue(self, keypoints: np.ndarray, eye_fatigue_count: int) -> Tuple[bool, int]:
        """检测眼疲劳状态
        Returns:
            (是否疲劳, 累计低EAR帧数)
        """
        ear, is_valid = Utils.calculate_eye_aspect_ratio(keypoints)

        if not is_valid:
            return False, 0

        if ear < self.config.EYE_AR_THRESHOLD:
            eye_fatigue_count += 1
        else:
            eye_fatigue_count = 0

        if eye_fatigue_count >= self.config.EYE_FATIGUE_FRAMES:
            return True, eye_fatigue_count

        return False, eye_fatigue_count

    def detect_security_actions(self, pose_results: List, prev_centers: Optional[List[np.ndarray]],
                                last_move_times: Optional[List[float]],
                                eye_fatigue_counts: Optional[List[int]] = None,
                                gather_start_times: Optional[dict] = None) -> Tuple[List[str], int, List[int], List[int], List[int], List[np.ndarray], List[float], List[int], dict, dict]:
        """检测所有安全行为，支持多人检测"""
        detected_actions = set()
        person_count = 0
        keypoints_list = []
        bboxes = []
        img_shape = None
        new_prev_centers = prev_centers if prev_centers is not None else []
        new_last_move_times = last_move_times if last_move_times is not None else []
        new_eye_fatigue_counts = eye_fatigue_counts if eye_fatigue_counts is not None else []
        new_gather_start_times = gather_start_times if gather_start_times is not None else {}
        fighting_persons = []
        fatigued_persons = []
        eye_fatigued_persons = []
        action_confidences = {}

        for r in pose_results:
            if r.keypoints is None:
                continue

            img_shape = r.orig_img.shape
            keypoints = r.keypoints.data
            person_count = len(keypoints)

            # 确保跟踪数据结构大小匹配
            new_prev_centers = new_prev_centers[:person_count]
            new_last_move_times = new_last_move_times[:person_count]
            new_eye_fatigue_counts = new_eye_fatigue_counts[:person_count]
            while len(new_prev_centers) < person_count:
                new_prev_centers.append(None)
            while len(new_last_move_times) < person_count:
                new_last_move_times.append(time.time())
            while len(new_eye_fatigue_counts) < person_count:
                new_eye_fatigue_counts.append(0)

            # 收集关键点和边界框 - 优化内存管理
            for i, kp in enumerate(keypoints):
                # 延迟CPU转换，只在需要时进行
                kp_np = kp.cpu().numpy() if hasattr(kp, 'cpu') else kp
                keypoints_list.append(kp_np)

                if len(r.boxes) > i:
                    # 延迟CPU转换
                    bbox = (
                        r.boxes[i].xyxy[0].cpu().numpy()
                        if hasattr(r.boxes[i].xyxy[0], 'cpu')
                        else r.boxes[i].xyxy[0]
                    )
                    bboxes.append(bbox / [img_shape[1], img_shape[0], img_shape[1], img_shape[0]])

                # 跌倒检测
                is_fall, fall_confidence = DetectionModule.detect_fall(kp_np)
                if is_fall:
                    detected_actions.add("跌倒")
                    action_confidences["跌倒"] = fall_confidence

                # 疲劳检测（支持多人）
                is_fatigue, fatigue_confidence, center, move_time = self.detect_fatigue(
                    kp_np, new_prev_centers[i], new_last_move_times[i]
                )
                if is_fatigue:
                    detected_actions.add("疲劳")
                    fatigued_persons.append(i)
                    action_confidences["疲劳"] = fatigue_confidence
                
                # 更新跟踪数据
                new_prev_centers[i] = center
                new_last_move_times[i] = move_time

                # 眼疲劳检测
                is_eye_fatigue, eye_fatigue_count = self.detect_eye_fatigue(
                    kp_np, new_eye_fatigue_counts[i]
                )
                if is_eye_fatigue:
                    detected_actions.add("疲劳")
                    eye_fatigued_persons.append(i)
                    action_confidences["疲劳"] = 1.0
                new_eye_fatigue_counts[i] = eye_fatigue_count

            # 打架检测
            if person_count >= 2 and img_shape is not None:
                is_fighting, fight_persons = self.detect_fighting(keypoints_list, bboxes, img_shape)
                if is_fighting:
                    detected_actions.add("打架")
                    fighting_persons = fight_persons
                    action_confidences["打架"] = 1.0  # 简化处理

            # 离岗检测
            if person_count == 0:
                detected_actions.add("离岗")
                action_confidences["离岗"] = 1.0

            # 人员聚集检测
            if person_count >= 2 and img_shape is not None:
                is_gathering, gather_count, gather_conf = self.detect_gathering(
                    keypoints_list, img_shape, new_gather_start_times
                )
                if is_gathering:
                    detected_actions.add("人员聚集")
                    action_confidences["人员聚集"] = gather_conf

        return (list(detected_actions), person_count, fighting_persons, fatigued_persons,
                eye_fatigued_persons, new_prev_centers, new_last_move_times,
                new_eye_fatigue_counts, action_confidences, new_gather_start_times)


# ===================== 数据保存模块 =====================
class DataSaver:
    """数据保存模块"""

    def __init__(self, config: Config):
        self.config = config
        # 创建必要的目录
        os.makedirs(os.path.dirname(config.RESULT_VIDEO_PATH), exist_ok=True)
        os.makedirs(config.DATASET_DIR, exist_ok=True)

    def save_detection_data(self, actions: List[str], person_count: int, fps: float, frame_count: int) -> str:
        """保存检测数据为JSON文件，返回时间戳"""
        # 生成时间戳文件名
        timestamp = Utils.generate_timestamp()

        # 构建检测数据
        detection_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "person_count": person_count,
            "actions": actions,
            "frame_count": frame_count,
            "fps": fps,
            "image_filename": f"frame_{timestamp}.jpg"  # 关联的图片文件名
        }

        # 保存JSON文件
        json_path = os.path.join(self.config.DATASET_DIR, f"detection_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(detection_data, f, ensure_ascii=False, indent=2)

        return timestamp

    def save_frame_image(self, frame: np.ndarray, actions: List[str], timestamp: str) -> None:
        """保存帧图像（仅当检测到行为时）"""
        if actions and self.config.SAVE_IMAGE_ON_ACTION:
            frame_path = os.path.join(self.config.DATASET_DIR, f"frame_{timestamp}.jpg")
            # type: ignore[arg-type]
            cv2.imwrite(frame_path, frame)


# ===================== 报警模块 =====================
class AlertManager:
    """报警管理模块"""

    def __init__(self, config: Config):
        self.config = config
        self.last_alert_time = 0.0

    def check_and_trigger_alert(self, actions: List[str], frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """检查是否需要触发报警"""
        is_alarm = "跌倒" in actions or "打架" in actions
        alert_triggered = False

        if is_alarm:
            current_time = time.time()
            if current_time - self.last_alert_time > self.config.ALERT_COOLDOWN:
                # 触发报警
                frame = self._draw_alert_banner(frame)
                self.last_alert_time = current_time
                alert_triggered = True
            else:
                # 仍在冷却期内，仅绘制报警横幅
                frame = self._draw_alert_banner(frame)

        return frame, alert_triggered

    def _draw_alert_banner(self, img: np.ndarray) -> np.ndarray:
        """绘制报警横幅"""
        banner_height = self.config.BANNER_HEIGHT
        banner = np.full((banner_height, img.shape[1], 3), self.config.COLORS['danger'], dtype=np.uint8)

        alert_text = "⚠ 危险行为检测中 ⚠"
        text_size = 20
        text_width, _ = Utils.measure_text_size(alert_text, text_size)
        text_x = (img.shape[1] - text_width) // 2

        banner = Utils.draw_text_cn(banner, alert_text, (text_x, 5), text_size, (255, 255, 255))
        return np.vstack((banner, img))

    # ===================== UI模块 =====================
class UIManager:
    """UI绘制管理模块"""

    def __init__(self, config: Config):
        self.config = config

    def draw_header(self, img: np.ndarray, is_alarm: bool) -> np.ndarray:
        """绘制顶部标题栏"""
        # 创建标题栏
        header_height = self.config.HEADER_HEIGHT
        header = np.full((header_height, img.shape[1], 3), self.config.COLORS['panel'], dtype=np.uint8)

        # 绘制左侧标题
        header = Utils.draw_text_cn(header, "AI SECURITY SYSTEM", (20, 15), 24, self.config.COLORS['text'])

        # 绘制右侧状态灯和文字
        live_text = "LIVE"
        live_color = self.config.COLORS['live_red'] if is_alarm else self.config.COLORS['live_green']

        # 绘制状态圆点
        circle_radius = 8
        circle_center = (img.shape[1] - 120, 30)
        cv2.circle(header, circle_center, circle_radius, live_color, -1)

        # 绘制LIVE文字
        header = Utils.draw_text_cn(header, live_text, (img.shape[1] - 100, 15), 20, self.config.COLORS['text'])

        # 将标题栏添加到图像顶部
        return np.vstack((header, img))

    def draw_card(self, img: np.ndarray, title: str, content: List, pos: Tuple[int, int],
                  width: int, height: int) -> np.ndarray:
        """绘制卡片UI"""
        x, y = pos

        # 绘制卡片背景
        cv2.rectangle(img, (x, y), (x + width, y + height), self.config.COLORS['card_bg'], -1)

        # 绘制卡片边框
        cv2.rectangle(img, (x, y), (x + width, y + height), self.config.COLORS['card_border'], 2)

        # 绘制卡片标题
        img = Utils.draw_text_cn(img, title, (x + 10, y + 20), 18, self.config.COLORS['text'])

        # 绘制卡片内容
        for i, line in enumerate(content):
            if isinstance(line, tuple):
                # 带颜色的文本
                text, color = line
                img = Utils.draw_text_cn(img, text, (x + 15, y + 50 + i * 30), 14, color)
            else:
                # 普通文本
                img = Utils.draw_text_cn(img, line, (x + 15, y + 50 + i * 30), 14, self.config.COLORS['text'])

        return img

    def draw_behavior_badge(self, img: np.ndarray, behavior: str, confidence: float, pos: Tuple[int, int]) -> Tuple[np.ndarray, int]:
        """绘制行为标签，显示置信度"""
        if behavior == "跌倒":
            color = self.config.COLORS['danger']
        elif behavior == "打架":
            color = self.config.COLORS['warning']
        elif behavior == "疲劳":
            color = self.config.COLORS['fatigue']
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
        # FPS卡片位置（右上角）
        card_width = 120
        card_height = 40
        x = img.shape[1] - card_width - 10
        y = 10

        # 绘制卡片背景
        cv2.rectangle(img, (x, y), (x + card_width, y + card_height), self.config.COLORS['panel'], -1)
        cv2.rectangle(img, (x, y), (x + card_width, y + card_height), self.config.COLORS['card_border'], 1)

        # 绘制FPS文本
        fps_text = f"{fps:.1f} FPS"
        cv2.putText(img, fps_text, (x + 10, y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.config.COLORS['text'], 2)

        return img

    def draw_left_panel(self, img: np.ndarray, person_count: int, actions: List[str], logs: List[str], action_confidences: dict) -> np.ndarray:
        """绘制左侧状态面板，显示行为置信度"""
        panel_width = self.config.PANEL_WIDTH
        panel_height = img.shape[0]

        # 创建左侧面板
        panel = np.full((panel_height, panel_width, 3), self.config.COLORS['panel'], dtype=np.uint8)

        # 绘制面板标题
        panel = Utils.draw_text_cn(panel, "SYSTEM STATUS", (20, 20), 20, self.config.COLORS['text'])

        # 1. 状态卡片
        status_card_height = 120
        status = "正常"
        status_color = self.config.COLORS['normal']
        if "跌倒" in actions or "打架" in actions:
            status = "警告"
            status_color = self.config.COLORS['warning']

        status_content = [
            (f"People: {person_count}", self.config.COLORS['text']),
            (f"状态: {status}", status_color)
        ]
        panel = self.draw_card(panel, "状态信息", status_content, (10, 50), panel_width - 20, status_card_height)

        # 2. 行为标签卡片
        behavior_card_height = 150
        panel = self.draw_card(panel, "行为检测", [], (10, 180), panel_width - 20, behavior_card_height)

        # 绘制行为标签
        behavior_start_y = 230
        behavior_x = 20
        for action in actions:
            confidence = action_confidences.get(action, 0.0)
            panel, text_width = self.draw_behavior_badge(panel, action, confidence, (behavior_x, behavior_start_y))
            behavior_x += text_width
            if behavior_x > panel_width - 120:
                behavior_x = 20
                behavior_start_y += 40

        # 3. 日志卡片
        log_card_height = 250
        panel = self.draw_card(panel, "最近日志", [], (10, 340), panel_width - 20, log_card_height)

        # 绘制日志内容
        log_start_y = 390
        log_x = 25
        for log in logs[-5:]:  # 只显示最近5条
            panel = Utils.draw_text_cn(panel, log, (log_x, log_start_y - 5), 14, self.config.COLORS['text'])
            log_start_y += 30

        # 将面板与主图像合并
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


# ===================== 主程序 =====================
class SecurityMonitor:
    """安防监控主程序"""

    def __init__(self):
        self.config = Config()

        # 自动检测可用摄像头
        self.config.SOURCES = detect_cameras(max_index=5)

        self.detection_module = DetectionModule(self.config)
        self.data_saver = DataSaver(self.config)
        self.alert_manager = AlertManager(self.config)
        self.ui_manager = UIManager(self.config)

        self.model = YOLO(self.config.MODEL_PATH)

        # 是否启用 web 视频流
        self.enable_web_stream = HAS_REQUESTS

        # 创建请求会话（连接复用）
        self.session = requests.Session() if HAS_REQUESTS else None

        # 调整帧大小以减少传输数据量 - 16:9比例，适合观看
        self.web_stream_width = 960  # 发送到web的帧宽度
        self.web_stream_height = 540  # 发送到web的帧高度 (16:9)

        # 多摄像头线程控制
        self._stop_event = threading.Event()
        self._threads = []

    def _init_video_source(self, source=0):
        """初始化视频源"""
        cap = None
        try:
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                print(f"视频源 {source} 打开失败")
                return True, None, 1280, 720

            # 设置摄像头参数
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)

            # 获取摄像头分辨率
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return False, cap, frame_width, frame_height
        except Exception as e:
            print(f"初始化视频源 {source} 时出错: {e}")
            return True, None, 1280, 720

    def _init_video_writer(self):
        """初始化视频写入器"""
        new_frame_width = self.frame_width + self.config.PANEL_WIDTH
        new_frame_height = self.frame_height + self.config.HEADER_HEIGHT

        # 确保输出目录存在
        results_dir = os.path.dirname(self.config.RESULT_VIDEO_PATH)
        os.makedirs(results_dir, exist_ok=True)

        # 使用MP4兼容的编码器
        # type: ignore[attr-defined]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # type: ignore[arg-type]
        out = cv2.VideoWriter(self.config.RESULT_VIDEO_PATH, fourcc, 30.0,
                               (new_frame_width, new_frame_height), isColor=True)

        # 检查视频写入器是否成功打开
        if not out.isOpened():
            print("警告：视频写入器初始化失败，将不会保存视频")
            out = None
        else:
            print(f"视频写入器初始化成功，输出路径: {self.config.RESULT_VIDEO_PATH}")
            print(f"视频尺寸: {new_frame_width}x{new_frame_height}")

        return out, (new_frame_width, new_frame_height)

    def send_frame_to_web(self, frame: np.ndarray, cam: str = "0") -> bool:
        """发送原始视频帧到 web 服务器 - 支持多摄像头"""
        if not self.enable_web_stream or self.session is None:
            return False

        try:
            # 调整帧大小以减少数据量
            frame_resized = cv2.resize(frame, (self.web_stream_width, self.web_stream_height))

            # 压缩帧为 JPEG，使用较低质量以提高速度
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            _, img_encoded = cv2.imencode('.jpg', frame_resized, encode_params)

            # 使用连接池发送 POST 请求，附带摄像头ID
            response = self.session.post(
                f"{WEB_SERVER_URL}/api/update_frame",
                files={'frame': ('frame.jpg', img_encoded.tobytes(), 'image/jpeg')},
                data={'cam': cam},
                timeout=0.5
            )
            return response.status_code == 200
        except Exception:
            # 发送失败静默处理
            return False

    def report_model_info(self):
        """向 Java 后端报告模型信息"""
        if not HAS_REQUESTS:
            return
        try:
            model_size = 0
            try:
                model_size = os.path.getsize(self.config.MODEL_PATH) / 1024 / 1024
            except OSError:
                pass
            info = {
                "precision": "FP16" if torch.cuda.is_available() else "FP32",
                "device": "cuda" if torch.cuda.is_available() else "cpu",
                "model_size_mb": round(model_size, 1),
                "total_layers": 0,
                "conv_layers": 0,
                "quantized_layers": 0,
                "gpu_available": torch.cuda.is_available(),
                "half_precision": torch.cuda.is_available()
            }
            requests.post(
                f"{WEB_SERVER_URL}/api/model_info",
                json=info,
                timeout=2
            )
        except Exception:
            pass  # 静默失败

    def run(self):
        """主运行循环 - 多摄像头模式"""
        sources = self.config.SOURCES
        if not sources:
            print("没有可用的摄像头，退出。")
            return

        print(f"\n系统启动，共 {len(sources)} 个摄像头: {sources}")
        print("按 Enter 退出系统\n")
        if self.enable_web_stream:
            print(f"视频流将发送到: {WEB_SERVER_URL}")

        # 启动时报告模型信息
        self.report_model_info()

        # 为每个摄像头启动独立线程
        self._threads = []
        for cam_id in sources:
            t = threading.Thread(target=self._run_camera_thread, args=(cam_id,), daemon=True)
            t.start()
            self._threads.append(t)

        # 主线程等待退出信号
        try:
            while not self._stop_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n收到中断信号，正在停止...")
            self._stop_event.set()

        # 等待所有线程结束
        for t in self._threads:
            t.join(timeout=3)

        cv2.destroyAllWindows()
        print("系统已退出")

    def _get_frame_from_cap(self, cap, use_static, test_image):
        """从指定摄像头获取视频帧"""
        if use_static:
            return test_image.copy(), use_static
        try:
            ret, frame = cap.read()
            if not ret:
                print("无法获取视频帧，切换到静态图像模式...")
                return test_image.copy(), True
            return frame, False
        except Exception as e:
            print(f"读取视频帧时出错: {e}")
            return test_image.copy(), True

    def _run_camera_thread(self, cam_id):
        """单个摄像头的检测循环（在线程中运行）"""
        source = int(cam_id)
        cam_str = str(cam_id)
        print(f"[摄像头 {cam_str}] 线程启动，视频源: {source}")

        # 初始化视频源
        use_static, cap, frame_width, frame_height = self._init_video_source(source)
        if use_static:
            test_image = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(test_image, f"Camera {cam_str}", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        else:
            test_image = np.zeros((720, 1280, 3), dtype=np.uint8)

        # 每个摄像头独立的会话
        session = requests.Session() if HAS_REQUESTS else None

        # 状态变量
        prev_centers = []
        last_move_times = []
        eye_fatigue_counts = []
        gather_start_times = {}
        logs = []
        prev_actions = []
        frame_count = 0
        start_time = time.time()
        last_model_info_time = time.time()

        # 窗口名（每个摄像头独立窗口）
        window_name = f"Camera {cam_str}"

        try:
            while not self._stop_event.is_set():
                # 1. 读取帧
                frame, use_static = self._get_frame_from_cap(cap, use_static, test_image)
                if use_static and cap is not None:
                    cap.release()
                    cap = None
                frame_count += 1

                # 2. 模型推理
                results = self.model(
                    frame,
                    imgsz=self.config.IMG_SIZE,
                    conf=self.config.CONF_THRESH,
                    device=self.config.DEVICE,
                    half=torch.cuda.is_available(),
                    batch=False
                )

                # 3. 检测行为
                actions, person_num, fighting_persons, fatigued_persons, eye_fatigued_persons, prev_centers, last_move_times, eye_fatigue_counts, action_confidences, gather_start_times = self.detection_module.detect_security_actions(
                    results, prev_centers, last_move_times, eye_fatigue_counts, gather_start_times
                )

                # 4. 可视化关键点
                frame_out = results[0].plot() if results and len(results) > 0 else frame.copy()

                # 5. 框选打架人员
                if "打架" in actions and results and len(results) > 0:
                    self._draw_fighting_persons(results[0], fighting_persons, frame_out)

                # 6. 标红疲劳人员
                if "疲劳" in actions and results and len(results) > 0:
                    all_fatigued = list(set(fatigued_persons + eye_fatigued_persons))
                    self._draw_fatigued_persons(results[0], all_fatigued, frame_out)

                # 7. 绘制人员聚集框
                if "人员聚集" in actions and results and len(results) > 0:
                    all_kp = []
                    for r in results:
                        if r.keypoints is not None:
                            for kp in r.keypoints.data:
                                all_kp.append(kp.cpu().numpy() if hasattr(kp, 'cpu') else kp)
                    if len(all_kp) >= self.config.GATHER_THRESHOLD:
                        self._draw_gathering_persons(results[0], all_kp, frame_out)

                # 8. 发送帧到 web（带摄像头ID）
                if frame_count % SEND_FRAME_INTERVAL == 0 and session is not None:
                    self._send_frame_session(frame, cam_str, session)

                # 9. 日志
                current_time_str = time.strftime("%H:%M:%S")
                for action in actions:
                    if action not in prev_actions:
                        log_entry = f"[{current_time_str}] [CAM-{cam_str}] {action}"
                        logs.append(log_entry)
                prev_actions = actions.copy()

                # 10. FPS
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0

                # 11. 每60秒报告模型信息（仅摄像头0负责）
                now = time.time()
                if cam_str == "0" and now - last_model_info_time > 60:
                    self.report_model_info()
                    last_model_info_time = now

                # 12. 绘制UI
                is_alarm = "跌倒" in actions or "打架" in actions
                frame_out = self._draw_ui(frame_out, is_alarm, actions, logs, action_confidences, person_num, fps)

                # 13. 显示
                cv2.imshow(window_name, frame_out)

                # 14. 保存检测数据（仅摄像头0负责，避免重复）
                if cam_str == "0" and frame_count % self.config.SAVE_INTERVAL == 0:
                    timestamp = self.data_saver.save_detection_data(actions, person_num, fps, frame_count)
                    if actions:
                        self.data_saver.save_frame_image(frame, actions, timestamp)

                # 15. 检查退出（任意窗口按Enter退出全部）
                key = cv2.waitKey(1) & 0xFF
                if key == 13:
                    print(f"[摄像头 {cam_str}] 收到退出信号，停止所有摄像头...")
                    self._stop_event.set()
                    break

        except Exception as e:
            print(f"[摄像头 {cam_str}] 线程异常: {e}")
        finally:
            if cap is not None:
                cap.release()
            if session is not None:
                session.close()
            print(f"[摄像头 {cam_str}] 线程结束")

    def _send_frame_session(self, frame, cam, session):
        """使用指定会话发送帧到web服务器"""
        try:
            frame_resized = cv2.resize(frame, (self.web_stream_width, self.web_stream_height))
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            _, img_encoded = cv2.imencode('.jpg', frame_resized, encode_params)
            session.post(
                f"{WEB_SERVER_URL}/api/update_frame",
                files={'frame': ('frame.jpg', img_encoded.tobytes(), 'image/jpeg')},
                data={'cam': cam},
                timeout=0.5
            )
        except Exception:
            pass

    def _draw_fighting_persons(self, result, fighting_persons, frame_out):
        """框选打架人员"""
        try:
            if result.boxes is not None:
                for i in fighting_persons:
                    if i < len(result.boxes):
                        bbox = result.boxes[i].xyxy[0].cpu().numpy() if hasattr(result.boxes[i].xyxy[0], 'cpu') else result.boxes[i].xyxy[0]
                        x1, y1, x2, y2 = map(int, bbox)
                        # 绘制红色边框
                        cv2.rectangle(frame_out, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        # 绘制标签
                        cv2.putText(frame_out, "打架", (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        except Exception as e:
            print(f"框选打架人员失败: {e}")

    def _draw_fatigued_persons(self, result, fatigued_persons, frame_out):
        """标红疲劳人员的关键点"""
        try:
            if result.keypoints is not None:
                keypoints = result.keypoints.data
                for i in fatigued_persons:
                    if i < len(keypoints):
                        kp = keypoints[i].cpu().numpy() if hasattr(keypoints[i], 'cpu') else keypoints[i]
                        for j in range(len(kp)):
                            if kp[j][2] > 0.5:
                                x, y = int(kp[j][0]), int(kp[j][1])
                                cv2.circle(frame_out, (x, y), 5, (0, 0, 255), -1)
        except Exception as e:
            print(f"标红疲劳人员关键点失败: {e}")

    def _draw_gathering_persons(self, result, keypoints_list, frame_out):
        """用黄色圆弧框选聚集人员"""
        try:
            n = len(keypoints_list)
            if n < self.config.GATHER_THRESHOLD:
                return
            h, w = frame_out.shape[:2]
            max_dim = max(w, h)
            # 找聚集簇
            clusters = []
            used = [False] * n
            for i in range(n):
                if used[i]:
                    continue
                center_i = Utils.get_body_center(keypoints_list[i])
                if center_i is None:
                    continue
                cluster = [i]
                used[i] = True
                for j in range(i + 1, n):
                    if used[j]:
                        continue
                    center_j = Utils.get_body_center(keypoints_list[j])
                    if center_j is None:
                        continue
                    dist = Utils.calculate_distance(center_i, center_j) / max_dim
                    if dist < self.config.GATHER_RADIUS:
                        cluster.append(j)
                        used[j] = True
                clusters.append(cluster)
            best = max(clusters, key=len) if clusters else []
            if len(best) < self.config.GATHER_THRESHOLD:
                return
            # 取最外圈
            xs = [Utils.get_body_center(keypoints_list[i])[0] * w for i in best]
            ys = [Utils.get_body_center(keypoints_list[i])[1] * h for i in best]
            if not xs:
                return
            min_x, max_x = int(min(xs)), int(max(xs))
            min_y, max_y = int(min(ys)), int(max(ys))
            pad = 20
            cv2.rectangle(frame_out, (min_x - pad, min_y - pad), (max_x + pad, max_y + pad),
                         (0, 255, 255), 3)
            label = f"人员聚集 {len(best)}人"
            cv2.putText(frame_out, label, (min_x - pad, min_y - pad - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        except Exception as e:
            print(f"绘制聚集人员失败: {e}")

    def _draw_ui(self, frame_out, is_alarm, actions, logs, action_confidences, person_num, fps):
        """绘制UI"""
        # 绘制标题栏
        frame_out = self.ui_manager.draw_header(frame_out, is_alarm)

        # 绘制报警横幅
        frame_out, _ = self.alert_manager.check_and_trigger_alert(actions, frame_out)

        # 绘制FPS卡片
        frame_out = self.ui_manager.draw_fps(frame_out, fps)

        # 绘制左侧面板
        frame_out = self.ui_manager.draw_left_panel(frame_out, person_num, actions, logs, action_confidences)

        # 绘制退出提示
        frame_out = self.ui_manager.draw_exit_hint(frame_out)

        return frame_out


# ===================== 程序入口 =====================
if __name__ == "__main__":
    monitor = SecurityMonitor()
    monitor.run()