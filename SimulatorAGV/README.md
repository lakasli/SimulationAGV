# VDA5050 AGV Simulator

基于VDA5050协议的AGV仿真器，使用Python实现。

## 功能特性

- 完整实现VDA5050 v2.0.0协议消息格式
- 支持MQTT通信
- 模拟AGV状态、订单处理和即时动作
- 可配置的车辆参数和仿真设置

## 消息类型支持

- Connection: 连接状态消息
- State: AGV状态消息
- Order: 任务订单消息
- InstantActions: 即时动作消息
- Visualization: 可视化数据消息

## 项目结构

```
SimulatorAGV/
├── vda5050/
│   ├── __init__.py
│   ├── connection.py
│   ├── state.py
│   ├── order.py
│   ├── instant_actions.py
│   └── visualization.py
├── agv_simulator.py
├── mqtt_client.py
├── utils.py
├── main.py
├── config.json
├── requirements.txt
├── test_mqtt.py
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

修改 `config.json` 文件来配置AGV参数：

- MQTT代理设置
- 车辆信息（序列号、制造商等）
- 仿真参数（地图ID、更新频率等）

## 使用方法

1. 确保MQTT代理正在运行（如Mosquitto）
2. 修改 `config.json` 中的MQTT代理设置
3. 运行仿真器：

```bash
python main.py
```

## VDA5050协议实现

本项目实现了VDA5050 v2.0.0协议的核心功能：

- AGV状态报告（位置、电池、安全状态等）
- 订单处理（节点、边、动作）
- 即时动作执行（如initPosition）
- 连接状态管理
- 可视化数据发布

## 注意事项

- 需要本地运行MQTT代理才能完整测试功能
- 默认配置连接到 `localhost:1883`
- 可通过修改 `config.json` 更改MQTT代理地址和端口