"""
传统API注册表实现 (已弃用)
建议使用 unified_api_server.py 中的统一实现

此文件保留作为参考和向后兼容
"""

import re
import json
import threading
import time
from typing import Dict, List, Callable, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import is_dataclass
from datetime import datetime
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import setup_logger

logger = setup_logger()


class APIRoute:
    """API路由定义"""
    def __init__(self, method: str, path: str, handler: Callable, description: str = ""):
        self.method = method.upper()
        self.path = path
        self.handler = handler
        self.description = description
        self.path_pattern = self._compile_path_pattern(path)
    
    def _compile_path_pattern(self, path: str):
        """将路径模式编译为正则表达式"""
        # 将 {param} 替换为命名捕获组
        pattern = re.sub(r'\{([^}]+)\}', r'(?P<\1>[^/]+)', path)
        return re.compile(f'^{pattern}$')
    
    def match(self, path: str) -> Optional[Dict[str, str]]:
        """检查路径是否匹配，返回路径参数"""
        match = self.path_pattern.match(path)
        if match:
            return match.groupdict()
        return None


class APIRegistry:
    """API路由注册表"""
    def __init__(self):
        self.routes: List[APIRoute] = []
    
    def register(self, method: str, path: str, handler: Callable, description: str = ""):
        """注册API路由"""
        route = APIRoute(method, path, handler, description)
        self.routes.append(route)
        logger.info(f"注册API路由: {method} {path}")
    
    def get(self, path: str, description: str = ""):
        """注册GET路由的装饰器"""
        def decorator(handler: Callable):
            self.register('GET', path, handler, description)
            return handler
        return decorator
    
    def post(self, path: str, description: str = ""):
        """注册POST路由的装饰器"""
        def decorator(handler: Callable):
            self.register('POST', path, handler, description)
            return handler
        return decorator
    
    def put(self, path: str, description: str = ""):
        """注册PUT路由的装饰器"""
        def decorator(handler: Callable):
            self.register('PUT', path, handler, description)
            return handler
        return decorator
    
    def delete(self, path: str, description: str = ""):
        """注册DELETE路由的装饰器"""
        def decorator(handler: Callable):
            self.register('DELETE', path, handler, description)
            return handler
        return decorator
    
    def find_route(self, method: str, path: str) -> Optional[Tuple[APIRoute, Dict[str, str]]]:
        """查找匹配的路由"""
        for route in self.routes:
            if route.method == method.upper():
                params = route.match(path)
                if params is not None:
                    return route, params
        return None
    
    def get_routes_info(self) -> List[Dict[str, str]]:
        """获取所有路由信息"""
        return [
            {
                "method": route.method,
                "path": route.path,
                "description": route.description
            }
            for route in self.routes
        ]


def safe_json_serialize(obj):
    """安全的JSON序列化，处理dataclass和其他复杂对象"""
    try:
        from shared import safe_serialize
        return safe_serialize(obj)
    except ImportError:
        # 回退实现
        if is_dataclass(obj):
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            else:
                from dataclasses import asdict
                return asdict(obj)
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, (list, tuple)):
            return [safe_json_serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: safe_json_serialize(value) for key, value in obj.items()}
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj


class APIRequestHandler(BaseHTTPRequestHandler):
    """API请求处理器 (传统实现)"""
    
    def __init__(self, registry: APIRegistry, *args, **kwargs):
        self.registry = registry
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self._handle_request('GET')
    
    def do_POST(self):
        self._handle_request('POST')
    
    def do_PUT(self):
        self._handle_request('PUT')
    
    def do_DELETE(self):
        self._handle_request('DELETE')
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self._send_cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def _handle_request(self, method: str):
        """处理HTTP请求"""
        try:
            # 解析URL
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # 获取请求体
            request_data = None
            if method in ['POST', 'PUT']:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    try:
                        request_data = json.loads(body.decode('utf-8'))
                    except json.JSONDecodeError:
                        request_data = body.decode('utf-8')
            
            # 查找路由
            route_match = self.registry.find_route(method, path)
            if route_match:
                route, path_params = route_match
                
                # 构建请求上下文
                request_context = {
                    'method': method,
                    'path': path,
                    'query_params': query_params,
                    'path_params': path_params,
                    'headers': dict(self.headers),
                    'body': request_data
                }
                
                # 调用处理器
                try:
                    result = route.handler(request_context)
                    if isinstance(result, tuple):
                        data, status_code = result
                    else:
                        data, status_code = result, 200
                    
                    self._send_json_response(data, status_code)
                    
                except Exception as e:
                    logger.error(f"路由处理器执行失败: {e}")
                    self._send_error_response(500, f"内部服务器错误: {str(e)}")
            else:
                self._send_error_response(404, "路由未找到")
                
        except Exception as e:
            logger.error(f"请求处理失败: {e}")
            self._send_error_response(500, f"服务器错误: {str(e)}")
    
    def _send_json_response(self, data: Any, status_code: int = 200):
        """发送JSON响应"""
        try:
            json_data = json.dumps(safe_json_serialize(data), ensure_ascii=False, indent=2)
            json_bytes = json_data.encode('utf-8')
            
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_bytes)))
            self.end_headers()
            
            self.wfile.write(json_bytes)
            
        except Exception as e:
            logger.error(f"发送JSON响应失败: {e}")
            self._send_error_response(500, "响应序列化失败")
    
    def _send_error_response(self, status_code: int, message: str):
        """发送错误响应"""
        try:
            error_data = {
                "error": True,
                "message": message,
                "status": status_code,
                "timestamp": datetime.now().isoformat()
            }
            json_data = json.dumps(error_data, ensure_ascii=False, indent=2)
            json_bytes = json_data.encode('utf-8')
            
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_bytes)))
            self.end_headers()
            
            self.wfile.write(json_bytes)
            
        except Exception as e:
            logger.error(f"发送错误响应失败: {e}")
    
    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def log_message(self, format, *args):
        """重写日志方法"""
        logger.info(f"[API] {format % args}")


class APIServer:
    """API服务器 (传统实现)"""
    
    def __init__(self, host: str = 'localhost', port: int = 8000):
        self.host = host
        self.port = port
        self.registry = APIRegistry()
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self, blocking: bool = False):
        """启动服务器"""
        try:
            def handler_factory(*args, **kwargs):
                return APIRequestHandler(self.registry, *args, **kwargs)
            
            self.server = HTTPServer((self.host, self.port), handler_factory)
            self.running = True
            
            logger.info(f"API服务器启动在 http://{self.host}:{self.port}")
            
            if blocking:
                self.server.serve_forever()
            else:
                self.server_thread = threading.Thread(
                    target=self.server.serve_forever,
                    name="APIServer-Thread"
                )
                self.server_thread.daemon = True
                self.server_thread.start()
                
        except Exception as e:
            logger.error(f"启动API服务器失败: {e}")
            self.running = False
            raise
    
    def stop(self):
        """停止服务器"""
        if self.server:
            logger.info("正在停止API服务器")
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logger.info("API服务器已停止")


# 全局API服务器实例 (传统实现)
_legacy_api_server: Optional[APIServer] = None


def get_api_server() -> APIServer:
    """获取全局API服务器实例 (传统实现)"""
    global _legacy_api_server
    if _legacy_api_server is None:
        _legacy_api_server = APIServer()
    return _legacy_api_server


def start_api_server(host: str = 'localhost', port: int = 8000, blocking: bool = False) -> APIServer:
    """启动API服务器 (传统实现)"""
    global _legacy_api_server
    if _legacy_api_server is None:
        _legacy_api_server = APIServer(host, port)
    
    _legacy_api_server.start(blocking=blocking)
    return _legacy_api_server


def stop_api_server():
    """停止API服务器 (传统实现)"""
    global _legacy_api_server
    if _legacy_api_server:
        _legacy_api_server.stop()
        _legacy_api_server = None


# 向后兼容的装饰器
def get(path: str, description: str = ""):
    """GET路由装饰器 (传统实现)"""
    def decorator(handler: Callable):
        server = get_api_server()
        server.registry.register('GET', path, handler, description)
        return handler
    return decorator


def post(path: str, description: str = ""):
    """POST路由装饰器 (传统实现)"""
    def decorator(handler: Callable):
        server = get_api_server()
        server.registry.register('POST', path, handler, description)
        return handler
    return decorator


def put(path: str, description: str = ""):
    """PUT路由装饰器 (传统实现)"""
    def decorator(handler: Callable):
        server = get_api_server()
        server.registry.register('PUT', path, handler, description)
        return handler
    return decorator


def delete(path: str, description: str = ""):
    """DELETE路由装饰器 (传统实现)"""
    def decorator(handler: Callable):
        server = get_api_server()
        server.registry.register('DELETE', path, handler, description)
        return handler
    return decorator