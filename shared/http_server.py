"""
HTTP服务器基类
统一项目中的HTTP服务器实现，减少重复代码
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Callable, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import threading
import time

from .serialization import create_json_response, from_json
from .logger_config import setup_logger


class BaseHTTPHandler(BaseHTTPRequestHandler):
    """基础HTTP请求处理器"""
    
    def __init__(self, server_instance, *args, **kwargs):
        self.server_instance = server_instance
        self.logger = setup_logger(self.__class__.__name__)
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """重写日志方法，使用统一的logger"""
        self.logger.info(format % args)
    
    def do_GET(self):
        """处理GET请求"""
        try:
            self._handle_request('GET')
        except Exception as e:
            self.logger.error(f"GET请求处理失败: {e}")
            self._send_error_response(500, str(e))
    
    def do_POST(self):
        """处理POST请求"""
        try:
            self._handle_request('POST')
        except Exception as e:
            self.logger.error(f"POST请求处理失败: {e}")
            self._send_error_response(500, str(e))
    
    def do_PUT(self):
        """处理PUT请求"""
        try:
            self._handle_request('PUT')
        except Exception as e:
            self.logger.error(f"PUT请求处理失败: {e}")
            self._send_error_response(500, str(e))
    
    def do_DELETE(self):
        """处理DELETE请求"""
        try:
            self._handle_request('DELETE')
        except Exception as e:
            self.logger.error(f"DELETE请求处理失败: {e}")
            self._send_error_response(500, str(e))
    
    def _handle_request(self, method: str):
        """统一处理请求"""
        # 解析URL和查询参数
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # 获取请求体数据
        request_data = None
        if method in ['POST', 'PUT']:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                raw_data = self.rfile.read(content_length)
                try:
                    if self.headers.get('Content-Type', '').startswith('application/json'):
                        request_data = from_json(raw_data.decode('utf-8'))
                    else:
                        request_data = raw_data.decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"请求数据解析失败: {e}")
                    request_data = raw_data.decode('utf-8', errors='ignore')
        
        # 调用服务器实例的路由处理方法
        response_data, status_code = self.server_instance.handle_route(
            method, path, query_params, request_data, self.headers
        )
        
        # 发送响应
        self._send_response(response_data, status_code)
    
    def _send_response(self, data: Any, status_code: int = 200):
        """发送响应"""
        try:
            if isinstance(data, str):
                response_body = data
                content_type = 'text/plain; charset=utf-8'
            else:
                response_body, _ = create_json_response(data)
                content_type = 'application/json; charset=utf-8'
            
            self.send_response(status_code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(response_body.encode('utf-8'))))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            
            self.wfile.write(response_body.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"发送响应失败: {e}")
            self._send_error_response(500, "内部服务器错误")
    
    def _send_error_response(self, status_code: int, message: str):
        """发送错误响应"""
        try:
            error_data = {
                "error": True,
                "message": message,
                "status": status_code,
                "timestamp": time.time()
            }
            response_body, _ = create_json_response(error_data)
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_body.encode('utf-8'))))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(response_body.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"发送错误响应失败: {e}")
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程HTTP服务器"""
    daemon_threads = True
    allow_reuse_address = True


class BaseHTTPServer(ABC):
    """HTTP服务器基类"""
    
    def __init__(self, host: str = 'localhost', port: int = 8000, 
                 server_name: str = "BaseHTTPServer"):
        self.host = host
        self.port = port
        self.server_name = server_name
        self.logger = setup_logger(f"{server_name}")
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.routes: Dict[str, Dict[str, Callable]] = {}
        
        # 注册默认路由
        self._register_default_routes()
    
    def _register_default_routes(self):
        """注册默认路由"""
        self.add_route('GET', '/health', self._health_check)
        self.add_route('GET', '/status', self._server_status)
    
    def add_route(self, method: str, path: str, handler: Callable):
        """添加路由"""
        if path not in self.routes:
            self.routes[path] = {}
        self.routes[path][method.upper()] = handler
        self.logger.debug(f"添加路由: {method.upper()} {path}")
    
    def handle_route(self, method: str, path: str, query_params: Dict, 
                    request_data: Any, headers: Dict) -> Tuple[Any, int]:
        """处理路由请求"""
        try:
            # 查找精确匹配的路由
            if path in self.routes and method in self.routes[path]:
                handler = self.routes[path][method]
                return handler(query_params, request_data, headers)
            
            # 查找模式匹配的路由
            for route_path, methods in self.routes.items():
                if self._match_route(path, route_path) and method in methods:
                    handler = methods[method]
                    return handler(query_params, request_data, headers)
            
            # 调用子类的自定义路由处理
            result = self.handle_custom_route(method, path, query_params, request_data, headers)
            if result is not None:
                return result
            
            # 未找到路由
            return {"error": "路由未找到", "path": path, "method": method}, 404
            
        except Exception as e:
            self.logger.error(f"路由处理失败: {e}")
            return {"error": "内部服务器错误", "message": str(e)}, 500
    
    def _match_route(self, request_path: str, route_path: str) -> bool:
        """简单的路由匹配（支持通配符）"""
        if route_path.endswith('*'):
            return request_path.startswith(route_path[:-1])
        return request_path == route_path
    
    @abstractmethod
    def handle_custom_route(self, method: str, path: str, query_params: Dict,
                           request_data: Any, headers: Dict) -> Optional[Tuple[Any, int]]:
        """处理自定义路由（子类实现）"""
        pass
    
    def _health_check(self, query_params: Dict, request_data: Any, headers: Dict) -> Tuple[Dict, int]:
        """健康检查"""
        return {
            "status": "healthy",
            "server": self.server_name,
            "timestamp": time.time()
        }, 200
    
    def _server_status(self, query_params: Dict, request_data: Any, headers: Dict) -> Tuple[Dict, int]:
        """服务器状态"""
        return {
            "server": self.server_name,
            "host": self.host,
            "port": self.port,
            "running": self.is_running,
            "routes": list(self.routes.keys()),
            "timestamp": time.time()
        }, 200
    
    def start(self, blocking: bool = False):
        """启动服务器"""
        try:
            # 创建处理器类，绑定服务器实例
            def handler_factory(*args, **kwargs):
                return BaseHTTPHandler(self, *args, **kwargs)
            
            # 创建服务器
            self.server = ThreadedHTTPServer((self.host, self.port), handler_factory)
            self.is_running = True
            
            self.logger.info(f"{self.server_name} 启动在 http://{self.host}:{self.port}")
            
            if blocking:
                # 阻塞模式
                self.server.serve_forever()
            else:
                # 非阻塞模式
                self.server_thread = threading.Thread(
                    target=self.server.serve_forever,
                    name=f"{self.server_name}-Thread"
                )
                self.server_thread.daemon = True
                self.server_thread.start()
                
        except Exception as e:
            self.logger.error(f"启动服务器失败: {e}")
            self.is_running = False
            raise
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.logger.info(f"正在停止 {self.server_name}")
            self.server.shutdown()
            self.server.server_close()
            self.is_running = False
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            self.logger.info(f"{self.server_name} 已停止")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


class SimpleHTTPServer(BaseHTTPServer):
    """简单的HTTP服务器实现"""
    
    def __init__(self, host: str = 'localhost', port: int = 8000):
        super().__init__(host, port, "SimpleHTTPServer")
    
    def handle_custom_route(self, method: str, path: str, query_params: Dict,
                           request_data: Any, headers: Dict) -> Optional[Tuple[Any, int]]:
        """简单服务器不处理自定义路由"""
        return None


# 便捷函数
def create_simple_server(host: str = 'localhost', port: int = 8000) -> SimpleHTTPServer:
    """创建简单HTTP服务器"""
    return SimpleHTTPServer(host, port)


def run_simple_server(host: str = 'localhost', port: int = 8000, blocking: bool = True):
    """运行简单HTTP服务器"""
    server = create_simple_server(host, port)
    try:
        server.start(blocking=blocking)
        if not blocking:
            return server
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        logging.error(f"服务器运行失败: {e}")
        server.stop()
        raise