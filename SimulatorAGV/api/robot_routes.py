"""
机器人相关API路由
"""

import json
from typing import Dict, Any
from .registry import get_api_server
from shared import setup_logger

logger = setup_logger()


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
        """更新机器人信息：
        - 将名称、类型、IP、厂商写入 registered_robots.json
        - 其余配置合并写入 robot_data/<serial>/state/current_state.json
        """
        try:
            import os
            from pathlib import Path
            from ..services.file_storage_manager import get_file_storage_manager


            robot_id = request["path_params"]["robot_id"]
            update_data = request.get("body", {}) or {}

            # 允许 body 中提供 serialNumber，但以路径参数为准
            serial_number = str(update_data.get("serialNumber") or robot_id)

            # 1) 更新注册文件 registered_robots.json
            registry_path = instance_manager.registry_path or os.path.join(os.getcwd(), "registered_robots.json")
            robots_list = []
            try:
                if os.path.exists(registry_path):
                    with open(registry_path, 'r', encoding='utf-8') as f:
                        robots_list = json.load(f) or []
            except Exception as e:
                logger.warning(f"读取注册文件失败，使用空列表: {e}")
                robots_list = []

            # 查找并更新或追加条目
            found = False
            for robot in robots_list:
                if robot.get("serialNumber") == serial_number:
                    # 基本信息同步
                    name_val = update_data.get("name") or update_data.get("robot_name")
                    if name_val:
                        robot["name"] = name_val
                    if "type" in update_data:
                        robot["type"] = update_data["type"]
                    if "ip" in update_data:
                        robot["ip"] = update_data["ip"]
                    if "manufacturer" in update_data:
                        robot["manufacturer"] = update_data["manufacturer"]
                    found = True
                    break
            if not found:
                # 若不存在则追加
                new_entry = {
                    "serialNumber": serial_number,
                    "manufacturer": update_data.get("manufacturer", "SimulatorAGV"),
                    "type": update_data.get("type", "AGV"),
                    "ip": update_data.get("ip", "127.0.0.1"),
                }
                name_val = update_data.get("name") or update_data.get("robot_name")
                if name_val:
                    new_entry["name"] = name_val
                robots_list.append(new_entry)

            # 写回注册文件
            try:
                with open(registry_path, 'w', encoding='utf-8') as f:
                    json.dump(robots_list, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"写入注册文件失败: {e}")
                return {"error": f"注册文件写入失败: {str(e)}"}

            # 2) 合并其他配置到 current_state.json
            fs = get_file_storage_manager()
            state_file = Path(fs.base_path) / serial_number / "state" / "current_state.json"

            existing_state = {}
            try:
                if state_file.exists():
                    with open(state_file, 'r', encoding='utf-8') as f:
                        existing_state = json.load(f) or {}
            except Exception as e:
                logger.warning(f"读取现有状态文件失败，使用空状态: {e}")
                existing_state = {}

            # 准备待合并的配置字段
            merged_state = dict(existing_state)
            if "battery" in update_data:
                merged_state["battery"] = update_data["battery"]
            if "maxSpeed" in update_data:
                merged_state["maxSpeed"] = update_data["maxSpeed"]
            # orientation 可能在 config.orientation 或直接提供
            orientation = None
            if isinstance(update_data.get("config"), dict) and "orientation" in update_data["config"]:
                orientation = update_data["config"]["orientation"]
            elif "orientation" in update_data:
                orientation = update_data["orientation"]
            if orientation is not None:
                merged_state["orientation"] = orientation
            # 初始位置：保存其 ID 以便追踪
            if "initialPosition" in update_data:
                merged_state["initialPositionId"] = update_data["initialPosition"]
            # 版本
            if "version" in update_data:
                merged_state["version"] = update_data["version"]
            # 标识冗余保存，便于外部关联
            merged_state["serialNumber"] = serial_number

            # 保存合并后的状态
            try:
                fs.save_state(serial_number, merged_state)
            except Exception as e:
                logger.error(f"保存状态文件失败: {e}")
                return {"error": f"状态文件保存失败: {str(e)}"}

            return {
                "success": True,
                "message": f"机器人 {serial_number} 信息已更新并同步"
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