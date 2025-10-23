"""
统一的API服务器实现
使用共享HTTP服务器基类，整合现有的API路由功能
"""
import re
from typing import Dict, Any, List, Callable, Optional, Tuple
from dataclasses import is_dataclass
from datetime import datetime

try:
    from shared import BaseHTTPServer, setup_logger, safe_serialize
    _use_shared_base = True
except ImportError:
    _use_shared_base = False
    import logging
    logger = logging.getLogger(__name__)

if _use_shared_base:
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
    if _use_shared_base:
        return safe_serialize(obj)
    
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


if _use_shared_base:
    class UnifiedAPIServer(BaseHTTPServer):
        """统一的API服务器，基于共享HTTP服务器基类"""
        
        def __init__(self, host: str = 'localhost', port: int = 8000, server_name: str = "UnifiedAPIServer"):
            super().__init__(host, port, server_name)
            self.registry = APIRegistry()
            
            # 添加默认的API信息路由
            self.add_route('GET', '/api', self._api_info)
            self.add_route('GET', '/api/routes', self._routes_info)
        
        def register_route(self, method: str, path: str, handler: Callable, description: str = ""):
            """注册API路由"""
            self.registry.register(method, path, handler, description)
        
        def handle_custom_route(self, method: str, path: str, query_params: Dict,
                               request_data: Any, headers: Dict) -> Optional[Tuple[Any, int]]:
            """处理自定义路由"""
            # 查找匹配的路由
            route_match = self.registry.find_route(method, path)
            if route_match:
                route, path_params = route_match
                try:
                    # 调用路由处理器
                    result = route.handler(query_params, request_data, headers, path_params)
                    if isinstance(result, tuple):
                        return result
                    else:
                        return result, 200
                except Exception as e:
                    self.logger.error(f"路由处理器执行失败: {e}")
                    return {"error": "路由处理失败", "message": str(e)}, 500
            
            return None
        
        def _api_info(self, query_params: Dict, request_data: Any, headers: Dict) -> Tuple[Dict, int]:
            """API信息"""
            return {
                "server": self.server_name,
                "version": "1.0.0",
                "routes_count": len(self.registry.routes),
                "endpoints": [f"{route.method} {route.path}" for route in self.registry.routes]
            }, 200
        
        def _routes_info(self, query_params: Dict, request_data: Any, headers: Dict) -> Tuple[List, int]:
            """路由信息"""
            return self.registry.get_routes_info(), 200
        
        # 装饰器方法
        def get(self, path: str, description: str = ""):
            return self.registry.get(path, description)
        
        def post(self, path: str, description: str = ""):
            return self.registry.post(path, description)
        
        def put(self, path: str, description: str = ""):
            return self.registry.put(path, description)
        
        def delete(self, path: str, description: str = ""):
            return self.registry.delete(path, description)

else:
    # 如果共享基类不可用，提供简化的实现
    class UnifiedAPIServer:
        """简化的API服务器实现（回退版本）"""
        
        def __init__(self, host: str = 'localhost', port: int = 8000, server_name: str = "UnifiedAPIServer"):
            self.host = host
            self.port = port
            self.server_name = server_name
            self.registry = APIRegistry()
            logger.warning("共享HTTP服务器基类不可用，使用简化实现")
        
        def register_route(self, method: str, path: str, handler: Callable, description: str = ""):
            """注册API路由"""
            self.registry.register(method, path, handler, description)
        
        def start(self, blocking: bool = False):
            """启动服务器（简化实现）"""
            logger.info(f"{self.server_name} 启动在 http://{self.host}:{self.port}")
            logger.warning("请使用完整的共享模块以获得完整功能")
        
        def stop(self):
            """停止服务器"""
            logger.info(f"{self.server_name} 已停止")


# 全局API服务器实例
_api_server: Optional[UnifiedAPIServer] = None


def get_api_server() -> UnifiedAPIServer:
    """获取全局API服务器实例"""
    global _api_server
    if _api_server is None:
        _api_server = UnifiedAPIServer()
    return _api_server


def start_api_server(host: str = 'localhost', port: int = 8000, blocking: bool = False) -> UnifiedAPIServer:
    """启动API服务器"""
    global _api_server
    if _api_server is None:
        _api_server = UnifiedAPIServer(host, port)
    
    _api_server.start(blocking=blocking)
    return _api_server


def stop_api_server():
    """停止API服务器"""
    global _api_server
    if _api_server:
        _api_server.stop()
        _api_server = None


def register_route(method: str, path: str, handler: Callable, description: str = ""):
    """注册API路由到全局服务器"""
    server = get_api_server()
    server.register_route(method, path, handler, description)


# 装饰器函数
def get(path: str, description: str = ""):
    """GET路由装饰器"""
    def decorator(handler: Callable):
        register_route('GET', path, handler, description)
        return handler
    return decorator


def post(path: str, description: str = ""):
    """POST路由装饰器"""
    def decorator(handler: Callable):
        register_route('POST', path, handler, description)
        return handler
    return decorator


def put(path: str, description: str = ""):
    """PUT路由装饰器"""
    def decorator(handler: Callable):
        register_route('PUT', path, handler, description)
        return handler
    return decorator


def delete(path: str, description: str = ""):
    """DELETE路由装饰器"""
    def decorator(handler: Callable):
        register_route('DELETE', path, handler, description)
        return handler
    return decorator