import json
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class BatteryState:
    battery_charge: float = 0.0
    battery_voltage: Optional[float] = None
    battery_health: Optional[float] = None
    
    def to_dict(self):
        return {
            "batteryCharge": self.battery_charge,
            "batteryVoltage": self.battery_voltage,
            "batteryHealth": self.battery_health
        }

@dataclass
class SafetyState:
    e_stop: Optional[str] = None  # "AUTOACK", "MANUAL", "REMOTE"
    field_violation: bool = False
    
    def to_dict(self):
        return {
            "eStop": self.e_stop,
            "fieldViolation": self.field_violation
        }

@dataclass
class AgvPosition:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    map_id: str = ""
    map_description: str = ""
    position_initialized: bool = False
    localization_score: float = 0.0
    deviation_range: float = 0.0
    
    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "mapId": self.map_id,
            "mapDescription": self.map_description,
            "positionInitialized": self.position_initialized,
            "localizationScore": self.localization_score,
            "deviationRange": self.deviation_range
        }

@dataclass
class NodeState:
    node_id: str = ""
    sequence_id: int = 0
    node_description: str = ""
    released: bool = False
    node_position: Optional[AgvPosition] = None
    
    def to_dict(self):
        result = {
            "nodeId": self.node_id,
            "sequenceId": self.sequence_id,
            "nodeDescription": self.node_description,
            "released": self.released
        }
        if self.node_position:
            result["nodePosition"] = self.node_position.to_dict()
        return result

@dataclass
class EdgeState:
    edge_id: str = ""
    sequence_id: int = 0
    edge_description: str = ""
    released: bool = False
    
    def to_dict(self):
        return {
            "edgeId": self.edge_id,
            "sequenceId": self.sequence_id,
            "edgeDescription": self.edge_description,
            "released": self.released
        }

@dataclass
class ActionState:
    action_id: str = ""
    action_type: str = ""
    action_description: str = ""
    action_status: str = "WAITING"  # "WAITING", "INITIALIZING", "RUNNING", "PAUSED", "FINISHED", "FAILED"
    
    def to_dict(self):
        return {
            "actionId": self.action_id,
            "actionType": self.action_type,
            "actionDescription": self.action_description,
            "actionStatus": self.action_status
        }

@dataclass
class State:
    header_id: int = 0
    timestamp: str = ""
    version: str = ""
    manufacturer: str = ""
    serial_number: str = ""
    
    # 订单相关信息
    order_id: str = ""
    order_update_id: int = 0
    
    # 节点和序列信息
    last_node_id: str = ""
    last_node_sequence_id: int = 0
    
    # 状态标志
    driving: bool = False
    paused: bool = False
    operating_mode: str = "AUTOMATIC"  # "AUTOMATIC", "SEMIAUTOMATIC", "MANUAL"
    
    # 状态对象
    battery_state: BatteryState = field(default_factory=BatteryState)
    safety_state: SafetyState = field(default_factory=SafetyState)
    agv_position: Optional[AgvPosition] = None
    
    # 状态数组
    node_states: List[NodeState] = field(default_factory=list)
    edge_states: List[EdgeState] = field(default_factory=list)
    action_states: List[ActionState] = field(default_factory=list)
    
    def to_dict(self):
        result = {
            "headerId": self.header_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "orderId": self.order_id,
            "orderUpdateId": self.order_update_id,
            "lastNodeId": self.last_node_id,
            "lastNodeSequenceId": self.last_node_sequence_id,
            "driving": self.driving,
            "paused": self.paused,
            "operatingMode": self.operating_mode,
            "batteryState": self.battery_state.to_dict(),
            "safetyState": self.safety_state.to_dict()
        }
        
        if self.agv_position:
            result["agvPosition"] = self.agv_position.to_dict()
            
        if self.node_states:
            result["nodeStates"] = [node.to_dict() for node in self.node_states]
            
        if self.edge_states:
            result["edgeStates"] = [edge.to_dict() for edge in self.edge_states]
            
        if self.action_states:
            result["actionStates"] = [action.to_dict() for action in self.action_states]
            
        return result
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建State对象"""
        state = cls(
            header_id=data.get("headerId", 0),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", ""),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", ""),
            order_id=data.get("orderId", ""),
            order_update_id=data.get("orderUpdateId", 0),
            last_node_id=data.get("lastNodeId", ""),
            last_node_sequence_id=data.get("lastNodeSequenceId", 0),
            driving=data.get("driving", False),
            paused=data.get("paused", False),
            operating_mode=data.get("operatingMode", "AUTOMATIC")
        )
        
        # 处理电池状态
        if "batteryState" in data:
            battery_data = data["batteryState"]
            state.battery_state = BatteryState(
                battery_charge=battery_data.get("batteryCharge", 0.0),
                battery_voltage=battery_data.get("batteryVoltage"),
                battery_health=battery_data.get("batteryHealth")
            )
        
        # 处理安全状态
        if "safetyState" in data:
            safety_data = data["safetyState"]
            state.safety_state = SafetyState(
                e_stop=safety_data.get("eStop"),
                field_violation=safety_data.get("fieldViolation", False)
            )
        
        # 处理AGV位置
        if "agvPosition" in data:
            pos_data = data["agvPosition"]
            state.agv_position = AgvPosition(
                x=pos_data.get("x", 0.0),
                y=pos_data.get("y", 0.0),
                theta=pos_data.get("theta", 0.0),
                map_id=pos_data.get("mapId", ""),
                map_description=pos_data.get("mapDescription", ""),
                position_initialized=pos_data.get("positionInitialized", False),
                localization_score=pos_data.get("localizationScore", 0.0),
                deviation_range=pos_data.get("deviationRange", 0.0)
            )
        
        # 处理节点状态
        if "nodeStates" in data:
            for node_data in data["nodeStates"]:
                node_position = None
                if "nodePosition" in node_data:
                    pos_data = node_data["nodePosition"]
                    node_position = AgvPosition(
                        x=pos_data.get("x", 0.0),
                        y=pos_data.get("y", 0.0),
                        theta=pos_data.get("theta", 0.0),
                        map_id=pos_data.get("mapId", ""),
                        map_description=pos_data.get("mapDescription", ""),
                        position_initialized=pos_data.get("positionInitialized", False),
                        localization_score=pos_data.get("localizationScore", 0.0),
                        deviation_range=pos_data.get("deviationRange", 0.0)
                    )
                
                node_state = NodeState(
                    node_id=node_data.get("nodeId", ""),
                    sequence_id=node_data.get("sequenceId", 0),
                    node_description=node_data.get("nodeDescription", ""),
                    released=node_data.get("released", False),
                    node_position=node_position
                )
                state.node_states.append(node_state)
        
        # 处理边状态
        if "edgeStates" in data:
            for edge_data in data["edgeStates"]:
                edge_state = EdgeState(
                    edge_id=edge_data.get("edgeId", ""),
                    sequence_id=edge_data.get("sequenceId", 0),
                    edge_description=edge_data.get("edgeDescription", ""),
                    released=edge_data.get("released", False)
                )
                state.edge_states.append(edge_state)
        
        # 处理动作状态
        if "actionStates" in data:
            for action_data in data["actionStates"]:
                action_state = ActionState(
                    action_id=action_data.get("actionId", ""),
                    action_type=action_data.get("actionType", ""),
                    action_description=action_data.get("actionDescription", ""),
                    action_status=action_data.get("actionStatus", "WAITING")
                )
                state.action_states.append(action_state)
        
        return state