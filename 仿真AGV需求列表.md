# 仿真AGV需求列表

## 项目概述

本项目旨在实现一个基于VDA5050协议的AGV（自动导引车）仿真系统。该系统需要实现通过VDA5050协议上报state、connection、visualization、factsheet消息，以及接收order和instantActions消息来实现机器人运动控制。

## 功能需求

### 1. VDA5050协议消息上报

#### 1.1 State状态上报
- **功能描述**: 定期上报AGV的当前状态信息，包括位置、电池状态、安全状态等
- **实现函数**: `publish_state_message()`
- **基础函数链**:
  1. `update_state()` - 更新AGV状态
  2. `get_state_message()` - 获取状态消息
  3. `mqtt_client.publish()` - 发布MQTT消息

#### 1.2 Connection连接状态上报
- **功能描述**: 上报AGV的连接状态，包括在线、离线等
- **实现函数**: `publish_connection_message()`
- **基础函数链**:
  1. `set_connection_state()` - 设置连接状态
  2. `get_connection_message()` - 获取连接消息
  3. `mqtt_client.publish()` - 发布MQTT消息

#### 1.3 Visualization可视化上报
- **功能描述**: 上报AGV的可视化信息，用于图形界面显示
- **实现函数**: `publish_visualization_message()`
- **基础函数链**:
  1. `update_visualization()` - 更新可视化信息
  2. `get_visualization_message()` - 获取可视化消息
  3. `mqtt_client.publish()` - 发布MQTT消息

#### 1.4 Factsheet事实表上报
- **功能描述**: 上报AGV的基本信息和能力描述
- **实现函数**: `publish_factsheet_message()`
- **基础函数链**:
  1. `create_factsheet()` - 创建事实表
  2. `get_factsheet_message()` - 获取事实表消息
  3. `mqtt_client.publish()` - 发布MQTT消息

### 2. VDA5050协议消息接收与处理

#### 2.1 Order订单接收与处理
- **功能描述**: 接收并处理来自控制器的订单消息
- **实现函数**: `handle_order_message()`
- **基础函数链**:
  1. `mqtt_client.handle_order_message()` - 处理订单消息
  2. `validate_order()` - 验证订单有效性
  3. `accept_order()` - 接受订单
  4. `process_order()` - 处理订单

#### 2.2 InstantActions即时动作接收与处理
- **功能描述**: 接收并处理来自控制器的即时动作消息
- **实现函数**: `handle_instant_actions_message()`
- **基础函数链**:
  1. `mqtt_client.handle_instant_actions_message()` - 处理即时动作消息
  2. `validate_instant_actions()` - 验证即时动作有效性
  3. `accept_instant_actions()` - 接受即时动作
  4. `process_instant_actions()` - 处理即时动作

### 3. 机器人运动控制

#### 3.1 机器人状态查询
- **功能描述**: 查询机器人当前状态信息
- **实现函数**: `query_robot_status()`
- **基础函数链**:
  1. `get_current_state()` - 获取当前状态
  2. `format_state_response()` - 格式化状态响应
  3. `send_state_response()` - 发送状态响应

#### 3.2 切换地图
- **功能描述**: 切换机器人使用的地图
- **实现函数**: `switch_map()`
- **基础函数链**:
  1. `validate_map_id()` - 验证地图ID
  2. `load_map_data()` - 加载地图数据
  3. `update_current_map()` - 更新当前地图
  4. `initialize_position_on_map()` - 在地图上初始化位置

#### 3.3 路径导航
- **功能描述**: 按照指定路径进行导航
- **实现函数**: `navigate_path()`
- **基础函数链**:
  1. `parse_path_data()` - 解析路径数据
  2. `validate_path()` - 验证路径有效性
  3. `create_path_trajectory()` - 创建路径轨迹
  4. `execute_path_navigation()` - 执行路径导航
  5. `monitor_navigation_progress()` - 监控导航进度

#### 3.4 站点导航
- **功能描述**: 导航到指定站点
- **实现函数**: `navigate_to_station()`
- **基础函数链**:
  1. `find_station_position()` - 查找站点位置
  2. `calculate_route_to_station()` - 计算到站点的路线
  3. `execute_station_navigation()` - 执行站点导航
  4. `verify_station_arrival()` - 验证站点到达

#### 3.5 贝塞尔曲线运动
- **功能描述**: 按照贝塞尔曲线轨迹进行运动
- **实现函数**: `move_bezier_curve()`
- **基础函数链**:
  1. `parse_bezier_parameters()` - 解析贝塞尔曲线参数
  2. `calculate_bezier_curve()` - 计算贝塞尔曲线
  3. `generate_bezier_trajectory()` - 生成贝塞尔轨迹
  4. `execute_bezier_movement()` - 执行贝塞尔运动

#### 3.6 平动
- **功能描述**: 实现机器人的平动运动
- **实现函数**: `move_translation()`
- **基础函数链**:
  1. `parse_translation_parameters()` - 解析平动参数
  2. `calculate_translation_vector()` - 计算平动向量
  3. `execute_translation_movement()` - 执行平动运动
  4. `monitor_translation_progress()` - 监控平动进度

#### 3.7 转动
- **功能描述**: 实现机器人的转动运动
- **实现函数**: `move_rotation()`
- **基础函数链**:
  1. `parse_rotation_parameters()` - 解析转动参数
  2. `calculate_rotation_angle()` - 计算转动角度
  3. `execute_rotation_movement()` - 执行转动运动
  4. `monitor_rotation_progress()` - 监控转动进度

#### 3.8 托盘旋转
- **功能描述**: 实现托盘的旋转运动
- **实现函数**: `rotate_pallet()`
- **基础函数链**:
  1. `parse_pallet_rotation_parameters()` - 解析托盘旋转参数
  2. `calculate_pallet_rotation_angle()` - 计算托盘旋转角度
  3. `execute_pallet_rotation()` - 执行托盘旋转
  4. `monitor_pallet_rotation_progress()` - 监控托盘旋转进度

#### 3.9 暂停当前导航
- **功能描述**: 暂停当前正在执行的导航任务
- **实现函数**: `pause_navigation()`
- **基础函数链**:
  1. `check_navigation_status()` - 检查导航状态
  2. `pause_navigation_execution()` - 暂停导航执行
  3. `update_navigation_state()` - 更新导航状态
  4. `notify_navigation_paused()` - 通知导航已暂停

#### 3.10 继续当前导航
- **功能描述**: 继续之前暂停的导航任务
- **实现函数**: `resume_navigation()`
- **基础函数链**:
  1. `check_paused_navigation()` - 检查暂停的导航
  2. `resume_navigation_execution()` - 恢复导航执行
  3. `update_navigation_state()` - 更新导航状态
  4. `notify_navigation_resumed()` - 通知导航已恢复

#### 3.11 查询机器人任务链
- **功能描述**: 查询机器人当前的任务链
- **实现函数**: `query_task_chain()`
- **基础函数链**:
  1. `get_current_task_chain()` - 获取当前任务链
  2. `format_task_chain_response()` - 格式化任务链响应
  3. `send_task_chain_response()` - 发送任务链响应

#### 3.12 获取路径导航的路径
- **功能描述**: 获取当前路径导航的路径信息
- **实现函数**: `get_navigation_path()`
- **基础函数链**:
  1. `get_current_navigation_path()` - 获取当前导航路径
  2. `format_path_response()` - 格式化路径响应
  3. `send_path_response()` - 发送路径响应

#### 3.13 上传机器人内的地图
- **功能描述**: 上传地图到机器人
- **实现函数**: `upload_map()`
- **基础函数链**:
  1. `validate_map_data()` - 验证地图数据
  2. `process_map_data()` - 处理地图数据
  3. `store_map_data()` - 存储地图数据
  4. `confirm_map_upload()` - 确认地图上传

#### 3.14 删除机器人内的地图
- **功能描述**: 删除机器人内的指定地图
- **实现函数**: `delete_map()`
- **基础函数链**:
  1. `validate_map_deletion()` - 验证地图删除
  2. `remove_map_data()` - 移除地图数据
  3. `update_map_list()` - 更新地图列表
  4. `confirm_map_deletion()` - 确认地图删除

## 需要实现的基础函数列表

### 1. 状态管理相关
- `update_state()` - 更新AGV状态
- `get_current_state()` - 获取当前状态
- `set_connection_state()` - 设置连接状态
- `update_visualization()` - 更新可视化信息
- `create_factsheet()` - 创建事实表

### 2. 消息处理相关
- `get_state_message()` - 获取状态消息
- `get_connection_message()` - 获取连接消息
- `get_visualization_message()` - 获取可视化消息
- `get_factsheet_message()` - 获取事实表消息
- `handle_order_message()` - 处理订单消息
- `handle_instant_actions_message()` - 处理即时动作消息

### 3. 验证相关
- `validate_order()` - 验证订单有效性
- `validate_instant_actions()` - 验证即时动作有效性
- `validate_map_id()` - 验证地图ID
- `validate_path()` - 验证路径有效性
- `validate_map_data()` - 验证地图数据
- `validate_map_deletion()` - 验证地图删除

### 4. 订单处理相关
- `accept_order()` - 接受订单
- `process_order()` - 处理订单
- `accept_instant_actions()` - 接受即时动作
- `process_instant_actions()` - 处理即时动作

### 5. 地图管理相关
- `load_map_data()` - 加载地图数据
- `update_current_map()` - 更新当前地图
- `initialize_position_on_map()` - 在地图上初始化位置
- `process_map_data()` - 处理地图数据
- `store_map_data()` - 存储地图数据
- `remove_map_data()` - 移除地图数据
- `update_map_list()` - 更新地图列表

### 6. 导航相关
- `parse_path_data()` - 解析路径数据
- `create_path_trajectory()` - 创建路径轨迹
- `execute_path_navigation()` - 执行路径导航
- `monitor_navigation_progress()` - 监控导航进度
- `find_station_position()` - 查找站点位置
- `calculate_route_to_station()` - 计算到站点的路线
- `execute_station_navigation()` - 执行站点导航
- `verify_station_arrival()` - 验证站点到达
- `check_navigation_status()` - 检查导航状态
- `pause_navigation_execution()` - 暂停导航执行
- `resume_navigation_execution()` - 恢复导航执行
- `get_current_navigation_path()` - 获取当前导航路径

### 7. 运动控制相关
- `parse_bezier_parameters()` - 解析贝塞尔曲线参数
- `calculate_bezier_curve()` - 计算贝塞尔曲线
- `generate_bezier_trajectory()` - 生成贝塞尔轨迹
- `execute_bezier_movement()` - 执行贝塞尔运动
- `parse_translation_parameters()` - 解析平动参数
- `calculate_translation_vector()` - 计算平动向量
- `execute_translation_movement()` - 执行平动运动
- `monitor_translation_progress()` - 监控平动进度
- `parse_rotation_parameters()` - 解析转动参数
- `calculate_rotation_angle()` - 计算转动角度
- `execute_rotation_movement()` - 执行转动运动
- `monitor_rotation_progress()` - 监控转动进度
- `parse_pallet_rotation_parameters()` - 解析托盘旋转参数
- `calculate_pallet_rotation_angle()` - 计算托盘旋转角度
- `execute_pallet_rotation()` - 执行托盘旋转
- `monitor_pallet_rotation_progress()` - 监控托盘旋转进度

### 8. 任务管理相关
- `get_current_task_chain()` - 获取当前任务链
- `update_navigation_state()` - 更新导航状态

### 9. 响应相关
- `format_state_response()` - 格式化状态响应
- `send_state_response()` - 发送状态响应
- `format_task_chain_response()` - 格式化任务链响应
- `send_task_chain_response()` - 发送任务链响应
- `format_path_response()` - 格式化路径响应
- `send_path_response()` - 发送路径响应
- `confirm_map_upload()` - 确认地图上传
- `confirm_map_deletion()` - 确认地图删除
- `notify_navigation_paused()` - 通知导航已暂停
- `notify_navigation_resumed()` - 通知导航已恢复

### 10. 通信相关
- `mqtt_client.publish()` - 发布MQTT消息

## 实现优先级建议

1. **高优先级**:
   - State状态上报
   - Connection连接状态上报
   - Order订单接收与处理
   - InstantActions即时动作接收与处理
   - 基本的机器人运动控制（平动、转动）

2. **中优先级**:
   - Visualization可视化上报
   - 路径导航
   - 站点导航
   - 暂停/继续导航功能

3. **低优先级**:
   - Factsheet事实表上报
   - 贝塞尔曲线运动
   - 托盘旋转
   - 地图管理功能

## 技术实现注意事项

1. 所有函数需要遵循VDA5050协议规范
2. 确保消息的序列化和反序列化正确处理
3. 实现适当的错误处理和异常管理
4. 考虑多线程环境下的状态同步问题
5. 确保运动控制的平滑性和准确性
6. 实现适当的日志记录功能，便于调试和监控