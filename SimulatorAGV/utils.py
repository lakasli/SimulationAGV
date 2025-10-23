import json
import random
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared import get_config


def get_timestamp() -> str:
    """获取当前UTC时间戳"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    加载配置文件 (已弃用，建议使用 shared.get_config())
    """
    # 为了向后兼容，保留此函数，但建议使用新的配置管理
    try:
        from shared import AppConfig
        return AppConfig.from_file(config_path).to_dict()
    except Exception:
        # 回退到原始实现
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def generate_vda_mqtt_base_topic(vda_interface: str, vda_version: str, manufacturer: str, serial_number: str) -> str:
    """生成VDA5050 MQTT基础主题"""
    return f"{vda_interface}/{vda_version}/{manufacturer}/{serial_number}"


def get_topic_type(topic: str) -> str:
    """从MQTT主题中提取消息类型"""
    if "/order" in topic:
        return "order"
    elif "/instantActions" in topic:
        return "instantActions"
    elif "/connection" in topic:
        return "connection"
    elif "/state" in topic:
        return "state"
    elif "/visualization" in topic:
        return "visualization"
    else:
        return "unknown"


def get_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """计算两点之间的距离"""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def generate_random_position(min_val: float = -2.5, max_val: float = 2.5) -> tuple:
    """生成随机位置"""
    x = random.uniform(min_val, max_val)
    y = random.uniform(min_val, max_val)
    return x, y