"""
地图相关的数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class MapPointType(Enum):
    """地图点位类型"""
    NORMAL = 1  # 普通点
    CHARGING = 2  # 充电点
    PARKING = 3  # 停靠点
    ACTION = 4  # 动作点
    LANDMARK = 15  # LM点


class MapRouteType(Enum):
    """路径类型"""
    STRAIGHT = 1  # 直线
    BEZIER2 = 2  # 二次贝塞尔曲线
    BEZIER3 = 3  # 三次贝塞尔曲线


class MapAreaType(Enum):
    """区域类型"""
    STORAGE = 1  # 库区
    EXCLUSIVE = 2  # 互斥区
    NON_EXCLUSIVE = 3  # 非互斥区
    CONSTRAINT = 4  # 约束区
    DESCRIPTION = 5  # 描述区


@dataclass
class Point:
    """坐标点"""
    x: float
    y: float


@dataclass
class Rect:
    """矩形区域"""
    x: float
    y: float
    width: float
    height: float


@dataclass
class MapPointInfo:
    """地图点位信息"""
    type: MapPointType
    enabled: Optional[int] = None
    associatedStorageLocations: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class MapRouteInfo:
    """地图路径信息"""
    type: MapRouteType
    direction: int = 1  # 1: 正向, -1: 反向
    pass_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class MapAreaInfo:
    """地图区域信息"""
    type: MapAreaType
    points: List[str] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    inoutflag: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class MapPen:
    """地图元素（点、线、区域等）"""
    id: str
    name: str
    tags: List[str] = field(default_factory=list)
    label: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    lineWidth: Optional[float] = None
    point: Optional[MapPointInfo] = None
    route: Optional[MapRouteInfo] = None
    area: Optional[MapAreaInfo] = None
    anchors: Optional[List[Dict[str, Any]]] = None
    locked: Optional[int] = None
    image: Optional[str] = None
    iconWidth: Optional[float] = None
    iconHeight: Optional[float] = None
    iconTop: Optional[float] = None
    canvasLayer: Optional[int] = None
    text: Optional[str] = None
    color: Optional[str] = None
    background: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None