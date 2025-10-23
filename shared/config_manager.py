"""
配置管理中心
统一管理项目中的所有配置参数
"""
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class MQTTConfig:
    """MQTT配置"""
    host: str = "localhost"
    port: int = 1883
    keepalive: int = 60
    username: Optional[str] = None
    password: Optional[str] = None
    client_id_prefix: str = "agv_"
    qos: int = 1
    retain: bool = False
    vda_interface: str = "uagv"


@dataclass
class RedisConfig:
    """Redis配置"""
    url: str = "redis://localhost:6379"
    db: int = 0
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # 键前缀配置
    robot_state_prefix: str = "robot:state:"
    robot_config_prefix: str = "robot:config:"
    robot_order_prefix: str = "robot:order:"
    robot_history_prefix: str = "robot:history:"
    active_robots_set: str = "active_robots"
    cache_stats_key: str = "cache:stats"
    
    # 过期时间配置
    state_ttl: int = 300
    config_ttl: int = 3600
    order_ttl: int = 1800
    history_ttl: int = 86400


@dataclass
class VehicleConfig:
    """车辆配置"""
    serial_number: str = "AGV-001"
    manufacturer: str = "SimulatorAGV"
    vda_version: str = "v2"
    vda_full_version: str = "2.0.0"


@dataclass
class SystemConfig:
    """系统配置"""
    map_id: str = "default"
    state_frequency: int = 1
    visualization_frequency: int = 1
    action_time: float = 1.0
    robot_count: int = 1
    speed: float = 0.05
    
    # API服务器配置
    api_host: str = "127.0.0.1"
    api_port: int = 8001
    status_api_port: int = 8002
    
    # 监控配置
    state_timeout: int = 30
    cleanup_interval: int = 300
    monitor_interval: int = 10
    max_history_entries: int = 1000
    batch_size: int = 100


@dataclass
class AppConfig:
    """应用配置"""
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    vehicle: VehicleConfig = field(default_factory=VehicleConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'AppConfig':
        """从配置文件加载配置"""
        if not os.path.exists(config_path):
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = cls()
            
            # 加载MQTT配置
            if 'mqtt_broker' in data:
                mqtt_data = data['mqtt_broker']
                config.mqtt = MQTTConfig(
                    host=mqtt_data.get('host', config.mqtt.host),
                    port=mqtt_data.get('port', config.mqtt.port),
                    username=mqtt_data.get('username'),
                    password=mqtt_data.get('password'),
                    vda_interface=mqtt_data.get('vda_interface', config.mqtt.vda_interface)
                )
            
            # 加载车辆配置
            if 'vehicle' in data:
                vehicle_data = data['vehicle']
                config.vehicle = VehicleConfig(
                    serial_number=vehicle_data.get('serial_number', config.vehicle.serial_number),
                    manufacturer=vehicle_data.get('manufacturer', config.vehicle.manufacturer),
                    vda_version=vehicle_data.get('vda_version', config.vehicle.vda_version),
                    vda_full_version=vehicle_data.get('vda_full_version', config.vehicle.vda_full_version)
                )
            
            # 加载系统配置
            if 'settings' in data:
                settings_data = data['settings']
                config.system.map_id = settings_data.get('map_id', config.system.map_id)
                config.system.state_frequency = settings_data.get('state_frequency', config.system.state_frequency)
                config.system.visualization_frequency = settings_data.get('visualization_frequency', config.system.visualization_frequency)
                config.system.action_time = settings_data.get('action_time', config.system.action_time)
                config.system.robot_count = settings_data.get('robot_count', config.system.robot_count)
                config.system.speed = settings_data.get('speed', config.system.speed)
            
            return config
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "mqtt_broker": {
                "host": self.mqtt.host,
                "port": self.mqtt.port,
                "vda_interface": self.mqtt.vda_interface,
                "username": self.mqtt.username,
                "password": self.mqtt.password
            },
            "vehicle": {
                "serial_number": self.vehicle.serial_number,
                "manufacturer": self.vehicle.manufacturer,
                "vda_version": self.vehicle.vda_version,
                "vda_full_version": self.vehicle.vda_full_version
            },
            "settings": {
                "map_id": self.system.map_id,
                "state_frequency": self.system.state_frequency,
                "visualization_frequency": self.system.visualization_frequency,
                "action_time": self.system.action_time,
                "robot_count": self.system.robot_count,
                "speed": self.system.speed
            }
        }
    
    def save_to_file(self, config_path: str):
        """保存配置到文件"""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get_vda_mqtt_base_topic(self) -> str:
        """获取VDA MQTT基础主题"""
        return f"{self.mqtt.vda_interface}/{self.vehicle.vda_version}/{self.vehicle.manufacturer}/{self.vehicle.serial_number}"


# 全局配置实例
_global_config: Optional[AppConfig] = None


def get_config(config_path: str = None) -> AppConfig:
    """获取全局配置实例"""
    global _global_config
    
    if _global_config is None:
        if config_path is None:
            # 尝试从默认位置加载配置
            default_paths = [
                "config.json",
                "SimulatorAGV/config.json",
                "config/config.json"
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if config_path and os.path.exists(config_path):
            _global_config = AppConfig.from_file(config_path)
        else:
            _global_config = AppConfig()
    
    return _global_config


def reload_config(config_path: str = None):
    """重新加载配置"""
    global _global_config
    _global_config = None
    return get_config(config_path)