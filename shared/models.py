"""
统一的数据模型
整合项目中的机器人状态、位置等数据结构
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class RobotStatusEnum(Enum):
    """机器人状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    WORKING = "working"
    IDLE = "idle"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class RobotType(Enum):
    """机器人类型"""
    AGV = "AGV"
    AMR = "AMR"
    FORKLIFT = "forklift"
    TRANSPORT = "transport"
    PICKER = "picker"
    CUSTOM = "custom"


@dataclass
class Position:
    """统一的位置模型"""
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0  # 角度（弧度）
    map_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "x": self.x,
            "y": self.y,
            "theta": self.theta
        }
        if self.map_id:
            result["mapId"] = self.map_id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """从字典创建"""
        return cls(
            x=data.get('x', 0.0),
            y=data.get('y', 0.0),
            theta=data.get('theta', 0.0),
            map_id=data.get('mapId')
        )


@dataclass
class BatteryState:
    """电池状态"""
    level: float = 100.0  # 电量百分比
    voltage: float = 24.0  # 电压
    charging: bool = False  # 是否充电中
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batteryCharge": self.level,
            "batteryVoltage": self.voltage,
            "charging": self.charging
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatteryState':
        return cls(
            level=data.get('batteryCharge', 100.0),
            voltage=data.get('batteryVoltage', 24.0),
            charging=data.get('charging', False)
        )


@dataclass
class SafetyState:
    """安全状态"""
    emergency_stop: bool = False
    protective_field: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eStop": self.emergency_stop,
            "fieldViolation": self.protective_field
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SafetyState':
        return cls(
            emergency_stop=data.get('eStop', False),
            protective_field=data.get('fieldViolation', False)
        )


@dataclass
class RobotStatus:
    """统一的机器人状态模型"""
    robot_id: str
    status: RobotStatusEnum = RobotStatusEnum.OFFLINE
    position: Position = field(default_factory=Position)
    battery: BatteryState = field(default_factory=BatteryState)
    safety: SafetyState = field(default_factory=SafetyState)
    
    # 扩展状态信息
    is_online: bool = False
    is_warning: bool = False
    is_fault: bool = False
    last_seen: Optional[datetime] = None
    current_order_id: Optional[str] = None
    
    # 设备信息
    manufacturer: str = "SimulatorAGV"
    model: str = "AGV-001"
    serial_number: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "robot_id": self.robot_id,
            "status": self.status.value,
            "position": self.position.to_dict(),
            "battery": self.battery.to_dict(),
            "safety": self.safety.to_dict(),
            "is_online": self.is_online,
            "is_warning": self.is_warning,
            "is_fault": self.is_fault,
            "manufacturer": self.manufacturer,
            "model": self.model
        }
        
        if self.last_seen:
            result["last_seen"] = self.last_seen.isoformat()
        if self.current_order_id:
            result["current_order_id"] = self.current_order_id
        if self.serial_number:
            result["serial_number"] = self.serial_number
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotStatus':
        """从字典创建"""
        status = cls(
            robot_id=data.get('robot_id', ''),
            status=RobotStatusEnum(data.get('status', 'offline')),
            position=Position.from_dict(data.get('position', {})),
            battery=BatteryState.from_dict(data.get('battery', {})),
            safety=SafetyState.from_dict(data.get('safety', {})),
            is_online=data.get('is_online', False),
            is_warning=data.get('is_warning', False),
            is_fault=data.get('is_fault', False),
            manufacturer=data.get('manufacturer', 'SimulatorAGV'),
            model=data.get('model', 'AGV-001'),
            serial_number=data.get('serial_number'),
            current_order_id=data.get('current_order_id')
        )
        
        if 'last_seen' in data:
            try:
                status.last_seen = datetime.fromisoformat(data['last_seen'])
            except:
                pass
                
        return status


@dataclass
class RobotInfo:
    """机器人基本信息"""
    id: str
    name: str = ""
    type: RobotType = RobotType.TRANSPORT
    ip: str = "127.0.0.1"
    manufacturer: str = "SimulatorAGV"
    version: str = "2.0.0"
    initial_position: Optional[Position] = None
    status: RobotStatusEnum = RobotStatusEnum.OFFLINE
    
    # 扩展属性以支持web_api.py中的访问需求
    speed: Optional[float] = None
    battery: Optional[float] = None
    position: Optional[Dict[str, Any]] = None
    gid: str = "default"
    is_warning: bool = False
    is_fault: bool = False
    last_update: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "id": self.id,
            "name": self.name or self.id,
            "type": self.type.value,
            "ip": self.ip,
            "manufacturer": self.manufacturer,
            "version": self.version,
            "status": self.status.value
        }
        
        if self.initial_position:
            result["initialPosition"] = self.initial_position.to_dict()
        
        # 添加扩展属性到字典
        if self.speed is not None:
            result["speed"] = self.speed
        if self.battery is not None:
            result["battery"] = self.battery
        if self.position is not None:
            result["position"] = self.position
        if self.gid:
            result["gid"] = self.gid
        if self.is_warning:
            result["is_warning"] = self.is_warning
        if self.is_fault:
            result["is_fault"] = self.is_fault
        if self.last_update:
            result["last_update"] = self.last_update
        if self.config:
            result["config"] = self.config
        if self.properties:
            result["properties"] = self.properties
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotInfo':
        """从字典创建"""
        info = cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            type=RobotType(data.get('type', 'transport')),
            ip=data.get('ip', '127.0.0.1'),
            manufacturer=data.get('manufacturer', 'SimulatorAGV'),
            version=data.get('version', '2.0.0'),
            status=RobotStatusEnum(data.get('status', 'offline'))
        )
        
        if 'initialPosition' in data:
            info.initial_position = Position.from_dict(data['initialPosition'])
        
        # 设置扩展属性
        info.speed = data.get('speed')
        info.battery = data.get('battery')
        info.position = data.get('position')
        info.gid = data.get('gid', 'default')
        info.is_warning = data.get('is_warning', False)
        info.is_fault = data.get('is_fault', False)
        info.last_update = data.get('last_update')
        info.config = data.get('config')
        info.properties = data.get('properties')
            
        return info


@dataclass
class RobotGroup:
    """机器人组"""
    id: str
    name: str
    robots: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "robots": self.robots
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotGroup':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            robots=data.get('robots', [])
        )


@dataclass
class RobotLabel:
    """机器人标签"""
    id: str
    name: str
    color: str = "#3498db"
    robots: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "robots": self.robots
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotLabel':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            color=data.get('color', '#3498db'),
            robots=data.get('robots', [])
        )