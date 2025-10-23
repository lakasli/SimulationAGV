# 代码优化指南

## 概述

本项目已完成代码重构和优化，创建了统一的共享模块来消除重复代码，提高代码质量和可维护性。

**🎉 更新**: 重复代码清理已完成！详见 [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md)

## 新增共享模块

### 1. 日志配置 (`shared/logger_config.py`)

**功能**: 统一的日志配置，替代重复的logger_config.py文件

**使用方法**:
```python
from shared import setup_logger

# 自动根据调用模块名创建logger
logger = setup_logger()

# 或指定logger名称
logger = setup_logger("MyModule")
```

**优势**:
- 自动检测调用模块名
- 统一的日志格式和配置
- 支持文件和控制台双重输出

### 2. 配置管理 (`shared/config_manager.py`)

**功能**: 中心化配置管理，统一MQTT、Redis等配置

**使用方法**:
```python
from shared import get_config, AppConfig

# 获取全局配置
config = get_config()

# 访问配置项
mqtt_config = config.mqtt
redis_config = config.redis
vehicle_config = config.vehicle

# 从文件加载配置
config = AppConfig.from_file("config.json")
```

**配置结构**:
- `MQTTConfig`: MQTT连接配置
- `RedisConfig`: Redis连接和键配置
- `VehicleConfig`: 车辆基本信息
- `SystemConfig`: 系统运行配置

### 3. 数据模型 (`shared/models.py`)

**功能**: 统一的机器人状态和位置数据模型

**主要模型**:
- `RobotStatus`: 机器人状态
- `Position`: 位置信息
- `BatteryState`: 电池状态
- `SafetyState`: 安全状态
- `RobotInfo`: 机器人信息
- `RobotGroup`: 机器人组
- `RobotLabel`: 机器人标签

**使用方法**:
```python
from shared import RobotStatus, Position

# 创建位置对象
position = Position(x=10.0, y=20.0, theta=1.57)

# 创建机器人状态
status = RobotStatus(
    robot_id="AGV001",
    position=position,
    battery_level=85.5
)

# 序列化
status_dict = status.to_dict()
status_json = status.to_json()

# 反序列化
status = RobotStatus.from_dict(status_dict)
```

### 4. 序列化工具 (`shared/serialization.py`)

**功能**: 统一的JSON序列化/反序列化工具

**主要功能**:
- `SerializationMixin`: 序列化混入类
- `safe_serialize`: 安全序列化任意对象
- `to_json/from_json`: JSON转换
- `create_json_response`: 创建JSON响应
- `batch_serialize/batch_deserialize`: 批量处理

**使用方法**:
```python
from shared import to_json, from_json, SerializationMixin

# 继承序列化混入类
class MyModel(SerializationMixin):
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['name'], data['value'])

# 使用
obj = MyModel("test", 123)
json_str = obj.to_json()
obj2 = MyModel.from_json(json_str)
```

### 5. HTTP服务器基类 (`shared/http_server.py`)

**功能**: 统一的HTTP服务器实现，减少重复代码

**主要类**:
- `BaseHTTPServer`: 抽象基类
- `SimpleHTTPServer`: 简单实现
- `BaseHTTPHandler`: 请求处理器

**使用方法**:
```python
from shared import BaseHTTPServer

class MyServer(BaseHTTPServer):
    def __init__(self):
        super().__init__(host='localhost', port=8080, server_name="MyServer")
        
        # 添加路由
        self.add_route('GET', '/api/data', self.get_data)
        self.add_route('POST', '/api/data', self.post_data)
    
    def handle_custom_route(self, method, path, query_params, request_data, headers):
        # 处理自定义路由
        if path == '/custom':
            return {"message": "Custom route"}, 200
        return None
    
    def get_data(self, query_params, request_data, headers):
        return {"data": "example"}, 200
    
    def post_data(self, query_params, request_data, headers):
        return {"received": request_data}, 201

# 启动服务器
server = MyServer()
server.start(blocking=False)  # 非阻塞启动
```

## 迁移指南

### 1. 替换日志配置

**原代码**:
```python
import logging
from logger_config import setup_logger

logger = setup_logger(__name__)
```

**新代码**:
```python
from shared import setup_logger

logger = setup_logger()  # 自动检测模块名
```

### 2. 使用统一配置管理

**原代码**:
```python
import json

with open('config.json', 'r') as f:
    config = json.load(f)

mqtt_broker = config.get('mqtt_broker', 'localhost')
```

**新代码**:
```python
from shared import get_config

config = get_config()
mqtt_broker = config.mqtt.broker
```

### 3. 使用统一数据模型

**原代码**:
```python
class RobotStatus:
    def __init__(self, robot_id, x, y, battery):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        self.battery = battery
    
    def to_dict(self):
        return {
            'robot_id': self.robot_id,
            'x': self.x,
            'y': self.y,
            'battery': self.battery
        }
```

**新代码**:
```python
from shared import RobotStatus, Position

position = Position(x=x, y=y)
status = RobotStatus(robot_id=robot_id, position=position, battery_level=battery)
```

### 4. 简化序列化逻辑

**原代码**:
```python
import json

def serialize_object(obj):
    if hasattr(obj, 'to_dict'):
        return json.dumps(obj.to_dict())
    return json.dumps(obj.__dict__)
```

**新代码**:
```python
from shared import to_json

json_str = to_json(obj)  # 自动处理各种对象类型
```

### 5. 使用HTTP服务器基类

**原代码**:
```python
from http.server import HTTPServer, BaseHTTPRequestHandler

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 大量重复的请求处理代码
        pass

server = HTTPServer(('localhost', 8080), MyHandler)
server.serve_forever()
```

**新代码**:
```python
from shared import SimpleHTTPServer

server = SimpleHTTPServer('localhost', 8080)
server.add_route('GET', '/api/data', my_handler_function)
server.start()
```

## 优化效果

### 代码减少
- 消除了重复的logger_config.py文件
- 统一了配置管理逻辑
- 简化了序列化/反序列化代码
- 减少了HTTP服务器重复实现

### 预期收益
- **代码量减少**: 20-30%
- **维护性提升**: 统一的接口和实现
- **一致性改善**: 统一的错误处理和日志格式
- **扩展性增强**: 易于添加新功能和配置

## 注意事项

1. **渐进式迁移**: 建议逐步迁移现有代码，避免一次性大规模修改
2. **测试验证**: 迁移后需要充分测试确保功能正常
3. **配置兼容**: 新的配置管理保持与现有配置文件的兼容性
4. **依赖管理**: 确保所有模块正确导入shared包

## 下一步计划

1. 逐步迁移现有模块使用新的共享工具
2. 删除重复的代码文件
3. 更新文档和示例
4. 添加单元测试覆盖新的共享模块