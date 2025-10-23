import json
from typing import List, Optional
from dataclasses import dataclass, field

# 尝试使用共享序列化工具
try:
    from shared import SerializationMixin, to_json, from_json
    _use_shared_serialization = True
except ImportError:
    _use_shared_serialization = False


@dataclass
class ActionParameter:
    key: str = ""
    value: str = ""
    
    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            key=data.get("key", ""),
            value=data.get("value", "")
        )

@dataclass
class Action:
    action_id: str = ""
    action_type: str = ""
    blocking_type: str = "NONE"  # "NONE", "SOFT", "HARD"
    action_description: str = ""
    action_parameters: List[ActionParameter] = field(default_factory=list)
    
    def to_dict(self):
        result = {
            "actionId": self.action_id,
            "actionType": self.action_type,
            "blockingType": self.blocking_type,
            "actionDescription": self.action_description
        }
        
        if self.action_parameters:
            result["actionParameters"] = [param.to_dict() for param in self.action_parameters]
            
        return result
    
    @classmethod
    def from_dict(cls, data: dict):
        action = cls(
            action_id=data.get("actionId", ""),
            action_type=data.get("actionType", ""),
            blocking_type=data.get("blockingType", "NONE"),
            action_description=data.get("actionDescription", "")
        )
        
        if "actionParameters" in data:
            for param_data in data["actionParameters"]:
                action.action_parameters.append(ActionParameter.from_dict(param_data))
                
        return action

@dataclass
class NodePosition:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    map_id: str = ""
    map_description: str = ""
    
    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "mapId": self.map_id,
            "mapDescription": self.map_description
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            theta=data.get("theta", 0.0),
            map_id=data.get("mapId", ""),
            map_description=data.get("mapDescription", "")
        )

@dataclass
class Node:
    node_id: str = ""
    sequence_id: int = 0
    node_description: str = ""
    released: bool = False
    actions: List[Action] = field(default_factory=list)
    node_position: Optional[NodePosition] = None
    
    def to_dict(self):
        result = {
            "nodeId": self.node_id,
            "sequenceId": self.sequence_id,
            "nodeDescription": self.node_description,
            "released": self.released
        }
        
        if self.actions:
            result["actions"] = [action.to_dict() for action in self.actions]
            
        if self.node_position:
            result["nodePosition"] = self.node_position.to_dict()
            
        return result
    
    @classmethod
    def from_dict(cls, data: dict):
        node = cls(
            node_id=data.get("nodeId", ""),
            sequence_id=data.get("sequenceId", 0),
            node_description=data.get("nodeDescription", ""),
            released=data.get("released", False)
        )
        
        if "actions" in data:
            for action_data in data["actions"]:
                node.actions.append(Action.from_dict(action_data))
                
        if "nodePosition" in data:
            node.node_position = NodePosition.from_dict(data["nodePosition"])
            
        return node

@dataclass
class Edge:
    edge_id: str = ""
    sequence_id: int = 0
    edge_description: str = ""
    start_node_id: str = ""
    end_node_id: str = ""
    released: bool = False
    trajectory: Optional[str] = None
    max_speed: Optional[float] = None
    max_height: Optional[float] = None
    min_height: Optional[float] = None
    orientation: Optional[str] = None
    direction: Optional[str] = None
    actions: List[Action] = field(default_factory=list)
    
    def to_dict(self):
        result = {
            "edgeId": self.edge_id,
            "sequenceId": self.sequence_id,
            "edgeDescription": self.edge_description,
            "startNodeId": self.start_node_id,
            "endNodeId": self.end_node_id,
            "released": self.released
        }
        
        if self.trajectory:
            result["trajectory"] = self.trajectory
        if self.max_speed:
            result["maxSpeed"] = self.max_speed
        if self.max_height:
            result["maxHeight"] = self.max_height
        if self.min_height:
            result["minHeight"] = self.min_height
        if self.orientation:
            result["orientation"] = self.orientation
        if self.direction:
            result["direction"] = self.direction
            
        if self.actions:
            result["actions"] = [action.to_dict() for action in self.actions]
            
        return result
    
    @classmethod
    def from_dict(cls, data: dict):
        edge = cls(
            edge_id=data.get("edgeId", ""),
            sequence_id=data.get("sequenceId", 0),
            edge_description=data.get("edgeDescription", ""),
            start_node_id=data.get("startNodeId", ""),
            end_node_id=data.get("endNodeId", ""),
            released=data.get("released", False),
            trajectory=data.get("trajectory"),
            max_speed=data.get("maxSpeed"),
            max_height=data.get("maxHeight"),
            min_height=data.get("minHeight"),
            orientation=data.get("orientation"),
            direction=data.get("direction")
        )
        
        if "actions" in data:
            for action_data in data["actions"]:
                edge.actions.append(Action.from_dict(action_data))
                
        return edge

@dataclass
class Order:
    header_id: int = 0
    timestamp: str = ""
    version: str = ""
    manufacturer: str = ""
    serial_number: str = ""
    order_id: str = ""
    order_update_id: int = 0
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    
    def to_dict(self):
        result = {
            "headerId": self.header_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "orderId": self.order_id,
            "orderUpdateId": self.order_update_id
        }
        
        if self.nodes:
            result["nodes"] = [node.to_dict() for node in self.nodes]
            
        if self.edges:
            result["edges"] = [edge.to_dict() for edge in self.edges]
            
        return result
    
    def to_json(self):
        if _use_shared_serialization:
            return to_json(self, indent=2)
        else:
            return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict):
        order = cls(
            header_id=data.get("headerId", 0),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", ""),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", ""),
            order_id=data.get("orderId", ""),
            order_update_id=data.get("orderUpdateId", 0)
        )
        
        if "nodes" in data:
            for node_data in data["nodes"]:
                order.nodes.append(Node.from_dict(node_data))
                
        if "edges" in data:
            for edge_data in data["edges"]:
                order.edges.append(Edge.from_dict(edge_data))
                
        return order