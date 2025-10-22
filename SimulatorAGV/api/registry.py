"""API注册中心
统一管理和注册所有API路由
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Callable, List, Tuple
import traceback
import sys
import os
import re
from datetime import datetime
from dataclasses import is_dataclass

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger_config import logger


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
        """GET方法装饰器"""
        def decorator(handler: Callable):
            self.register("GET", path, handler, description)
            return handler
        return decorator
    
    def post(self, path: str, description: str = ""):
        """POST方法装饰器"""
        def decorator(handler: Callable):
            self.register("POST", path, handler, description)
            return handler
        return decorator
    
    def put(self, path: str, description: str = ""):
        """PUT方法装饰器"""
        def decorator(handler: Callable):
            self.register("PUT", path, handler, description)
            return handler
        return decorator
    
    def delete(self, path: str, description: str = ""):
        """DELETE方法装饰器"""
        def decorator(handler: Callable):
            self.register("DELETE", path, handler, description)
            return handler
        return decorator
    
    def find_route(self, method: str, path: str) -> Optional[tuple]:
        """查找匹配的路由，返回(route, path_params)"""
        for route in self.routes:
            if route.method == method.upper():
                path_params = route.match(path)
                if path_params is not None:
                    return route, path_params
        return None
    
    def get_routes(self) -> List[Dict[str, str]]:
        """获取所有注册的路由信息"""
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
    if is_dataclass(obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        else:
            # 如果没有to_dict方法，使用dataclass的字段
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
    """API请求处理器"""
    
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
            
            # 查找匹配的路由
            route_match = self.registry.find_route(method, path)
            if not route_match:
                self._send_error(404, "API endpoint not found")
                return
            
            route, path_params = route_match
            
            # 准备请求数据
            request_data = {
                'method': method,
                'path': path,
                'path_params': path_params,
                'query_params': query_params,
                'headers': dict(self.headers)
            }
            
            # 读取请求体（对于POST和PUT请求）
            if method in ['POST', 'PUT']:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length).decode('utf-8')
                    try:
                        request_data['body'] = json.loads(body)
                    except json.JSONDecodeError:
                        request_data['body'] = body
            
            # 调用路由处理器
            try:
                response = route.handler(request_data)
                self._send_json_response(response)
            except Exception as e:
                logger.error(f"API处理器执行失败: {e}")
                self._send_error(500, f"Internal server error: {str(e)}")
            
        except Exception as e:
            logger.error(f"处理API请求失败: {e}")
            self._send_error(500, "Internal server error")
    
    def _send_json_response(self, data: Any, status_code: int = 200):
        """发送JSON响应"""
        try:
            # 使用安全的JSON序列化
            json_data = json.dumps(safe_json_serialize(data), ensure_ascii=False, indent=2)
            
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(json_data.encode('utf-8'))
        except Exception as e:
            logger.error(f"发送JSON响应失败: {e}")
            self._send_error(500, "Failed to serialize response")
    
    def _send_error(self, status_code: int, message: str):
        """发送错误响应"""
        error_data = {
            "error": True,
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            json_data = json.dumps(error_data, ensure_ascii=False, indent=2)
            
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(json_data.encode('utf-8'))
        except Exception as e:
            logger.error(f"发送错误响应失败: {e}")
    
    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def log_message(self, format, *args):
        """重写日志方法，使用我们的logger"""
        logger.info(f"[API] {format % args}")


class APIServer:
    """API服务器"""
    def __init__(self):
        self.registry = APIRegistry()
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
    
    def start(self, host: str = 'localhost', port: int = 8000):
        """启动API服务器"""
        if self.running:
            logger.warning("API服务器已在运行")
            return
        
        def handler_factory(*args, **kwargs):
            return APIRequestHandler(self.registry, *args, **kwargs)
        
        try:
            self.server = HTTPServer((host, port), handler_factory)
            self.running = True
            
            logger.info(f"API服务器启动在 http://{host}:{port}")
            
            def run_server():
                try:
                    self.server.serve_forever()
                except Exception as e:
                    logger.error(f"API服务器运行错误: {e}")
                finally:
                    self.running = False
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            logger.info(f"API服务器已启动，地址: http://{host}:{port}")
            
        except Exception as e:
            logger.error(f"启动API服务器失败: {e}")
            self.running = False
            raise
    
    def stop(self):
        """停止API服务器"""
        if not self.running:
            return
        
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            self.running = False
            logger.info("API服务器已停止")
            
        except Exception as e:
            logger.error(f"停止API服务器失败: {e}")
    
    def get_registry(self) -> APIRegistry:
        """获取路由注册表"""
        return self.registry


# 全局API服务器实例（单例模式）
_api_server: Optional[APIServer] = None


def get_api_server() -> APIServer:
    """获取API服务器实例"""
    global _api_server
    if _api_server is None:
        _api_server = APIServer()
    return _api_server


def start_api_server(host: str = 'localhost', port: int = 8000) -> APIServer:
    """启动API服务器"""
    server = get_api_server()
    server.start(host, port)
    return server


def stop_api_server():
    """停止API服务器"""
    global _api_server
    if _api_server:
        _api_server.stop()
        _api_server = None