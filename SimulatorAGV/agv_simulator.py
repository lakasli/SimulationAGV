import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import random

from vda5050.state import State, AgvPosition, ActionState
from vda5050.connection import Connection
from vda5050.visualization import Visualization
from vda5050.order import Order
from vda5050.instant_actions import InstantActions
from utils import get_timestamp, get_distance
from shared import setup_logger

logger = setup_logger()


class AgvSimulator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 创建MQTT主题
        self.base_topic = self._generate_base_topic()
        self.connection_topic = f"{self.base_topic}/connection"
        self.state_topic = f"{self.base_topic}/state"
        self.visualization_topic = f"{self.base_topic}/visualization"
        
        # 初始化VDA5050消息对象
        self.connection = self._create_initial_connection()
        self.state = self._create_initial_state()
        self.visualization = self._create_initial_visualization()
        
        # 当前订单和即时动作
        self.current_order: Optional[Order] = None
        self.instant_actions: Optional[InstantActions] = None
        
        # 动作执行状态
        self.action_start_time: Optional[float] = None

    def _generate_base_topic(self) -> str:
        """生成基础MQTT主题"""
        return f"{self.config['mqtt_broker']['vda_interface']}/{self.config['vehicle']['vda_version']}/{self.config['vehicle']['manufacturer']}/{self.config['vehicle']['serial_number']}"

    def _create_initial_connection(self) -> Connection:
        """创建初始连接对象"""
        connection = Connection(
            version=self.config['vehicle']['vda_full_version'],
            manufacturer=self.config['vehicle']['manufacturer'],
            serial_number=self.config['vehicle']['serial_number']
        )
        return connection

    def _create_initial_state(self) -> State:
        """创建初始状态对象"""
        state = State(
            version=self.config['vehicle']['vda_full_version'],
            manufacturer=self.config['vehicle']['manufacturer'],
            serial_number=self.config['vehicle']['serial_number']
        )
        
        # 使用配置中的初始位置，如果没有则使用随机位置
        if 'initial_x' in self.config['settings'] and 'initial_y' in self.config['settings']:
            initial_x = self.config['settings']['initial_x']
            initial_y = self.config['settings']['initial_y']
            initial_theta = self.config['settings'].get('initial_theta', 0)
            logger.info(f"Using configured initial position: x={initial_x}, y={initial_y}, theta={initial_theta}")
        else:
            initial_x, initial_y = 0.0 , 0.0
            initial_theta = 0.0
            logger.info(f"Using (0.0,0.0,0.0) initial position: x={initial_x}, y={initial_y}, theta={initial_theta}")
        
        state.agv_position = AgvPosition(x=initial_x, y=initial_y, theta=initial_theta, map_id=self.config['settings']['map_id'])
        state.agv_position.position_initialized = True  # 设置为True，因为我们有明确的初始位置
        
        # 设置电池状态
        state.battery_state.battery_charge = 100.0
        
        return state

    def _create_initial_visualization(self) -> Visualization:
        """创建初始可视化对象"""
        visualization = Visualization(
            version=self.config['vehicle']['vda_full_version'],
            manufacturer=self.config['vehicle']['manufacturer'],
            serial_number=self.config['vehicle']['serial_number']
        )
        if self.state.agv_position:
            visualization.agv_position = self.state.agv_position
        return visualization

    def update_state(self):
        """更新AGV状态"""
        self.state.header_id += 1
        self.state.timestamp = get_timestamp()
        
        # 处理即时动作
        self._process_instant_actions()
        
        # 处理订单
        if self.current_order:
            self._process_order()

    def _process_instant_actions(self):
        """处理即时动作"""
        if self.instant_actions and self.instant_actions.actions:
            # 简单处理：执行所有即时动作
            for action in self.instant_actions.actions:
                if action.action_type == "initPosition":
                    self._handle_init_position_action(action)
            
            # 清空已处理的动作
            self.instant_actions.actions.clear()

    def _handle_init_position_action(self, action):
        """处理位置初始化动作"""
        logger.info(f"执行位置初始化动作: {action.action_id}")
        
        # 提取参数
        x, y, theta, map_id, last_node_id = 0.0, 0.0, 0.0, "", ""
        
        if action.action_parameters:
            for param in action.action_parameters:
                if param.key == "x":
                    x = float(param.value) if isinstance(param.value, str) else param.value
                elif param.key == "y":
                    y = float(param.value) if isinstance(param.value, str) else param.value
                elif param.key == "theta":
                    theta = float(param.value) if isinstance(param.value, str) else param.value
                elif param.key == "mapId":
                    map_id = str(param.value)
                elif param.key == "lastNodeId":
                    last_node_id = str(param.value)
        
        # 更新位置
        if not self.state.agv_position:
            self.state.agv_position = AgvPosition(x=x, y=y, map_id=map_id)
        else:
            self.state.agv_position.x = x
            self.state.agv_position.y = y
            self.state.agv_position.theta = theta
            self.state.agv_position.map_id = map_id
            
        self.state.agv_position.position_initialized = True
        self.state.last_node_id = last_node_id
        
        # 更新可视化位置
        if self.visualization.agv_position:
            self.visualization.agv_position = self.state.agv_position

    def _process_order(self):
        """处理订单"""
        # 简单模拟：更新车辆位置向第一个节点移动
        if self.state.node_states and self.state.agv_position and self.state.agv_position.position_initialized:
            target_node = self.state.node_states[0]
            if target_node.node_position:
                # 计算距离
                distance = get_distance(
                    self.state.agv_position.x,
                    self.state.agv_position.y,
                    target_node.node_position.x,
                    target_node.node_position.y
                )
                
                # 如果距离很近，认为已到达节点
                if distance < 0.1:
                    self.state.last_node_id = target_node.node_id
                    self.state.last_node_sequence_id = target_node.sequence_id
                    logger.info(f"到达节点: {target_node.node_id}")
                else:
                    # 向目标节点移动
                    speed = self.config['settings']['speed']
                    direction_x = target_node.node_position.x - self.state.agv_position.x
                    direction_y = target_node.node_position.y - self.state.agv_position.y
                    
                    # 归一化方向向量
                    length = (direction_x ** 2 + direction_y ** 2) ** 0.5
                    if length > 0:
                        direction_x /= length
                        direction_y /= length
                        
                        # 更新位置
                        self.state.agv_position.x += direction_x * speed
                        self.state.agv_position.y += direction_y * speed
                        self.state.driving = True
                        
                        logger.debug(f"向节点 {target_node.node_id} 移动: ({self.state.agv_position.x:.2f}, {self.state.agv_position.y:.2f})")
                    else:
                        self.state.driving = False

    def accept_order(self, order: Order):
        """接受订单"""
        logger.info(f"接受订单: {order.order_id}")
        self.current_order = order
        
        # 更新状态信息
        self.state.order_id = order.order_id
        self.state.order_update_id = order.order_update_id
        
        # 清除之前的状态
        self.state.node_states.clear()
        self.state.edge_states.clear()
        self.state.action_states.clear()
        
        # 处理节点
        for node in order.nodes:
            from vda5050.state import NodeState
            node_state = NodeState(node_id=node.node_id, sequence_id=node.sequence_id)
            node_state.released = node.released
            node_state.node_description = node.node_description
            if node.node_position:
                node_state.node_position = AgvPosition(
                    x=node.node_position.x,
                    y=node.node_position.y,
                    map_id=node.node_position.map_id
                )
                node_state.node_position.theta = node.node_position.theta
            self.state.node_states.append(node_state)
            
            # 添加动作状态
            for action in node.actions:
                action_state = ActionState(action_id=action.action_id, action_type=action.action_type)
                self.state.action_states.append(action_state)
        
        # 处理边
        for edge in order.edges:
            from vda5050.state import EdgeState
            edge_state = EdgeState(edge_id=edge.edge_id, sequence_id=edge.sequence_id)
            edge_state.released = edge.released
            edge_state.edge_description = edge.edge_description
            self.state.edge_states.append(edge_state)
            
            # 添加动作状态
            for action in edge.actions:
                action_state = ActionState(action_id=action.action_id, action_type=action.action_type)
                self.state.action_states.append(action_state)

    def accept_instant_actions(self, instant_actions: InstantActions):
        """接受即时动作"""
        logger.info(f"接受即时动作")
        self.instant_actions = instant_actions
        
        # 添加动作状态
        for action in instant_actions.actions:
            action_state = ActionState(action_id=action.action_id, action_type=action.action_type)
            action_state.action_status = "WAITING"
            self.state.action_states.append(action_state)

    def get_connection_message(self) -> str:
        """获取连接消息"""
        return json.dumps(self.connection.to_dict())

    def get_state_message(self) -> str:
        """获取状态消息"""
        return self.state.to_json()

    def get_visualization_message(self) -> str:
        """获取可视化消息"""
        return json.dumps(self.visualization.to_dict())

    def set_connection_state(self, state: str):
        """设置连接状态"""
        self.connection.connection_state = state
        self.connection.header_id += 1
        self.connection.timestamp = get_timestamp()