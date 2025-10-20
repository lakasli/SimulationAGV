"""Web API接口
为HTML地图查看器提供HTTP接口
"""
import sys
import os
import json
import uuid
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
from models.map_models import Point, MapPointType, MapRouteType, MapAreaType, Rect
from models.robot_models import RobotType, RobotStatus


class MapEditorAPIHandler(BaseHTTPRequestHandler):
    """地图编辑器API处理器"""
    
    def __init__(self, *args, editor_service: EditorService = None, **kwargs):
        self.editor_service = editor_service or EditorService()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            if path == '/api/scene/data':
                self._handle_get_scene_data()
            elif path == '/api/points':
                self._handle_get_points(query_params)
            elif path == '/api/routes':
                self._handle_get_routes(query_params)
            elif path == '/api/areas':
                self._handle_get_areas(query_params)
            elif path == '/api/robots':
                self._handle_get_robots(query_params)
            elif path == '/api/statistics':
                self._handle_get_statistics()
            elif path == '/api/search':
                self._handle_search(query_params)
            else:
                self._send_error(404, "API endpoint not found")
                
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """处理POST请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data) if post_data else {}
            
            if path == '/api/scene/load':
                self._handle_load_scene(data)
            elif path == '/api/scene/save':
                self._handle_save_scene(data)
            elif path == '/api/points':
                self._handle_create_point(data)
            elif path == '/api/routes':
                self._handle_create_route(data)
            elif path == '/api/areas':
                self._handle_create_area(data)
            elif path == '/api/robots':
                self._handle_create_robot(data)
            else:
                self._send_error(404, "API endpoint not found")
                
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_PUT(self):
        """处理PUT请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data) if post_data else {}
            
            if path.startswith('/api/points/'):
                point_id = path.split('/')[-1]
                self._handle_update_point(point_id, data)
            elif path.startswith('/api/routes/'):
                route_id = path.split('/')[-1]
                self._handle_update_route(route_id, data)
            elif path.startswith('/api/areas/'):
                area_id = path.split('/')[-1]
                self._handle_update_area(area_id, data)
            elif path.startswith('/api/robots/'):
                robot_id = path.split('/')[-1]
                self._handle_update_robot(robot_id, data)
            else:
                self._send_error(404, "API endpoint not found")
                
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_DELETE(self):
        """处理DELETE请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path.startswith('/api/points/'):
                point_id = path.split('/')[-1]
                self._handle_delete_point(point_id)
            elif path.startswith('/api/routes/'):
                route_id = path.split('/')[-1]
                self._handle_delete_route(route_id)
            elif path.startswith('/api/areas/'):
                area_id = path.split('/')[-1]
                self._handle_delete_area(area_id)
            elif path.startswith('/api/robots/'):
                robot_id = path.split('/')[-1]
                self._handle_delete_robot(robot_id)
            else:
                self._send_error(404, "API endpoint not found")
                
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self._send_cors_headers()
        self.end_headers()
    
    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def _send_json_response(self, data: Any, status_code: int = 200):
        """发送JSON响应"""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            self.wfile.write(json_data.encode('utf-8'))
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            # 客户端断开连接，记录日志但不抛出异常
            print(f"客户端连接断开: {e}")
        except Exception as e:
            # 其他异常，记录详细信息
            print(f"发送响应时出错: {e}")
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
            self._send_json_response(error_data, status_code)
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            # 客户端断开连接，记录日志但不抛出异常
            print(f"发送错误响应时客户端连接断开: {e}")
        except Exception as e:
            # 其他异常，记录详细信息
            print(f"发送错误响应时出错: {e}")
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
            print(f"获取场景数据失败: {e}")
            import traceback
            traceback.print_exc()
            try:
                self._send_error(500, f"获取场景数据失败: {str(e)}")
            except (ConnectionResetError, BrokenPipeError, OSError):
                # 客户端已断开连接，无需发送错误响应
                print("客户端连接已断开，无法发送错误响应")
            except Exception as send_error:
                print(f"发送错误响应失败: {send_error}")
    
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
        """获取机器人列表"""
        robots = self.editor_service.robot_service.get_robots()
        robots_data = [robot.__dict__ for robot in robots]
        self._send_json_response(robots_data)
    
    def _handle_create_robot(self, data: Dict[str, Any]):
        """创建机器人"""
        # 这里需要根据实际需求实现机器人创建逻辑
        self._send_json_response({"success": False, "message": "Robot creation not implemented"})
    
    def _handle_update_robot(self, robot_id: str, data: Dict[str, Any]):
        """更新机器人"""
        success = self.editor_service.robot_service.update_robot(robot_id, data)
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success})
    
    def _handle_delete_robot(self, robot_id: str):
        """删除机器人"""
        success = self.editor_service.robot_service.remove_robots([robot_id])
        if success:
            self.editor_service.mark_modified()
        self._send_json_response({"success": success > 0})
    
    # 其他API
    def _handle_get_statistics(self):
        """获取统计信息"""
        stats = self.editor_service.get_scene_statistics()
        self._send_json_response(stats)
    
    def _handle_search(self, query_params: Dict[str, list]):
        """搜索"""
        keyword = query_params.get('q', [''])[0]
        if not keyword:
            self._send_error(400, "Missing search keyword")
            return
        
        results = self.editor_service.search_all(keyword)
        # 转换为字典格式
        results_data = {}
        for key, items in results.items():
            results_data[key] = [item.__dict__ for item in items]
        
        self._send_json_response(results_data)


class MapEditorAPIServer:
    """地图编辑器API服务器"""
    
    def __init__(self, host: str = 'localhost', port: int = 8001):
        self.host = host
        self.port = port
        self.editor_service = EditorService()
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
    
    def create_handler(self):
        """创建请求处理器"""
        editor_service = self.editor_service
        
        class Handler(MapEditorAPIHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, editor_service=editor_service, **kwargs)
        
        return Handler
    
    def start(self):
        """启动服务器"""
        if self.is_running:
            return
        
        try:
            handler_class = self.create_handler()
            self.server = HTTPServer((self.host, self.port), handler_class)
            
            def run_server():
                print(f"Map Editor API Server started at http://{self.host}:{self.port}")
                self.server.serve_forever()
            
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