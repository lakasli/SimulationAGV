import json
import random
from datetime import datetime
from typing import Dict, Any


def get_timestamp() -> str:
    """获取当前UTC时间戳"""
    return datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """加载配置文件"""
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