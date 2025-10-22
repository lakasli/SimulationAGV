#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多机器人MQTT通信测试脚本
测试多个机器人实例同时连接到同一个MQTT服务器的场景
"""

import os
import sys
import time
import json
import threading
import signal
from typing import Dict, List, Any
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.robot_factory import RobotFactory
from instances.robot_instance import RobotInstance
from logger_config import logger


class MultiRobotMQTTTester:
    """多机器人MQTT通信测试器"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化测试器
        
        Args:
            config_path: 基础配置文件路径
        """
        self.robot_factory = RobotFactory(config_path)
        self.robot_instances: Dict[str, RobotInstance] = {}
        self.test_results = {}
        self.running = False
        self.test_start_time = None
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("多机器人MQTT测试器初始化完成")
    
    def _signal_handler(self, signum, frame):
        """信号处理器，用于优雅关闭"""
        logger.info(f"接收到信号 {signum}，正在关闭测试器...")
        self.stop_all_robots()
        sys.exit(0)
    
    def create_test_robots(self, robot_count: int = 3) -> List[str]:
        """
        创建测试用的机器人实例
        
        Args:
            robot_count: 要创建的机器人数量
            
        Returns:
            创建的机器人ID列表
        """
        robot_ids = []
        
        for i in range(robot_count):
            robot_info = {
                'id': f'test_robot_{i+1:03d}',
                'serialNumber': f'AGV-TEST-{i+1:03d}',
                'manufacturer': 'TestCompany',
                'position': {
                    'x': i * 5.0,
                    'y': i * 2.0,
                    'theta': i * 30.0
                }
            }
            
            try:
                robot_instance = self.robot_factory.create_robot_instance(robot_info)
                if robot_instance:
                    self.robot_instances[robot_info['id']] = robot_instance
                    robot_ids.append(robot_info['id'])
                    logger.info(f"创建测试机器人: {robot_info['id']} (序列号: {robot_info['serialNumber']})")
                else:
                    logger.error(f"创建机器人失败: {robot_info['id']}")
            except Exception as e:
                logger.error(f"创建机器人 {robot_info['id']} 时出错: {e}")
        
        logger.info(f"成功创建 {len(robot_ids)} 个测试机器人")
        return robot_ids
    
    def start_all_robots(self):
        """启动所有机器人实例"""
        logger.info("开始启动所有机器人实例...")
        self.running = True
        self.test_start_time = datetime.now()
        
        for robot_id, robot_instance in self.robot_instances.items():
            try:
                robot_instance.start()
                logger.info(f"启动机器人: {robot_id}")
                # 稍微延迟，避免同时连接造成冲突
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"启动机器人 {robot_id} 时出错: {e}")
        
        logger.info("所有机器人启动完成")
    
    def stop_all_robots(self):
        """停止所有机器人实例"""
        logger.info("开始停止所有机器人实例...")
        self.running = False
        
        for robot_id, robot_instance in self.robot_instances.items():
            try:
                robot_instance.stop()
                logger.info(f"停止机器人: {robot_id}")
            except Exception as e:
                logger.error(f"停止机器人 {robot_id} 时出错: {e}")
        
        logger.info("所有机器人已停止")
    
    def test_mqtt_connectivity(self) -> Dict[str, Any]:
        """
        测试MQTT连接性
        
        Returns:
            连接测试结果
        """
        logger.info("开始测试MQTT连接性...")
        connectivity_results = {}
        
        for robot_id, robot_instance in self.robot_instances.items():
            try:
                # 检查机器人是否存活
                is_alive = robot_instance.is_alive()
                
                # 获取机器人状态
                status = robot_instance.get_status()
                
                connectivity_results[robot_id] = {
                    'is_alive': is_alive,
                    'status': status['status'],
                    'mqtt_connected': status.get('mqtt_connected', False),
                    'serial_number': robot_instance.get_serial_number(),
                    'manufacturer': robot_instance.get_manufacturer(),
                    'last_update': status.get('last_update', 'Unknown')
                }
                
                logger.info(f"机器人 {robot_id} 连接状态: 存活={is_alive}, MQTT连接={status.get('mqtt_connected', False)}")
                
            except Exception as e:
                logger.error(f"测试机器人 {robot_id} 连接性时出错: {e}")
                connectivity_results[robot_id] = {
                    'is_alive': False,
                    'status': 'error',
                    'error': str(e)
                }
        
        return connectivity_results
    
    def test_message_publishing(self) -> Dict[str, Any]:
        """
        测试消息发布功能
        
        Returns:
            消息发布测试结果
        """
        logger.info("开始测试消息发布功能...")
        publishing_results = {}
        
        # 测试订单消息
        test_order = {
            "headerId": 1,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "manufacturer": "TestCompany",
            "serialNumber": "TEST-ORDER",
            "orderId": "test_order_001",
            "orderUpdateId": 1,
            "nodes": [
                {
                    "nodeId": "node_1",
                    "sequenceId": 1,
                    "released": True,
                    "nodePosition": {"x": 10.0, "y": 5.0, "theta": 0.0}
                }
            ],
            "edges": []
        }
        
        # 测试即时动作消息
        test_instant_action = {
            "headerId": 2,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "manufacturer": "TestCompany",
            "serialNumber": "TEST-ACTION",
            "instantActions": [
                {
                    "actionId": "test_action_001",
                    "actionType": "startPause",
                    "actionParameters": []
                }
            ]
        }
        
        for robot_id, robot_instance in self.robot_instances.items():
            try:
                # 发送测试订单
                robot_instance.send_order(test_order)
                
                # 发送测试即时动作
                robot_instance.send_instant_action(test_instant_action)
                
                publishing_results[robot_id] = {
                    'order_sent': True,
                    'instant_action_sent': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"向机器人 {robot_id} 发送测试消息成功")
                
            except Exception as e:
                logger.error(f"向机器人 {robot_id} 发送消息时出错: {e}")
                publishing_results[robot_id] = {
                    'order_sent': False,
                    'instant_action_sent': False,
                    'error': str(e)
                }
        
        return publishing_results
    
    def test_client_id_uniqueness(self) -> Dict[str, Any]:
        """
        测试MQTT客户端ID唯一性
        
        Returns:
            客户端ID唯一性测试结果
        """
        logger.info("开始测试MQTT客户端ID唯一性...")
        
        client_ids = {}
        uniqueness_results = {
            'unique_client_ids': True,
            'client_id_mapping': {},
            'duplicates': []
        }
        
        for robot_id, robot_instance in self.robot_instances.items():
            try:
                # 获取MQTT客户端配置
                config = robot_instance.config
                client_id = config.get('mqtt_broker', {}).get('client_id', 'unknown')
                
                uniqueness_results['client_id_mapping'][robot_id] = client_id
                
                if client_id in client_ids:
                    uniqueness_results['unique_client_ids'] = False
                    uniqueness_results['duplicates'].append({
                        'client_id': client_id,
                        'robots': [client_ids[client_id], robot_id]
                    })
                    logger.warning(f"发现重复的客户端ID: {client_id} (机器人: {client_ids[client_id]}, {robot_id})")
                else:
                    client_ids[client_id] = robot_id
                
            except Exception as e:
                logger.error(f"检查机器人 {robot_id} 客户端ID时出错: {e}")
        
        if uniqueness_results['unique_client_ids']:
            logger.info("所有MQTT客户端ID都是唯一的")
        else:
            logger.warning(f"发现 {len(uniqueness_results['duplicates'])} 个重复的客户端ID")
        
        return uniqueness_results
    
    def monitor_robots(self, duration: int = 30):
        """
        监控机器人状态
        
        Args:
            duration: 监控持续时间（秒）
        """
        logger.info(f"开始监控机器人状态，持续时间: {duration} 秒")
        
        start_time = time.time()
        monitoring_data = []
        
        while self.running and (time.time() - start_time) < duration:
            timestamp = datetime.now().isoformat()
            status_snapshot = {}
            
            for robot_id, robot_instance in self.robot_instances.items():
                try:
                    status = robot_instance.get_status()
                    status_snapshot[robot_id] = {
                        'timestamp': timestamp,
                        'status': status['status'],
                        'is_alive': robot_instance.is_alive(),
                        'position': status.get('position', {}),
                        'battery_level': status.get('battery_level', 0),
                        'mqtt_connected': status.get('mqtt_connected', False)
                    }
                except Exception as e:
                    status_snapshot[robot_id] = {
                        'timestamp': timestamp,
                        'error': str(e)
                    }
            
            monitoring_data.append(status_snapshot)
            
            # 每5秒输出一次状态摘要
            if len(monitoring_data) % 5 == 0:
                alive_count = sum(1 for robot_id in self.robot_instances.keys() 
                                if status_snapshot.get(robot_id, {}).get('is_alive', False))
                logger.info(f"监控进度: {len(monitoring_data)}s/{duration}s, 存活机器人: {alive_count}/{len(self.robot_instances)}")
            
            time.sleep(1)
        
        self.test_results['monitoring_data'] = monitoring_data
        logger.info("机器人状态监控完成")
    
    def generate_test_report(self) -> Dict[str, Any]:
        """
        生成测试报告
        
        Returns:
            完整的测试报告
        """
        logger.info("生成测试报告...")
        
        report = {
            'test_info': {
                'start_time': self.test_start_time.isoformat() if self.test_start_time else None,
                'end_time': datetime.now().isoformat(),
                'robot_count': len(self.robot_instances),
                'robot_ids': list(self.robot_instances.keys())
            },
            'connectivity_test': self.test_results.get('connectivity', {}),
            'publishing_test': self.test_results.get('publishing', {}),
            'uniqueness_test': self.test_results.get('uniqueness', {}),
            'monitoring_data': self.test_results.get('monitoring_data', [])
        }
        
        # 计算统计信息
        if 'connectivity' in self.test_results:
            connectivity_stats = {
                'total_robots': len(self.test_results['connectivity']),
                'alive_robots': sum(1 for r in self.test_results['connectivity'].values() if r.get('is_alive', False)),
                'mqtt_connected_robots': sum(1 for r in self.test_results['connectivity'].values() if r.get('mqtt_connected', False))
            }
            report['connectivity_stats'] = connectivity_stats
        
        return report
    
    def save_test_report(self, report: Dict[str, Any], filename: str = None):
        """
        保存测试报告到文件
        
        Args:
            report: 测试报告数据
            filename: 报告文件名
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_robot_mqtt_test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"测试报告已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存测试报告时出错: {e}")
    
    def run_comprehensive_test(self, robot_count: int = 3, monitor_duration: int = 30):
        """
        运行综合测试
        
        Args:
            robot_count: 机器人数量
            monitor_duration: 监控持续时间
        """
        logger.info(f"开始运行多机器人MQTT综合测试 (机器人数量: {robot_count})")
        
        try:
            # 1. 创建测试机器人
            robot_ids = self.create_test_robots(robot_count)
            if not robot_ids:
                logger.error("没有成功创建任何机器人，测试终止")
                return
            
            # 2. 启动所有机器人
            self.start_all_robots()
            
            # 等待连接稳定
            logger.info("等待MQTT连接稳定...")
            time.sleep(5)
            
            # 3. 测试连接性
            connectivity_results = self.test_mqtt_connectivity()
            self.test_results['connectivity'] = connectivity_results
            
            # 4. 测试客户端ID唯一性
            uniqueness_results = self.test_client_id_uniqueness()
            self.test_results['uniqueness'] = uniqueness_results
            
            # 5. 测试消息发布
            publishing_results = self.test_message_publishing()
            self.test_results['publishing'] = publishing_results
            
            # 6. 监控机器人状态
            self.monitor_robots(monitor_duration)
            
            # 7. 生成并保存测试报告
            report = self.generate_test_report()
            self.save_test_report(report)
            
            # 8. 输出测试摘要
            self._print_test_summary(report)
            
        except KeyboardInterrupt:
            logger.info("用户中断测试")
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
        finally:
            # 清理资源
            self.stop_all_robots()
    
    def _print_test_summary(self, report: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("多机器人MQTT通信测试摘要")
        print("="*60)
        
        test_info = report.get('test_info', {})
        print(f"测试时间: {test_info.get('start_time', 'Unknown')} - {test_info.get('end_time', 'Unknown')}")
        print(f"测试机器人数量: {test_info.get('robot_count', 0)}")
        
        connectivity_stats = report.get('connectivity_stats', {})
        if connectivity_stats:
            print(f"\n连接性测试:")
            print(f"  总机器人数: {connectivity_stats.get('total_robots', 0)}")
            print(f"  存活机器人: {connectivity_stats.get('alive_robots', 0)}")
            print(f"  MQTT连接成功: {connectivity_stats.get('mqtt_connected_robots', 0)}")
        
        uniqueness_test = report.get('uniqueness_test', {})
        if uniqueness_test:
            print(f"\n客户端ID唯一性测试:")
            print(f"  客户端ID唯一: {'是' if uniqueness_test.get('unique_client_ids', False) else '否'}")
            if uniqueness_test.get('duplicates'):
                print(f"  重复客户端ID数量: {len(uniqueness_test['duplicates'])}")
        
        print("\n" + "="*60)


def main():
    """主函数"""
    print("多机器人MQTT通信测试脚本")
    print("按 Ctrl+C 可随时停止测试")
    
    # 创建测试器
    tester = MultiRobotMQTTTester()
    
    # 运行综合测试
    # 参数：机器人数量=5，监控时间=60秒
    tester.run_comprehensive_test(robot_count=5, monitor_duration=60)


if __name__ == "__main__":
    main()