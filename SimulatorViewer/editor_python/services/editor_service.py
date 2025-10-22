"""
编辑器主服务
整合所有子服务，提供统一的接口
"""
import json
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加父目录到路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from models.scene_models import SceneData, StandardScene
from models.robot_models import RobotInfo, RobotStatus, RobotType, RobotGroup
from models.map_models import MapPointInfo, MapPointType
from services.robot_service import RobotService
from services.point_service import PointService
from services.route_service import RouteService
from services.area_service import AreaService
from logger_config import logger


class EditorService:
    """主编辑器服务"""
    
    def __init__(self):
        self.robot_service = RobotService()
        self.point_service = PointService()
        self.route_service = RouteService()
        self.area_service = AreaService()
        
        self.scene_data: Optional[SceneData] = None
        self.current_scene_id: Optional[str] = None
        self.is_modified = False
        self.last_save_time: Optional[str] = None
    
    def load_scene_data(self, scene_data: SceneData) -> bool:
        """加载场景数据到各个服务"""
        try:
            from models.robot_models import RobotInfo, RobotGroup, RobotStatus
            from models.map_models import MapPointInfo, Point, MapPointType, MapPen
            from models.scene_models import StandardScenePoint, StandardSceneRoute, StandardSceneArea
            
            self.scene_data = scene_data
            
            # 加载画笔数据（包含点位信息）
            pens = []
            if scene_data.pens:
                for pen_data in scene_data.pens:
                    if isinstance(pen_data, dict):
                        # 转换为MapPen格式
                        pen_dict = {
                            'id': pen_data.get('id', ''),
                            'name': pen_data.get('name', ''),
                            'tags': pen_data.get('tags', []),
                            'label': pen_data.get('label'),
                            'x': pen_data.get('x'),
                            'y': pen_data.get('y'),
                            'width': pen_data.get('width'),
                            'height': pen_data.get('height'),
                            'lineWidth': pen_data.get('lineWidth'),
                            'point': None,
                            'route': None,
                            'area': None,
                            'anchors': pen_data.get('anchors'),
                            'locked': pen_data.get('locked'),
                            'image': pen_data.get('image'),
                            'iconWidth': pen_data.get('iconWidth'),
                            'iconHeight': pen_data.get('iconHeight'),
                            'iconTop': pen_data.get('iconTop'),
                            'canvasLayer': pen_data.get('canvasLayer'),
                            'text': pen_data.get('text'),
                            'color': pen_data.get('color'),
                            'background': pen_data.get('background'),
                            'config': pen_data.get('config'),
                            'properties': pen_data.get('properties')
                        }
                        
                        # 处理点位信息
                        if pen_data.get('point'):
                            point_info = pen_data['point']
                            pen_dict['point'] = MapPointInfo(
                                type=MapPointType(point_info.get('type', 1)),
                                enabled=point_info.get('enabled'),
                                associatedStorageLocations=point_info.get('associatedStorageLocations'),
                                config=point_info.get('config'),
                                properties=point_info.get('properties')
                            )
                        
                        pens.append(MapPen(**pen_dict))
                    elif isinstance(pen_data, MapPen):
                        pens.append(pen_data)
            
            # 暂时跳过点位服务的直接加载，因为点位信息在pens中
            self.point_service.load_initial_data([])
            
            # 加载路径数据 - 需要转换格式
            routes = []
            if scene_data.routes:
                for route_data in scene_data.routes:
                    if isinstance(route_data, dict):
                        # 这里需要根据实际的路径数据结构进行转换
                        # 暂时跳过，因为需要了解具体的数据格式
                        pass
                    else:
                        routes.append(route_data)
            
            self.route_service.load_initial_data(routes)
            
            # 加载区域数据 - 需要转换格式
            areas = []
            if scene_data.areas:
                for area_data in scene_data.areas:
                    if isinstance(area_data, dict):
                        # 这里需要根据实际的区域数据结构进行转换
                        # 暂时跳过，因为需要了解具体的数据格式
                        pass
                    else:
                        areas.append(area_data)
            
            self.area_service.load_initial_data(areas)
            
            # 加载机器人数据 - 需要转换格式
            robots = []
            if scene_data.robots:
                for robot_data in scene_data.robots:
                    if isinstance(robot_data, dict):
                        # 处理机器人类型
                        robot_type = None
                        if robot_data.get('type'):
                            try:
                                if isinstance(robot_data['type'], int):
                                    # 如果是整数，尝试转换为枚举
                                    robot_type = RobotType(robot_data['type'])
                                elif isinstance(robot_data['type'], str):
                                    # 如果是字符串，尝试按名称获取
                                    robot_type = RobotType[robot_data['type']]
                                else:
                                    robot_type = robot_data['type']
                            except (KeyError, ValueError):
                                robot_type = RobotType.AGV  # 默认类型
                        
                        # 确保必需字段存在
                        robot_dict = {
                            'id': robot_data.get('id', ''),
                            'label': robot_data.get('label', ''),
                            'gid': robot_data.get('gid', ''),
                            'brand': robot_data.get('brand'),
                            'type': robot_type,
                            'ip': robot_data.get('ip', ''),
                            'status': RobotStatus.OFFLINE,  # 默认状态
                            'position': robot_data.get('position'),
                            'battery': robot_data.get('battery'),
                            'speed': robot_data.get('speed'),
                            'is_warning': robot_data.get('is_warning', False),
                            'is_fault': robot_data.get('is_fault', False),
                            'last_update': robot_data.get('last_update'),
                            'config': robot_data.get('config'),
                            'properties': robot_data.get('properties')
                        }
                        robots.append(RobotInfo(**robot_dict))
                    elif isinstance(robot_data, RobotInfo):
                        robots.append(robot_data)
            
            # 加载机器人组数据
            groups = []
            if scene_data.robotGroups:
                for group_data in scene_data.robotGroups:
                    if isinstance(group_data, dict):
                        group_dict = {
                            'id': group_data.get('id', ''),
                            'label': group_data.get('label', ''),
                            'robots': group_data.get('robots', []),
                            'config': group_data.get('config'),
                            'properties': group_data.get('properties')
                        }
                        groups.append(RobotGroup(**group_dict))
                    elif isinstance(group_data, RobotGroup):
                        groups.append(group_data)
            
            robot_labels = []  # 暂时为空，因为场景文件中没有这个字段
            
            self.robot_service.load_initial_data(groups, robots, robot_labels)
            
            self.is_modified = False
            return True
            
        except Exception as e:
            logger.error(f"加载场景数据失败: {e}")
            return False
    
    def load_scene_from_file(self, file_path: str) -> bool:
        """从文件加载场景"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 过滤掉SceneData不支持的字段，但保留兼容性字段
            supported_fields = {
                'scale', 'origin', 'pens', 'robotGroups', 'robots', 
                'points', 'routes', 'areas', 'blocks', 'colorConfig'
            }
            filtered_data = {k: v for k, v in data.items() if k in supported_fields}
            
            scene_data = SceneData(**filtered_data)
            return self.load_scene_data(scene_data)
            
        except Exception as e:
            logger.error(f"从文件加载场景失败: {e}")
            return False
    
    def save_scene_to_file(self, file_path: str) -> bool:
        """保存场景到文件"""
        try:
            scene_data = self.get_current_scene_data()
            if not scene_data:
                return False
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scene_data.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.is_modified = False
            self.last_save_time = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"保存场景到文件失败: {e}")
            return False
    
    def get_current_scene_data(self) -> Optional[SceneData]:
        """获取当前场景数据"""
        if not self.scene_data:
            return None
        
        # 直接返回场景数据
        return self.scene_data
    
    def create_new_scene(self, scene_id: str = None) -> str:
        """创建新场景"""
        if not scene_id:
            scene_id = f"scene_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建空的场景数据
        standard_scene = StandardScene(
            id=scene_id,
            name=f"新场景_{scene_id}",
            points=[],
            routes=[],
            areas=[]
        )
        
        scene_data = SceneData(
            id=scene_id,
            standard_scene=standard_scene,
            group_scene_details=[]
        )
        
        self.load_scene_data(scene_data)
        self.current_scene_id = scene_id
        return scene_id
    
    def mark_modified(self) -> None:
        """标记场景已修改"""
        self.is_modified = True
    
    def get_modification_status(self) -> Dict[str, Any]:
        """获取修改状态"""
        return {
            "is_modified": self.is_modified,
            "last_save_time": self.last_save_time,
            "current_scene_id": self.current_scene_id
        }
    
    def validate_scene_data(self) -> List[str]:
        """验证场景数据"""
        errors = []
        
        # 验证点位数据
        for point in self.point_service.get_points():
            point_errors = self.point_service.validate_point_data(point)
            errors.extend([f"点位 {point.id}: {error}" for error in point_errors])
        
        # 验证路径数据
        for route in self.route_service.get_routes():
            route_errors = self.route_service.validate_route_data(route)
            errors.extend([f"路径 {route.id}: {error}" for error in route_errors])
            
            # 检查路径的起点和终点是否存在
            if not self.point_service.has_point(route.start_point_id):
                errors.append(f"路径 {route.id}: 起点 {route.start_point_id} 不存在")
            if not self.point_service.has_point(route.end_point_id):
                errors.append(f"路径 {route.id}: 终点 {route.end_point_id} 不存在")
        
        # 验证区域数据
        for area in self.area_service.get_areas():
            area_errors = self.area_service.validate_area_data(area)
            errors.extend([f"区域 {area.id}: {error}" for error in area_errors])
            
            # 检查区域的边界点是否存在
            if area.bound_points:
                for point_id in area.bound_points:
                    if not self.point_service.has_point(point_id):
                        errors.append(f"区域 {area.id}: 边界点 {point_id} 不存在")
        
        return errors
    
    def get_scene_statistics(self) -> Dict[str, Any]:
        """获取场景统计信息"""
        return {
            "scene_id": self.current_scene_id,
            "is_modified": self.is_modified,
            "last_save_time": self.last_save_time,
            "points": self.point_service.get_statistics(),
            "routes": self.route_service.get_statistics(),
            "areas": self.area_service.get_statistics(),
            "robots": {
                "total_robots": len(self.robot_service.get_robots()),
                "total_groups": len(self.robot_service.get_robot_groups()),
                "total_labels": len(self.robot_service.get_robot_labels())
            }
        }
    
    def search_all(self, keyword: str) -> Dict[str, List[Any]]:
        """全局搜索"""
        return {
            "points": self.point_service.search_points(keyword),
            "routes": self.route_service.search_routes(keyword),
            "areas": self.area_service.search_areas(keyword)
        }
    
    def export_data(self, format_type: str = "json") -> str:
        """导出数据"""
        scene_data = self.get_current_scene_data()
        if not scene_data:
            return ""
        
        if format_type.lower() == "json":
            return json.dumps(scene_data.to_dict(), ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")
    
    def import_data(self, data: str, format_type: str = "json") -> bool:
        """导入数据"""
        try:
            if format_type.lower() == "json":
                data_dict = json.loads(data)
                scene_data = SceneData(**data_dict)
                return self.load_scene_data(scene_data)
            else:
                raise ValueError(f"不支持的导入格式: {format_type}")
        except Exception as e:
            logger.error(f"导入数据失败: {e}")
            return False
    
    def clear_all_data(self) -> None:
        """清空所有数据"""
        self.robot_service = RobotService()
        self.point_service = PointService()
        self.route_service = RouteService()
        self.area_service = AreaService()
        self.scene_data = None
        self.current_scene_id = None
        self.is_modified = False
        self.last_save_time = None
    
    def undo_last_operation(self) -> bool:
        """撤销上一次操作（需要实现操作历史记录）"""
        # 这里需要实现操作历史记录功能
        # 暂时返回False表示未实现
        return False
    
    def redo_last_operation(self) -> bool:
        """重做上一次操作（需要实现操作历史记录）"""
        # 这里需要实现操作历史记录功能
        # 暂时返回False表示未实现
        return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "robot_service": {
                "robots_count": len(self.robot_service.robots),
                "groups_count": len(self.robot_service.robot_groups),
                "labels_count": len(self.robot_service.robot_labels)
            },
            "point_service": {
                "points_count": len(self.point_service.points),
                "storage_locations_count": len(self.point_service.storage_locations)
            },
            "route_service": {
                "routes_count": len(self.route_service.routes),
                "connected_points_count": len(self.route_service.point_routes)
            },
            "area_service": {
                "areas_count": len(self.area_service.areas),
                "point_areas_count": len(self.area_service.point_areas)
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        scene_data = self.get_current_scene_data()
        return {
            "scene_data": scene_data.to_dict() if scene_data else None,
            "modification_status": self.get_modification_status(),
            "statistics": self.get_scene_statistics()
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)