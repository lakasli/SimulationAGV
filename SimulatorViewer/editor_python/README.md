# AGV地图编辑器Python模块

这是一个用Python重构的AGV地图编辑器模块，为HTML地图查看器提供后端API服务。

## 项目结构

```
editor_python/
├── __init__.py                 # 模块初始化
├── main.py                     # 主程序入口
├── requirements.txt            # 依赖文件
├── README.md                   # 说明文档
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── map_models.py          # 地图相关模型
│   ├── robot_models.py        # 机器人相关模型
│   └── scene_models.py        # 场景相关模型
├── services/                   # 服务模块
│   ├── __init__.py
│   ├── robot_service.py       # 机器人服务
│   ├── point_service.py       # 点位服务
│   ├── route_service.py       # 路径服务
│   ├── area_service.py        # 区域服务
│   └── editor_service.py      # 编辑器主服务
└── api/                        # API接口
    ├── __init__.py
    └── web_api.py             # Web API服务器
```

## 功能特性

### 核心服务模块
- **RobotService**: 机器人信息管理（增删改查、分组、标签）
- **PointService**: 地图点位管理（增删改查、存储位置、搜索）
- **RouteService**: 路径管理（增删改查、双向路径、路径查找）
- **AreaService**: 区域管理（增删改查、点位关联、重叠检测）
- **EditorService**: 统一服务接口（场景加载保存、数据验证、统计）

### Web API接口
- **场景管理**: 加载、保存、创建新场景
- **点位操作**: CRUD操作、搜索、统计
- **路径操作**: CRUD操作、路径查找、双向路径
- **区域操作**: CRUD操作、点位关联、重叠检测
- **机器人管理**: CRUD操作、状态更新、分组管理
- **数据统计**: 全局统计信息、搜索功能

## 安装和使用

### 1. 环境要求
- Python 3.7+
- 无需额外依赖（仅使用Python标准库）

### 2. 启动服务器

#### 基本启动
```powershell
cd d:\CodeProject\SimulationAGV\SimulatorViewer\editor_python
python main.py
```

#### 指定参数启动
```powershell
# 指定主机和端口
python main.py --host localhost --port 8001

# 加载指定场景文件
python main.py --scene-file ../SimulatorAGV/map_flie/testmap.scene

# 启用调试模式
python main.py --debug
```

### 3. API端点

服务器默认运行在 `http://localhost:8001`

#### 场景管理
- `GET /api/scene/data` - 获取当前场景数据
- `POST /api/scene/load` - 加载场景文件
- `POST /api/scene/save` - 保存场景到文件

#### 点位管理
- `GET /api/points` - 获取所有点位
- `POST /api/points` - 创建新点位
- `PUT /api/points/{id}` - 更新点位
- `DELETE /api/points/{id}` - 删除点位

#### 路径管理
- `GET /api/routes` - 获取所有路径
- `POST /api/routes` - 创建新路径
- `PUT /api/routes/{id}` - 更新路径
- `DELETE /api/routes/{id}` - 删除路径

#### 区域管理
- `GET /api/areas` - 获取所有区域
- `POST /api/areas` - 创建新区域
- `PUT /api/areas/{id}` - 更新区域
- `DELETE /api/areas/{id}` - 删除区域

#### 机器人管理
- `GET /api/robots` - 获取所有机器人
- `POST /api/robots` - 创建新机器人
- `PUT /api/robots/{id}` - 更新机器人
- `DELETE /api/robots/{id}` - 删除机器人

#### 其他功能
- `GET /api/statistics` - 获取统计信息
- `GET /api/search?q=关键词` - 全局搜索

## 与HTML地图查看器集成

HTML地图查看器已经集成了与Python API的通信功能：

1. **自动检测**: 优先尝试连接Python API，如果不可用则回退到本地文件
2. **错误处理**: 提供详细的错误信息和恢复建议
3. **双向同步**: 支持通过API进行数据的增删改查操作
4. **用户友好**: 提供启动Python API的详细指导

## 开发说明

### 数据模型
所有数据模型都使用Python的`dataclasses`定义，支持JSON序列化和反序列化。

### 服务架构
采用分层架构设计：
- **模型层**: 定义数据结构
- **服务层**: 实现业务逻辑
- **API层**: 提供HTTP接口

### 错误处理
- 统一的错误响应格式
- 详细的错误日志记录
- 优雅的降级处理

### 扩展性
- 模块化设计，易于扩展新功能
- 标准的REST API接口
- 支持插件式功能扩展

## 故障排除

### 常见问题

1. **端口被占用**
   ```
   python main.py --port 8002
   ```

2. **场景文件加载失败**
   - 检查文件路径是否正确
   - 确认文件格式为有效的JSON

3. **API连接失败**
   - 确认服务器正在运行
   - 检查防火墙设置
   - 验证端口是否可访问

### 调试模式
启用调试模式可以获得更详细的错误信息：
```powershell
python main.py --debug
```

## 许可证

本项目遵循MIT许可证。