import json
from typing import Optional
from dataclasses import dataclass

from vda5050.state import AgvPosition

@dataclass
class Visualization:
    header_id: int = 0
    timestamp: str = ""
    version: str = ""
    manufacturer: str = ""
    serial_number: str = ""
    agv_position: Optional[AgvPosition] = None
    
    def to_dict(self):
        result = {
            "headerId": self.header_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number
        }
        
        if self.agv_position:
            result["agvPosition"] = self.agv_position.to_dict()
            
        return result
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict):
        visualization = cls(
            header_id=data.get("headerId", 0),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", ""),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", "")
        )
        
        if "agvPosition" in data:
            pos_data = data["agvPosition"]
            visualization.agv_position = AgvPosition(
                x=pos_data.get("x", 0.0),
                y=pos_data.get("y", 0.0),
                theta=pos_data.get("theta", 0.0),
                map_id=pos_data.get("mapId", ""),
                map_description=pos_data.get("mapDescription", ""),
                position_initialized=pos_data.get("positionInitialized", False),
                localization_score=pos_data.get("localizationScore", 0.0),
                deviation_range=pos_data.get("deviationRange", 0.0)
            )
            
        return visualization