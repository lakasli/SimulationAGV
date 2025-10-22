#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT消息路由测试脚本
专门测试多机器人环境下的消息路由和订阅机制
"""

import os
import sys
import time
import json
import threading
from typing import Dict, List, Any
from datetime import datetime
import paho.mqtt.client as mqtt

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.robot_factory import RobotFactory
from instances.robot_instance import RobotInstance
from logger_config import logger


class MQTTMessageRoutingTester:
    """MQTT消息路由测试器"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化测试器"""
        self.robot_factory = RobotFactory(config_path)
        self.robot_instances: Dict[str, RobotInstance] = {}
        self.message_log: List[Dict[str, Any]] = []
        self.test_client = None
        self.running = False
        
        # 加载基础配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.base_config = json.load(f)
        
        logger.info("MQTT消息路由测试器初始化完成")
    
    def setup_test_mqtt_client(self):
        """设置测试用的MQTT客户端"""
        self.test_client = mqtt.Client(client_id="mqtt_routing_tester")
        self.test_client.on_connect = self._on_test_client_connect
        self.test_client.on_message = self._on_test_client_message
        
        # 连接到MQTT服务器
        host = self.base_config['mqtt_broker']['host']
        port = self.base_config['mqtt_broker']['port']
        
        try:
            self.test_client.connect(host, port, 60)
            self.test_client.loop_start()
            logger.info(f"测试客户端已连接到MQTT服务器 {host}:{port}")
        except Exception as e:
            logger.error(f"测试客户端连接失败: {e}")
    
    def _on_test_client_connect(self, client, userdata, flags, rc):
        """测试客户端连接回调"""
        if rc == 0:
            logger.info("测试客户端连接成功")
            # 订阅所有VDA5050相关主题
            self.test_client.subscribe("uagv/+/+/+/+")
            self.test_client.subscribe("uagv/+/+/+/+/+")
        else:
            logger.error(f"测试客户端连接失败，错误代码: {rc}")
    
    def _on_test_client_message(self, client, userdata, msg):
        """测试客户端消息回调"""
        try:
            payload = msg.payload.decode('utf-8')
            message_info = {
                'timestamp': datetime.now().isoformat(),
                'topic': msg.topic,
                'payload_size': len(payload),
                'payload': payload[:200] + '...' if len(payload) > 200 else payload  # 截断长消息
            }
            self.message_log.append(message_info)
            logger.debug(f"测试客户端收到消息 - 主题: {msg.topic}")
        except Exception as e:
            logger.error(f"处理测试客户端消息时出错: {e}")
    
    def create_test_robots_with_different_configs(self, robot_count: int = 3) -> List[str]:
        """
        创建具有不同配置的测试机器人
        
        Args:
            robot_count: 机器人数量
            
        Returns:
            机器人ID列表
        """
        robot_ids = []
        manufacturers = ["CompanyA", "CompanyB", "CompanyC", "CompanyD", "CompanyE"]
        
        for i in range(robot_count):
            robot_info = {
                'id': f'routing_test_robot_{i+1:03d}',
                'serialNumber': f'ROUTE-{i+1:03d}',
                'manufacturer': manufacturers[i % len(manufacturers)],
                'position': {
                    'x': i * 3.0,
                    'y': i * 1.5,
                    'theta': i * 45.0
                }
            }
            
            try:
                robot_instance = self.robot_factory.create_robot_instance(robot_info)
                if robot_instance:
                    self.robot_instances[robot_info['id']] = robot_instance
                    robot_ids.append(robot_info['id'])
                    logger.info(f"创建路由测试机器人: {robot_info['id']} (制造商: {robot_info['manufacturer']})")
            except Exception as e:
                logger.error(f"创建机器人 {robot_info['id']} 时出错: {e}")
        
        return robot_ids
    
    def analyze_topic_structure(self) -> Dict[str, Any]:
        """分析主题结构"""
        logger.info("分析MQTT主题结构...")
        
        topic_analysis = {
            'robots': {},
            'topic_patterns': set(),
            'manufacturers': set(),
            'serial_numbers': set()
        }
        
        for robot_id, robot_instance in self.robot_instances.items():
            config = robot_instance.config
            
            # 生成主题
            base_topic = f"{config['mqtt_broker']['vda_interface']}/{config['vehicle']['vda_version']}/{config['vehicle']['manufacturer']}/{config['vehicle']['serial_number']}"
            
            robot_topics = {
                'base_topic': base_topic,
                'order_topic': f"{base_topic}/order",
                'instant_actions_topic': f"{base_topic}/instantActions",
                'state_topic': f"{base_topic}/state",
                'visualization_topic': f"{base_topic}/visualization",
                'connection_topic': f"{base_topic}/connection"
            }
            
            topic_analysis['robots'][robot_id] = {
                'config': {
                    'manufacturer': config['vehicle']['manufacturer'],
                    'serial_number': config['vehicle']['serial_number'],
                    'client_id': config['mqtt_broker'].get('client_id', 'unknown')
                },
                'topics': robot_topics
            }
            
            # 收集统计信息
            topic_analysis['manufacturers'].add(config['vehicle']['manufacturer'])
            topic_analysis['serial_numbers'].add(config['vehicle']['serial_number'])
            
            for topic_name, topic in robot_topics.items():
                topic_analysis['topic_patterns'].add(topic)
        
        # 转换set为list以便JSON序列化
        topic_analysis['topic_patterns'] = list(topic_analysis['topic_patterns'])
        topic_analysis['manufacturers'] = list(topic_analysis['manufacturers'])
        topic_analysis['serial_numbers'] = list(topic_analysis['serial_numbers'])
        
        return topic_analysis
    
    def test_targeted_message_delivery(self) -> Dict[str, Any]:
        """
        测试定向消息投递
        
        Returns:
            定向消息投递测试结果
        """
        logger.info("开始测试定向消息投递...")
        
        delivery_results = {}
        
        for target_robot_id, target_robot in self.robot_instances.items():
            logger.info(f"测试向机器人 {target_robot_id} 发送定向消息")
            
            # 创建特定的测试订单
            test_order = {
                "headerId": int(time.time()),
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "manufacturer": target_robot.config['vehicle']['manufacturer'],
                "serialNumber": target_robot.config['vehicle']['serial_number'],
                "orderId": f"targeted_order_{target_robot_id}_{int(time.time())}",
                "orderUpdateId": 1,
                "nodes": [
                    {
                        "nodeId": f"target_node_{target_robot_id}",
                        "sequenceId": 1,
                        "released": True,
                        "nodePosition": {"x": 20.0, "y": 10.0, "theta": 0.0}
                    }
                ],
                "edges": []
            }
            
            try:
                # 记录发送前的消息日志长度
                pre_send_log_length = len(self.message_log)
                
                # 发送消息
                target_robot.send_order(test_order)
                
                # 等待消息传播
                time.sleep(2)
                
                # 分析消息日志
                new_messages = self.message_log[pre_send_log_length:]
                
                delivery_results[target_robot_id] = {
                    'order_sent': True,
                    'order_id': test_order['orderId'],
                    'target_manufacturer': test_order['manufacturer'],
                    'target_serial_number': test_order['serialNumber'],
                    'messages_captured': len(new_messages),
                    'message_topics': [msg['topic'] for msg in new_messages]
                }
                
                logger.info(f"向 {target_robot_id} 发送消息完成，捕获到 {len(new_messages)} 条相关消息")
                
            except Exception as e:
                logger.error(f"向机器人 {target_robot_id} 发送消息时出错: {e}")
                delivery_results[target_robot_id] = {
                    'order_sent': False,
                    'error': str(e)
                }
        
        return delivery_results
    
    def test_broadcast_vs_unicast(self) -> Dict[str, Any]:
        """
        测试广播与单播消息的区别
        
        Returns:
            广播与单播测试结果
        """
        logger.info("开始测试广播与单播消息...")
        
        broadcast_test_results = {
            'broadcast_messages': [],
            'unicast_messages': [],
            'message_distribution': {}
        }
        
        # 清空消息日志
        self.message_log.clear()
        
        # 1. 测试广播消息（使用通配符主题）
        logger.info("发送广播消息...")
        broadcast_message = {
            "messageType": "broadcast_test",
            "timestamp": datetime.now().isoformat(),
            "content": "这是一条广播测试消息"
        }
        
        try:
            # 发布到通用主题
            self.test_client.publish("uagv/broadcast/test", json.dumps(broadcast_message))
            time.sleep(3)
            
            broadcast_messages = [msg for msg in self.message_log if 'broadcast' in msg['topic']]
            broadcast_test_results['broadcast_messages'] = broadcast_messages
            
        except Exception as e:
            logger.error(f"发送广播消息时出错: {e}")
        
        # 2. 测试单播消息（发送到特定机器人）
        logger.info("发送单播消息...")
        
        for robot_id, robot_instance in self.robot_instances.items():
            config = robot_instance.config
            specific_topic = f"uagv/{config['vehicle']['vda_version']}/{config['vehicle']['manufacturer']}/{config['vehicle']['serial_number']}/test"
            
            unicast_message = {
                "messageType": "unicast_test",
                "timestamp": datetime.now().isoformat(),
                "targetRobot": robot_id,
                "content": f"这是发送给 {robot_id} 的单播消息"
            }
            
            try:
                self.test_client.publish(specific_topic, json.dumps(unicast_message))
                time.sleep(1)
            except Exception as e:
                logger.error(f"发送单播消息到 {robot_id} 时出错: {e}")
        
        # 等待消息传播
        time.sleep(3)
        
        # 分析消息分布
        for msg in self.message_log:
            topic_parts = msg['topic'].split('/')
            if len(topic_parts) >= 4:
                manufacturer = topic_parts[2] if len(topic_parts) > 2 else 'unknown'
                serial_number = topic_parts[3] if len(topic_parts) > 3 else 'unknown'
                
                key = f"{manufacturer}/{serial_number}"
                if key not in broadcast_test_results['message_distribution']:
                    broadcast_test_results['message_distribution'][key] = 0
                broadcast_test_results['message_distribution'][key] += 1
        
        return broadcast_test_results
    
    def test_message_collision_handling(self) -> Dict[str, Any]:
        """
        测试消息冲突处理
        
        Returns:
            消息冲突处理测试结果
        """
        logger.info("开始测试消息冲突处理...")
        
        collision_results = {
            'simultaneous_sends': [],
            'message_timing': [],
            'collision_detected': False
        }
        
        # 准备同时发送的消息
        messages_to_send = []
        for i, (robot_id, robot_instance) in enumerate(self.robot_instances.items()):
            message = {
                "headerId": int(time.time()) + i,
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "manufacturer": robot_instance.config['vehicle']['manufacturer'],
                "serialNumber": robot_instance.config['vehicle']['serial_number'],
                "orderId": f"collision_test_{robot_id}_{int(time.time())}",
                "orderUpdateId": 1,
                "nodes": [],
                "edges": []
            }
            messages_to_send.append((robot_id, robot_instance, message))
        
        # 记录发送前的时间和消息数量
        pre_send_time = time.time()
        pre_send_log_length = len(self.message_log)
        
        # 使用多线程同时发送消息
        def send_message(robot_id, robot_instance, message):
            try:
                send_time = time.time()
                robot_instance.send_order(message)
                collision_results['simultaneous_sends'].append({
                    'robot_id': robot_id,
                    'send_time': send_time,
                    'order_id': message['orderId']
                })
            except Exception as e:
                logger.error(f"同时发送消息到 {robot_id} 时出错: {e}")
        
        # 创建并启动线程
        threads = []
        for robot_id, robot_instance, message in messages_to_send:
            thread = threading.Thread(target=send_message, args=(robot_id, robot_instance, message))
            threads.append(thread)
        
        # 同时启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 等待消息传播
        time.sleep(5)
        
        # 分析消息时序
        post_send_messages = self.message_log[pre_send_log_length:]
        
        for msg in post_send_messages:
            collision_results['message_timing'].append({
                'timestamp': msg['timestamp'],
                'topic': msg['topic'],
                'relative_time': time.time() - pre_send_time
            })
        
        # 检测是否有消息冲突（简单检测：同一时间戳的消息）
        timestamps = [msg['timestamp'] for msg in post_send_messages]
        if len(timestamps) != len(set(timestamps)):
            collision_results['collision_detected'] = True
        
        return collision_results
    
    def generate_routing_report(self, topic_analysis: Dict[str, Any], 
                              delivery_results: Dict[str, Any],
                              broadcast_results: Dict[str, Any],
                              collision_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成路由测试报告"""
        
        report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'robot_count': len(self.robot_instances),
                'total_messages_captured': len(self.message_log)
            },
            'topic_analysis': topic_analysis,
            'targeted_delivery': delivery_results,
            'broadcast_unicast_test': broadcast_results,
            'collision_handling': collision_results,
            'message_log_sample': self.message_log[-10:] if len(self.message_log) > 10 else self.message_log
        }
        
        return report
    
    def run_routing_test(self, robot_count: int = 4):
        """
        运行完整的路由测试
        
        Args:
            robot_count: 测试机器人数量
        """
        logger.info(f"开始运行MQTT消息路由测试 (机器人数量: {robot_count})")
        
        try:
            # 1. 设置测试MQTT客户端
            self.setup_test_mqtt_client()
            time.sleep(2)
            
            # 2. 创建测试机器人
            robot_ids = self.create_test_robots_with_different_configs(robot_count)
            if not robot_ids:
                logger.error("没有成功创建任何机器人，测试终止")
                return
            
            # 3. 启动所有机器人
            self.running = True
            for robot_id, robot_instance in self.robot_instances.items():
                robot_instance.start()
                time.sleep(1)
            
            # 等待连接稳定
            logger.info("等待MQTT连接稳定...")
            time.sleep(5)
            
            # 4. 分析主题结构
            topic_analysis = self.analyze_topic_structure()
            
            # 5. 测试定向消息投递
            delivery_results = self.test_targeted_message_delivery()
            
            # 6. 测试广播与单播
            broadcast_results = self.test_broadcast_vs_unicast()
            
            # 7. 测试消息冲突处理
            collision_results = self.test_message_collision_handling()
            
            # 8. 生成报告
            report = self.generate_routing_report(
                topic_analysis, delivery_results, 
                broadcast_results, collision_results
            )
            
            # 9. 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mqtt_routing_test_report_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"路由测试报告已保存到: {filename}")
            
            # 10. 打印摘要
            self._print_routing_summary(report)
            
        except Exception as e:
            logger.error(f"路由测试过程中出错: {e}")
        finally:
            # 清理资源
            self.running = False
            for robot_instance in self.robot_instances.values():
                robot_instance.stop()
            
            if self.test_client:
                self.test_client.loop_stop()
                self.test_client.disconnect()
    
    def _print_routing_summary(self, report: Dict[str, Any]):
        """打印路由测试摘要"""
        print("\n" + "="*60)
        print("MQTT消息路由测试摘要")
        print("="*60)
        
        test_info = report['test_info']
        print(f"测试时间: {test_info['timestamp']}")
        print(f"测试机器人数量: {test_info['robot_count']}")
        print(f"捕获消息总数: {test_info['total_messages_captured']}")
        
        topic_analysis = report['topic_analysis']
        print(f"\n主题分析:")
        print(f"  不同制造商数量: {len(topic_analysis['manufacturers'])}")
        print(f"  不同序列号数量: {len(topic_analysis['serial_numbers'])}")
        print(f"  主题模式数量: {len(topic_analysis['topic_patterns'])}")
        
        delivery_results = report['targeted_delivery']
        successful_deliveries = sum(1 for r in delivery_results.values() if r.get('order_sent', False))
        print(f"\n定向消息投递:")
        print(f"  成功投递: {successful_deliveries}/{len(delivery_results)}")
        
        broadcast_results = report['broadcast_unicast_test']
        print(f"\n广播/单播测试:")
        print(f"  广播消息数量: {len(broadcast_results['broadcast_messages'])}")
        print(f"  消息分布: {len(broadcast_results['message_distribution'])} 个目标")
        
        collision_results = report['collision_handling']
        print(f"\n冲突处理测试:")
        print(f"  同时发送消息数: {len(collision_results['simultaneous_sends'])}")
        print(f"  检测到冲突: {'是' if collision_results['collision_detected'] else '否'}")
        
        print("\n" + "="*60)


def main():
    """主函数"""
    print("MQTT消息路由测试脚本")
    print("按 Ctrl+C 可随时停止测试")
    
    # 创建测试器
    tester = MQTTMessageRoutingTester()
    
    # 运行路由测试
    tester.run_routing_test(robot_count=4)


if __name__ == "__main__":
    main()