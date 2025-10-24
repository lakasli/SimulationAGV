import json
import copy
from typing import Dict, Any
from datetime import datetime
import uuid


class ConfigGenerator:
    """配置生成器，为每个机器人实例生成独立的配置"""
    
    def __init__(self, base_config_path: str = "config.json"):
        """
        初始化配置生成器
        
        Args:
            base_config_path: 基础配置文件路径 (已弃用，建议使用共享配置)
        """
        self.base_config_path = base_config_path
        
        # 尝试使用新的配置管理，如果失败则回退到原始方式
        try:
            from shared import get_config
            self.shared_config = get_config()
            self.base_config = self.shared_config.to_dict()
        except Exception:
            # 回退到原始实现
            self.shared_config = None
            self.base_config = self._load_base_config()
    
    def _load_base_config(self) -> Dict[str, Any]:
        """加载基础配置文件 (回退方法)"""
        try:
            with open(self.base_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 如果配置文件不存在，返回默认配置
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "mqtt_broker": {
                "host": "localhost",
                "port": 1883,
                "vda_interface": "uagv"
            },
            "vehicle": {
                "serial_number": "AMB-01",
                "manufacturer": "SimulatorAGV",
                "vda_version": "v2",
                "vda_full_version": "2.0.0"
            },
            "settings": {
                "map_id": "default",
                "state_frequency": 1,
                "visualization_frequency": 1,
                "action_time": 1.0,
                "robot_count": 1,
                "speed": 0.05
            }
        }
    
    def generate_robot_config(self, robot_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        为单个机器人生成配置
        
        Args:
            robot_info: 机器人信息，包含id, serialNumber, manufacturer, type, ip
            
        Returns:
            机器人的完整配置
        """
        # 使用新的配置格式
        robot_config = {
            "mqtt_broker": {
                "host": "localhost",
                "port": 1883,
                "vda_interface": "uagv",
                "client_id": f"{robot_info.get('manufacturer', 'SimulatorAGV')}_{robot_info.get('serialNumber', 'AMB-01')}_{int(datetime.now().timestamp())}"
            },
            "vehicle": {
                "serial_number": robot_info.get("serialNumber", f"AMB-{uuid.uuid4().hex[:6]}"),
                "manufacturer": robot_info.get("manufacturer", "SimulatorAGV"),
                "vda_version": "v2",
                "vda_full_version": "2.0.0"
            },
            "settings": {
                "map_id": "default",
                "state_frequency": 1,
                "visualization_frequency": 1,
                "action_time": 1.0,
                "robot_count": 1,
                "speed": 0.05,
                "initial_x": 0.0,
                "initial_y": 0.0,
                "initial_theta": 0.0,
                "initial_battery": 100.0,
                "max_speed": 2.0,
                "initial_orientation": 0,
                "initial_position": "0"
            },
            "robot_id": robot_info.get("id", str(uuid.uuid4())),
            "robot_type": robot_info.get("type", "AMR")
        }
        
        # 添加机器人IP地址
        if "ip" in robot_info:
            robot_config["robot_ip"] = robot_info["ip"]
        
        # 使用serialNumber作为robot_id
        robot_config["robot_id"] = robot_info.get("serialNumber", robot_config["robot_id"])
        
        return robot_config
    
    def generate_configs_from_registry(self, registry_path: str) -> Dict[str, Dict[str, Any]]:
        """
        从注册文件生成所有机器人的配置
        
        Args:
            registry_path: 注册文件路径
            
        Returns:
            字典，键为机器人序列号，值为配置
        """
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                robots = json.load(f)
        except FileNotFoundError:
            return {}
        
        configs = {}
        for robot in robots:
            # 使用serialNumber作为唯一标识符，如果没有则生成默认值
            robot_id = robot.get("serialNumber", f"ROBOT-{uuid.uuid4().hex[:8]}")
            configs[robot_id] = self.generate_robot_config(robot)
        
        return configs
    
    def save_robot_config(self, robot_config: Dict[str, Any], output_path: str):
        """
        保存机器人配置到文件
        
        Args:
            robot_config: 机器人配置
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(robot_config, f, indent=2, ensure_ascii=False)
    
    def update_base_config(self, new_config: Dict[str, Any]):
        """
        更新基础配置
        
        Args:
            new_config: 新的基础配置
        """
        self.base_config.update(new_config)