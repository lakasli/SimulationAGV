"""
机器人相关的数据模型 (已迁移到共享模块)
建议使用: from shared import RobotType, RobotStatusEnum, RobotInfo, RobotGroup, RobotLabel
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# 为了向后兼容，重新导出共享模型
try:
    from shared import (
        RobotType as SharedRobotType,
        RobotStatusEnum as SharedRobotStatusEnum,
        RobotInfo as SharedRobotInfo,
        RobotGroup as SharedRobotGroup,
        RobotLabel as SharedRobotLabel
    )
    
    # 创建别名以保持向后兼容
    RobotType = SharedRobotType
    RobotStatus = SharedRobotStatusEnum  # 注意：共享模块中是RobotStatusEnum
    RobotInfo = SharedRobotInfo
    RobotGroup = SharedRobotGroup
    RobotLabel = SharedRobotLabel
    
except ImportError:
    # 如果共享模块不可用，保留原始定义
    class RobotType(Enum):
        """机器人类型"""
        AGV = "AGV"
        AMR = "AMR"
        Forklift = "Forklift"
        Conveyor = "Conveyor"


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