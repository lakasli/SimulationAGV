"""
机器人相关API路由
"""

import json
from typing import Dict, Any
from .registry import get_api_server
from logger_config import logger


def register_robot_routes(instance_manager):
    """注册机器人相关的API路由"""
    
    server = get_api_server()
    registry = server.get_registry()
    
    @registry.get("/api/status", "获取系统状态")
    def get_system_status(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            return {
                "status": "running" if instance_manager.is_running() else "stopped",
                "robot_count": instance_manager.get_robot_count(),
                "timestamp": instance_manager._get_timestamp() if hasattr(instance_manager, '_get_timestamp') else None
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/robots", "获取所有机器人列表")
    def get_robots(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取所有机器人列表"""
        try:
            robots = []
            for robot_id in instance_manager.get_robot_list():
                robot_status = instance_manager.get_robot_status(robot_id)
                robots.append({
                    "id": robot_id,
                    "status": robot_status.get("status", "unknown"),
                    "position": robot_status.get("position", {}),
                    "battery": robot_status.get("battery", 0),
                    "is_warning": robot_status.get("is_warning", False),
                    "is_fault": robot_status.get("is_fault", False)
                })
            
            return {
                "robots": robots,
                "total": len(robots)
            }
        except Exception as e:
            logger.error(f"获取机器人列表失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/robots/{robot_id}/status", "获取指定机器人状态")
    def get_robot_status(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取指定机器人状态"""
        try:
            robot_id = request["path_params"]["robot_id"]
            status = instance_manager.get_robot_status(robot_id)
            
            if not status:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            return status
        except Exception as e:
            logger.error(f"获取机器人状态失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/health", "健康检查")
    def health_check(request: Dict[str, Any]) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "service": "SimulatorAGV",
            "version": "1.0.0"
        }
    
    @registry.post("/api/robots", "创建新机器人")
    def create_robot(request: Dict[str, Any]) -> Dict[str, Any]:
        """创建新机器人"""
        try:
            robot_info = request.get("body", {})
            
            if not robot_info:
                return {"error": "缺少机器人信息"}
            
            success = instance_manager.add_robot(robot_info)
            
            if success:
                return {
                    "success": True,
                    "message": f"机器人 {robot_info.get('id')} 创建成功"
                }
            else:
                return {"error": "创建机器人失败"}
                
        except Exception as e:
            logger.error(f"创建机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.put("/api/robots/{robot_id}", "更新机器人信息")
    def update_robot(request: Dict[str, Any]) -> Dict[str, Any]:
        """更新机器人信息"""
        try:
            robot_id = request["path_params"]["robot_id"]
            update_data = request.get("body", {})
            
            # 获取机器人实例
            robot_instance = instance_manager.get_robot_instance(robot_id)
            if not robot_instance:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            # 这里可以添加更新机器人配置的逻辑
            # 目前只返回成功消息
            return {
                "success": True,
                "message": f"机器人 {robot_id} 更新成功"
            }
            
        except Exception as e:
            logger.error(f"更新机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.delete("/api/robots/{robot_id}", "删除机器人")
    def delete_robot(request: Dict[str, Any]) -> Dict[str, Any]:
        """删除机器人"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            success = instance_manager.remove_robot(robot_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"机器人 {robot_id} 删除成功"
                }
            else:
                return {"error": f"删除机器人 {robot_id} 失败"}
                
        except Exception as e:
            logger.error(f"删除机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/robots/{robot_id}/start", "启动机器人")
    def start_robot(request: Dict[str, Any]) -> Dict[str, Any]:
        """启动机器人"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            success = instance_manager.start_robot(robot_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"机器人 {robot_id} 启动成功"
                }
            else:
                return {"error": f"启动机器人 {robot_id} 失败"}
                
        except Exception as e:
            logger.error(f"启动机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/robots/{robot_id}/stop", "停止机器人")
    def stop_robot(request: Dict[str, Any]) -> Dict[str, Any]:
        """停止机器人"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            success = instance_manager.stop_robot(robot_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"机器人 {robot_id} 停止成功"
                }
            else:
                return {"error": f"停止机器人 {robot_id} 失败"}
                
        except Exception as e:
            logger.error(f"停止机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/robots/{robot_id}/restart", "重启机器人")
    def restart_robot(request: Dict[str, Any]) -> Dict[str, Any]:
        """重启机器人"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            success = instance_manager.restart_robot(robot_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"机器人 {robot_id} 重启成功"
                }
            else:
                return {"error": f"重启机器人 {robot_id} 失败"}
                
        except Exception as e:
            logger.error(f"重启机器人失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/robots/{robot_id}/config", "获取机器人配置")
    def get_robot_config(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取机器人配置"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            robot_instance = instance_manager.get_robot_instance(robot_id)
            if not robot_instance:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            # 获取机器人配置
            config = robot_instance.get_config() if hasattr(robot_instance, 'get_config') else {}
            
            return {
                "robot_id": robot_id,
                "config": config
            }
            
        except Exception as e:
            logger.error(f"获取机器人配置失败: {e}")
            return {"error": str(e)}
    
    @registry.put("/api/robots/{robot_id}/config", "更新机器人配置")
    def update_robot_config(request: Dict[str, Any]) -> Dict[str, Any]:
        """更新机器人配置"""
        try:
            robot_id = request["path_params"]["robot_id"]
            config_data = request.get("body", {})
            
            robot_instance = instance_manager.get_robot_instance(robot_id)
            if not robot_instance:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            # 更新机器人配置
            if hasattr(robot_instance, 'update_config'):
                success = robot_instance.update_config(config_data)
                if success:
                    return {
                        "success": True,
                        "message": f"机器人 {robot_id} 配置更新成功"
                    }
                else:
                    return {"error": "配置更新失败"}
            else:
                return {"error": "机器人不支持配置更新"}
            
        except Exception as e:
            logger.error(f"更新机器人配置失败: {e}")
            return {"error": str(e)}
    
    logger.info("机器人API路由注册完成")