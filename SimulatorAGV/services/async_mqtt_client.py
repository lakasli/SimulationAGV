import asyncio
import json
from typing import Dict, Any, Callable, Optional, List
from contextlib import asynccontextmanager
import asyncio_mqtt as aiomqtt
from logger_config import logger


class AsyncMqttClient:
    """异步MQTT客户端，基于asyncio-mqtt实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[aiomqtt.Client] = None
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.subscribed_topics: List[str] = []
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    async def connect(self):
        """连接到MQTT代理"""
        try:
            mqtt_config = self.config['mqtt_broker']
            
            # 创建客户端配置
            client_config = {
                'hostname': mqtt_config['host'],
                'port': mqtt_config['port'],
                'keepalive': mqtt_config.get('keepalive', 60),
            }
            
            # 添加认证信息（如果有）
            if 'username' in mqtt_config and 'password' in mqtt_config:
                client_config['username'] = mqtt_config['username']
                client_config['password'] = mqtt_config['password']
            
            # 设置客户端ID
            if 'client_id' in mqtt_config:
                client_config['client_id'] = mqtt_config['client_id']
            
            self.client = aiomqtt.Client(**client_config)
            await self.client.__aenter__()
            
            logger.info(f"异步MQTT客户端已连接到 {mqtt_config['host']}:{mqtt_config['port']}")
            self._running = True
            
            # 启动消息监听任务
            listen_task = asyncio.create_task(self._listen_messages())
            self._tasks.append(listen_task)
            
        except Exception as e:
            logger.error(f"连接MQTT代理失败: {e}")
            raise
    
    async def disconnect(self):
        """断开MQTT连接"""
        try:
            self._running = False
            
            # 取消所有任务
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # 等待任务完成
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            if self.client:
                await self.client.__aexit__(None, None, None)
                self.client = None
            
            logger.info("异步MQTT客户端已断开连接")
            
        except Exception as e:
            logger.error(f"断开MQTT连接时出错: {e}")
    
    async def subscribe(self, topic: str, handler: Callable = None):
        """订阅主题"""
        if not self.client:
            raise RuntimeError("MQTT客户端未连接")
        
        try:
            await self.client.subscribe(topic)
            self.subscribed_topics.append(topic)
            
            if handler:
                if topic not in self.message_handlers:
                    self.message_handlers[topic] = []
                self.message_handlers[topic].append(handler)
            
            logger.info(f"已订阅主题: {topic}")
            
        except Exception as e:
            logger.error(f"订阅主题 {topic} 失败: {e}")
            raise
    
    async def unsubscribe(self, topic: str):
        """取消订阅主题"""
        if not self.client:
            raise RuntimeError("MQTT客户端未连接")
        
        try:
            await self.client.unsubscribe(topic)
            if topic in self.subscribed_topics:
                self.subscribed_topics.remove(topic)
            if topic in self.message_handlers:
                del self.message_handlers[topic]
            
            logger.info(f"已取消订阅主题: {topic}")
            
        except Exception as e:
            logger.error(f"取消订阅主题 {topic} 失败: {e}")
            raise
    
    async def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """发布消息"""
        if not self.client:
            raise RuntimeError("MQTT客户端未连接")
        
        try:
            await self.client.publish(topic, payload, qos=qos, retain=retain)
            logger.debug(f"成功发布消息到 {topic}")
            
        except Exception as e:
            logger.error(f"发布消息到 {topic} 失败: {e}")
            raise
    
    async def _listen_messages(self):
        """监听消息的异步任务"""
        if not self.client:
            return
        
        try:
            async for message in self.client.messages:
                if not self._running:
                    break
                
                try:
                    topic = message.topic.value
                    payload = message.payload.decode('utf-8')
                    
                    logger.debug(f"收到消息 - 主题: {topic}, 内容: {payload}")
                    
                    # 调用注册的处理器
                    await self._handle_message(topic, payload)
                    
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    
        except asyncio.CancelledError:
            logger.info("消息监听任务已取消")
        except Exception as e:
            logger.error(f"消息监听出错: {e}")
    
    async def _handle_message(self, topic: str, payload: str):
        """处理收到的消息"""
        # 查找匹配的处理器
        handlers = []
        
        # 精确匹配
        if topic in self.message_handlers:
            handlers.extend(self.message_handlers[topic])
        
        # 通配符匹配
        for pattern, pattern_handlers in self.message_handlers.items():
            if self._topic_matches(topic, pattern):
                handlers.extend(pattern_handlers)
        
        # 执行所有匹配的处理器
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(topic, payload)
                else:
                    handler(topic, payload)
            except Exception as e:
                logger.error(f"消息处理器执行失败: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """检查主题是否匹配模式（支持MQTT通配符）"""
        # 简单的通配符匹配实现
        if '+' in pattern or '#' in pattern:
            topic_parts = topic.split('/')
            pattern_parts = pattern.split('/')
            
            if '#' in pattern:
                # # 通配符匹配
                hash_index = pattern_parts.index('#')
                if len(topic_parts) >= hash_index:
                    return topic_parts[:hash_index] == pattern_parts[:hash_index]
            
            if '+' in pattern:
                # + 通配符匹配
                if len(topic_parts) != len(pattern_parts):
                    return False
                for i, (t_part, p_part) in enumerate(zip(topic_parts, pattern_parts)):
                    if p_part != '+' and p_part != t_part:
                        return False
                return True
        
        return topic == pattern
    
    def add_message_handler(self, topic_pattern: str, handler: Callable):
        """添加消息处理器"""
        if topic_pattern not in self.message_handlers:
            self.message_handlers[topic_pattern] = []
        self.message_handlers[topic_pattern].append(handler)
    
    def remove_message_handler(self, topic_pattern: str, handler: Callable):
        """移除消息处理器"""
        if topic_pattern in self.message_handlers:
            if handler in self.message_handlers[topic_pattern]:
                self.message_handlers[topic_pattern].remove(handler)
            if not self.message_handlers[topic_pattern]:
                del self.message_handlers[topic_pattern]
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.client is not None and self._running
    
    @asynccontextmanager
    async def connection_context(self):
        """连接上下文管理器"""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()


class VDA5050AsyncMqttClient(AsyncMqttClient):
    """专门用于VDA5050协议的异步MQTT客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_topic = self._generate_base_topic()
        
    def _generate_base_topic(self) -> str:
        """生成VDA5050基础主题"""
        return f"{self.config['mqtt_broker']['vda_interface']}/{self.config['vehicle']['vda_version']}/{self.config['vehicle']['manufacturer']}/{self.config['vehicle']['serial_number']}"
    
    async def subscribe_vda5050_topics(self, order_handler=None, instant_actions_handler=None):
        """订阅VDA5050相关主题"""
        # 订阅订单主题
        order_topic = f"{self.base_topic}/order"
        await self.subscribe(order_topic, order_handler)
        
        # 订阅即时动作主题
        instant_actions_topic = f"{self.base_topic}/instantActions"
        await self.subscribe(instant_actions_topic, instant_actions_handler)
    
    async def publish_state(self, state_message: str):
        """发布状态消息"""
        topic = f"{self.base_topic}/state"
        await self.publish(topic, state_message)
    
    async def publish_connection(self, connection_message: str):
        """发布连接状态消息"""
        topic = f"{self.base_topic}/connection"
        await self.publish(topic, connection_message)
    
    async def publish_visualization(self, visualization_message: str):
        """发布可视化消息"""
        topic = f"{self.base_topic}/visualization"
        await self.publish(topic, visualization_message)