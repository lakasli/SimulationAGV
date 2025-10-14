import json
from typing import List
from dataclasses import dataclass, field

from vda5050.order import Action

@dataclass
class InstantActions:
    header_id: int = 0
    timestamp: str = ""
    version: str = ""
    manufacturer: str = ""
    serial_number: str = ""
    actions: List[Action] = field(default_factory=list)
    
    def to_dict(self):
        result = {
            "headerId": self.header_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number
        }
        
        if self.actions:
            result["actions"] = [action.to_dict() for action in self.actions]
            
        return result
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict):
        instant_actions = cls(
            header_id=data.get("headerId", 0),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", ""),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", "")
        )
        
        if "actions" in data:
            for action_data in data["actions"]:
                instant_actions.actions.append(Action.from_dict(action_data))
                
        return instant_actions