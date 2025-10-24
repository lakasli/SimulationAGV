import os
import sys
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..instances.robot_instance import RobotInstance
from .config_generator import ConfigGenerator
from shared import setup_logger

logger = setup_logger()


class RobotFactory:
    """机器人工厂类，负责创建和管理机器人实例"""
    
    def __init__(self, base_config_path: str = "config.json"):
        """
        初始化机器人工厂
        
        Args:
            base_config_path: 基础配置文件路径 (已弃用，建议使用共享配置)
        """
        # 尝试使用新的配置管理，如果失败则回退到原始方式
        try:
            from shared import get_config
            self.config = get_config()
            self.config_generator = ConfigGenerator()  # 使用默认配置
        except Exception:
            # 回退到原始实现
            self.config_generator = ConfigGenerator(base_config_path)
            self.config = None
            
        logger.info("机器人工厂初始化完成")
    
    def create_robot_instance(self, robot_info: Dict[str, Any]) -> Optional[RobotInstance]:
        """
        创建单个机器人实例
        
        Args:
            robot_info: 机器人信息，包含serialNumber, manufacturer等
            
        Returns:
            创建的机器人实例，如果创建失败返回None
        """
        try:
            serial_number = robot_info.get("serialNumber")
            if not serial_number:
                logger.error("机器人信息缺少serialNumber")
                return None
            
            # 生成机器人配置
            robot_config = self.config_generator.generate_robot_config(robot_info)
            
            # 创建机器人实例，使用serialNumber作为标识符
            robot_instance = RobotInstance(serial_number, robot_config)
            
            logger.info(f"成功创建机器人实例: {serial_number} ({robot_info.get('manufacturer', 'Unknown')})")
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
            字典，键为机器人serialNumber，值为机器人实例
        """
        robots = {}
        
        try:
            import json
            with open(registry_path, 'r', encoding='utf-8') as f:
                robots_data = json.load(f)
            
            for robot_info in robots_data:
                robot_instance = self.create_robot_instance(robot_info)
                if robot_instance:
                    # 使用serialNumber作为字典的键
                    serial_number = robot_info.get('serialNumber')
                    if serial_number:
                        robots[serial_number] = robot_instance
                    else:
                        logger.warning(f"机器人缺少serialNumber，使用robot_id作为键: {robot_instance.robot_id}")
                        robots[robot_instance.robot_id] = robot_instance
                else:
                    logger.warning(f"跳过创建机器人: {robot_info.get('serialNumber', 'Unknown')}")
            
            logger.info(f"从注册文件创建了 {len(robots)} 个机器人实例")
            
        except FileNotFoundError:
            logger.warning(f"注册文件不存在: {registry_path}")
        except json.JSONDecodeError as e:
            logger.error(f"解析注册文件失败: {e}")
        except Exception as e:
            logger.error(f"从注册文件创建机器人实例时出错: {e}")
        
        return robots
    
    def create_robot_from_config(self, serial_number: str, config: Dict[str, Any]) -> Optional[RobotInstance]:
        """
        从配置直接创建机器人实例
        
        Args:
            serial_number: 机器人序列号
            config: 完整的机器人配置
            
        Returns:
            创建的机器人实例，如果创建失败返回None
        """
        try:
            robot_instance = RobotInstance(serial_number, config)
            logger.info(f"从配置创建机器人实例: {serial_number}")
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
        required_fields = ["serialNumber", "manufacturer", "type", "ip"]
        
        for field in required_fields:
            if field not in robot_info:
                logger.error(f"机器人信息缺少必需字段: {field}")
                return False
        
        # 验证序列号唯一性（这里可以扩展为更复杂的验证逻辑）
        serial_number = robot_info.get("serialNumber")
        if not serial_number or len(serial_number.strip()) == 0:
            logger.error("机器人序列号不能为空")
            return False
        
        # 验证IP地址格式
        ip = robot_info.get("ip")
        if not ip or len(ip.strip()) == 0:
            logger.error("机器人IP地址不能为空")
            return False
        
        # 验证机器人类型
        robot_type = robot_info.get("type")
        if robot_type not in ["AGV", "AMR"]:
            logger.warning(f"机器人类型 '{robot_type}' 不在标准类型列表中")
        
        return True
    
    def get_default_robot_info(self, serial_number: str = None) -> Dict[str, Any]:
        """
        获取默认的机器人信息模板
        
        Args:
            serial_number: 序列号，如果不提供会自动生成
            
        Returns:
            默认机器人信息
        """
        import uuid
        
        if not serial_number:
            serial_number = f"AMB-{uuid.uuid4().hex[:6].upper()}"
        
        return {
            "serialNumber": serial_number,
            "manufacturer": "SimulatorAGV",
            "type": "AMR",
            "ip": "192.168.1.100"
        }
    
    def update_base_config(self, new_config: Dict[str, Any]):
        """
        更新基础配置
        
        Args:
            new_config: 新的基础配置
        """
        self.config_generator.update_base_config(new_config)
        logger.info("基础配置已更新")