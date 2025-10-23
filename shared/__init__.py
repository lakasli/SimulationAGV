"""
共享模块
包含项目中通用的工具和配置
"""

from .logger_config import setup_logger, logger
from .config_manager import AppConfig, get_config, reload_config
from .models import (
    RobotStatusEnum, RobotType, Position, BatteryState, 
    SafetyState, RobotStatus, RobotInfo, RobotGroup, RobotLabel
)
from .serialization import (
    SerializationMixin, safe_serialize, safe_deserialize,
    to_json, from_json, create_json_response, batch_serialize, batch_deserialize
)
from .http_server import BaseHTTPServer, SimpleHTTPServer, create_simple_server, run_simple_server

__all__ = [
    # 日志
    'setup_logger', 'logger',
    # 配置管理
    'AppConfig', 'get_config', 'reload_config',
    # 数据模型
    'RobotStatusEnum', 'RobotType', 'Position', 'BatteryState', 
    'SafetyState', 'RobotStatus', 'RobotInfo', 'RobotGroup', 'RobotLabel',
    # 序列化工具
    'SerializationMixin', 'safe_serialize', 'safe_deserialize',
    'to_json', 'from_json', 'create_json_response', 'batch_serialize', 'batch_deserialize',
    # HTTP服务器
    'BaseHTTPServer', 'SimpleHTTPServer', 'create_simple_server', 'run_simple_server'
]

# 版本信息
__version__ = "1.0.0"