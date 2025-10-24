"""配置管理模块
提供统一的配置管理功能
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path


@dataclass
class MqttConfig:
    """MQTT配置"""
    broker: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id_prefix: str = "agv_simulator"
    keepalive: int = 60
    qos: int = 0
    retain: bool = False
    
    # VDA5050主题配置
    topic_prefix: str = "uagv/v1"
    
    def get_topics(self, manufacturer: str, serial_number: str) -> Dict[str, str]:
        """获取VDA5050标准主题"""
        base = f"{self.topic_prefix}/{manufacturer}/{serial_number}"
        return {
            "order": f"{base}/order",
            "instantActions": f"{base}/instantActions", 
            "state": f"{base}/state",
            "visualization": f"{base}/visualization",
            "connection": f"{base}/connection"
        }


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    cors_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class StorageConfig:
    """存储配置"""
    base_path: str = "robot_data"
    max_history_entries: int = 100
    auto_cleanup_days: int = 30


@dataclass
class Config:
    """主配置类"""
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    log: LogConfig = field(default_factory=LogConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """从文件加载配置"""
        if not os.path.exists(config_path):
            # 如果配置文件不存在，创建默认配置
            config = cls()
            config.save_to_file(config_path)
            return config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            mqtt=MqttConfig(**data.get('mqtt', {})),
            log=LogConfig(**data.get('log', {})),
            server=ServerConfig(**data.get('server', {})),
            storage=StorageConfig(**data.get('storage', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'mqtt': self.mqtt.__dict__,
            'log': self.log.__dict__,
            'server': self.server.__dict__,
            'storage': self.storage.__dict__
        }
    
    def save_to_file(self, config_path: str):
        """保存配置到文件"""
        data = {
            'mqtt': self.mqtt.__dict__,
            'log': self.log.__dict__,
            'server': self.server.__dict__,
            'storage': self.storage.__dict__
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    



# 全局配置实例
_config: Optional[Config] = None


def get_config(config_path: str = None) -> Config:
    """获取全局配置实例"""
    global _config
    
    if _config is None:
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "SimulatorAGV", "config.json"
            )
        
        _config = Config.from_file(config_path)
    
    return _config


def reload_config(config_path: str = None) -> Config:
    """重新加载配置"""
    global _config
    _config = None
    return get_config(config_path)