"""
机器人相关的数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RobotType(Enum):
    """机器人类型"""
    TYPE_1 = 1
    TYPE_2 = 2
    TYPE_3 = 3


class RobotStatus(Enum):
    """机器人状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    CHARGING = "charging"
    WORKING = "working"
    IDLE = "idle"
    ERROR = "error"


@dataclass
class RobotInfo:
    """机器人信息"""
    id: str
    label: str
    gid: str  # 机器人组ID
    brand: Optional[str] = None
    type: Optional[RobotType] = None
    ip: Optional[str] = None
    status: RobotStatus = RobotStatus.OFFLINE
    position: Optional[Dict[str, float]] = None  # {"x": 0, "y": 0, "rotate": 0}
    battery: Optional[float] = None
    speed: Optional[float] = None
    is_warning: bool = False
    is_fault: bool = False
    last_update: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class RobotGroup:
    """机器人组"""
    id: str
    label: str
    robots: List[str] = field(default_factory=list)
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class RobotLabel:
    """机器人标签"""
    id: str
    label: str
    robots: List[str] = field(default_factory=list)
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None