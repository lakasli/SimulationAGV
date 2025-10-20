"""
点位管理服务
"""
import json
import uuid
import sys
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

# 添加父目录到路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from models.map_models import MapPointInfo, Point, MapPointType


class PointService:
    """点位管理服务"""
    
    def __init__(self):
        self.points: Dict[str, MapPointInfo] = {}
        self.storage_locations: Dict[str, List[str]] = {}  # 点位ID -> 存储位置列表
    
    def load_initial_data(self, points: Optional[List[MapPointInfo]] = None) -> None:
        """加载初始数据"""
        self.points.clear()
        self.storage_locations.clear()
        
        if points:
            for point in points:
                self.points[point.id] = point
                if point.storage_locations:
                    self.storage_locations[point.id] = point.storage_locations
    
    def get_points(self) -> List[MapPointInfo]:
        """获取所有点位"""
        return list(self.points.values())
    
    def get_point_by_id(self, point_id: str) -> Optional[MapPointInfo]:
        """根据ID获取点位"""
        return self.points.get(point_id)
    
    def has_point(self, point_id: str) -> bool:
        """检查点位是否存在"""
        return point_id in self.points
    
    def add_point(self, point: MapPointInfo) -> bool:
        """添加点位"""
        if point.id in self.points:
            return False
        
        self.points[point.id] = point
        if point.storage_locations:
            self.storage_locations[point.id] = point.storage_locations
        
        return True
    
    def create_point(self, position: Point, point_type: MapPointType = MapPointType.NORMAL,
                    label: str = "", description: str = "") -> str:
        """创建新点位"""
        point_id = str(uuid.uuid4())
        point = MapPointInfo(
            id=point_id,
            position=position,
            type=point_type,
            label=label,
            description=description
        )
        
        self.points[point_id] = point
        return point_id
    
    def update_point(self, point_id: str, updates: Dict[str, Any]) -> bool:
        """更新点位信息"""
        if point_id not in self.points:
            return False
        
        point = self.points[point_id]
        for key, value in updates.items():
            if hasattr(point, key):
                setattr(point, key, value)
        
        return True
    
    def update_point_position(self, point_id: str, position: Point) -> bool:
        """更新点位位置"""
        if point_id not in self.points:
            return False
        
        self.points[point_id].position = position
        return True
    
    def update_point_type(self, point_id: str, point_type: MapPointType) -> bool:
        """更新点位类型"""
        if point_id not in self.points:
            return False
        
        self.points[point_id].type = point_type
        return True
    
    def update_point_label(self, point_id: str, label: str) -> bool:
        """更新点位标签"""
        if point_id not in self.points:
            return False
        
        self.points[point_id].label = label
        return True
    
    def delete_point(self, point_id: str) -> bool:
        """删除点位"""
        if point_id not in self.points:
            return False
        
        del self.points[point_id]
        if point_id in self.storage_locations:
            del self.storage_locations[point_id]
        
        return True
    
    def delete_points(self, point_ids: List[str]) -> int:
        """批量删除点位"""
        deleted_count = 0
        for point_id in point_ids:
            if self.delete_point(point_id):
                deleted_count += 1
        return deleted_count
    
    def get_points_by_type(self, point_type: MapPointType) -> List[MapPointInfo]:
        """根据类型获取点位"""
        return [point for point in self.points.values() if point.type == point_type]
    
    def get_points_in_area(self, min_x: float, min_y: float, 
                          max_x: float, max_y: float) -> List[MapPointInfo]:
        """获取指定区域内的点位"""
        result = []
        for point in self.points.values():
            if (min_x <= point.position.x <= max_x and 
                min_y <= point.position.y <= max_y):
                result.append(point)
        return result
    
    def get_nearest_point(self, position: Point, max_distance: Optional[float] = None) -> Optional[MapPointInfo]:
        """获取最近的点位"""
        nearest_point = None
        min_distance = float('inf')
        
        for point in self.points.values():
            distance = self._calculate_distance(position, point.position)
            if distance < min_distance:
                if max_distance is None or distance <= max_distance:
                    min_distance = distance
                    nearest_point = point
        
        return nearest_point
    
    def get_points_within_distance(self, position: Point, distance: float) -> List[Tuple[MapPointInfo, float]]:
        """获取指定距离内的所有点位"""
        result = []
        for point in self.points.values():
            point_distance = self._calculate_distance(position, point.position)
            if point_distance <= distance:
                result.append((point, point_distance))
        
        # 按距离排序
        result.sort(key=lambda x: x[1])
        return result
    
    def _calculate_distance(self, p1: Point, p2: Point) -> float:
        """计算两点间距离"""
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5
    
    def add_storage_location(self, point_id: str, location: str) -> bool:
        """为点位添加存储位置"""
        if point_id not in self.points:
            return False
        
        if point_id not in self.storage_locations:
            self.storage_locations[point_id] = []
        
        if location not in self.storage_locations[point_id]:
            self.storage_locations[point_id].append(location)
            self.points[point_id].storage_locations = self.storage_locations[point_id]
        
        return True
    
    def remove_storage_location(self, point_id: str, location: str) -> bool:
        """移除点位的存储位置"""
        if point_id not in self.storage_locations:
            return False
        
        if location in self.storage_locations[point_id]:
            self.storage_locations[point_id].remove(location)
            self.points[point_id].storage_locations = self.storage_locations[point_id]
            return True
        
        return False
    
    def get_storage_locations(self, point_id: str) -> List[str]:
        """获取点位的存储位置"""
        return self.storage_locations.get(point_id, [])
    
    def update_storage_locations(self, point_id: str, locations: List[str]) -> bool:
        """更新点位的存储位置"""
        if point_id not in self.points:
            return False
        
        self.storage_locations[point_id] = locations
        self.points[point_id].storage_locations = locations
        return True
    
    def get_points_with_storage(self) -> List[MapPointInfo]:
        """获取有存储位置的点位"""
        return [point for point in self.points.values() 
                if point.storage_locations and len(point.storage_locations) > 0]
    
    def search_points(self, keyword: str) -> List[MapPointInfo]:
        """搜索点位（根据标签或描述）"""
        keyword = keyword.lower()
        result = []
        
        for point in self.points.values():
            if (keyword in point.label.lower() or 
                keyword in point.description.lower() or
                keyword in point.id.lower()):
                result.append(point)
        
        return result
    
    def validate_point_data(self, point: MapPointInfo) -> List[str]:
        """验证点位数据"""
        errors = []
        
        if not point.id:
            errors.append("点位ID不能为空")
        
        if point.position.x is None or point.position.y is None:
            errors.append("点位坐标不能为空")
        
        if point.type not in MapPointType:
            errors.append("无效的点位类型")
        
        return errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取点位统计信息"""
        stats = {
            "total_points": len(self.points),
            "points_by_type": {},
            "points_with_storage": len(self.get_points_with_storage()),
            "total_storage_locations": sum(len(locations) for locations in self.storage_locations.values())
        }
        
        for point_type in MapPointType:
            stats["points_by_type"][point_type.value] = len(self.get_points_by_type(point_type))
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "points": [point.__dict__ for point in self.points.values()],
            "storage_locations": self.storage_locations
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)