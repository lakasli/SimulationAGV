"""
区域管理服务
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

from models.map_models import MapAreaInfo, Point, MapAreaType, Rect


class AreaService:
    """区域管理服务"""
    
    def __init__(self):
        self.areas: Dict[str, MapAreaInfo] = {}
        self.point_areas: Dict[str, List[str]] = {}  # 点位ID -> 包含该点的区域ID列表
    
    def load_initial_data(self, areas: Optional[List[MapAreaInfo]] = None) -> None:
        """加载初始数据"""
        self.areas.clear()
        self.point_areas.clear()
        
        if areas:
            for area in areas:
                self.areas[area.id] = area
                self._update_point_areas(area)
    
    def _update_point_areas(self, area: MapAreaInfo) -> None:
        """更新点位区域索引"""
        # 清除该区域的旧索引
        for point_list in self.point_areas.values():
            if area.id in point_list:
                point_list.remove(area.id)
        
        # 添加新索引
        if area.bound_points:
            for point_id in area.bound_points:
                if point_id not in self.point_areas:
                    self.point_areas[point_id] = []
                if area.id not in self.point_areas[point_id]:
                    self.point_areas[point_id].append(area.id)
    
    def get_areas(self) -> List[MapAreaInfo]:
        """获取所有区域"""
        return list(self.areas.values())
    
    def get_area_by_id(self, area_id: str) -> Optional[MapAreaInfo]:
        """根据ID获取区域"""
        return self.areas.get(area_id)
    
    def has_area(self, area_id: str) -> bool:
        """检查区域是否存在"""
        return area_id in self.areas
    
    def add_area(self, area: MapAreaInfo) -> bool:
        """添加区域"""
        if area.id in self.areas:
            return False
        
        self.areas[area.id] = area
        self._update_point_areas(area)
        return True
    
    def create_area(self, area_type: MapAreaType = MapAreaType.STORAGE,
                   label: str = "", description: str = "",
                   bound_points: Optional[List[str]] = None,
                   bound_lines: Optional[List[str]] = None,
                   bound_rect: Optional[Rect] = None) -> str:
        """创建新区域"""
        area_id = str(uuid.uuid4())
        area = MapAreaInfo(
            id=area_id,
            type=area_type,
            label=label,
            description=description,
            bound_points=bound_points or [],
            bound_lines=bound_lines or [],
            bound_rect=bound_rect
        )
        
        self.areas[area_id] = area
        self._update_point_areas(area)
        return area_id
    
    def update_area(self, area_id: str, updates: Dict[str, Any]) -> bool:
        """更新区域信息"""
        if area_id not in self.areas:
            return False
        
        area = self.areas[area_id]
        old_bound_points = area.bound_points.copy() if area.bound_points else []
        
        for key, value in updates.items():
            if hasattr(area, key):
                setattr(area, key, value)
        
        # 如果边界点发生变化，更新索引
        new_bound_points = area.bound_points or []
        if set(old_bound_points) != set(new_bound_points):
            self._update_point_areas(area)
        
        return True
    
    def update_area_type(self, area_id: str, area_type: MapAreaType) -> bool:
        """更新区域类型"""
        return self.update_area(area_id, {"type": area_type})
    
    def update_area_label(self, area_id: str, label: str) -> bool:
        """更新区域标签"""
        return self.update_area(area_id, {"label": label})
    
    def update_area_bounds(self, area_id: str, 
                          bound_points: Optional[List[str]] = None,
                          bound_lines: Optional[List[str]] = None,
                          bound_rect: Optional[Rect] = None) -> bool:
        """更新区域边界"""
        updates = {}
        if bound_points is not None:
            updates["bound_points"] = bound_points
        if bound_lines is not None:
            updates["bound_lines"] = bound_lines
        if bound_rect is not None:
            updates["bound_rect"] = bound_rect
        
        return self.update_area(area_id, updates)
    
    def delete_area(self, area_id: str) -> bool:
        """删除区域"""
        if area_id not in self.areas:
            return False
        
        # 从点位索引中移除
        for point_list in self.point_areas.values():
            if area_id in point_list:
                point_list.remove(area_id)
        
        del self.areas[area_id]
        return True
    
    def delete_areas(self, area_ids: List[str]) -> int:
        """批量删除区域"""
        deleted_count = 0
        for area_id in area_ids:
            if self.delete_area(area_id):
                deleted_count += 1
        return deleted_count
    
    def get_areas_by_type(self, area_type: MapAreaType) -> List[MapAreaInfo]:
        """根据类型获取区域"""
        return [area for area in self.areas.values() if area.type == area_type]
    
    def get_areas_by_point(self, point_id: str) -> List[MapAreaInfo]:
        """获取包含指定点位的所有区域"""
        if point_id not in self.point_areas:
            return []
        
        return [self.areas[area_id] for area_id in self.point_areas[point_id]
                if area_id in self.areas]
    
    def get_areas_by_line(self, line_id: str) -> List[MapAreaInfo]:
        """获取包含指定线段的所有区域"""
        result = []
        for area in self.areas.values():
            if area.bound_lines and line_id in area.bound_lines:
                result.append(area)
        return result
    
    def add_point_to_area(self, area_id: str, point_id: str) -> bool:
        """向区域添加边界点"""
        if area_id not in self.areas:
            return False
        
        area = self.areas[area_id]
        if not area.bound_points:
            area.bound_points = []
        
        if point_id not in area.bound_points:
            area.bound_points.append(point_id)
            self._update_point_areas(area)
        
        return True
    
    def remove_point_from_area(self, area_id: str, point_id: str) -> bool:
        """从区域移除边界点"""
        if area_id not in self.areas:
            return False
        
        area = self.areas[area_id]
        if area.bound_points and point_id in area.bound_points:
            area.bound_points.remove(point_id)
            self._update_point_areas(area)
            return True
        
        return False
    
    def add_line_to_area(self, area_id: str, line_id: str) -> bool:
        """向区域添加边界线"""
        if area_id not in self.areas:
            return False
        
        area = self.areas[area_id]
        if not area.bound_lines:
            area.bound_lines = []
        
        if line_id not in area.bound_lines:
            area.bound_lines.append(line_id)
        
        return True
    
    def remove_line_from_area(self, area_id: str, line_id: str) -> bool:
        """从区域移除边界线"""
        if area_id not in self.areas:
            return False
        
        area = self.areas[area_id]
        if area.bound_lines and line_id in area.bound_lines:
            area.bound_lines.remove(line_id)
            return True
        
        return False
    
    def set_area_rect(self, area_id: str, rect: Rect) -> bool:
        """设置区域矩形边界"""
        return self.update_area(area_id, {"bound_rect": rect})
    
    def get_area_bounds(self, area_id: str) -> Optional[Tuple[float, float, float, float]]:
        """获取区域边界（返回 min_x, min_y, max_x, max_y）"""
        if area_id not in self.areas:
            return None
        
        area = self.areas[area_id]
        
        # 如果有矩形边界，直接返回
        if area.bound_rect:
            rect = area.bound_rect
            return rect.x, rect.y, rect.x + rect.width, rect.y + rect.height
        
        # 如果有边界点，计算边界
        if area.bound_points:
            # 这里需要点位坐标信息，暂时返回None
            # 在实际使用中，需要传入点位服务来获取坐标
            pass
        
        return None
    
    def is_point_in_area(self, area_id: str, point: Point, 
                        point_coordinates: Optional[Dict[str, Point]] = None) -> bool:
        """检查点是否在区域内"""
        if area_id not in self.areas:
            return False
        
        area = self.areas[area_id]
        
        # 检查矩形边界
        if area.bound_rect:
            rect = area.bound_rect
            return (rect.x <= point.x <= rect.x + rect.width and
                   rect.y <= point.y <= rect.y + rect.height)
        
        # 检查多边形边界（需要点位坐标）
        if area.bound_points and point_coordinates:
            polygon_points = []
            for point_id in area.bound_points:
                if point_id in point_coordinates:
                    polygon_points.append(point_coordinates[point_id])
            
            if len(polygon_points) >= 3:
                return self._point_in_polygon(point, polygon_points)
        
        return False
    
    def _point_in_polygon(self, point: Point, polygon: List[Point]) -> bool:
        """使用射线法判断点是否在多边形内"""
        x, y = point.x, point.y
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def get_overlapping_areas(self, area_id: str, 
                             point_coordinates: Optional[Dict[str, Point]] = None) -> List[MapAreaInfo]:
        """获取与指定区域重叠的其他区域"""
        if area_id not in self.areas:
            return []
        
        target_area = self.areas[area_id]
        overlapping = []
        
        for other_id, other_area in self.areas.items():
            if other_id == area_id:
                continue
            
            if self._areas_overlap(target_area, other_area, point_coordinates):
                overlapping.append(other_area)
        
        return overlapping
    
    def _areas_overlap(self, area1: MapAreaInfo, area2: MapAreaInfo,
                      point_coordinates: Optional[Dict[str, Point]] = None) -> bool:
        """检查两个区域是否重叠"""
        # 简单的矩形重叠检查
        if area1.bound_rect and area2.bound_rect:
            rect1 = area1.bound_rect
            rect2 = area2.bound_rect
            
            return not (rect1.x + rect1.width < rect2.x or
                       rect2.x + rect2.width < rect1.x or
                       rect1.y + rect1.height < rect2.y or
                       rect2.y + rect2.height < rect1.y)
        
        # 更复杂的多边形重叠检查需要更多计算
        return False
    
    def delete_areas_by_point(self, point_id: str) -> int:
        """删除包含指定点位的所有区域"""
        areas_to_delete = self.get_areas_by_point(point_id)
        return self.delete_areas([area.id for area in areas_to_delete])
    
    def delete_areas_by_line(self, line_id: str) -> int:
        """删除包含指定线段的所有区域"""
        areas_to_delete = self.get_areas_by_line(line_id)
        return self.delete_areas([area.id for area in areas_to_delete])
    
    def validate_area_data(self, area: MapAreaInfo) -> List[str]:
        """验证区域数据"""
        errors = []
        
        if not area.id:
            errors.append("区域ID不能为空")
        
        if area.type not in MapAreaType:
            errors.append("无效的区域类型")
        
        # 检查边界定义
        has_bounds = False
        if area.bound_rect:
            has_bounds = True
            if area.bound_rect.width <= 0 or area.bound_rect.height <= 0:
                errors.append("矩形边界的宽度和高度必须大于0")
        
        if area.bound_points and len(area.bound_points) >= 3:
            has_bounds = True
        
        if area.bound_lines and len(area.bound_lines) >= 3:
            has_bounds = True
        
        if not has_bounds:
            errors.append("区域必须定义有效的边界（矩形、点集或线集）")
        
        return errors
    
    def search_areas(self, keyword: str) -> List[MapAreaInfo]:
        """搜索区域（根据标签或描述）"""
        keyword = keyword.lower()
        result = []
        
        for area in self.areas.values():
            if (keyword in area.label.lower() or 
                keyword in area.description.lower() or
                keyword in area.id.lower()):
                result.append(area)
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取区域统计信息"""
        stats = {
            "total_areas": len(self.areas),
            "areas_by_type": {},
            "areas_with_rect_bounds": 0,
            "areas_with_point_bounds": 0,
            "areas_with_line_bounds": 0
        }
        
        for area_type in MapAreaType:
            stats["areas_by_type"][area_type.value] = len(self.get_areas_by_type(area_type))
        
        for area in self.areas.values():
            if area.bound_rect:
                stats["areas_with_rect_bounds"] += 1
            if area.bound_points:
                stats["areas_with_point_bounds"] += 1
            if area.bound_lines:
                stats["areas_with_line_bounds"] += 1
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "areas": [area.__dict__ for area in self.areas.values()]
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)