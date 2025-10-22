"""
异步架构演示脚本
展示如何使用 asyncio + aioredis + asyncio-mqtt 技术架构
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.async_instance_manager import AsyncInstanceManager
from services.state_monitor import RobotStatus
from services.async_mqtt_client import VDA5050AsyncMqttClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AsyncArchitectureDemo:
    """异步架构演示类"""
    
    def __init__(self):
        """初始化演示环境"""
        self.config_path = "config/async_config.json"
        self.async_manager = None
        self.demo_robots = []
        
    async def run_demo(self):
        """运行完整演示"""
        logger.info("开始异步架构演示...")
        
        try:
            # 1. 初始化异步管理器
            await self.initialize_manager()
            
            # 2. 模拟机器人注册和状态发布
            await self.simulate_robot_registration()
            
            # 3. 演示状态监控
            await self.demonstrate_state_monitoring()
            
            # 4. 演示任务分配
            await self.demonstrate_task_assignment()
            
            # 5. 演示错误处理
            await self.demonstrate_error_handling()
            
            # 6. 演示性能监控
            await self.demonstrate_performance_monitoring()
            
            logger.info("异步架构演示完成")
            
        except Exception as e:
            logger.error(f"演示过程中发生错误: {e}")
            raise
        finally:
            if self.async_manager:
                await self.async_manager.stop()
                
    async def initialize_manager(self):
        """初始化异步管理器"""
        logger.info("初始化异步管理器...")
        
        # 创建异步实例管理器
        self.async_manager = AsyncInstanceManager(
            mqtt_broker="localhost",
            mqtt_port=1883,
            redis_url="redis://localhost:6379"
        )
        
        # 启动管理器
        await self.async_manager.start()
        
        logger.info("异步管理器初始化完成")
        
    async def simulate_robot_registration(self):
        """模拟机器人注册"""
        logger.info("模拟机器人注册...")
        
        # 创建MQTT客户端用于模拟机器人
        mqtt_client = VDA5050AsyncMqttClient("localhost", 1883)
        await mqtt_client.connect()
        
        # 模拟3个机器人
        self.demo_robots = [
            {
                "manufacturer": "DemoMfg",
                "serialNumber": "001",
                "name": "搬运机器人-001",
                "type": "TRANSPORT",
                "battery": 85.0,
                "position": {"x": 10.0, "y": 20.0, "theta": 0.0}
            },
            {
                "manufacturer": "DemoMfg", 
                "serialNumber": "002",
                "name": "清洁机器人-002",
                "type": "CLEANING",
                "battery": 92.0,
                "position": {"x": 50.0, "y": 30.0, "theta": 1.57}
            },
            {
                "manufacturer": "DemoMfg",
                "serialNumber": "003", 
                "name": "巡检机器人-003",
                "type": "INSPECTION",
                "battery": 78.0,
                "position": {"x": 80.0, "y": 15.0, "theta": 3.14}
            }
        ]
        
        # 发布机器人连接状态
        for robot in self.demo_robots:
            connection_data = {
                "manufacturer": robot["manufacturer"],
                "serialNumber": robot["serialNumber"],
                "timestamp": datetime.now().isoformat(),
                "connectionState": "ONLINE"
            }
            
            await mqtt_client.publish_connection(
                robot["manufacturer"], 
                robot["serialNumber"], 
                connection_data
            )
            
        # 发布初始状态
        for robot in self.demo_robots:
            state_data = {
                "manufacturer": robot["manufacturer"],
                "serialNumber": robot["serialNumber"],
                "timestamp": datetime.now().isoformat(),
                "operatingMode": "IDLE",
                "batteryState": {
                    "batteryCharge": robot["battery"],
                    "charging": False,
                    "reach": 100
                },
                "safetyState": {
                    "eStop": "NONE",
                    "fieldViolation": False
                },
                "agvPosition": robot["position"],
                "velocity": {"vx": 0.0, "vy": 0.0, "omega": 0.0},
                "loads": [],
                "driving": False,
                "errors": [],
                "information": [
                    {
                        "infoType": "ROBOT_TYPE",
                        "infoDescription": robot["type"]
                    }
                ]
            }
            
            await mqtt_client.publish_state(
                robot["manufacturer"],
                robot["serialNumber"], 
                state_data
            )
            
        await mqtt_client.disconnect()
        
        # 等待状态处理
        await asyncio.sleep(3)
        
        logger.info(f"已注册 {len(self.demo_robots)} 个演示机器人")
        
    async def demonstrate_state_monitoring(self):
        """演示状态监控功能"""
        logger.info("演示状态监控功能...")
        
        # 获取所有机器人状态
        all_status = await self.async_manager.get_robot_status()
        logger.info(f"当前在线机器人数量: {all_status.get('online_robots', 0)}")
        
        # 显示每个机器人的详细状态
        for robot_id, status in all_status.get('robots', {}).items():
            logger.info(f"机器人 {robot_id}:")
            logger.info(f"  - 操作模式: {status.get('operating_mode', 'UNKNOWN')}")
            logger.info(f"  - 电量: {status.get('battery_level', 0):.1f}%")
            logger.info(f"  - 位置: {status.get('position', {})}")
            logger.info(f"  - 在线状态: {status.get('is_online', False)}")
            
        # 按条件筛选机器人
        idle_robots = await self.async_manager.get_robots_by_criteria(
            operating_mode="IDLE",
            min_battery=80.0
        )
        
        logger.info(f"空闲且电量充足的机器人数量: {len(idle_robots)}")
        
        # 获取缓存统计
        cache_stats = await self.async_manager.get_cache_statistics()
        logger.info(f"缓存统计: {cache_stats}")
        
    async def demonstrate_task_assignment(self):
        """演示任务分配功能"""
        logger.info("演示任务分配功能...")
        
        # 创建示例任务
        tasks = [
            {
                "task_id": "TRANSPORT_001",
                "type": "TRANSPORT",
                "priority": "HIGH",
                "source": {"x": 10.0, "y": 20.0},
                "destination": {"x": 100.0, "y": 50.0},
                "payload": "货物A",
                "deadline": (datetime.now().timestamp() + 3600)  # 1小时后
            },
            {
                "task_id": "CLEANING_001", 
                "type": "CLEANING",
                "priority": "MEDIUM",
                "area": {
                    "points": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 20.0, "y": 0.0},
                        {"x": 20.0, "y": 20.0},
                        {"x": 0.0, "y": 20.0}
                    ]
                },
                "cleaning_mode": "DEEP"
            },
            {
                "task_id": "INSPECTION_001",
                "type": "INSPECTION", 
                "priority": "LOW",
                "route": [
                    {"x": 80.0, "y": 15.0},
                    {"x": 90.0, "y": 25.0},
                    {"x": 85.0, "y": 35.0}
                ],
                "inspection_points": ["CAMERA", "SENSOR", "TEMPERATURE"]
            }
        ]
        
        # 将任务添加到队列
        for task in tasks:
            await self.async_manager.add_task_to_queue(task)
            logger.info(f"任务 {task['task_id']} 已添加到队列")
            
        # 等待任务处理
        await asyncio.sleep(5)
        
        # 尝试直接分配任务给可用机器人
        direct_task = {
            "task_id": "DIRECT_001",
            "type": "MOVE",
            "destination": {"x": 60.0, "y": 40.0},
            "priority": "URGENT"
        }
        
        assigned_robot = await self.async_manager.assign_task_to_available_robot(direct_task)
        if assigned_robot:
            logger.info(f"任务 {direct_task['task_id']} 已直接分配给机器人 {assigned_robot}")
        else:
            logger.warning(f"无法分配任务 {direct_task['task_id']}，没有可用机器人")
            
    async def demonstrate_error_handling(self):
        """演示错误处理功能"""
        logger.info("演示错误处理功能...")
        
        # 模拟机器人错误状态
        mqtt_client = VDA5050AsyncMqttClient("localhost", 1883)
        await mqtt_client.connect()
        
        # 模拟导航错误
        error_state = {
            "manufacturer": "DemoMfg",
            "serialNumber": "001",
            "timestamp": datetime.now().isoformat(),
            "operatingMode": "ERROR",
            "batteryState": {
                "batteryCharge": 85.0,
                "charging": False
            },
            "safetyState": {
                "eStop": "NONE",
                "fieldViolation": False
            },
            "agvPosition": {"x": 10.0, "y": 20.0, "theta": 0.0},
            "errors": [
                {
                    "errorType": "NAVIGATION_ERROR",
                    "errorLevel": "WARNING", 
                    "errorDescription": "路径规划失败",
                    "errorHint": "检查目标位置是否可达"
                }
            ]
        }
        
        await mqtt_client.publish_state("DemoMfg", "001", error_state)
        
        # 等待错误处理
        await asyncio.sleep(2)
        
        # 模拟低电量警告
        low_battery_state = {
            "manufacturer": "DemoMfg",
            "serialNumber": "002",
            "timestamp": datetime.now().isoformat(),
            "operatingMode": "IDLE",
            "batteryState": {
                "batteryCharge": 15.0,  # 低电量
                "charging": False
            },
            "safetyState": {
                "eStop": "NONE",
                "fieldViolation": False
            },
            "agvPosition": {"x": 50.0, "y": 30.0, "theta": 1.57},
            "errors": [
                {
                    "errorType": "BATTERY_LOW",
                    "errorLevel": "WARNING",
                    "errorDescription": "电量不足",
                    "errorHint": "需要充电"
                }
            ]
        }
        
        await mqtt_client.publish_state("DemoMfg", "002", low_battery_state)
        
        # 等待错误处理
        await asyncio.sleep(2)
        
        # 模拟紧急停止
        emergency_state = {
            "manufacturer": "DemoMfg",
            "serialNumber": "003",
            "timestamp": datetime.now().isoformat(),
            "operatingMode": "ERROR",
            "batteryState": {
                "batteryCharge": 78.0,
                "charging": False
            },
            "safetyState": {
                "eStop": "EMERGENCY_STOP",  # 紧急停止
                "fieldViolation": False
            },
            "agvPosition": {"x": 80.0, "y": 15.0, "theta": 3.14},
            "errors": [
                {
                    "errorType": "EMERGENCY_STOP",
                    "errorLevel": "FATAL",
                    "errorDescription": "紧急停止按钮被按下",
                    "errorHint": "检查安全状况后手动复位"
                }
            ]
        }
        
        await mqtt_client.publish_state("DemoMfg", "003", emergency_state)
        
        await mqtt_client.disconnect()
        
        # 等待错误处理
        await asyncio.sleep(3)
        
        logger.info("错误处理演示完成")
        
    async def demonstrate_performance_monitoring(self):
        """演示性能监控功能"""
        logger.info("演示性能监控功能...")
        
        # 获取系统状态
        system_status = await self.async_manager.get_robot_status()
        
        logger.info("系统性能指标:")
        logger.info(f"  - 总机器人数: {system_status.get('total_robots', 0)}")
        logger.info(f"  - 在线机器人数: {system_status.get('online_robots', 0)}")
        
        # 获取缓存统计
        cache_stats = await self.async_manager.get_cache_statistics()
        logger.info("缓存性能指标:")
        for key, value in cache_stats.items():
            logger.info(f"  - {key}: {value}")
            
        # 模拟高频状态更新以测试性能
        logger.info("开始性能压力测试...")
        
        mqtt_client = VDA5050AsyncMqttClient("localhost", 1883)
        await mqtt_client.connect()
        
        start_time = datetime.now()
        message_count = 0
        
        # 发送100条状态更新消息
        for i in range(100):
            for robot in self.demo_robots:
                state_data = {
                    "manufacturer": robot["manufacturer"],
                    "serialNumber": robot["serialNumber"],
                    "timestamp": datetime.now().isoformat(),
                    "operatingMode": "MOVING" if i % 2 == 0 else "IDLE",
                    "batteryState": {
                        "batteryCharge": max(10, robot["battery"] - i * 0.1),
                        "charging": False
                    },
                    "safetyState": {
                        "eStop": "NONE",
                        "fieldViolation": False
                    },
                    "agvPosition": {
                        "x": robot["position"]["x"] + i * 0.1,
                        "y": robot["position"]["y"] + i * 0.1,
                        "theta": robot["position"]["theta"]
                    },
                    "velocity": {
                        "vx": 1.0 if i % 2 == 0 else 0.0,
                        "vy": 0.5 if i % 2 == 0 else 0.0,
                        "omega": 0.1
                    },
                    "errors": []
                }
                
                await mqtt_client.publish_state(
                    robot["manufacturer"],
                    robot["serialNumber"],
                    state_data
                )
                message_count += 1
                
            # 每10条消息暂停一下
            if i % 10 == 0:
                await asyncio.sleep(0.1)
                
        await mqtt_client.disconnect()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"性能测试完成:")
        logger.info(f"  - 发送消息数: {message_count}")
        logger.info(f"  - 耗时: {duration:.2f}秒")
        logger.info(f"  - 消息处理速率: {message_count/duration:.1f} 消息/秒")
        
        # 等待消息处理完成
        await asyncio.sleep(5)
        
        # 获取最终缓存统计
        final_cache_stats = await self.async_manager.get_cache_statistics()
        logger.info("最终缓存统计:")
        for key, value in final_cache_stats.items():
            logger.info(f"  - {key}: {value}")


async def main():
    """主函数"""
    logger.info("启动异步架构演示...")
    
    # 检查依赖
    try:
        import aioredis
        import asyncio_mqtt
        logger.info("依赖检查通过")
    except ImportError as e:
        logger.error(f"依赖检查失败: {e}")
        logger.error("请确保已安装 aioredis 和 asyncio-mqtt")
        logger.error("运行: pip install aioredis asyncio-mqtt")
        return
        
    # 运行演示
    demo = AsyncArchitectureDemo()
    await demo.run_demo()
    
    logger.info("异步架构演示结束")


if __name__ == "__main__":
    asyncio.run(main())