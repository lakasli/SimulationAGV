"""
订单相关API路由
"""

import json
from typing import Dict, Any
from .registry import get_api_server
from shared import setup_logger

logger = setup_logger()


def register_order_routes(instance_manager):
    """注册订单相关的API路由"""
    
    server = get_api_server()
    registry = server.get_registry()
    
    @registry.post("/api/robots/{robot_id}/orders", "发送订单给机器人")
    def send_order(request: Dict[str, Any]) -> Dict[str, Any]:
        """发送订单给机器人"""
        try:
            robot_id = request["path_params"]["robot_id"]
            order_data = request.get("body", {})
            
            if not order_data:
                return {"error": "缺少订单数据"}
            
            success = instance_manager.send_order_to_robot(robot_id, order_data)
            
            if success:
                return {
                    "success": True,
                    "message": f"订单已发送给机器人 {robot_id}",
                    "order_id": order_data.get("orderId", "unknown")
                }
            else:
                return {"error": f"发送订单给机器人 {robot_id} 失败"}
                
        except Exception as e:
            logger.error(f"发送订单失败: {e}")
            return {"error": str(e)}
    
    @registry.post("/api/robots/{robot_id}/instant-actions", "发送即时动作给机器人")
    def send_instant_action(request: Dict[str, Any]) -> Dict[str, Any]:
        """发送即时动作给机器人"""
        try:
            robot_id = request["path_params"]["robot_id"]
            action_data = request.get("body", {})
            
            if not action_data:
                return {"error": "缺少动作数据"}
            
            success = instance_manager.send_instant_action_to_robot(robot_id, action_data)
            
            if success:
                return {
                    "success": True,
                    "message": f"即时动作已发送给机器人 {robot_id}",
                    "action_id": action_data.get("actionId", "unknown")
                }
            else:
                return {"error": f"发送即时动作给机器人 {robot_id} 失败"}
                
        except Exception as e:
            logger.error(f"发送即时动作失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/robots/{robot_id}/orders", "获取机器人订单历史")
    def get_robot_orders(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取机器人订单历史"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            robot_instance = instance_manager.get_robot_instance(robot_id)
            if not robot_instance:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            # 获取订单历史（如果机器人实例支持）
            orders = []
            if hasattr(robot_instance, 'get_order_history'):
                orders = robot_instance.get_order_history()
            
            return {
                "robot_id": robot_id,
                "orders": orders,
                "total": len(orders)
            }
            
        except Exception as e:
            logger.error(f"获取机器人订单历史失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/robots/{robot_id}/current-order", "获取机器人当前订单")
    def get_current_order(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取机器人当前订单"""
        try:
            robot_id = request["path_params"]["robot_id"]
            
            robot_instance = instance_manager.get_robot_instance(robot_id)
            if not robot_instance:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            # 获取当前订单（如果机器人实例支持）
            current_order = None
            if hasattr(robot_instance, 'get_current_order'):
                current_order = robot_instance.get_current_order()
            
            return {
                "robot_id": robot_id,
                "current_order": current_order
            }
            
        except Exception as e:
            logger.error(f"获取机器人当前订单失败: {e}")
            return {"error": str(e)}
    
    @registry.delete("/api/robots/{robot_id}/orders/{order_id}", "取消机器人订单")
    def cancel_order(request: Dict[str, Any]) -> Dict[str, Any]:
        """取消机器人订单"""
        try:
            robot_id = request["path_params"]["robot_id"]
            order_id = request["path_params"]["order_id"]
            
            robot_instance = instance_manager.get_robot_instance(robot_id)
            if not robot_instance:
                return {"error": f"机器人 {robot_id} 不存在"}
            
            # 取消订单（如果机器人实例支持）
            success = False
            if hasattr(robot_instance, 'cancel_order'):
                success = robot_instance.cancel_order(order_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"订单 {order_id} 已取消"
                }
            else:
                return {"error": f"取消订单 {order_id} 失败"}
            
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {"error": str(e)}
    
    logger.info("订单API路由注册完成")