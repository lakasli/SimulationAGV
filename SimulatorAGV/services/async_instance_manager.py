"""
异步实例管理器
集成状态监控服务和现有的机器人实例管理功能
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .state_monitor import StateMonitorService, DecisionEngine, RobotStatus
from .redis_manager import StateCache, RedisConnectionManager
from core.instance_manager import InstanceManager
from core.robot_factory import RobotFactory
from instances.robot_instance import RobotInstance
from logger_config import logger


class AsyncInstanceManager:
    """异步实例管理器"""
    
    def __init__(self, 
                 base_config_path: str = "config.json",
                 registry_path: str = None,
                 mqtt_broker: str = "localhost",
                 mqtt_port: int = 1883,
                 redis_url: str = "redis://localhost:6379"):
        """
        初始化异步实例管理器
        
        Args:
            base_config_path: 基础配置文件路径
            registry_path: 机器人注册文件路径
            mqtt_broker: MQTT代理地址
            mqtt_port: MQTT代理端口
            redis_url: Redis连接URL
        """
        # 传统实例管理器（用于机器人生命周期管理）
        self.sync_manager = InstanceManager(base_config_path, registry_path)
        
        # 异步状态监控服务
        self.state_monitor = StateMonitorService(mqtt_broker, mqtt_port, redis_url)
        
        # 决策引擎
        self.decision_engine = DecisionEngine(self.state_monitor)
        
        # 状态缓存
        self.state_cache = StateCache()
        
        # 任务队列和处理器
        self.task_queue = asyncio.Queue()
        self.task_processors: List[asyncio.Task] = []
        
        # 运行状态
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # 日志
        self.logger = logging.getLogger(__name__)
        
        # 注册状态变化回调
        self.state_monitor.add_state_change_callback(self._on_robot_state_change)
        self.state_monitor.add_error_callback(self._on_robot_error)
        self.state_monitor.add_offline_callback(self._on_robot_offline)
        
    async def start(self):
        """启动异步实例管理器"""
        if self._running:
            self.logger.warning("异步实例管理器已在运行")
            return
            
        try:
            self.logger.info("启动异步实例管理器...")
            
            # 启动传统实例管理器
            self.sync_manager.start_all()
            
            # 启动状态监控服务
            await self.state_monitor.start()
            
            # 启动任务处理器
            self._running = True
            for i in range(3):  # 启动3个任务处理器
                task = asyncio.create_task(self._task_processor(f"processor-{i}"))
                self.task_processors.append(task)
                
            self.logger.info("异步实例管理器启动完成")
            
        except Exception as e:
            self.logger.error(f"启动异步实例管理器失败: {e}")
            await self.stop()
            raise
            
    async def stop(self):
        """停止异步实例管理器"""
        self.logger.info("停止异步实例管理器...")
        
        self._running = False
        
        # 停止任务处理器
        for task in self.task_processors:
            task.cancel()
            
        # 等待任务完成
        if self.task_processors:
            await asyncio.gather(*self.task_processors, return_exceptions=True)
            
        # 停止状态监控服务
        await self.state_monitor.stop()
        
        # 停止传统实例管理器
        self.sync_manager.stop_all()
        
        self.logger.info("异步实例管理器已停止")
        
    async def add_robot(self, robot_info: Dict[str, Any]) -> bool:
        """
        添加机器人实例
        
        Args:
            robot_info: 机器人信息
            
        Returns:
            添加是否成功
        """
        try:
            # 使用传统管理器添加机器人
            success = self.sync_manager.add_robot(robot_info)
            
            if success:
                robot_id = robot_info["id"]
                
                # 初始化机器人配置到Redis
                await self.state_cache.set_robot_config(robot_id, robot_info)
                
                self.logger.info(f"成功添加机器人: {robot_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"添加机器人失败: {e}")
            return False
            
    async def remove_robot(self, robot_id: str) -> bool:
        """
        移除机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            移除是否成功
        """
        try:
            # 使用传统管理器移除机器人
            success = self.sync_manager.remove_robot(robot_id)
            
            if success:
                # 清理Redis中的数据
                await self.state_cache.delete_robot_state(robot_id)
                await self.state_cache.delete_robot_config(robot_id)
                
                self.logger.info(f"成功移除机器人: {robot_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"移除机器人失败: {e}")
            return False
            
    async def send_order_to_robot(self, robot_id: str, order_data: Dict[str, Any]) -> bool:
        """
        向机器人发送订单
        
        Args:
            robot_id: 机器人ID
            order_data: 订单数据
            
        Returns:
            发送是否成功
        """
        try:
            # 检查机器人状态
            robot_status = await self.state_monitor.get_robot_status(robot_id)
            if not robot_status or not robot_status.is_online:
                self.logger.warning(f"机器人 {robot_id} 不在线，无法发送订单")
                return False
                
            # 缓存订单到Redis
            await self.state_cache.set_robot_order(robot_id, order_data)
            
            # 使用传统管理器发送订单
            success = self.sync_manager.send_order_to_robot(robot_id, order_data)
            
            if success:
                self.logger.info(f"成功向机器人 {robot_id} 发送订单")
            else:
                # 如果发送失败，清理Redis中的订单
                await self.state_cache.delete_robot_order(robot_id)
                
            return success
            
        except Exception as e:
            self.logger.error(f"发送订单失败: {e}")
            return False
            
    async def send_instant_action_to_robot(self, robot_id: str, action_data: Dict[str, Any]) -> bool:
        """
        向机器人发送即时动作
        
        Args:
            robot_id: 机器人ID
            action_data: 动作数据
            
        Returns:
            发送是否成功
        """
        try:
            # 检查机器人状态
            robot_status = await self.state_monitor.get_robot_status(robot_id)
            if not robot_status or not robot_status.is_online:
                self.logger.warning(f"机器人 {robot_id} 不在线，无法发送即时动作")
                return False
                
            # 使用传统管理器发送即时动作
            success = self.sync_manager.send_instant_action_to_robot(robot_id, action_data)
            
            if success:
                self.logger.info(f"成功向机器人 {robot_id} 发送即时动作")
                
            return success
            
        except Exception as e:
            self.logger.error(f"发送即时动作失败: {e}")
            return False
            
    async def get_robot_status(self, robot_id: str = None) -> Dict[str, Any]:
        """
        获取机器人状态
        
        Args:
            robot_id: 机器人ID，如果为None则返回所有机器人状态
            
        Returns:
            机器人状态信息
        """
        try:
            if robot_id:
                # 获取单个机器人状态
                robot_status = await self.state_monitor.get_robot_status(robot_id)
                if robot_status:
                    return robot_status.to_dict()
                else:
                    return {"error": f"机器人 {robot_id} 状态不可用"}
            else:
                # 获取所有机器人状态
                all_status = await self.state_monitor.get_all_robot_status()
                
                # 获取传统管理器的统计信息
                sync_status = self.sync_manager.get_robot_status()
                
                return {
                    "total_robots": len(all_status),
                    "online_robots": len(all_status),
                    "sync_manager_status": sync_status,
                    "robots": {rid: status.to_dict() for rid, status in all_status.items()}
                }
                
        except Exception as e:
            self.logger.error(f"获取机器人状态失败: {e}")
            return {"error": str(e)}
            
    async def get_robots_by_criteria(self, 
                                   operating_mode: Optional[str] = None,
                                   safety_state: Optional[str] = None,
                                   min_battery: Optional[float] = None) -> List[RobotStatus]:
        """
        根据条件筛选机器人
        
        Args:
            operating_mode: 操作模式
            safety_state: 安全状态
            min_battery: 最小电量
            
        Returns:
            符合条件的机器人列表
        """
        return await self.state_monitor.get_robots_by_status(
            operating_mode=operating_mode,
            safety_state=safety_state,
            min_battery=min_battery
        )
        
    async def assign_task_to_available_robot(self, task_data: Dict[str, Any]) -> Optional[str]:
        """
        将任务分配给可用的机器人
        
        Args:
            task_data: 任务数据
            
        Returns:
            分配到的机器人ID，如果没有可用机器人返回None
        """
        try:
            # 获取空闲且电量充足的机器人
            available_robots = await self.get_robots_by_criteria(
                operating_mode="IDLE",
                min_battery=20.0
            )
            
            if not available_robots:
                self.logger.warning("没有可用的机器人来执行任务")
                return None
                
            # 选择电量最高的机器人
            best_robot = max(available_robots, key=lambda r: r.battery_level)
            
            # 发送订单
            success = await self.send_order_to_robot(best_robot.robot_id, task_data)
            
            if success:
                self.logger.info(f"任务已分配给机器人 {best_robot.robot_id}")
                return best_robot.robot_id
            else:
                self.logger.error(f"向机器人 {best_robot.robot_id} 发送任务失败")
                return None
                
        except Exception as e:
            self.logger.error(f"分配任务失败: {e}")
            return None
            
    async def add_task_to_queue(self, task_data: Dict[str, Any]):
        """
        添加任务到队列
        
        Args:
            task_data: 任务数据
        """
        await self.task_queue.put(task_data)
        self.logger.info("任务已添加到队列")
        
    async def _task_processor(self, processor_name: str):
        """
        任务处理器
        
        Args:
            processor_name: 处理器名称
        """
        self.logger.info(f"任务处理器 {processor_name} 已启动")
        
        while self._running:
            try:
                # 从队列获取任务
                task_data = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                self.logger.info(f"处理器 {processor_name} 开始处理任务")
                
                # 分配任务给可用机器人
                assigned_robot = await self.assign_task_to_available_robot(task_data)
                
                if assigned_robot:
                    self.logger.info(f"任务已由处理器 {processor_name} 分配给机器人 {assigned_robot}")
                else:
                    # 如果没有可用机器人，将任务重新放回队列
                    await asyncio.sleep(5)  # 等待5秒后重试
                    await self.task_queue.put(task_data)
                    self.logger.warning(f"处理器 {processor_name} 未找到可用机器人，任务重新入队")
                    
                # 标记任务完成
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"处理器 {processor_name} 处理任务时出错: {e}")
                await asyncio.sleep(1)
                
        self.logger.info(f"任务处理器 {processor_name} 已停止")
        
    async def _on_robot_state_change(self, robot_id: str, status: RobotStatus):
        """处理机器人状态变化"""
        self.logger.debug(f"机器人 {robot_id} 状态变化: {status.operating_mode}")
        
        # 这里可以添加自定义的状态变化处理逻辑
        # 例如：状态统计、告警等
        
    async def _on_robot_error(self, robot_id: str, errors: List[Dict]):
        """处理机器人错误"""
        self.logger.warning(f"机器人 {robot_id} 发生错误: {len(errors)} 个错误")
        
        # 这里可以添加自定义的错误处理逻辑
        # 例如：错误统计、告警、自动恢复等
        
    async def _on_robot_offline(self, robot_id: str):
        """处理机器人离线"""
        self.logger.warning(f"机器人 {robot_id} 离线")
        
        # 这里可以添加自定义的离线处理逻辑
        # 例如：任务重新分配、告警等
        
    def get_sync_manager(self) -> InstanceManager:
        """获取同步实例管理器（用于兼容性）"""
        return self.sync_manager
        
    def get_state_monitor(self) -> StateMonitorService:
        """获取状态监控服务"""
        return self.state_monitor
        
    def get_decision_engine(self) -> DecisionEngine:
        """获取决策引擎"""
        return self.decision_engine
        
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return await self.state_cache.get_cache_statistics()


# 便捷函数
async def create_async_instance_manager(config_path: str = None) -> AsyncInstanceManager:
    """
    创建异步实例管理器的便捷函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        异步实例管理器实例
    """
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        return AsyncInstanceManager(
            base_config_path=config.get('base_config_path', 'config.json'),
            registry_path=config.get('registry_path'),
            mqtt_broker=config.get('mqtt_broker', 'localhost'),
            mqtt_port=config.get('mqtt_port', 1883),
            redis_url=config.get('redis_url', 'redis://localhost:6379')
        )
    else:
        return AsyncInstanceManager()


if __name__ == "__main__":
    async def main():
        """测试异步实例管理器"""
        manager = AsyncInstanceManager()
        
        try:
            await manager.start()
            
            # 等待一段时间观察状态
            await asyncio.sleep(30)
            
            # 获取所有机器人状态
            status = await manager.get_robot_status()
            print(f"机器人状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
            
        finally:
            await manager.stop()
            
    asyncio.run(main())