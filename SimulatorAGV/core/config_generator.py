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
            base_config_path: 基础配置文件路径
        """
        self.base_config_path = base_config_path
        self.base_config = self._load_base_config()
    
    def _load_base_config(self) -> Dict[str, Any]:
        """加载基础配置文件"""
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
            robot_info: 机器人信息，包含serialNumber, manufacturer等
            
        Returns:
            机器人的完整配置
        """
        # 深拷贝基础配置
        robot_config = copy.deepcopy(self.base_config)
        
        # 更新车辆信息
        robot_config["vehicle"]["serial_number"] = robot_info.get("serialNumber", f"AMB-{uuid.uuid4().hex[:6]}")
        robot_config["vehicle"]["manufacturer"] = robot_info.get("manufacturer", "SimulatorAGV")
        
        # 更新MQTT配置，确保每个机器人有唯一的客户端ID
        robot_config["mqtt_broker"]["client_id"] = f"{robot_config['vehicle']['manufacturer']}_{robot_config['vehicle']['serial_number']}_{int(datetime.now().timestamp())}"
        
        # 如果机器人信息中包含IP地址，可以用于特定的MQTT代理配置
        if "ip" in robot_info:
            robot_config["robot_ip"] = robot_info["ip"]
        
        # 添加机器人特定的设置
        if "config" in robot_info:
            robot_specific_config = robot_info["config"]
            
            # 更新电池设置
            if "battery" in robot_specific_config:
                robot_config["settings"]["initial_battery"] = robot_specific_config["battery"]
            
            # 更新最大速度
            if "maxSpeed" in robot_specific_config:
                robot_config["settings"]["max_speed"] = robot_specific_config["maxSpeed"]
            
            # 更新初始方向
            if "orientation" in robot_specific_config:
                robot_config["settings"]["initial_orientation"] = robot_specific_config["orientation"]
            
            # 更新初始位置
            if "initialPosition" in robot_specific_config:
                robot_config["settings"]["initial_position"] = robot_specific_config["initialPosition"]
        
        # 添加位置信息
        if "position" in robot_info:
            robot_config["settings"]["initial_x"] = robot_info["position"]["x"]
            robot_config["settings"]["initial_y"] = robot_info["position"]["y"]
            robot_config["settings"]["initial_theta"] = robot_info["position"].get("rotate", 0)
        
        # 添加机器人ID和类型
        robot_config["robot_id"] = robot_info.get("id", str(uuid.uuid4()))
        robot_config["robot_type"] = robot_info.get("type", "AMR")
        
        return robot_config
    
    def generate_configs_from_registry(self, registry_path: str) -> Dict[str, Dict[str, Any]]:
        """
        从注册文件生成所有机器人的配置
        
        Args:
            registry_path: 注册文件路径
            
        Returns:
            字典，键为机器人ID，值为配置
        """
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                robots = json.load(f)
        except FileNotFoundError:
            return {}
        
        configs = {}
        for robot in robots:
            robot_id = robot.get("id", str(uuid.uuid4()))
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