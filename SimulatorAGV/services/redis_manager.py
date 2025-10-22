import time
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import aioredis
from logger_config import logger


class RedisManager:
    """Redis连接管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.redis: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认Redis配置"""
        return {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
            'max_connections': 20,
            'retry_on_timeout': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5
        }
    
    async def connect(self):
        """连接到Redis"""
        try:
            # 创建连接池
            self._connection_pool = aioredis.ConnectionPool(
                host=self.config['host'],
                port=self.config['port'],
                db=self.config['db'],
                password=self.config.get('password'),
                max_connections=self.config.get('max_connections', 20),
                retry_on_timeout=self.config.get('retry_on_timeout', True),
                socket_timeout=self.config.get('socket_timeout', 5),
                socket_connect_timeout=self.config.get('socket_connect_timeout', 5)
            )
            
            # 创建Redis客户端
            self.redis = aioredis.Redis(connection_pool=self._connection_pool)
            
            # 测试连接
            await self.redis.ping()
            
            logger.info(f"Redis连接成功: {self.config['host']}:{self.config['port']}")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    async def disconnect(self):
        """断开Redis连接"""
        try:
            if self.redis:
                await self.redis.close()
                self.redis = None
            
            if self._connection_pool:
                await self._connection_pool.disconnect()
                self._connection_pool = None
            
            logger.info("Redis连接已断开")
            
        except Exception as e:
            logger.error(f"断开Redis连接时出错: {e}")
    
    async def set(self, key: str, value: Union[str, dict, list], expire: int = None):
        """设置键值"""
        if not self.redis:
            raise RuntimeError("Redis未连接")
        
        try:
            # 如果值是字典或列表，转换为JSON字符串
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            await self.redis.set(key, value, ex=expire)
            
        except Exception as e:
            logger.error(f"Redis设置键值失败 {key}: {e}")
            raise
    
    async def get(self, key: str, as_json: bool = False) -> Optional[Union[str, dict, list]]:
        """获取键值"""
        if not self.redis:
            raise RuntimeError("Redis未连接")
        
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            value = value.decode('utf-8')
            
            if as_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis获取键值失败 {key}: {e}")
            raise
    
    async def delete(self, *keys: str) -> int:
        """删除键"""
        if not self.redis:
            raise RuntimeError("Redis未连接")
        
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis删除键失败 {keys}: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.redis:
            raise RuntimeError("Redis未连接")
        
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis检查键存在失败 {key}: {e}")
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        if not self.redis:
            raise RuntimeError("Redis未连接")
        
        try:
            return bool(await self.redis.expire(key, seconds))
        except Exception as e:
            logger.error(f"Redis设置过期时间失败 {key}: {e}")
            raise
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的所有键"""
        if not self.redis:
            raise RuntimeError("Redis未连接")
        
        try:
            keys = await self.redis.keys(pattern)
            return [key.decode('utf-8') for key in keys]
        except Exception as e:
            logger.error(f"Redis获取键列表失败 {pattern}: {e}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.redis is not None


class StateCache:
    """机器人状态缓存服务"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.state_prefix = "robot:state:"
        self.config_prefix = "robot:config:"
        self.order_prefix = "robot:order:"
        self.history_prefix = "robot:history:"
        
    async def set_robot_state(self, robot_id: str, state: Dict[str, Any], expire: int = 300):
        """设置机器人状态"""
        key = f"{self.state_prefix}{robot_id}"
        
        # 添加时间戳
        state['cached_at'] = datetime.now().timestamp()
        state['cached_datetime'] = datetime.now().isoformat()
        
        await self.redis.set(key, state, expire=expire)
        logger.debug(f"已缓存机器人 {robot_id} 状态")
    
    async def get_robot_state(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """获取机器人状态"""
        key = f"{self.state_prefix}{robot_id}"
        return await self.redis.get(key, as_json=True)
    
    async def get_all_robot_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有机器人状态"""
        pattern = f"{self.state_prefix}*"
        keys = await self.redis.keys(pattern)
        
        states = {}
        for key in keys:
            robot_id = key.replace(self.state_prefix, "")
            state = await self.redis.get(key, as_json=True)
            if state:
                states[robot_id] = state
        
        return states
    
    async def set_robot_config(self, robot_id: str, config: Dict[str, Any]):
        """设置机器人配置"""
        key = f"{self.config_prefix}{robot_id}"
        await self.redis.set(key, config)
        logger.debug(f"已缓存机器人 {robot_id} 配置")
    
    async def get_robot_config(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """获取机器人配置"""
        key = f"{self.config_prefix}{robot_id}"
        return await self.redis.get(key, as_json=True)
    
    async def set_robot_order(self, robot_id: str, order: Dict[str, Any], expire: int = 3600):
        """设置机器人当前订单"""
        key = f"{self.order_prefix}{robot_id}"
        
        # 添加时间戳
        order['assigned_at'] = datetime.now().timestamp()
        order['assigned_datetime'] = datetime.now().isoformat()
        
        await self.redis.set(key, order, expire=expire)
        logger.debug(f"已缓存机器人 {robot_id} 订单")
    
    async def get_robot_order(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """获取机器人当前订单"""
        key = f"{self.order_prefix}{robot_id}"
        return await self.redis.get(key, as_json=True)
    
    async def clear_robot_order(self, robot_id: str):
        """清除机器人订单"""
        key = f"{self.order_prefix}{robot_id}"
        await self.redis.delete(key)
        logger.debug(f"已清除机器人 {robot_id} 订单")
    
    async def add_state_history(self, robot_id: str, state: Dict[str, Any], max_history: int = 100):
        """添加状态历史记录"""
        key = f"{self.history_prefix}{robot_id}"
        
        # 添加时间戳
        history_entry = {
            'timestamp': datetime.now().timestamp(),
            'datetime': datetime.now().isoformat(),
            'state': state
        }
        
        # 使用Redis列表存储历史记录
        await self.redis.redis.lpush(key, json.dumps(history_entry, ensure_ascii=False))
        
        # 限制历史记录数量
        await self.redis.redis.ltrim(key, 0, max_history - 1)
        
        # 设置过期时间（24小时）
        await self.redis.expire(key, 86400)
    
    async def get_state_history(self, robot_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取状态历史记录"""
        key = f"{self.history_prefix}{robot_id}"
        
        try:
            history_data = await self.redis.redis.lrange(key, 0, limit - 1)
            history = []
            
            for entry in history_data:
                try:
                    history.append(json.loads(entry.decode('utf-8')))
                except json.JSONDecodeError:
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 历史状态失败: {e}")
            return []
    
    async def get_active_robots(self) -> List[str]:
        """获取活跃的机器人列表"""
        pattern = f"{self.state_prefix}*"
        keys = await self.redis.keys(pattern)
        
        active_robots = []
        for key in keys:
            robot_id = key.replace(self.state_prefix, "")
            state = await self.redis.get(key, as_json=True)
            
            if state and 'cached_at' in state:
                # 检查状态是否在最近5分钟内更新
                if datetime.now().timestamp() - state['cached_at'] < 300:
                    active_robots.append(robot_id)
        
        return active_robots
    
    async def cleanup_expired_data(self):
        """清理过期数据"""
        try:
            # 清理过期的状态数据
            pattern = f"{self.state_prefix}*"
            keys = await self.redis.keys(pattern)
            
            expired_count = 0
            for key in keys:
                state = await self.redis.get(key, as_json=True)
                if state and 'cached_at' in state:
                    # 如果状态超过10分钟未更新，认为已过期
                    if datetime.now().timestamp() - state['cached_at'] > 600:
                        await self.redis.delete(key)
                        expired_count += 1
            
            if expired_count > 0:
                logger.info(f"清理了 {expired_count} 个过期状态记录")
                
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = {
                'active_robots': len(await self.get_active_robots()),
                'total_states': len(await self.redis.keys(f"{self.state_prefix}*")),
                'total_configs': len(await self.redis.keys(f"{self.config_prefix}*")),
                'total_orders': len(await self.redis.keys(f"{self.order_prefix}*")),
                'total_histories': len(await self.redis.keys(f"{self.history_prefix}*")),
                'timestamp': datetime.now().timestamp(),
                'datetime': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计信息失败: {e}")
            return {}


class RedisConnectionManager:
    """Redis连接管理器单例"""
    
    _instance = None
    _redis_manager = None
    _state_cache = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, config: Dict[str, Any] = None):
        """初始化Redis连接"""
        if self._redis_manager is None:
            self._redis_manager = RedisManager(config)
            await self._redis_manager.connect()
            
            self._state_cache = StateCache(self._redis_manager)
            
            logger.info("Redis连接管理器已初始化")
    
    async def close(self):
        """关闭Redis连接"""
        if self._redis_manager:
            await self._redis_manager.disconnect()
            self._redis_manager = None
            self._state_cache = None
            
            logger.info("Redis连接管理器已关闭")
    
    @property
    def redis_manager(self) -> RedisManager:
        """获取Redis管理器"""
        if self._redis_manager is None:
            raise RuntimeError("Redis连接管理器未初始化")
        return self._redis_manager
    
    @property
    def state_cache(self) -> StateCache:
        """获取状态缓存"""
        if self._state_cache is None:
            raise RuntimeError("Redis连接管理器未初始化")
        return self._state_cache