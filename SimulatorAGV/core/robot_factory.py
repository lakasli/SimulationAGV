import os
import sys
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instances.robot_instance import RobotInstance
from core.config_generator import ConfigGenerator
from logger_config import logger


class RobotFactory:
    """机器人工厂类，负责创建和管理机器人实例"""
    
    def __init__(self, base_config_path: str = "config.json"):
        """
        初始化机器人工厂
        
        Args:
            base_config_path: 基础配置文件路径
        """
        self.config_generator = ConfigGenerator(base_config_path)
        logger.info("机器人工厂初始化完成")
    
    def create_robot_instance(self, robot_info: Dict[str, Any]) -> Optional[RobotInstance]:
        """
        创建单个机器人实例
        
        Args:
            robot_info: 机器人信息，包含id, serialNumber, manufacturer等
            
        Returns:
            创建的机器人实例，如果创建失败返回None
        """
        try:
            robot_id = robot_info.get("id")
            if not robot_id:
                logger.error("机器人信息缺少ID")
                return None
            
            # 生成机器人配置
            robot_config = self.config_generator.generate_robot_config(robot_info)
            
            # 创建机器人实例
            robot_instance = RobotInstance(robot_id, robot_config)
            
            logger.info(f"成功创建机器人实例: {robot_id} ({robot_info.get('serialNumber', 'Unknown')})")
            return robot_instance
            
        except Exception as e:
            logger.error(f"创建机器人实例失败: {e}")
            return None
    
    def create_robots_from_registry(self, registry_path: str) -> Dict[str, RobotInstance]:
        """
        从注册文件创建所有机器人实例
        
        Args:
            registry_path: 注册文件路径
            
        Returns:
            字典，键为机器人ID，值为机器人实例
        """
        robots = {}
        
        try:
            import json
            with open(registry_path, 'r', encoding='utf-8') as f:
                robots_data = json.load(f)
            
            for robot_info in robots_data:
                robot_instance = self.create_robot_instance(robot_info)
                if robot_instance:
                    robots[robot_instance.robot_id] = robot_instance
                else:
                    logger.warning(f"跳过创建机器人: {robot_info.get('id', 'Unknown')}")
            
            logger.info(f"从注册文件创建了 {len(robots)} 个机器人实例")
            
        except FileNotFoundError:
            logger.warning(f"注册文件不存在: {registry_path}")
        except json.JSONDecodeError as e:
            logger.error(f"解析注册文件失败: {e}")
        except Exception as e:
            logger.error(f"从注册文件创建机器人实例时出错: {e}")
        
        return robots
    
    def create_robot_from_config(self, robot_id: str, config: Dict[str, Any]) -> Optional[RobotInstance]:
        """
        从配置直接创建机器人实例
        
        Args:
            robot_id: 机器人ID
            config: 完整的机器人配置
            
        Returns:
            创建的机器人实例，如果创建失败返回None
        """
        try:
            robot_instance = RobotInstance(robot_id, config)
            logger.info(f"从配置创建机器人实例: {robot_id}")
            return robot_instance
        except Exception as e:
            logger.error(f"从配置创建机器人实例失败: {e}")
            return None
    
    def validate_robot_info(self, robot_info: Dict[str, Any]) -> bool:
        """
        验证机器人信息是否完整
        
        Args:
            robot_info: 机器人信息
            
        Returns:
            验证结果
        """
        required_fields = ["id", "serialNumber", "manufacturer"]
        
        for field in required_fields:
            if field not in robot_info:
                logger.error(f"机器人信息缺少必需字段: {field}")
                return False
        
        # 验证序列号唯一性（这里可以扩展为更复杂的验证逻辑）
        serial_number = robot_info.get("serialNumber")
        if not serial_number or len(serial_number.strip()) == 0:
            logger.error("机器人序列号不能为空")
            return False
        
        return True
    
    def get_default_robot_info(self, robot_id: str = None, serial_number: str = None) -> Dict[str, Any]:
        """
        获取默认的机器人信息模板
        
        Args:
            robot_id: 机器人ID，如果不提供会自动生成
            serial_number: 序列号，如果不提供会自动生成
            
        Returns:
            默认机器人信息
        """
        import uuid
        
        if not robot_id:
            robot_id = str(uuid.uuid4())
        
        if not serial_number:
            serial_number = f"AMB-{uuid.uuid4().hex[:6].upper()}"
        
        return {
            "id": robot_id,
            "serialNumber": serial_number,
            "manufacturer": "SimulatorAGV",
            "type": "AMR",
            "ip": "192.168.1.100",
            "status": "offline",
            "position": {
                "x": 0.0,
                "y": 0.0,
                "rotate": 0
            },
            "battery": 100.0,
            "maxSpeed": 2.0,
            "gid": "default",
            "is_warning": False,
            "is_fault": False,
            "config": {
                "battery": 100,
                "maxSpeed": 2,
                "orientation": 0,
                "initialPosition": "0"
            }
        }
    
    def update_base_config(self, new_config: Dict[str, Any]):
        """
        更新基础配置
        
        Args:
            new_config: 新的基础配置
        """
        self.config_generator.update_base_config(new_config)
        logger.info("基础配置已更新")