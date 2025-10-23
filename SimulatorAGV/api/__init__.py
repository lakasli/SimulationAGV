"""
API模块初始化文件
统一管理所有API路由和服务器
"""

from .registry import APIRegistry, start_api_server, stop_api_server, get_api_server
from .robot_routes import register_robot_routes
from .order_routes import register_order_routes
from .system_routes import register_system_routes
from .map_routes import register_map_routes


def register_all_routes(instance_manager):
    """注册所有API路由"""
    register_robot_routes(instance_manager)
    register_order_routes(instance_manager)
    register_system_routes(instance_manager)
    register_map_routes(instance_manager)


__all__ = [
    'APIRegistry', 
    'start_api_server', 
    'stop_api_server', 
    'get_api_server',
    'register_all_routes'
]