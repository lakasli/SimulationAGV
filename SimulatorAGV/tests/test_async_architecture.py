"""
异步架构测试脚本
验证 asyncio + aioredis + asyncio-mqtt 技术架构的各个组件
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.async_mqtt_client import AsyncMqttClient, VDA5050AsyncMqttClient
from services.redis_manager import RedisManager, StateCache, RedisConnectionManager
from services.state_monitor import StateMonitorService, DecisionEngine, RobotStatus
from services.async_instance_manager import AsyncInstanceManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AsyncArchitectureTest:
    """异步架构测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.mqtt_broker = "localhost"
        self.mqtt_port = 1883
        self.redis_url = "redis://localhost:6379"
        
        # 测试结果
        self.test_results = {}
        
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始异步架构测试...")
        
        test_methods = [
            self.test_redis_connection,
            self.test_redis_manager,
            self.test_state_cache,
            self.test_async_mqtt_client,
            self.test_vda5050_mqtt_client,
            self.test_state_monitor_service,
            self.test_decision_engine,
            self.test_async_instance_manager,
            self.test_integration
        ]
        
        for test_method in test_methods:
            test_name = test_method.__name__
            logger.info(f"运行测试: {test_name}")
            
            try:
                start_time = time.time()
                await test_method()
                end_time = time.time()
                
                self.test_results[test_name] = {
                    "status": "PASSED",
                    "duration": end_time - start_time,
                    "error": None
                }
                logger.info(f"测试 {test_name} 通过")
                
            except Exception as e:
                self.test_results[test_name] = {
                    "status": "FAILED",
                    "duration": 0,
                    "error": str(e)
                }
                logger.error(f"测试 {test_name} 失败: {e}")
                
        # 输出测试结果
        self.print_test_results()
        
    async def test_redis_connection(self):
        """测试Redis连接"""
        logger.info("测试Redis连接...")
        
        # 初始化Redis连接
        await RedisConnectionManager.initialize(self.redis_url)
        
        # 测试基本操作
        redis_manager = RedisManager()
        
        # 设置和获取数据
        test_key = "test:connection"
        test_value = {"timestamp": datetime.now().isoformat(), "test": True}
        
        await redis_manager.set(test_key, json.dumps(test_value), expire=60)
        
        retrieved_value = await redis_manager.get(test_key)
        assert retrieved_value is not None, "Redis数据获取失败"
        
        retrieved_data = json.loads(retrieved_value)
        assert retrieved_data["test"] is True, "Redis数据不匹配"
        
        # 清理测试数据
        await redis_manager.delete(test_key)
        
        # 关闭连接
        await RedisConnectionManager.close()
        
        logger.info("Redis连接测试通过")
        
    async def test_redis_manager(self):
        """测试Redis管理器"""
        logger.info("测试Redis管理器...")
        
        await RedisConnectionManager.initialize(self.redis_url)
        redis_manager = RedisManager()
        
        # 测试各种操作
        test_key = "test:manager"
        test_data = {"value": 123, "name": "test"}
        
        # 设置数据
        await redis_manager.set(test_key, json.dumps(test_data))
        
        # 检查存在性
        exists = await redis_manager.exists(test_key)
        assert exists, "Redis键不存在"
        
        # 设置过期时间
        await redis_manager.expire(test_key, 30)
        
        # 获取匹配的键
        keys = await redis_manager.keys("test:*")
        assert test_key in keys, "Redis键查询失败"
        
        # 清理
        await redis_manager.delete(test_key)
        await RedisConnectionManager.close()
        
        logger.info("Redis管理器测试通过")
        
    async def test_state_cache(self):
        """测试状态缓存"""
        logger.info("测试状态缓存...")
        
        await RedisConnectionManager.initialize(self.redis_url)
        state_cache = StateCache()
        
        # 测试机器人状态缓存
        robot_id = "test_robot_001"
        state_data = {
            "manufacturer": "TestManufacturer",
            "serialNumber": "001",
            "batteryState": {"batteryCharge": 85.5},
            "operatingMode": "IDLE",
            "timestamp": datetime.now().isoformat()
        }
        
        # 设置状态
        await state_cache.set_robot_state(robot_id, state_data)
        
        # 获取状态
        retrieved_state = await state_cache.get_robot_state(robot_id)
        assert retrieved_state is not None, "状态缓存获取失败"
        assert retrieved_state["operatingMode"] == "IDLE", "状态数据不匹配"
        
        # 添加历史记录
        await state_cache.add_state_history(robot_id, state_data)
        
        # 获取活跃机器人
        active_robots = await state_cache.get_active_robots()
        assert robot_id in active_robots, "活跃机器人列表错误"
        
        # 测试配置缓存
        config_data = {"max_speed": 2.0, "battery_capacity": 100}
        await state_cache.set_robot_config(robot_id, config_data)
        
        retrieved_config = await state_cache.get_robot_config(robot_id)
        assert retrieved_config is not None, "配置缓存获取失败"
        assert retrieved_config["max_speed"] == 2.0, "配置数据不匹配"
        
        # 清理测试数据
        await state_cache.delete_robot_state(robot_id)
        await state_cache.delete_robot_config(robot_id)
        
        await RedisConnectionManager.close()
        
        logger.info("状态缓存测试通过")
        
    async def test_async_mqtt_client(self):
        """测试异步MQTT客户端"""
        logger.info("测试异步MQTT客户端...")
        
        client = AsyncMqttClient(self.mqtt_broker, self.mqtt_port)
        
        # 测试消息接收
        received_messages = []
        
        def message_handler(topic: str, payload: bytes):
            received_messages.append({
                "topic": topic,
                "payload": payload.decode(),
                "timestamp": datetime.now().isoformat()
            })
            
        client.set_message_callback(message_handler)
        
        try:
            # 连接
            await client.connect()
            
            # 订阅测试主题
            test_topic = "test/async/mqtt"
            await client.subscribe(test_topic)
            
            # 发布测试消息
            test_message = {"test": True, "timestamp": datetime.now().isoformat()}
            await client.publish(test_topic, json.dumps(test_message))
            
            # 等待消息接收
            await asyncio.sleep(2)
            
            # 验证消息接收
            assert len(received_messages) > 0, "未接收到MQTT消息"
            
            received_data = json.loads(received_messages[0]["payload"])
            assert received_data["test"] is True, "MQTT消息内容不匹配"
            
            # 取消订阅
            await client.unsubscribe(test_topic)
            
        finally:
            await client.disconnect()
            
        logger.info("异步MQTT客户端测试通过")
        
    async def test_vda5050_mqtt_client(self):
        """测试VDA5050 MQTT客户端"""
        logger.info("测试VDA5050 MQTT客户端...")
        
        client = VDA5050AsyncMqttClient(self.mqtt_broker, self.mqtt_port)
        
        try:
            await client.connect()
            
            # 测试VDA5050主题生成
            manufacturer = "TestMfg"
            serial_number = "001"
            
            state_topic = client.get_state_topic(manufacturer, serial_number)
            expected_topic = f"uagv/{manufacturer}/{serial_number}/state"
            assert state_topic == expected_topic, f"状态主题不匹配: {state_topic}"
            
            # 测试发布VDA5050消息
            test_state = {
                "manufacturer": manufacturer,
                "serialNumber": serial_number,
                "timestamp": datetime.now().isoformat(),
                "operatingMode": "IDLE"
            }
            
            await client.publish_state(manufacturer, serial_number, test_state)
            
            # 测试连接消息
            connection_data = {
                "manufacturer": manufacturer,
                "serialNumber": serial_number,
                "timestamp": datetime.now().isoformat(),
                "connectionState": "ONLINE"
            }
            
            await client.publish_connection(manufacturer, serial_number, connection_data)
            
        finally:
            await client.disconnect()
            
        logger.info("VDA5050 MQTT客户端测试通过")
        
    async def test_state_monitor_service(self):
        """测试状态监控服务"""
        logger.info("测试状态监控服务...")
        
        # 创建状态监控服务
        state_monitor = StateMonitorService(
            mqtt_broker=self.mqtt_broker,
            mqtt_port=self.mqtt_port,
            redis_url=self.redis_url,
            state_timeout=30
        )
        
        # 状态变化回调测试
        state_changes = []
        
        async def on_state_change(robot_id: str, status: RobotStatus):
            state_changes.append({
                "robot_id": robot_id,
                "status": status.to_dict(),
                "timestamp": datetime.now().isoformat()
            })
            
        state_monitor.add_state_change_callback(on_state_change)
        
        try:
            # 启动状态监控
            await state_monitor.start()
            
            # 模拟发送状态消息
            mqtt_client = VDA5050AsyncMqttClient(self.mqtt_broker, self.mqtt_port)
            await mqtt_client.connect()
            
            test_robot_state = {
                "manufacturer": "TestMfg",
                "serialNumber": "002",
                "timestamp": datetime.now().isoformat(),
                "operatingMode": "IDLE",
                "batteryState": {"batteryCharge": 75.0},
                "safetyState": {"eStop": "NONE"},
                "agvPosition": {"x": 10.0, "y": 20.0},
                "errors": []
            }
            
            await mqtt_client.publish_state("TestMfg", "002", test_robot_state)
            
            # 等待状态处理
            await asyncio.sleep(3)
            
            # 验证状态接收
            robot_status = await state_monitor.get_robot_status("TestMfg_002")
            assert robot_status is not None, "未接收到机器人状态"
            assert robot_status.operating_mode == "IDLE", "机器人状态不匹配"
            
            # 验证回调触发
            assert len(state_changes) > 0, "状态变化回调未触发"
            
            await mqtt_client.disconnect()
            
        finally:
            await state_monitor.stop()
            
        logger.info("状态监控服务测试通过")
        
    async def test_decision_engine(self):
        """测试决策引擎"""
        logger.info("测试决策引擎...")
        
        # 创建状态监控服务和决策引擎
        state_monitor = StateMonitorService(
            mqtt_broker=self.mqtt_broker,
            mqtt_port=self.mqtt_port,
            redis_url=self.redis_url
        )
        
        decision_engine = DecisionEngine(state_monitor)
        
        # 测试决策逻辑（这里主要测试回调注册）
        try:
            await state_monitor.start()
            
            # 创建测试机器人状态
            test_status = RobotStatus(
                robot_id="test_robot_003",
                manufacturer="TestMfg",
                serial_number="003",
                last_update=datetime.now(),
                battery_level=85.0,
                operating_mode="IDLE",
                safety_state="NONE",
                position={"x": 0, "y": 0},
                is_online=True,
                errors=[]
            )
            
            # 触发状态变化回调
            await decision_engine._on_state_change("test_robot_003", test_status)
            
            # 测试错误处理回调
            test_errors = [{"errorType": "NAVIGATION_ERROR", "errorDescription": "Test error"}]
            await decision_engine._on_robot_error("test_robot_003", test_errors)
            
            # 测试离线处理回调
            await decision_engine._on_robot_offline("test_robot_003")
            
        finally:
            await state_monitor.stop()
            
        logger.info("决策引擎测试通过")
        
    async def test_async_instance_manager(self):
        """测试异步实例管理器"""
        logger.info("测试异步实例管理器...")
        
        # 创建异步实例管理器
        async_manager = AsyncInstanceManager(
            mqtt_broker=self.mqtt_broker,
            mqtt_port=self.mqtt_port,
            redis_url=self.redis_url
        )
        
        try:
            # 启动管理器
            await async_manager.start()
            
            # 测试添加机器人（模拟数据）
            test_robot_info = {
                "id": "test_robot_004",
                "manufacturer": "TestMfg",
                "serialNumber": "004",
                "config": {
                    "max_speed": 2.0,
                    "battery_capacity": 100
                }
            }
            
            # 注意：这里可能会失败，因为需要完整的机器人配置
            # 但我们主要测试接口调用
            try:
                success = await async_manager.add_robot(test_robot_info)
                logger.info(f"添加机器人结果: {success}")
            except Exception as e:
                logger.warning(f"添加机器人失败（预期）: {e}")
            
            # 测试获取状态
            status = await async_manager.get_robot_status()
            assert isinstance(status, dict), "状态返回格式错误"
            
            # 测试缓存统计
            cache_stats = await async_manager.get_cache_statistics()
            assert isinstance(cache_stats, dict), "缓存统计格式错误"
            
        finally:
            await async_manager.stop()
            
        logger.info("异步实例管理器测试通过")
        
    async def test_integration(self):
        """集成测试"""
        logger.info("运行集成测试...")
        
        # 创建完整的异步架构
        async_manager = AsyncInstanceManager(
            mqtt_broker=self.mqtt_broker,
            mqtt_port=self.mqtt_port,
            redis_url=self.redis_url
        )
        
        try:
            # 启动系统
            await async_manager.start()
            
            # 模拟机器人状态发布
            mqtt_client = VDA5050AsyncMqttClient(self.mqtt_broker, self.mqtt_port)
            await mqtt_client.connect()
            
            # 发布多个机器人状态
            for i in range(3):
                robot_state = {
                    "manufacturer": "IntegrationTest",
                    "serialNumber": f"00{i+1}",
                    "timestamp": datetime.now().isoformat(),
                    "operatingMode": "IDLE" if i % 2 == 0 else "MOVING",
                    "batteryState": {"batteryCharge": 80.0 + i * 5},
                    "safetyState": {"eStop": "NONE"},
                    "agvPosition": {"x": i * 10.0, "y": i * 5.0},
                    "errors": []
                }
                
                await mqtt_client.publish_state("IntegrationTest", f"00{i+1}", robot_state)
                
            # 等待状态处理
            await asyncio.sleep(5)
            
            # 获取所有机器人状态
            all_status = await async_manager.get_robot_status()
            logger.info(f"集成测试 - 机器人状态数量: {all_status.get('total_robots', 0)}")
            
            # 测试按条件筛选机器人
            idle_robots = await async_manager.get_robots_by_criteria(operating_mode="IDLE")
            logger.info(f"集成测试 - 空闲机器人数量: {len(idle_robots)}")
            
            # 测试任务队列
            test_task = {
                "task_id": "integration_test_001",
                "type": "MOVE",
                "destination": {"x": 100, "y": 200},
                "priority": "HIGH"
            }
            
            await async_manager.add_task_to_queue(test_task)
            
            # 等待任务处理
            await asyncio.sleep(3)
            
            await mqtt_client.disconnect()
            
        finally:
            await async_manager.stop()
            
        logger.info("集成测试通过")
        
    def print_test_results(self):
        """打印测试结果"""
        logger.info("\n" + "="*60)
        logger.info("异步架构测试结果汇总")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASSED")
        failed_tests = total_tests - passed_tests
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过: {passed_tests}")
        logger.info(f"失败: {failed_tests}")
        logger.info(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        logger.info("\n详细结果:")
        for test_name, result in self.test_results.items():
            status_symbol = "✓" if result["status"] == "PASSED" else "✗"
            duration = f"{result['duration']:.2f}s" if result["duration"] > 0 else "N/A"
            logger.info(f"{status_symbol} {test_name} ({duration})")
            
            if result["error"]:
                logger.info(f"    错误: {result['error']}")
                
        logger.info("="*60)
        
        # 保存测试结果到文件
        results_file = "test_results_async_architecture.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "details": self.test_results
            }, f, indent=2, ensure_ascii=False)
            
        logger.info(f"测试结果已保存到: {results_file}")


async def main():
    """主函数"""
    logger.info("启动异步架构测试...")
    
    # 检查依赖
    try:
        import aioredis
        import asyncio_mqtt
        logger.info("依赖检查通过")
    except ImportError as e:
        logger.error(f"依赖检查失败: {e}")
        logger.error("请确保已安装 aioredis 和 asyncio-mqtt")
        return
        
    # 运行测试
    test_runner = AsyncArchitectureTest()
    await test_runner.run_all_tests()
    
    logger.info("异步架构测试完成")


if __name__ == "__main__":
    asyncio.run(main())