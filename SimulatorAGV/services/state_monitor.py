"""
异步状态监控服务
监听机器人状态变化，缓存状态数据，并触发决策逻辑
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from .async_mqtt_client import VDA5050AsyncMqttClient
from .redis_manager import StateCache, RedisConnectionManager
from ..vda5050.state import State


@dataclass
class RobotStatus:
    """机器人状态摘要"""
    robot_id: str
    manufacturer: str
    serial_number: str
    last_update: datetime
    battery_level: float
    operating_mode: str
    safety_state: str
    position: Dict[str, Any]
    is_online: bool
    errors: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['last_update'] = self.last_update.isoformat()
        return data


class StateMonitorService:
    """异步状态监控服务"""
    
    def __init__(self, 
                 mqtt_broker: str = "localhost",
                 mqtt_port: int = 1883,
                 redis_url: str = "redis://localhost:6379",
                 state_timeout: int = 30):
        """
        初始化状态监控服务
        
        Args:
            mqtt_broker: MQTT代理地址
            mqtt_port: MQTT代理端口
            redis_url: Redis连接URL
            state_timeout: 状态超时时间（秒）
        """
        self.mqtt_client = VDA5050AsyncMqttClient(mqtt_broker, mqtt_port)
        self.state_cache = StateCache()
        self.state_timeout = state_timeout
        
        # 状态变化回调函数
        self.state_change_callbacks: List[Callable[[str, RobotStatus], None]] = []
        self.error_callbacks: List[Callable[[str, List[Dict]], None]] = []
        self.offline_callbacks: List[Callable[[str], None]] = []
        
        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 日志
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """启动状态监控服务"""
        if self._running:
            self.logger.warning("状态监控服务已在运行")
            return
            
        try:
            # 初始化Redis连接
            await RedisConnectionManager.initialize()
            
            # 连接MQTT
            await self.mqtt_client.connect()
            
            # 订阅所有机器人的状态主题
            await self.mqtt_client.subscribe("uagv/+/+/state")
            
            # 设置消息处理回调
            self.mqtt_client.set_message_callback(self._handle_state_message)
            
            # 启动监控任务
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("状态监控服务已启动")
            
        except Exception as e:
            self.logger.error(f"启动状态监控服务失败: {e}")
            await self.stop()
            raise
            
    async def stop(self):
        """停止状态监控服务"""
        self._running = False
        
        # 取消监控任务
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 断开MQTT连接
        await self.mqtt_client.disconnect()
        
        # 关闭Redis连接
        await RedisConnectionManager.close()
        
        self.logger.info("状态监控服务已停止")
        
    def add_state_change_callback(self, callback: Callable[[str, RobotStatus], None]):
        """添加状态变化回调函数"""
        self.state_change_callbacks.append(callback)
        
    def add_error_callback(self, callback: Callable[[str, List[Dict]], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)
        
    def add_offline_callback(self, callback: Callable[[str], None]):
        """添加离线回调函数"""
        self.offline_callbacks.append(callback)
        
    async def get_robot_status(self, robot_id: str) -> Optional[RobotStatus]:
        """获取机器人状态"""
        try:
            state_data = await self.state_cache.get_robot_state(robot_id)
            if not state_data:
                return None
                
            # 检查状态是否过期
            last_update = datetime.fromisoformat(state_data.get('timestamp', ''))
            if datetime.now() - last_update > timedelta(seconds=self.state_timeout):
                return None
                
            return self._create_robot_status(robot_id, state_data)
            
        except Exception as e:
            self.logger.error(f"获取机器人 {robot_id} 状态失败: {e}")
            return None
            
    async def get_all_robot_status(self) -> Dict[str, RobotStatus]:
        """获取所有机器人状态"""
        try:
            active_robots = await self.state_cache.get_active_robots()
            status_dict = {}
            
            for robot_id in active_robots:
                status = await self.get_robot_status(robot_id)
                if status:
                    status_dict[robot_id] = status
                    
            return status_dict
            
        except Exception as e:
            self.logger.error(f"获取所有机器人状态失败: {e}")
            return {}
            
    async def get_robots_by_status(self, 
                                 operating_mode: Optional[str] = None,
                                 safety_state: Optional[str] = None,
                                 min_battery: Optional[float] = None) -> List[RobotStatus]:
        """根据条件筛选机器人"""
        try:
            all_status = await self.get_all_robot_status()
            filtered_robots = []
            
            for status in all_status.values():
                if operating_mode and status.operating_mode != operating_mode:
                    continue
                if safety_state and status.safety_state != safety_state:
                    continue
                if min_battery and status.battery_level < min_battery:
                    continue
                    
                filtered_robots.append(status)
                
            return filtered_robots
            
        except Exception as e:
            self.logger.error(f"筛选机器人失败: {e}")
            return []
            
    async def _handle_state_message(self, topic: str, payload: bytes):
        """处理状态消息"""
        try:
            # 解析主题获取机器人ID
            topic_parts = topic.split('/')
            if len(topic_parts) < 4 or topic_parts[3] != 'state':
                return
                
            manufacturer = topic_parts[1]
            serial_number = topic_parts[2]
            robot_id = f"{manufacturer}_{serial_number}"
            
            # 解析状态数据
            state_data = json.loads(payload.decode())
            state_data['timestamp'] = datetime.now().isoformat()
            
            # 缓存状态数据
            await self.state_cache.set_robot_state(robot_id, state_data)
            
            # 添加历史记录
            await self.state_cache.add_state_history(robot_id, state_data)
            
            # 创建机器人状态对象
            robot_status = self._create_robot_status(robot_id, state_data)
            
            # 触发状态变化回调
            for callback in self.state_change_callbacks:
                try:
                    await self._safe_callback(callback, robot_id, robot_status)
                except Exception as e:
                    self.logger.error(f"状态变化回调执行失败: {e}")
                    
            # 检查错误状态
            if robot_status.errors:
                for callback in self.error_callbacks:
                    try:
                        await self._safe_callback(callback, robot_id, robot_status.errors)
                    except Exception as e:
                        self.logger.error(f"错误回调执行失败: {e}")
                        
            self.logger.debug(f"处理机器人 {robot_id} 状态更新")
            
        except Exception as e:
            self.logger.error(f"处理状态消息失败: {e}")
            
    def _create_robot_status(self, robot_id: str, state_data: Dict) -> RobotStatus:
        """创建机器人状态对象"""
        return RobotStatus(
            robot_id=robot_id,
            manufacturer=state_data.get('manufacturer', ''),
            serial_number=state_data.get('serialNumber', ''),
            last_update=datetime.fromisoformat(state_data.get('timestamp', datetime.now().isoformat())),
            battery_level=state_data.get('batteryState', {}).get('batteryCharge', 0.0),
            operating_mode=state_data.get('operatingMode', 'UNKNOWN'),
            safety_state=state_data.get('safetyState', {}).get('eStop', 'UNKNOWN'),
            position=state_data.get('agvPosition', {}),
            is_online=True,
            errors=state_data.get('errors', [])
        )
        
    async def _safe_callback(self, callback: Callable, *args):
        """安全执行回调函数"""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)
            
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 检查离线机器人
                await self._check_offline_robots()
                
                # 等待下一次检查
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(5)
                
    async def _cleanup_loop(self):
        """清理循环"""
        while self._running:
            try:
                # 清理过期数据
                await self.state_cache.cleanup_expired_data()
                
                # 等待下一次清理
                await asyncio.sleep(300)  # 5分钟清理一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理循环错误: {e}")
                await asyncio.sleep(60)
                
    async def _check_offline_robots(self):
        """检查离线机器人"""
        try:
            active_robots = await self.state_cache.get_active_robots()
            current_time = datetime.now()
            
            for robot_id in active_robots:
                state_data = await self.state_cache.get_robot_state(robot_id)
                if not state_data:
                    continue
                    
                last_update = datetime.fromisoformat(state_data.get('timestamp', ''))
                if current_time - last_update > timedelta(seconds=self.state_timeout):
                    # 机器人离线
                    for callback in self.offline_callbacks:
                        try:
                            await self._safe_callback(callback, robot_id)
                        except Exception as e:
                            self.logger.error(f"离线回调执行失败: {e}")
                            
        except Exception as e:
            self.logger.error(f"检查离线机器人失败: {e}")


class DecisionEngine:
    """决策引擎"""
    
    def __init__(self, state_monitor: StateMonitorService):
        """
        初始化决策引擎
        
        Args:
            state_monitor: 状态监控服务
        """
        self.state_monitor = state_monitor
        self.logger = logging.getLogger(__name__)
        
        # 注册回调函数
        self.state_monitor.add_state_change_callback(self._on_state_change)
        self.state_monitor.add_error_callback(self._on_robot_error)
        self.state_monitor.add_offline_callback(self._on_robot_offline)
        
    async def _on_state_change(self, robot_id: str, status: RobotStatus):
        """处理状态变化"""
        self.logger.info(f"机器人 {robot_id} 状态变化: {status.operating_mode}")
        
        # 根据状态变化触发相应逻辑
        if status.operating_mode == "IDLE" and status.battery_level > 20:
            # 机器人空闲且电量充足，可以分配新任务
            await self._assign_task_if_available(robot_id, status)
        elif status.battery_level < 10:
            # 电量不足，需要充电
            await self._handle_low_battery(robot_id, status)
            
    async def _on_robot_error(self, robot_id: str, errors: List[Dict]):
        """处理机器人错误"""
        self.logger.warning(f"机器人 {robot_id} 发生错误: {errors}")
        
        # 根据错误类型采取相应措施
        for error in errors:
            error_type = error.get('errorType', '')
            if error_type == 'EMERGENCY_STOP':
                await self._handle_emergency_stop(robot_id)
            elif error_type == 'NAVIGATION_ERROR':
                await self._handle_navigation_error(robot_id, error)
                
    async def _on_robot_offline(self, robot_id: str):
        """处理机器人离线"""
        self.logger.warning(f"机器人 {robot_id} 离线")
        
        # 重新分配该机器人的任务给其他机器人
        await self._reassign_tasks(robot_id)
        
    async def _assign_task_if_available(self, robot_id: str, status: RobotStatus):
        """如果有可用任务，分配给机器人"""
        # TODO: 实现任务分配逻辑
        self.logger.info(f"检查是否有任务可分配给机器人 {robot_id}")
        
    async def _handle_low_battery(self, robot_id: str, status: RobotStatus):
        """处理低电量情况"""
        # TODO: 实现充电逻辑
        self.logger.info(f"机器人 {robot_id} 电量不足，需要充电")
        
    async def _handle_emergency_stop(self, robot_id: str):
        """处理紧急停止"""
        # TODO: 实现紧急停止处理逻辑
        self.logger.warning(f"机器人 {robot_id} 紧急停止")
        
    async def _handle_navigation_error(self, robot_id: str, error: Dict):
        """处理导航错误"""
        # TODO: 实现导航错误处理逻辑
        self.logger.warning(f"机器人 {robot_id} 导航错误: {error}")
        
    async def _reassign_tasks(self, robot_id: str):
        """重新分配任务"""
        # TODO: 实现任务重新分配逻辑
        self.logger.info(f"重新分配机器人 {robot_id} 的任务")