"""
系统相关API路由
"""

import json
import os
from typing import Dict, Any
from .registry import get_api_server
from shared import setup_logger

logger = setup_logger()


def register_system_routes(instance_manager):
    """注册系统相关的API路由"""
    
    server = get_api_server()
    registry = server.get_registry()
    
    @registry.get("/api/system/info", "获取系统信息")
    def get_system_info(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            return {
                "service_name": "SimulatorAGV",
                "version": "1.0.0",
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "platform": os.name,
                "pid": os.getpid(),
                "working_directory": os.getcwd()
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/system/stats", "获取系统统计信息")
    def get_system_stats(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            stats = {
                "total_robots": instance_manager.get_robot_count(),
                "running_robots": 0,
                "idle_robots": 0,
                "error_robots": 0
            }
            
            # 统计各状态机器人数量
            for robot_id in instance_manager.get_robot_list():
                robot_status = instance_manager.get_robot_status(robot_id)
                status = robot_status.get("status", "unknown").lower()
                
                if status == "running":
                    stats["running_robots"] += 1
                elif status == "idle":
                    stats["idle_robots"] += 1
                elif status in ["error", "fault"]:
                    stats["error_robots"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取系统统计信息失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/system/config", "获取系统配置")
    def get_system_config(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统配置"""
        try:
            # 获取基础配置
            config = {}
            if hasattr(instance_manager, 'base_config'):
                config = instance_manager.base_config
            
            return {
                "config": config,
                "config_file": getattr(instance_manager, 'base_config_path', 'unknown'),
                "registry_file": getattr(instance_manager, 'registry_path', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/system/reload-config", "重新加载配置")
    def reload_config(request: Dict[str, Any]) -> Dict[str, Any]:
        """重新加载配置"""
        try:
            # 重新加载机器人注册信息
            if hasattr(instance_manager, '_reload_robots_from_registry'):
                instance_manager._reload_robots_from_registry()
                return {
                    "success": True,
                    "message": "配置重新加载成功"
                }
            else:
                return {"error": "系统不支持配置重新加载"}
            
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/system/start-all", "启动所有机器人")
    def start_all_robots(request: Dict[str, Any]) -> Dict[str, Any]:
        """启动所有机器人"""
        try:
            instance_manager.start_all()
            return {
                "success": True,
                "message": "所有机器人启动命令已发送",
                "robot_count": instance_manager.get_robot_count()
            }
            
        except Exception as e:
            logger.error(f"启动所有机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/system/stop-all", "停止所有机器人")
    def stop_all_robots(request: Dict[str, Any]) -> Dict[str, Any]:
        """停止所有机器人"""
        try:
            instance_manager.stop_all()
            return {
                "success": True,
                "message": "所有机器人停止命令已发送",
                "robot_count": instance_manager.get_robot_count()
            }
            
        except Exception as e:
            logger.error(f"停止所有机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/system/logs", "获取系统日志")
    def get_system_logs(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统日志"""
        try:
            query_params = request.get("query_params", {})
            lines = int(query_params.get("lines", [100])[0])
            
            # 读取日志文件
            log_file = "logs/SimulatorAGV.logs"
            logs = []
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    logs = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    logs = [line.strip() for line in logs]
            
            return {
                "logs": logs,
                "total_lines": len(logs),
                "log_file": log_file
            }
            
        except Exception as e:
            logger.error(f"获取系统日志失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/routes", "获取所有API路由")
    def get_api_routes(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取所有API路由"""
        try:
            routes = server.get_registry().get_routes()
            return {
                "routes": routes,
                "total": len(routes)
            }
            
        except Exception as e:
            logger.error(f"获取API路由失败: {e}")
            return {"error": str(e)}
    
    logger.info("系统API路由注册完成")