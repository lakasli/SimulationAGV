"""
路径管理服务
"""
import json
import uuid
import sys
import os
from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import datetime
from collections import deque

# 添加父目录到路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from models.map_models import MapRouteInfo, Point, MapRouteType


class RouteService:
    """路径管理服务"""
    
    def __init__(self):
        self.routes: Dict[str, MapRouteInfo] = {}
        self.point_routes: Dict[str, Set[str]] = {}  # 点位ID -> 相关路径ID集合
    
    def load_initial_data(self, routes: Optional[List[MapRouteInfo]] = None) -> None:
        """加载初始数据"""
        self.routes.clear()
        self.point_routes.clear()
        
        if routes:
            for route in routes:
                self.routes[route.id] = route
                self._update_point_routes(route)
    
    def _update_point_routes(self, route: MapRouteInfo) -> None:
        """更新点位路径索引"""
        if route.start_point_id not in self.point_routes:
            self.point_routes[route.start_point_id] = set()
        if route.end_point_id not in self.point_routes:
            self.point_routes[route.end_point_id] = set()
        
        self.point_routes[route.start_point_id].add(route.id)
        self.point_routes[route.end_point_id].add(route.id)
    
    def _remove_from_point_routes(self, route: MapRouteInfo) -> None:
        """从点位路径索引中移除"""
        if route.start_point_id in self.point_routes:
            self.point_routes[route.start_point_id].discard(route.id)
        if route.end_point_id in self.point_routes:
            self.point_routes[route.end_point_id].discard(route.id)
    
    def get_routes(self) -> List[MapRouteInfo]:
        """获取所有路径"""
        return list(self.routes.values())
    
    def get_route_by_id(self, route_id: str) -> Optional[MapRouteInfo]:
        """根据ID获取路径"""
        return self.routes.get(route_id)
    
    def has_route(self, route_id: str) -> bool:
        """检查路径是否存在"""
        return route_id in self.routes
    
    def add_route(self, route: MapRouteInfo) -> bool:
        """添加路径"""
        if route.id in self.routes:
            return False
        
        self.routes[route.id] = route
        self._update_point_routes(route)
        return True
    
    def create_route(self, start_point_id: str, end_point_id: str, 
                    route_type: MapRouteType = MapRouteType.STRAIGHT,
                    label: str = "", description: str = "",
                    cost: float = 1.0, max_speed: float = 1.0) -> str:
        """创建新路径"""
        route_id = str(uuid.uuid4())
        route = MapRouteInfo(
            id=route_id,
            start_point_id=start_point_id,
            end_point_id=end_point_id,
            type=route_type,
            label=label,
            description=description,
            cost=cost,
            max_speed=max_speed
        )
        
        self.routes[route_id] = route
        self._update_point_routes(route)
        return route_id
    
    def update_route(self, route_id: str, updates: Dict[str, Any]) -> bool:
        """更新路径信息"""
        if route_id not in self.routes:
            return False
        
        route = self.routes[route_id]
        old_start = route.start_point_id
        old_end = route.end_point_id
        
        for key, value in updates.items():
            if hasattr(route, key):
                setattr(route, key, value)
        
        # 如果起点或终点发生变化，更新索引
        if (route.start_point_id != old_start or 
            route.end_point_id != old_end):
            # 移除旧的索引
            if old_start in self.point_routes:
                self.point_routes[old_start].discard(route_id)
            if old_end in self.point_routes:
                self.point_routes[old_end].discard(route_id)
            
            # 添加新的索引
            self._update_point_routes(route)
        
        return True
    
    def update_route_type(self, route_id: str, route_type: MapRouteType) -> bool:
        """更新路径类型"""
        return self.update_route(route_id, {"type": route_type})
    
    def update_route_cost(self, route_id: str, cost: float) -> bool:
        """更新路径成本"""
        return self.update_route(route_id, {"cost": cost})
    
    def update_route_speed(self, route_id: str, max_speed: float) -> bool:
        """更新路径最大速度"""
        return self.update_route(route_id, {"max_speed": max_speed})
    
    def delete_route(self, route_id: str) -> bool:
        """删除路径"""
        if route_id not in self.routes:
            return False
        
        route = self.routes[route_id]
        self._remove_from_point_routes(route)
        del self.routes[route_id]
        return True
    
    def delete_routes(self, route_ids: List[str]) -> int:
        """批量删除路径"""
        deleted_count = 0
        for route_id in route_ids:
            if self.delete_route(route_id):
                deleted_count += 1
        return deleted_count
    
    def get_routes_by_type(self, route_type: MapRouteType) -> List[MapRouteInfo]:
        """根据类型获取路径"""
        return [route for route in self.routes.values() if route.type == route_type]
    
    def get_routes_by_point(self, point_id: str) -> List[MapRouteInfo]:
        """获取与指定点位相关的所有路径"""
        if point_id not in self.point_routes:
            return []
        
        return [self.routes[route_id] for route_id in self.point_routes[point_id]
                if route_id in self.routes]
    
    def get_routes_from_point(self, point_id: str) -> List[MapRouteInfo]:
        """获取从指定点位出发的路径"""
        return [route for route in self.routes.values() 
                if route.start_point_id == point_id]
    
    def get_routes_to_point(self, point_id: str) -> List[MapRouteInfo]:
        """获取到达指定点位的路径"""
        return [route for route in self.routes.values() 
                if route.end_point_id == point_id]
    
    def get_route_between_points(self, start_point_id: str, end_point_id: str) -> Optional[MapRouteInfo]:
        """获取两点间的直接路径"""
        for route in self.routes.values():
            if (route.start_point_id == start_point_id and 
                route.end_point_id == end_point_id):
                return route
        return None
    
    def has_route_between_points(self, start_point_id: str, end_point_id: str) -> bool:
        """检查两点间是否存在直接路径"""
        return self.get_route_between_points(start_point_id, end_point_id) is not None
    
    def get_bidirectional_route(self, point1_id: str, point2_id: str) -> Tuple[Optional[MapRouteInfo], Optional[MapRouteInfo]]:
        """获取两点间的双向路径"""
        route1 = self.get_route_between_points(point1_id, point2_id)
        route2 = self.get_route_between_points(point2_id, point1_id)
        return route1, route2
    
    def create_bidirectional_route(self, point1_id: str, point2_id: str,
                                  route_type: MapRouteType = MapRouteType.STRAIGHT,
                                  label: str = "", description: str = "",
                                  cost: float = 1.0, max_speed: float = 1.0) -> Tuple[str, str]:
        """创建双向路径"""
        route1_id = self.create_route(
            point1_id, point2_id, route_type, label, description, cost, max_speed
        )
        route2_id = self.create_route(
            point2_id, point1_id, route_type, label, description, cost, max_speed
        )
        return route1_id, route2_id
    
    def delete_routes_by_point(self, point_id: str) -> int:
        """删除与指定点位相关的所有路径"""
        routes_to_delete = self.get_routes_by_point(point_id)
        return self.delete_routes([route.id for route in routes_to_delete])
    
    def get_connected_points(self, point_id: str) -> Set[str]:
        """获取与指定点位直接连接的所有点位"""
        connected = set()
        routes = self.get_routes_by_point(point_id)
        
        for route in routes:
            if route.start_point_id == point_id:
                connected.add(route.end_point_id)
            elif route.end_point_id == point_id:
                connected.add(route.start_point_id)
        
        return connected
    
    def find_path(self, start_point_id: str, end_point_id: str, 
                 max_depth: int = 10) -> Optional[List[str]]:
        """使用BFS查找两点间的路径"""
        if start_point_id == end_point_id:
            return [start_point_id]
        
        visited = set()
        queue = [(start_point_id, [start_point_id])]
        
        while queue:
            current_point, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            if current_point in visited:
                continue
            
            visited.add(current_point)
            
            # 获取当前点的所有连接点
            connected_points = self.get_connected_points(current_point)
            
            for next_point in connected_points:
                if next_point == end_point_id:
                    return path + [next_point]
                
                if next_point not in visited:
                    queue.append((next_point, path + [next_point]))
        
        return None
    
    def get_shortest_path(self, start_point_id: str, end_point_id: str) -> Optional[Tuple[List[str], float]]:
        """使用Dijkstra算法查找最短路径"""
        if start_point_id == end_point_id:
            return [start_point_id], 0.0
        
        # 构建图
        graph = {}
        for route in self.routes.values():
            if route.start_point_id not in graph:
                graph[route.start_point_id] = {}
            graph[route.start_point_id][route.end_point_id] = route.cost
        
        # Dijkstra算法
        distances = {start_point_id: 0}
        previous = {}
        unvisited = set(graph.keys())
        
        while unvisited:
            current = min(unvisited, key=lambda x: distances.get(x, float('inf')))
            
            if distances.get(current, float('inf')) == float('inf'):
                break
            
            unvisited.remove(current)
            
            if current == end_point_id:
                # 重构路径
                path = []
                while current is not None:
                    path.append(current)
                    current = previous.get(current)
                path.reverse()
                return path, distances[end_point_id]
            
            if current in graph:
                for neighbor, cost in graph[current].items():
                    distance = distances[current] + cost
                    if distance < distances.get(neighbor, float('inf')):
                        distances[neighbor] = distance
                        previous[neighbor] = current
        
        return None
    
    def validate_route_data(self, route: MapRouteInfo) -> List[str]:
        """验证路径数据"""
        errors = []
        
        if not route.id:
            errors.append("路径ID不能为空")
        
        if not route.start_point_id:
            errors.append("起点ID不能为空")
        
        if not route.end_point_id:
            errors.append("终点ID不能为空")
        
        if route.start_point_id == route.end_point_id:
            errors.append("起点和终点不能相同")
        
        if route.type not in MapRouteType:
            errors.append("无效的路径类型")
        
        if route.cost < 0:
            errors.append("路径成本不能为负数")
        
        if route.max_speed <= 0:
            errors.append("最大速度必须大于0")
        
        return errors
    
    def search_routes(self, keyword: str) -> List[MapRouteInfo]:
        """搜索路径（根据标签或描述）"""
        keyword = keyword.lower()
        result = []
        
        for route in self.routes.values():
            if (keyword in route.label.lower() or 
                keyword in route.description.lower() or
                keyword in route.id.lower()):
                result.append(route)
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取路径统计信息"""
        stats = {
            "total_routes": len(self.routes),
            "routes_by_type": {},
            "total_cost": sum(route.cost for route in self.routes.values()),
            "average_cost": 0,
            "connected_points": len(self.point_routes)
        }
        
        if self.routes:
            stats["average_cost"] = stats["total_cost"] / len(self.routes)
        
        for route_type in MapRouteType:
            stats["routes_by_type"][route_type.value] = len(self.get_routes_by_type(route_type))
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "routes": [route.__dict__ for route in self.routes.values()]
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)