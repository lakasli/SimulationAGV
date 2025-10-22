"""Web API接口
为HTML地图查看器提供HTTP接口
"""
import sys
import os
import json
import uuid
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional
import threading
import time

# 添加父目录到路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from services.editor_service import EditorService
from services.robot_instance_service import RobotInstanceService
from models.map_models import Point, MapPointType, MapRouteType, MapAreaType, Rect
from models.robot_models import RobotType, RobotStatus
from logger_config import logger


class MapEditorAPIHandler(BaseHTTPRequestHandler):
    """地图编辑器API处理器"""
    
    # 设置HTTP协议版本为1.1，解决前端ERR_INVALID_HTTP_RESPONSE问题
    protocol_version = 'HTTP/1.1'
    
    def __init__(self, *args, editor_service: EditorService = None, robot_instance_service: RobotInstanceService = None, **kwargs):
        self.editor_service = editor_service or EditorService()
        self.robot_instance_service = robot_instance_service or RobotInstanceService()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        logger.info(f"[API] 收到GET请求: {self.path}")
        start_time = time.time()
        
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            logger.info(f"[API] 解析路径: {path}, 查询参数: {query_params}")
            
            # 路由处理
            if path == '/api/scene/data':
                logger.info("[API] 处理场景数据请求")
                self._handle_get_scene_data()
            elif path == '/api/robots':
                logger.info("[API] 处理机器人列表请求")
                self._handle_get_robots(query_params)
            elif path.startswith('/api/robots/'):
                robot_id = path.split('/')[-1]
                logger.info(f"[API] 处理单个机器人请求: {robot_id}")
                # 注意：_handle_get_robot函数不存在，需要实现或移除此路由
                self._send_error(404, f"单个机器人API暂未实现: {robot_id}")
            elif path == '/api/points':
                logger.info("[API] 处理点位列表请求")
                self._handle_get_points(query_params)
            elif path == '/api/routes':
                logger.info("[API] 处理路径列表请求")
                self._handle_get_routes(query_params)
            elif path == '/api/areas':
                logger.info("[API] 处理区域列表请求")
                self._handle_get_areas(query_params)
            elif path == '/api/robot-instances/status':
                logger.info("[API] 处理机器人实例状态请求")
                self._handle_get_robot_instances_status()
            else:
                logger.warning(f"[API] 未知的GET路径: {path}")
                self._send_error(404, f"路径不存在: {path}")
            
            end_time = time.time()
            logger.info(f"[API] GET请求处理完成，耗时: {(end_time - start_time)*1000:.2f}ms")
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"[API] GET请求处理失败，耗时: {(end_time - start_time)*1000:.2f}ms, 错误: {e}")
            import traceback
            traceback.print_exc()
            self._send_error(500, f"服务器内部错误: {e}")
    
    def do_POST(self):
        """处理POST请求"""
        logger.info(f"[API] 收到POST请求: {self.path}")
        start_time = time.time()
        
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data) if post_data else {}
            
            logger.info(f"[API] POST解析路径: {path}, 数据长度: {len(post_data)}")
            
            if path == '/api/scene/load':
                logger.info("[API] 处理场景加载请求")
                self._handle_load_scene(data)
            elif path == '/api/scene/save':
                logger.info("[API] 处理场景保存请求")
                self._handle_save_scene(data)
            elif path == '/api/points':
                logger.info("[API] 处理创建点位请求")
                self._handle_create_point(data)
            elif path == '/api/routes':
                logger.info("[API] 处理创建路径请求")
                self._handle_create_route(data)
            elif path == '/api/areas':
                logger.info("[API] 处理创建区域请求")
                self._handle_create_area(data)
            elif path == '/api/robots':
                logger.info("[API] 处理创建机器人请求")
                self._handle_create_robot(data)
            elif path.startswith('/api/robots/') and path.endswith('/update'):
                robot_id = path.split('/')[-2]
                logger.info(f"[API] 处理修改机器人配置请求: {robot_id}")
                self._handle_update_robot_config(robot_id, data)
            elif path == '/api/logs':
                logger.info("[API] 处理前端日志请求")
                self._handle_frontend_log(data)
            else:
                logger.warning(f"[API] 未知的POST路径: {path}")
                self._send_error(404, "API endpoint not found")
            
            end_time = time.time()
            logger.info(f"[API] POST请求处理完成，耗时: {(end_time - start_time)*1000:.2f}ms")
                
        except Exception as e:
            end_time = time.time()
            logger.error(f"[API] POST请求处理失败，耗时: {(end_time - start_time)*1000:.2f}ms, 错误: {e}")
            import traceback
            traceback.print_exc()
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_PUT(self):
        """处理PUT请求"""
        logger.info(f"[API] 收到PUT请求: {self.path}")
        start_time = time.time()
        
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data) if post_data else {}
            
            logger.info(f"[API] PUT解析路径: {path}, 数据长度: {len(post_data)}")
            
            if path.startswith('/api/points/'):
                point_id = path.split('/')[-1]
                logger.info(f"[API] 处理更新点位请求: {point_id}")
                self._handle_update_point(point_id, data)
            elif path.startswith('/api/routes/'):
                route_id = path.split('/')[-1]
                logger.info(f"[API] 处理更新路径请求: {route_id}")
                self._handle_update_route(route_id, data)
            elif path.startswith('/api/areas/'):
                area_id = path.split('/')[-1]
                logger.info(f"[API] 处理更新区域请求: {area_id}")
                self._handle_update_area(area_id, data)
            elif path.startswith('/api/robots/'):
                robot_id = path.split('/')[-1]
                logger.info(f"[API] 处理更新机器人请求: {robot_id}")
                self._handle_update_robot(robot_id, data)
            else:
                logger.warning(f"[API] 未知的PUT路径: {path}")
                self._send_error(404, "API endpoint not found")
            
            end_time = time.time()
            logger.info(f"[API] PUT请求处理完成，耗时: {(end_time - start_time)*1000:.2f}ms")
                
        except Exception as e:
            end_time = time.time()
            logger.error(f"[API] PUT请求处理失败，耗时: {(end_time - start_time)*1000:.2f}ms, 错误: {e}")
            import traceback
            traceback.print_exc()
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_DELETE(self):
        """处理DELETE请求"""
        logger.info(f"[API] 收到DELETE请求: {self.path}")
        start_time = time.time()
        
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            logger.info(f"[API] DELETE解析路径: {path}")
            
            if path.startswith('/api/points/'):
                point_id = path.split('/')[-1]
                logger.info(f"[API] 处理删除点位请求: {point_id}")
                self._handle_delete_point(point_id)
            elif path.startswith('/api/routes/'):
                route_id = path.split('/')[-1]
                logger.info(f"[API] 处理删除路径请求: {route_id}")
                self._handle_delete_route(route_id)
            elif path.startswith('/api/areas/'):
                area_id = path.split('/')[-1]
                logger.info(f"[API] 处理删除区域请求: {area_id}")
                self._handle_delete_area(area_id)
            elif path.startswith('/api/robots/'):
                robot_id = path.split('/')[-1]
                logger.info(f"[API] 处理删除机器人请求: {robot_id}")
                self._handle_delete_robot(robot_id)
            else:
                logger.warning(f"[API] 未知的DELETE路径: {path}")
                self._send_error(404, "API endpoint not found")
            
            end_time = time.time()
            logger.info(f"[API] DELETE请求处理完成，耗时: {(end_time - start_time)*1000:.2f}ms")
                
        except Exception as e:
            end_time = time.time()
            logger.error(f"[API] DELETE请求处理失败，耗时: {(end_time - start_time)*1000:.2f}ms, 错误: {e}")
            import traceback
            traceback.print_exc()
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Cache-Control')
    
    def _send_json_response(self, data: Any, status_code: int = 200):
        """发送JSON响应"""
        try:
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            json_bytes = json_data.encode('utf-8')
            
            # 发送响应状态行
            self.send_response(status_code)
            
            # 发送必要的HTTP头
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_bytes)))
            
            # 发送CORS头
            self._send_cors_headers()
            
            # 发送连接头
            self.send_header('Connection', 'close')  # 改为close避免keep-alive问题
            
            # 结束头部
            self.end_headers()
            
            # 发送响应体
            self.wfile.write(json_bytes)
            self.wfile.flush()  # 确保数据被发送
            
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            # 客户端断开连接，记录日志但不抛出异常
            logger.warning(f"客户端连接断开: {e}")
        except Exception as e:
            # 其他异常，记录详细信息
            logger.error(f"发送响应时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_error(self, status_code: int, message: str):
        """发送错误响应"""
        error_data = {
            "error": True,
            "message": message,
            "status_code": status_code
        }
        try:
            # 发送响应状态行
            self.send_response(status_code)
            
            # 准备JSON数据
            json_data = json.dumps(error_data, ensure_ascii=False, indent=2)
            json_bytes = json_data.encode('utf-8')
            
            # 发送必要的HTTP头
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_bytes)))
            
            # 发送CORS头
            self._send_cors_headers()
            
            # 发送连接头
            self.send_header('Connection', 'close')
            
            # 结束头部
            self.end_headers()
            
            # 发送响应体
            self.wfile.write(json_bytes)
            self.wfile.flush()
            
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            # 客户端断开连接，记录日志但不抛出异常
            logger.warning(f"发送错误响应时客户端连接断开: {e}")
        except Exception as e:
            # 其他异常，记录详细信息
            logger.error(f"发送错误响应时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 场景数据相关API
    def _handle_get_scene_data(self):
        """获取场景数据"""
        try:
            scene_data = self.editor_service.get_current_scene_data()
            if scene_data:
                self._send_json_response(scene_data.to_dict())
            else:
                self._send_json_response({"message": "No scene data loaded"})
        except Exception as e:
            logger.error(f"获取场景数据失败: {e}")
            self._send_error(500, f"获取场景数据失败: {e}")

    def _handle_load_scene(self, data: Dict[str, Any]):
        """加载场景"""
        file_path = data.get('file_path')
        if file_path:
            success = self.editor_service.load_scene_from_file(file_path)
            self._send_json_response({"success": success})
        else:
            self._send_error(400, "Missing file_path parameter")
    
    def _handle_save_scene(self, data: Dict[str, Any]):
        """保存场景"""
        file_path = data.get('file_path')
        if file_path:
            success = self.editor_service.save_scene_to_file(file_path)
            self._send_json_response({"success": success})
        else:
            self._send_error(400, "Missing file_path parameter")
    
    # 点位相关API
    def _handle_get_points(self, query_params: Dict[str, list]):
        """获取点位列表"""
        point_type = query_params.get('type', [None])[0]
        if point_type:
            try:
                point_type_enum = MapPointType(point_type)
                points = self.editor_service.point_service.get_points_by_type(point_type_enum)
            except ValueError:
                self._send_error(400, f"Invalid point type: {point_type}")
                return
        else:
            points = self.editor_service.point_service.get_points()
        
        points_data = [point.__dict__ for point in points]
        self._send_json_response(points_data)
    
    def _handle_create_point(self, data: Dict[str, Any]):
        """创建点位"""
        try:
            position = Point(**data['position'])
            point_type = MapPointType(data.get('type', 'normal'))
            label = data.get('label', '')
            description = data.get('description', '')
            
            point_id = self.editor_service.point_service.create_point(
                position, point_type, label, description
            )
            self.editor_service.mark_modified()
            
            self._send_json_response({"id": point_id, "success": True})
        except Exception as e:
            self._send_error(400, f"Failed to create point: {str(e)}")
    
    def _handle_update_point(self, point_id: str, data: Dict[str, Any]):
        """更新点位"""
        success = self.editor_service.point_service.update_point(point_id, data)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    def _handle_delete_point(self, point_id: str):
        """删除点位"""
        success = self.editor_service.point_service.delete_point(point_id)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    # 路径相关API
    def _handle_get_routes(self, query_params: Dict[str, list]):
        """获取路径列表"""
        route_type = query_params.get('type', [None])[0]
        if route_type:
            try:
                route_type_enum = MapRouteType(route_type)
                routes = self.editor_service.route_service.get_routes_by_type(route_type_enum)
            except ValueError:
                self._send_error(400, f"Invalid route type: {route_type}")
                return
        else:
            routes = self.editor_service.route_service.get_routes()
        
        routes_data = [route.__dict__ for route in routes]
        self._send_json_response(routes_data)
    
    def _handle_create_route(self, data: Dict[str, Any]):
        """创建路径"""
        try:
            start_point_id = data['start_point_id']
            end_point_id = data['end_point_id']
            route_type = MapRouteType(data.get('type', 'normal'))
            label = data.get('label', '')
            description = data.get('description', '')
            cost = data.get('cost', 1.0)
            max_speed = data.get('max_speed', 1.0)
            
            route_id = self.editor_service.route_service.create_route(
                start_point_id, end_point_id, route_type, label, description, cost, max_speed
            )
            self.editor_service.mark_modified()
            
            self._send_json_response({"id": route_id, "success": True})
        except Exception as e:
            self._send_error(400, f"Failed to create route: {str(e)}")
    
    def _handle_update_route(self, route_id: str, data: Dict[str, Any]):
        """更新路径"""
        success = self.editor_service.route_service.update_route(route_id, data)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    def _handle_delete_route(self, route_id: str):
        """删除路径"""
        success = self.editor_service.route_service.delete_route(route_id)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    # 区域相关API
    def _handle_get_areas(self, query_params: Dict[str, list]):
        """获取区域列表"""
        area_type = query_params.get('type', [None])[0]
        if area_type:
            try:
                area_type_enum = MapAreaType(area_type)
                areas = self.editor_service.area_service.get_areas_by_type(area_type_enum)
            except ValueError:
                self._send_error(400, f"Invalid area type: {area_type}")
                return
        else:
            areas = self.editor_service.area_service.get_areas()
        
        areas_data = [area.__dict__ for area in areas]
        self._send_json_response(areas_data)
    
    def _handle_create_area(self, data: Dict[str, Any]):
        """创建区域"""
        try:
            area_type = MapAreaType(data.get('type', 'normal'))
            label = data.get('label', '')
            description = data.get('description', '')
            bound_points = data.get('bound_points', [])
            bound_lines = data.get('bound_lines', [])
            bound_rect = None
            
            if 'bound_rect' in data:
                bound_rect = Rect(**data['bound_rect'])
            
            area_id = self.editor_service.area_service.create_area(
                area_type, label, description, bound_points, bound_lines, bound_rect
            )
            self.editor_service.mark_modified()
            
            self._send_json_response({"id": area_id, "success": True})
        except Exception as e:
            self._send_error(400, f"Failed to create area: {str(e)}")
    
    def _handle_update_area(self, area_id: str, data: Dict[str, Any]):
        """更新区域"""
        success = self.editor_service.area_service.update_area(area_id, data)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    def _handle_delete_area(self, area_id: str):
        """删除区域"""
        success = self.editor_service.area_service.delete_area(area_id)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    # 机器人相关API
    def _handle_get_robots(self, query_params: Dict[str, list]):
        """获取机器人列表 - 每次都从registered_robots.json文件重新加载"""
        try:
            # 每次请求都从JSON文件重新加载机器人数据，确保数据是最新的
            self._load_robots_from_file()
            
            robots = self.editor_service.robot_service.get_robots()
            robots_data = []
            
            for robot in robots:
                robot_dict = {
                    "id": robot.id,
                    "serialNumber": robot.label,
                    "manufacturer": robot.brand or "",
                    "type": robot.type.name if robot.type else "TYPE_1",
                    "ip": robot.ip,
                    "status": robot.status.value if robot.status else "offline",
                    "position": robot.position or {"x": 0, "y": 0, "rotate": 0},
                    "battery": robot.battery or 100.0,
                    "maxSpeed": robot.speed or 2.0,
                    "gid": robot.gid or "default",
                    "is_warning": robot.is_warning,
                    "is_fault": robot.is_fault,
                    "last_update": robot.last_update,
                    "config": robot.config or {}
                }
                robots_data.append(robot_dict)
            
            logger.info(f"从JSON文件加载了 {len(robots_data)} 个机器人")
            self._send_json_response(robots_data)
        except Exception as e:
            logger.error(f"获取机器人列表失败: {e}")
            self._send_error(500, f"获取机器人列表失败: {e}")

    def _save_robots_to_file(self):
        """保存机器人数据到JSON文件"""
        try:
            logger.info("开始保存机器人数据到文件...")
            # 修改路径计算，指向 SimulatorAGV 目录
            base_dir = os.path.dirname(os.path.dirname(current_dir))  # 到 SimulatorViewer
            project_root = os.path.dirname(base_dir)  # 到项目根目录
            robots_dir = os.path.join(project_root, "SimulatorAGV")
            logger.info(f"机器人目录: {robots_dir}")
            os.makedirs(robots_dir, exist_ok=True)
            
            # 保存机器人数据
            robots_file = os.path.join(robots_dir, "registered_robots.json")
            logger.info(f"机器人文件路径: {robots_file}")
            robots = self.editor_service.robot_service.get_robots()
            logger.info(f"获取到的机器人数量: {len(robots)}")
            
            robots_data = []
            for robot in robots:
                robot_dict = {
                    "id": robot.id,
                    "serialNumber": robot.label,
                    "manufacturer": robot.brand or "",
                    "type": robot.type.name if robot.type else "TYPE_1",
                    "ip": robot.ip,
                    "status": robot.status.value if robot.status else "offline",
                    "position": robot.position or {"x": 0, "y": 0, "rotate": 0},
                    "battery": robot.battery or 100.0,
                    "maxSpeed": robot.speed or 2.0,
                    "gid": robot.gid or "default",
                    "is_warning": robot.is_warning,
                    "is_fault": robot.is_fault,
                    "last_update": robot.last_update,
                    "config": robot.config or {}
                }
                robots_data.append(robot_dict)
            
            with open(robots_file, 'w', encoding='utf-8') as f:
                json.dump(robots_data, f, ensure_ascii=False, indent=2)
            logger.info("机器人数据保存成功!")
                
        except Exception as e:
            logger.error(f"保存机器人数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _load_robots_from_file(self):
        """从JSON文件加载机器人数据"""
        try:
            # 修改路径计算，指向 SimulatorAGV 目录
            # current_dir 是 api 目录，需要向上两级到 SimulatorViewer，然后到项目根目录，再进入 SimulatorAGV
            base_dir = os.path.dirname(os.path.dirname(current_dir))  # 到 SimulatorViewer
            project_root = os.path.dirname(base_dir)  # 到项目根目录
            robots_dir = os.path.join(project_root, "SimulatorAGV")
            robots_file = os.path.join(robots_dir, "registered_robots.json")
            
            print(f"[DEBUG] 尝试从文件加载机器人数据: {robots_file}")
            
            if os.path.exists(robots_file):
                with open(robots_file, 'r', encoding='utf-8') as f:
                    robots_data = json.load(f)
                
                print(f"[DEBUG] 成功读取到 {len(robots_data)} 个机器人数据")
                
                from models.robot_models import RobotInfo, RobotStatus, RobotType
                
                # 清空现有机器人数据
                self.editor_service.robot_service.robots.clear()
                
                # 加载机器人数据
                for robot_data in robots_data:
                    try:
                        robot_type = RobotType.AGV
                        if robot_data.get('type'):
                            try:
                                robot_type = RobotType(robot_data['type'])
                            except (KeyError, ValueError):
                                robot_type = RobotType.AGV
                        
                        robot_status = RobotStatus.OFFLINE
                        if robot_data.get('status'):
                            try:
                                robot_status = RobotStatus(robot_data['status'])
                            except ValueError:
                                robot_status = RobotStatus.OFFLINE
                        
                        robot_info = RobotInfo(
                            id=robot_data['id'],
                            label=robot_data['serialNumber'],
                            gid=robot_data.get('gid', 'default'),
                            brand=robot_data.get('manufacturer', ''),
                            type=robot_type,
                            ip=robot_data['ip'],
                            status=robot_status,
                            position=robot_data.get('position', {"x": 0, "y": 0, "rotate": 0}),
                            battery=robot_data.get('battery', 100.0),
                            speed=robot_data.get('maxSpeed', 2.0),
                            is_warning=robot_data.get('is_warning', False),
                            is_fault=robot_data.get('is_fault', False),
                            last_update=robot_data.get('last_update'),
                            config=robot_data.get('config', {}),
                            properties=robot_data.get('properties', {})
                        )
                        
                        self.editor_service.robot_service.robots[robot_info.id] = robot_info
                        print(f"[DEBUG] 成功加载机器人: {robot_info.label} (ID: {robot_info.id})")
                        
                    except Exception as e:
                        print(f"加载机器人数据失败 {robot_data.get('id', 'unknown')}: {e}")
                        
                print(f"[DEBUG] 机器人数据加载完成，共加载 {len(self.editor_service.robot_service.robots)} 个机器人")
            else:
                print(f"[DEBUG] 机器人数据文件不存在: {robots_file}")
                        
        except Exception as e:
            print(f"从文件加载机器人数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_create_robot(self, data: Dict[str, Any]):
        """创建机器人"""
        try:
            from models.robot_models import RobotInfo, RobotStatus, RobotType
            
            # 1. 基础数据验证
            if not isinstance(data, dict):
                self._send_error(400, "无效的数据类型")
                return
            
            # 2. 验证必需字段
            required_fields = ['serialNumber', 'type', 'ip']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self._send_error(400, f"缺少必需字段: {', '.join(missing_fields)}")
                return
            
            # 3. 基础字段验证
            robot_name = str(data['serialNumber']).strip()
            robot_ip = str(data['ip']).strip()
            
            if not robot_name:
                self._send_error(400, "机器人名称不能为空")
                return
            
            if not robot_ip:
                self._send_error(400, "IP地址不能为空")
                return
            
            # 4. 检查唯一性
            existing_robots = self.editor_service.robot_service.get_robots()
            for existing_robot in existing_robots:
                if existing_robot.label == robot_name:
                    self._send_error(409, f"机器人名称 '{robot_name}' 已存在")
                    return
                if existing_robot.ip == robot_ip:
                    self._send_error(409, f"IP地址 '{robot_ip}' 已被使用")
                    return
            
            # 处理机器人类型
            robot_type = RobotType.AGV  # 默认类型
            if data.get('type'):
                try:
                    robot_type = RobotType(data['type'])
                except (KeyError, ValueError):
                    robot_type = RobotType.AGV
            
            # 5. 创建机器人 - 按照标准JSON格式
            robot_id = str(uuid.uuid4())
            robot_info = RobotInfo(
                id=robot_id,
                label=robot_name,
                gid=data.get('gid', "default"),
                brand=data.get('manufacturer', 'SEER'),
                type=robot_type,
                ip=robot_ip,
                status=RobotStatus.OFFLINE,
                position=data.get('position', {"x": 0, "y": 0, "rotate": 0}),
                battery=float(data.get('battery', 100.0)),
                speed=float(data.get('maxSpeed', 2.0)),
                is_warning=data.get('is_warning', False),
                is_fault=data.get('is_fault', False),

                config=data.get('config', {}),
                properties={}
            )
            
            # 6. 保存机器人
            self.editor_service.robot_service.robots[robot_id] = robot_info
            self._save_robots_to_file()
            
            # 7. 启动机器人实例
            try:
                # 准备机器人实例数据
                instance_data = {
                    "id": robot_id,
                    "serialNumber": robot_name,
                    "manufacturer": data.get('manufacturer', 'SEER'),
                    "type": data['type'],
                    "ip": robot_ip,
                    "status": "offline",
                    "position": data.get('position', {"x": 0, "y": 0, "rotate": 0}),
                    "battery": float(data.get('battery', 100.0)),
                    "maxSpeed": float(data.get('maxSpeed', 2.0)),
                    "gid": data.get('gid', "default"),
                    "is_warning": data.get('is_warning', False),
                    "is_fault": data.get('is_fault', False),
                    "config": data.get('config', {})
                }
                
                # 启动机器人实例
                start_result = self.robot_instance_service.start_robot_instance(instance_data)
                logger.info(f"机器人实例启动结果: {start_result}")
                
            except Exception as e:
                logger.warning(f"启动机器人实例失败: {e}")
                # 即使实例启动失败，机器人注册仍然成功
            
            # 8. 返回成功响应
            response_data = {
                "success": True,
                "robot_id": robot_id,
                "message": "Robot registered successfully",
                "robot_info": {
                    "id": robot_id,
                    "serialNumber": robot_name,
                    "ip": robot_ip,
                    "type": data['type'],
                    "status": "offline"
                }
            }
            self._send_json_response(response_data)
                
        except ImportError as e:
            error_msg = f"导入模块失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(f"[CREATE_ROBOT] 导入错误: {error_msg}")
            self._send_error(500, "服务器配置错误，请联系管理员")
            
        except KeyError as e:
            error_msg = f"访问字典键时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(f"[CREATE_ROBOT] 键错误: {error_msg}")
            self._send_error(400, f"请求数据格式错误: 缺少或无效的字段 {str(e)}")
            
        except ValueError as e:
            error_msg = f"数据值错误: {str(e)}"
            logger.error(error_msg, exc_info=True)  
            print(f"[CREATE_ROBOT] 值错误: {error_msg}")
            self._send_error(400, f"数据格式错误: {str(e)}")
            
        except TypeError as e:
            error_msg = f"数据类型错误: {str(e)}"
            logger.error(error_msg, exc_info=True)  
            print(f"[CREATE_ROBOT] 类型错误: {error_msg}")
            self._send_error(400, f"数据类型错误: {str(e)}")
            
        except PermissionError as e:
            error_msg = f"文件权限错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(f"[CREATE_ROBOT] 权限错误: {error_msg}")
            self._send_error(500, "服务器文件权限错误，请联系管理员")
            
        except OSError as e:
            error_msg = f"操作系统错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(f"[CREATE_ROBOT] 系统错误: {error_msg}")
            self._send_error(500, "服务器系统错误，请联系管理员")
            
        except Exception as e:
            error_msg = f"创建机器人时发生未预期的错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(f"[CREATE_ROBOT] 未预期错误: {error_msg}")
            import traceback
            traceback.print_exc()
            self._send_error(500, "服务器内部错误，请稍后重试或联系管理员")
        
        finally:
            print(f"[CREATE_ROBOT] 函数执行完成")

    def _handle_update_robot_config(self, robot_id: str, data: Dict[str, Any]):
        """处理修改机器人配置的POST请求"""
        try:
            logger.info(f"开始处理机器人配置修改请求: {robot_id}")
            
            # 1. 先从文件加载最新数据
            self._load_robots_from_file()
            
            # 2. 检查机器人是否存在
            if robot_id not in self.editor_service.robot_service.robots:
                logger.warning(f"机器人 {robot_id} 不存在")
                self._send_error(404, f"机器人 {robot_id} 不存在")
                return
            
            # 3. 获取当前机器人信息
            robot = self.editor_service.robot_service.robots[robot_id]
            logger.info(f"找到机器人: {robot.label}")
            
            # 4. 验证和更新字段
            updated_fields = []
            
            # 更新基本信息
            if 'serialNumber' in data and data['serialNumber'] != robot.label:
                # 检查名称唯一性
                for existing_id, existing_robot in self.editor_service.robot_service.robots.items():
                    if existing_id != robot_id and existing_robot.label == data['serialNumber']:
                        self._send_error(409, f"机器人名称 '{data['serialNumber']}' 已存在")
                        return
                robot.label = data['serialNumber']
                updated_fields.append('serialNumber')
            
            if 'ip' in data and data['ip'] != robot.ip:
                # 检查IP唯一性
                for existing_id, existing_robot in self.editor_service.robot_service.robots.items():
                    if existing_id != robot_id and existing_robot.ip == data['ip']:
                        self._send_error(409, f"IP地址 '{data['ip']}' 已被使用")
                        return
                robot.ip = data['ip']
                updated_fields.append('ip')
            
            if 'gid' in data:
                robot.gid = data['gid']
                updated_fields.append('gid')
            
            if 'manufacturer' in data:
                robot.brand = data['manufacturer']
                updated_fields.append('manufacturer')
            
            # 处理manufacturer和version属性（已经在上面处理了manufacturer）
            if 'version' in data:
                if not robot.properties:
                    robot.properties = {}
                robot.properties['version'] = data['version']
                updated_fields.append('version')
            
            if 'maxSpeed' in data:
                robot.speed = float(data['maxSpeed'])
                updated_fields.append('maxSpeed')
            
            if 'battery' in data:
                robot.battery = float(data['battery'])
                updated_fields.append('battery')
            
            if 'position' in data:
                robot.position = data['position']
                updated_fields.append('position')
            
            if 'is_warning' in data:
                robot.is_warning = bool(data['is_warning'])
                updated_fields.append('is_warning')
            
            if 'is_fault' in data:
                robot.is_fault = bool(data['is_fault'])
                updated_fields.append('is_fault')
            
            if 'config' in data:
                robot.config = data['config']
                updated_fields.append('config')
            
            if 'properties' in data:
                robot.properties = data['properties']
                updated_fields.append('properties')
            
            # 5. 更新时间戳
            import datetime
            robot.last_update = datetime.datetime.now().isoformat()
            
            # 6. 保存到文件
            self._save_robots_to_file()
            
            # 7. 返回成功响应
            response_data = {
                "success": True,
                "message": "机器人配置更新成功",
                "robot_id": robot_id,
                "updated_fields": updated_fields,
                "robot_info": {
                        "id": robot.id,
                        "serialNumber": robot.label,
                        "manufacturer": robot.brand,
                        "type": robot.type.name if robot.type else "TYPE_1",
                        "ip": robot.ip,
                        "status": robot.status.value if robot.status else "offline",
                        "position": robot.position,
                        "battery": robot.battery,
                        "maxSpeed": robot.speed,
                        "gid": robot.gid,
                        "is_warning": robot.is_warning,
                        "is_fault": robot.is_fault,
                        "last_update": robot.last_update,
                        "config": robot.config
                    }
            }
            
            logger.info(f"机器人配置更新成功: {robot_id}, 更新字段: {updated_fields}")
            self._send_json_response(response_data)
            
        except ValueError as e:
            error_msg = f"数据格式错误: {str(e)}"
            logger.error(error_msg)
            self._send_error(400, error_msg)
            
        except Exception as e:
            error_msg = f"更新机器人配置失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._send_error(500, error_msg)

    def _handle_update_robot(self, robot_id: str, data: Dict[str, Any]):
        """更新机器人信息"""
        try:
            logger.info(f"开始处理机器人更新请求: {robot_id}")
            logger.info(f"接收到的数据: {data}")
            
            # 先从文件加载最新数据
            self._load_robots_from_file()
            
            # 检查机器人是否存在
            if robot_id not in self.editor_service.robot_service.robots:
                self._send_error(404, f"机器人 {robot_id} 不存在")
                return
            
            # 获取当前机器人信息
            robot = self.editor_service.robot_service.robots[robot_id]
            logger.info(f"找到机器人: {robot.label}")
            
            # 验证和更新字段
            updated_fields = []
            
            # 更新基本信息 - 字段映射
            if 'serialNumber' in data and data['serialNumber'] != robot.label:
                # 检查名称唯一性
                for existing_id, existing_robot in self.editor_service.robot_service.robots.items():
                    if existing_id != robot_id and existing_robot.label == data['serialNumber']:
                        self._send_error(409, f"机器人名称 '{data['serialNumber']}' 已存在")
                        return
                robot.label = data['serialNumber']
                updated_fields.append('serialNumber')
            
            if 'ip' in data and data['ip'] != robot.ip:
                # 检查IP唯一性
                for existing_id, existing_robot in self.editor_service.robot_service.robots.items():
                    if existing_id != robot_id and existing_robot.ip == data['ip']:
                        self._send_error(409, f"IP地址 '{data['ip']}' 已被使用")
                        return
                robot.ip = data['ip']
                updated_fields.append('ip')
            
            if 'type' in data:
                # 确保type是RobotType枚举对象
                from models.robot_models import RobotType
                if isinstance(data['type'], str):
                    try:
                        robot.type = RobotType(data['type'])
                    except (KeyError, ValueError):
                        robot.type = RobotType.AGV  # 默认类型
                elif isinstance(data['type'], RobotType):
                    robot.type = data['type']
                else:
                    robot.type = RobotType.AGV  # 默认类型
                updated_fields.append('type')
            
            if 'gid' in data:
                robot.gid = data['gid']
                updated_fields.append('gid')
            
            if 'manufacturer' in data:
                robot.brand = data['manufacturer']
                updated_fields.append('manufacturer')
            
            if 'maxSpeed' in data:
                robot.speed = float(data['maxSpeed'])
                updated_fields.append('maxSpeed')
            
            if 'battery' in data:
                robot.battery = float(data['battery'])
                updated_fields.append('battery')
            
            if 'position' in data:
                robot.position = data['position']
                updated_fields.append('position')
            
            if 'orientation' in data:
                # 将orientation存储到config中
                if not robot.config:
                    robot.config = {}
                robot.config['orientation'] = data['orientation']
                updated_fields.append('orientation')
            
            if 'initialPosition' in data:
                # 将initialPosition存储到config中
                if not robot.config:
                    robot.config = {}
                robot.config['initialPosition'] = data['initialPosition']
                updated_fields.append('initialPosition')
            
            if 'is_warning' in data:
                robot.is_warning = bool(data['is_warning'])
                updated_fields.append('is_warning')
            
            if 'is_fault' in data:
                robot.is_fault = bool(data['is_fault'])
                updated_fields.append('is_fault')
            
            if 'config' in data:
                if not robot.config:
                    robot.config = {}
                robot.config.update(data['config'])
                updated_fields.append('config')
            
            if 'properties' in data:
                robot.properties = data['properties']
                updated_fields.append('properties')
            
            # 更新时间戳
            import datetime
            robot.last_update = datetime.datetime.now().isoformat()
            
            # 保存到文件
            self._save_robots_to_file()
            
            logger.info(f"机器人更新成功: {robot_id}, 更新字段: {updated_fields}")
            self._send_json_response({"success": True, "message": "机器人信息更新成功"})
                
        except Exception as e:
            logger.error(f"更新机器人失败: {e}")
            self._send_error(500, f"更新机器人失败: {e}")

    def _handle_delete_robot(self, robot_id: str):
        """删除机器人"""
        try:
            # 先从文件加载最新数据
            self._load_robots_from_file()
            
            # 检查机器人是否存在
            if robot_id not in self.editor_service.robot_service.robots:
                self._send_error(404, f"机器人 {robot_id} 不存在")
                return
            
            # 停止机器人实例
            try:
                stop_result = self.robot_instance_service.stop_robot_instance(robot_id)
                logger.info(f"机器人实例停止结果: {stop_result}")
            except Exception as e:
                logger.warning(f"停止机器人实例失败: {e}")
                # 即使实例停止失败，仍然继续删除机器人记录
            
            # 删除机器人
            removed_count = self.editor_service.robot_service.remove_robots([robot_id])
            if removed_count > 0:
                # 保存到文件
                self._save_robots_to_file()
                self._send_json_response({"success": True, "message": "机器人删除成功"})
            else:
                self._send_error(400, "删除机器人失败")
                
        except Exception as e:
            logger.error(f"删除机器人失败: {e}")
            self._send_error(500, f"删除机器人失败: {e}")

    def _handle_get_robot_instances_status(self):
        """获取机器人实例状态"""
        try:
            status_data = self.robot_instance_service.get_all_instances_status()
            self._send_json_response({
                "success": True,
                "instances": status_data
            })
        except Exception as e:
            logger.error(f"获取机器人实例状态失败: {e}")
            self._send_error(500, f"获取机器人实例状态失败: {e}")

    def _handle_frontend_log(self, data: Dict[str, Any]):
        """处理前端日志请求"""
        try:
            # 提取日志信息
            level = data.get('level', 'INFO')
            message = data.get('message', '')
            log_data = data.get('data')
            timestamp = data.get('timestamp', '')
            source = data.get('source', 'frontend')
            
            # 构建日志消息
            log_message = f"[{timestamp}] [{source.upper()}] {message}"
            
            # 根据日志级别记录到后端日志
            if level.upper() == 'ERROR':
                logger.error(log_message)
                if log_data:
                    logger.error(f"[{source.upper()}] 错误详情: {log_data}")
            elif level.upper() == 'WARNING' or level.upper() == 'WARN':
                logger.warning(log_message)
                if log_data:
                    logger.warning(f"[{source.upper()}] 警告详情: {log_data}")
            else:
                logger.info(log_message)
                if log_data:
                    logger.info(f"[{source.upper()}] 数据详情: {log_data}")
            
            # 返回成功响应
            self._send_json_response({"success": True, "message": "日志记录成功"})
            
        except Exception as e:
            logger.error(f"处理前端日志失败: {e}")
            self._send_json_response({"success": False, "message": f"日志记录失败: {e}"}, 500)


class MapEditorAPIServer:
    """地图编辑器API服务器"""
    
    def __init__(self, host: str = 'localhost', port: int = 8001):
        self.host = host
        self.port = port
        self.editor_service = EditorService()
        self.robot_instance_service = RobotInstanceService()
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
    
    def create_handler(self):
        """创建请求处理器"""
        editor_service = self.editor_service
        robot_instance_service = self.robot_instance_service
        
        class Handler(MapEditorAPIHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, editor_service=editor_service, robot_instance_service=robot_instance_service, **kwargs)
        
        return Handler
    
    def start(self):
        """启动服务器"""
        if self.is_running:
            return
        
        try:
            handler_class = self.create_handler()
            self.server = HTTPServer((self.host, self.port), handler_class)
            
            # 设置服务器超时
            self.server.timeout = 30
            self.server.socket.settimeout(30)
            
            def run_server():
                print(f"Map Editor API Server started at http://{self.host}:{self.port}")
                try:
                    self.server.serve_forever()
                except Exception as e:
                    print(f"服务器运行错误: {e}")
                    import traceback
                    traceback.print_exc()
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.is_running = True
            
            # 等待服务器启动
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Failed to start API server: {e}")
            raise
        
    def stop(self):
        """停止服务器"""
        if not self.is_running:
            return
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.server_thread:
            self.server_thread.join(timeout=5)
        
        self.is_running = False
        print("Map Editor API Server stopped")
    
    def get_editor_service(self) -> EditorService:
        """获取编辑器服务实例"""
        return self.editor_service
    
    def load_scene_file(self, file_path: str) -> bool:
        """加载场景文件"""
        return self.editor_service.load_scene_from_file(file_path)
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return {
            "host": self.host,
            "port": self.port,
            "is_running": self.is_running,
            "api_base_url": f"http://{self.host}:{self.port}/api"
        }


# 全局API服务器实例
_api_server: Optional[MapEditorAPIServer] = None


def get_api_server(host: str = 'localhost', port: int = 8001) -> MapEditorAPIServer:
    """获取API服务器实例（单例模式）"""
    global _api_server
    if _api_server is None:
        _api_server = MapEditorAPIServer(host, port)
    return _api_server


def start_api_server(host: str = 'localhost', port: int = 8001) -> MapEditorAPIServer:
    """启动API服务器"""
    server = get_api_server(host, port)
    server.start()
    return server


def stop_api_server():
    """停止API服务器"""
    global _api_server
    if _api_server:
        _api_server.stop()
        _api_server = None


if __name__ == "__main__":
    """主函数，用于直接运行API服务器"""
    import argparse
    
    parser = argparse.ArgumentParser(description='启动地图编辑器API服务器')
    parser.add_argument('--host', default='localhost', help='服务器主机地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=8001, help='服务器端口 (默认: 8001)')
    
    args = parser.parse_args()
    
    try:
        logger.info(f"正在启动API服务器 - 主机: {args.host}, 端口: {args.port}")
        server = start_api_server(args.host, args.port)
        logger.info(f"API服务器已启动，访问地址: http://{args.host}:{args.port}")
        
        # 保持服务器运行
        try:
            while server.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止服务器...")
            stop_api_server()
            logger.info("API服务器已停止")
            
    except Exception as e:
        logger.error(f"启动API服务器失败: {e}")
        import traceback
        traceback.print_exc()