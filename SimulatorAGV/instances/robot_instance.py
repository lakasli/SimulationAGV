import threading
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime

# 导入现有的模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agv_simulator import AgvSimulator
from mqtt_client import MqttClient
from vda5050.connection import Connection
from shared import setup_logger

logger = setup_logger()


class RobotInstance:
    """单个机器人实例，封装AGV模拟器和MQTT客户端"""
    
    def __init__(self, robot_id: str, config: Dict[str, Any]):
        """
        初始化机器人实例
        
        Args:
            robot_id: 机器人唯一标识
            config: 机器人配置
        """
        self.robot_id = robot_id
        self.config = config
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # 创建AGV模拟器
        self.agv_simulator = AgvSimulator(config)
        
        # 创建MQTT客户端
        self.mqtt_client = MqttClient(config, self._handle_mqtt_message)
        
        # 状态信息
        self.status = "offline"
        self.last_update = datetime.now()
        
        # 线程锁
        self._lock = threading.Lock()
        
        logger.info(f"机器人实例 {robot_id} 初始化完成")
    
    def _handle_mqtt_message(self, topic: str, payload: str):
        """处理MQTT消息"""
        try:
            with self._lock:
                # 根据主题处理不同类型的VDA5050消息
                if topic.endswith("/order"):
                    order = self.mqtt_client.handle_order_message(payload)
                    if order:
                        self.agv_simulator.accept_order(order)
                        logger.info(f"机器人 {self.robot_id} 接收到订单: {order.order_id}")
                elif topic.endswith("/instantActions"):
                    instant_actions = self.mqtt_client.handle_instant_actions_message(payload)
                    if instant_actions:
                        self.agv_simulator.accept_instant_actions(instant_actions)
                        logger.info(f"机器人 {self.robot_id} 接收到即时动作")
                else:
                    logger.warning(f"机器人 {self.robot_id} 收到未知主题的消息: {topic}")
        except Exception as e:
            logger.error(f"机器人 {self.robot_id} 处理MQTT消息时出错: {e}")
    
    def start(self):
        """启动机器人实例"""
        if self.running:
            logger.warning(f"机器人 {self.robot_id} 已经在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"机器人 {self.robot_id} 启动成功")
    
    def stop(self):
        """停止机器人实例"""
        if not self.running:
            return
        
        logger.info(f"正在停止机器人 {self.robot_id}...")
        self.running = False
        
        # 发布离线消息
        try:
            self._publish_connection_message(Connection.CONNECTION_STATE_OFFLINE)
            self.mqtt_client.disconnect()
        except Exception as e:
            logger.error(f"机器人 {self.robot_id} 断开连接时出错: {e}")
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.status = "offline"
        logger.info(f"机器人 {self.robot_id} 已停止")
    
    def _run(self):
        """机器人主运行循环"""
        try:
            # 连接到MQTT代理
            self.mqtt_client.connect()
            
            # 发布初始连接消息
            self._publish_connection_message(Connection.CONNECTION_STATE_ONLINE)
            
            # 发布初始状态消息
            self._publish_state_message()
            
            self.status = "online"
            
            # 主循环
            while self.running:
                try:
                    with self._lock:
                        # 更新AGV状态
                        self.agv_simulator.update_state()
                        
                        # 定期发布状态和可视化消息
                        self._publish_state_message()
                        self._publish_visualization_message()
                        
                        # 更新最后更新时间
                        self.last_update = datetime.now()
                    
                    # 等待指定的时间间隔
                    time.sleep(1.0 / self.config['settings']['state_frequency'])
                    
                except Exception as e:
                    logger.error(f"机器人 {self.robot_id} 运行时出错: {e}")
                    time.sleep(1)
        
        except Exception as e:
            logger.error(f"机器人 {self.robot_id} 启动失败: {e}")
            self.status = "error"
        
        finally:
            # 确保发布离线消息
            try:
                self._publish_connection_message(Connection.CONNECTION_STATE_OFFLINE)
                self.mqtt_client.disconnect()
            except:
                pass
            
            self.status = "offline"
    
    def _publish_connection_message(self, state: str):
        """发布连接消息"""
        try:
            self.agv_simulator.set_connection_state(state)
            message = self.agv_simulator.get_connection_message()
            self.mqtt_client.publish(
                self.agv_simulator.connection_topic,
                message,
                qos=1,
                retain=True
            )
        except Exception as e:
            logger.error(f"机器人 {self.robot_id} 发布连接消息失败: {e}")
    
    def _publish_state_message(self):
        """发布状态消息"""
        try:
            message = self.agv_simulator.get_state_message()
            self.mqtt_client.publish(
                self.agv_simulator.state_topic,
                message,
                qos=0
            )
        except Exception as e:
            logger.error(f"机器人 {self.robot_id} 发布状态消息失败: {e}")
    
    def _publish_visualization_message(self):
        """发布可视化消息"""
        try:
            message = self.agv_simulator.get_visualization_message()
            self.mqtt_client.publish(
                self.agv_simulator.visualization_topic,
                message,
                qos=0
            )
        except Exception as e:
            logger.error(f"机器人 {self.robot_id} 发布可视化消息失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取机器人状态信息"""
        with self._lock:
            # 安全获取电池状态
            battery_charge = 100  # 默认值
            try:
                if hasattr(self.agv_simulator.state, 'battery_state'):
                    battery_state = self.agv_simulator.state.battery_state
                    if hasattr(battery_state, 'battery_charge'):
                        battery_charge = battery_state.battery_charge
                    elif isinstance(battery_state, dict):
                        battery_charge = battery_state.get('battery_charge', 100)
            except Exception as e:
                logger.warning(f"获取机器人 {self.robot_id} 电池状态失败: {e}")
            
            # 安全获取位置信息
            position = None
            try:
                if hasattr(self.agv_simulator.state, 'agv_position'):
                    position = self.agv_simulator.state.agv_position
            except Exception as e:
                logger.warning(f"获取机器人 {self.robot_id} 位置信息失败: {e}")
            
            # 安全获取订单ID
            current_order = None
            try:
                if hasattr(self.agv_simulator.state, 'order_id'):
                    current_order = self.agv_simulator.state.order_id
            except Exception as e:
                logger.warning(f"获取机器人 {self.robot_id} 订单信息失败: {e}")
            
            return {
                "robot_id": self.robot_id,
                "status": self.status,
                "serial_number": self.config["vehicle"]["serial_number"],
                "manufacturer": self.config["vehicle"]["manufacturer"],
                "last_update": self.last_update.isoformat(),
                "running": self.running,
                "position": position,
                "battery": battery_charge,
                "current_order": current_order
            }
    
    def send_order(self, order_data: Dict[str, Any]):
        """发送订单给机器人"""
        try:
            order_topic = f"{self.agv_simulator.base_topic}/order"
            order_json = json.dumps(order_data)
            self.mqtt_client.publish(order_topic, order_json, qos=1)
            logger.info(f"向机器人 {self.robot_id} 发送订单")
        except Exception as e:
            logger.error(f"向机器人 {self.robot_id} 发送订单失败: {e}")
    
    def send_instant_action(self, action_data: Dict[str, Any]):
        """发送即时动作给机器人"""
        try:
            action_topic = f"{self.agv_simulator.base_topic}/instantActions"
            action_json = json.dumps(action_data)
            self.mqtt_client.publish(action_topic, action_json, qos=1)
            logger.info(f"向机器人 {self.robot_id} 发送即时动作")
        except Exception as e:
            logger.error(f"向机器人 {self.robot_id} 发送即时动作失败: {e}")
    
    def is_alive(self) -> bool:
        """检查机器人实例是否存活"""
        return self.running and (self.thread is not None and self.thread.is_alive())
    
    def get_serial_number(self) -> str:
        """获取机器人序列号"""
        return self.config["vehicle"]["serial_number"]
    
    def get_manufacturer(self) -> str:
        """获取机器人制造商"""
        return self.config["vehicle"]["manufacturer"]
    
    def update_config(self, config_data: Dict[str, Any]) -> bool:
        """更新机器人配置"""
        try:
            # 处理位置初始化
            if 'position' in config_data:
                position_data = config_data['position']
                x = position_data.get('x', 0.0)
                y = position_data.get('y', 0.0)
                theta = position_data.get('rotate', 0.0)
                
                # 更新AGV模拟器的位置
                with self._lock:
                    if self.agv_simulator.state.agv_position:
                        self.agv_simulator.state.agv_position.x = x
                        self.agv_simulator.state.agv_position.y = y
                        self.agv_simulator.state.agv_position.theta = theta
                        self.agv_simulator.state.agv_position.position_initialized = True
                    else:
                        from vda5050.state import AgvPosition
                        self.agv_simulator.state.agv_position = AgvPosition(
                            x=x, y=y, theta=theta, 
                            map_id=self.config['settings']['map_id'],
                            position_initialized=True
                        )
                    
                    # 同步更新可视化位置
                    if self.agv_simulator.visualization.agv_position:
                        self.agv_simulator.visualization.agv_position.x = x
                        self.agv_simulator.visualization.agv_position.y = y
                        self.agv_simulator.visualization.agv_position.theta = theta
                    else:
                        self.agv_simulator.visualization.agv_position = self.agv_simulator.state.agv_position
                    
                    # 立即发布更新后的状态和可视化消息
                    self._publish_state_message()
                    self._publish_visualization_message()
                
                logger.info(f"机器人 {self.robot_id} 位置已更新并发布MQTT消息: x={x}, y={y}, theta={theta}")
            
            # 处理其他配置更新
            if 'initialPosition' in config_data:
                # 这里可以处理初始位置ID的存储
                logger.info(f"机器人 {self.robot_id} 初始位置ID: {config_data['initialPosition']}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新机器人 {self.robot_id} 配置失败: {e}")
            return False