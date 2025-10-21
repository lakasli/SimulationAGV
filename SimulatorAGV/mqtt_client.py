import json
import paho.mqtt.client as mqtt
from typing import Dict, Any, Callable
import time

from vda5050.order import Order
from vda5050.instant_actions import InstantActions
from logger_config import logger


class MqttClient:
    def __init__(self, config: Dict[str, Any], message_callback: Callable):
        self.config = config
        self.message_callback = message_callback
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # 设置用户名和密码（如果配置中有）
        if 'username' in self.config['mqtt_broker'] and 'password' in self.config['mqtt_broker']:
            self.client.username_pw_set(
                self.config['mqtt_broker']['username'],
                self.config['mqtt_broker']['password']
            )
        
        # 订阅的主题
        self.subscribed_topics = []

    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            logger.info("成功连接到MQTT代理")
            self._subscribe_to_topics()
        else:
            logger.error(f"连接失败，错误代码: {rc}")

    def _on_message(self, client, userdata, msg):
        """消息回调"""
        try:
            payload = msg.payload.decode('utf-8')
            logger.debug(f"收到消息 - 主题: {msg.topic}, 内容: {payload}")
            
            # 调用外部回调处理消息
            self.message_callback(msg.topic, payload)
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        logger.info("与MQTT代理断开连接")

    def _subscribe_to_topics(self):
        """订阅相关主题"""
        base_topic = self._generate_base_topic()
        
        # 订阅订单主题
        order_topic = f"{base_topic}/order"
        self.client.subscribe(order_topic)
        self.subscribed_topics.append(order_topic)
        logger.info(f"已订阅订单主题: {order_topic}")
        
        # 订阅即时动作主题
        instant_actions_topic = f"{base_topic}/instantActions"
        self.client.subscribe(instant_actions_topic)
        self.subscribed_topics.append(instant_actions_topic)
        logger.info(f"已订阅即时动作主题: {instant_actions_topic}")

    def _generate_base_topic(self) -> str:
        """生成基础MQTT主题"""
        return f"{self.config['mqtt_broker']['vda_interface']}/{self.config['vehicle']['vda_version']}/{self.config['vehicle']['manufacturer']}/{self.config['vehicle']['serial_number']}"

    def connect(self):
        """连接到MQTT代理"""
        try:
            host = self.config['mqtt_broker']['host']
            port = self.config['mqtt_broker']['port']
            logger.info(f"正在连接到MQTT代理 {host}:{port}")
            self.client.connect(host, port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"连接MQTT代理失败: {e}")

    def disconnect(self):
        """断开与MQTT代理的连接"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("已断开与MQTT代理的连接")

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """发布消息"""
        try:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"发布消息失败，错误代码: {result.rc}")
            else:
                logger.debug(f"成功发布消息到 {topic}")
        except Exception as e:
            logger.error(f"发布消息时出错: {e}")

    def handle_order_message(self, payload: str) -> Order:
        """处理订单消息"""
        try:
            data = json.loads(payload)
            order = Order.from_dict(data)
            return order
        except Exception as e:
            logger.error(f"解析订单消息失败: {e}")
            return None

    def handle_instant_actions_message(self, payload: str) -> InstantActions:
        """处理即时动作消息"""
        try:
            data = json.loads(payload)
            instant_actions = InstantActions.from_dict(data)
            return instant_actions
        except Exception as e:
            logger.error(f"解析即时动作消息失败: {e}")
            return None