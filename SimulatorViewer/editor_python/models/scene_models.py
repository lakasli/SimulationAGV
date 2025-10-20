"""
场景相关的数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .map_models import MapPen
from .robot_models import RobotInfo, RobotGroup, RobotLabel


@dataclass
class StandardScenePoint:
    """标准场景点位"""
    id: str
    name: str
    x: float
    y: float
    type: int
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    associatedStorageLocations: Optional[List[str]] = None


@dataclass
class StandardSceneRoute:
    """标准场景路径"""
    id: str
    desc: str
    from_point: str  # from是Python关键字，使用from_point
    to: str
    type: str
    pass_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    c1: Optional[Dict[str, float]] = None  # 控制点1
    c2: Optional[Dict[str, float]] = None  # 控制点2


@dataclass
class StandardSceneArea:
    """标准场景区域"""
    id: str
    name: str
    type: int
    x: float
    y: float
    width: float
    height: float
    points: List[str] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class SceneData:
    """场景数据"""
    scale: float = 1.0
    origin: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    pens: List[MapPen] = field(default_factory=list)
    robotGroups: List[RobotGroup] = field(default_factory=list)
    robots: List[RobotInfo] = field(default_factory=list)
    points: List[StandardScenePoint] = field(default_factory=list)
    routes: List[StandardSceneRoute] = field(default_factory=list)
    areas: List[StandardSceneArea] = field(default_factory=list)
    # 兼容性字段，用于支持现有场景文件格式
    blocks: Optional[str] = None
    colorConfig: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "scale": self.scale,
            "origin": self.origin,
            "pens": [pen.__dict__ if hasattr(pen, '__dict__') else pen for pen in self.pens],
            "robotGroups": [group.__dict__ if hasattr(group, '__dict__') else group for group in self.robotGroups],
            "robots": [robot.__dict__ if hasattr(robot, '__dict__') else robot for robot in self.robots],
            "points": [point.__dict__ if hasattr(point, '__dict__') else point for point in self.points],
            "routes": [route.__dict__ if hasattr(route, '__dict__') else route for route in self.routes],
            "areas": [area.__dict__ if hasattr(area, '__dict__') else area for area in self.areas]
        }
        
        # 添加兼容性字段
        if self.blocks is not None:
            result["blocks"] = self.blocks
        if self.colorConfig is not None:
            result["colorConfig"] = self.colorConfig
            
        return result


@dataclass
class StandardScene:
    """标准场景"""
    id: str
    name: str
    data: SceneData
    version: str = "1.0.0"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class GroupSceneDetail:
    """组场景详情"""
    scene_id: str
    group_id: str
    robots: List[RobotInfo] = field(default_factory=list)
    labels: List[RobotLabel] = field(default_factory=list)
    config: Optional[Dict[str, Any]] = None