import json
import time
import signal
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import load_config
from agv_simulator import AgvSimulator
from mqtt_client import MqttClient
from vda5050.connection import Connection


class Vda5050AgvSimulator:
    def __init__(self, config_path: str = "config.json"):
        # 加载配置
        self.config = load_config(config_path)
        
        # 创建AGV模拟器
        self.agv_simulator = AgvSimulator(self.config)
        
        # 创建MQTT客户端
        self.mqtt_client = MqttClient(self.config, self._handle_mqtt_message)
        
        # 运行状态标志
        self.running = True
        
        # 注册信号处理器以优雅地关闭
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _handle_mqtt_message(self, topic: str, payload: str):
        """处理MQTT消息"""
        try:
            # 根据主题处理不同类型的VDA5050消息
            if topic.endswith("/order"):
                order = self.mqtt_client.handle_order_message(payload)
                if order:
                    self.agv_simulator.accept_order(order)
            elif topic.endswith("/instantActions"):
                instant_actions = self.mqtt_client.handle_instant_actions_message(payload)
                if instant_actions:
                    self.agv_simulator.accept_instant_actions(instant_actions)
            else:
                print(f"未知主题的消息: {topic}")
        except Exception as e:
            print(f"处理MQTT消息时出错: {e}")

    def _signal_handler(self, signum, frame):
        """信号处理器，用于关闭程序"""
        print("\n接收到关闭信号，正在停止...")
        self.running = False

    def start(self):
        """启动AGV模拟器"""
        print("启动VDA5050 AGV模拟器...")
        
        # 连接到MQTT代理
        self.mqtt_client.connect()
        
        # 发布初始连接消息
        self._publish_connection_message(Connection.CONNECTION_STATE_ONLINE)
        
        # 发布初始状态消息
        self._publish_state_message()
        
        # 主循环
        while self.running:
            try:
                # 更新AGV状态
                self.agv_simulator.update_state()
                
                # 定期发布状态和可视化消息
                self._publish_state_message()
                self._publish_visualization_message()
                
                # 等待指定的时间间隔
                time.sleep(1.0 / self.config['settings']['state_frequency'])
            except Exception as e:
                print(f"运行时出错: {e}")
                time.sleep(1)

        # 程序结束前发布离线消息
        self._publish_connection_message(Connection.CONNECTION_STATE_OFFLINE)
        self.mqtt_client.disconnect()
        print("AGV模拟器已停止")

    def _publish_connection_message(self, state: str):
        """发布连接消息"""
        self.agv_simulator.set_connection_state(state)
        message = self.agv_simulator.get_connection_message()
        self.mqtt_client.publish(
            self.agv_simulator.connection_topic,
            message,
            qos=1,
            retain=True
        )

    def _publish_state_message(self):
        """发布状态消息"""
        message = self.agv_simulator.get_state_message()
        self.mqtt_client.publish(
            self.agv_simulator.state_topic,
            message,
            qos=0
        )

    def _publish_visualization_message(self):
        """发布可视化消息"""
        message = self.agv_simulator.get_visualization_message()
        self.mqtt_client.publish(
            self.agv_simulator.visualization_topic,
            message,
            qos=0
        )


if __name__ == "__main__":
    simulator = Vda5050AgvSimulator()
    simulator.start()