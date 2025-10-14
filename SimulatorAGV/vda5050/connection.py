import json
from dataclasses import dataclass, field

@dataclass
class Connection:
    # 连接状态常量
    CONNECTION_STATE_ONLINE = "ONLINE"
    CONNECTION_STATE_OFFLINE = "OFFLINE"
    CONNECTION_STATE_CONNECTION_BROKEN = "CONNECTIONBROKEN"
    
    header_id: int = 0
    timestamp: str = ""
    version: str = ""
    manufacturer: str = ""
    serial_number: str = ""
    connection_state: str = CONNECTION_STATE_OFFLINE
    
    def to_dict(self):
        return {
            "headerId": self.header_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "connectionState": self.connection_state
        }
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            header_id=data.get("headerId", 0),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", ""),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", ""),
            connection_state=data.get("connectionState", cls.CONNECTION_STATE_OFFLINE)
        )