#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多机器人MQTT通信测试套件主脚本
运行所有多机器人测试并生成综合报告
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_multi_robot_mqtt import MultiRobotMQTTTester
from test_mqtt_message_routing import MQTTMessageRoutingTester
from logger_config import logger


class MultiRobotTestSuite:
    """多机器人测试套件"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化测试套件"""
        self.config_path = config_path
        self.test_results = {}
        self.start_time = datetime.now()
        
        logger.info("多机器人测试套件初始化完成")
    
    def check_mqtt_server(self) -> bool:
        """
        检查MQTT服务器是否可用
        
        Returns:
            MQTT服务器是否可用
        """
        logger.info("检查MQTT服务器连接...")
        
        try:
            import paho.mqtt.client as mqtt
            
            # 加载配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            host = config['mqtt_broker']['host']
            port = config['mqtt_broker']['port']
            
            # 创建测试客户端
            test_client = mqtt.Client(client_id="mqtt_server_checker")
            
            # 设置连接结果标志
            connection_result = {'connected': False}
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    connection_result['connected'] = True
                    logger.info(f"MQTT服务器 {host}:{port} 连接成功")
                else:
                    logger.error(f"MQTT服务器连接失败，错误代码: {rc}")
            
            test_client.on_connect = on_connect
            
            # 尝试连接
            test_client.connect(host, port, 10)
            test_client.loop_start()
            
            # 等待连接结果
            time.sleep(3)
            
            test_client.loop_stop()
            test_client.disconnect()
            
            return connection_result['connected']
            
        except Exception as e:
            logger.error(f"检查MQTT服务器时出错: {e}")
            return False
    
    def run_basic_connectivity_test(self, robot_count: int = 3, monitor_duration: int = 30) -> Dict[str, Any]:
        """
        运行基础连接性测试
        
        Args:
            robot_count: 机器人数量
            monitor_duration: 监控持续时间
            
        Returns:
            测试结果
        """
        logger.info("开始运行基础连接性测试...")
        
        try:
            tester = MultiRobotMQTTTester(self.config_path)
            
            # 创建机器人
            robot_ids = tester.create_test_robots(robot_count)
            if not robot_ids:
                return {'success': False, 'error': '无法创建机器人实例'}
            
            # 启动机器人
            tester.start_all_robots()
            time.sleep(5)  # 等待连接稳定
            
            # 运行测试
            connectivity_results = tester.test_mqtt_connectivity()
            uniqueness_results = tester.test_client_id_uniqueness()
            publishing_results = tester.test_message_publishing()
            
            # 短时间监控
            tester.monitor_robots(monitor_duration)
            
            # 生成报告
            report = tester.generate_test_report()
            
            # 停止机器人
            tester.stop_all_robots()
            
            return {
                'success': True,
                'report': report,
                'summary': {
                    'robot_count': len(robot_ids),
                    'connectivity_success_rate': sum(1 for r in connectivity_results.values() if r.get('is_alive', False)) / len(connectivity_results),
                    'mqtt_connection_rate': sum(1 for r in connectivity_results.values() if r.get('mqtt_connected', False)) / len(connectivity_results),
                    'unique_client_ids': uniqueness_results.get('unique_client_ids', False)
                }
            }
            
        except Exception as e:
            logger.error(f"基础连接性测试失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_message_routing_test(self, robot_count: int = 4) -> Dict[str, Any]:
        """
        运行消息路由测试
        
        Args:
            robot_count: 机器人数量
            
        Returns:
            测试结果
        """
        logger.info("开始运行消息路由测试...")
        
        try:
            tester = MQTTMessageRoutingTester(self.config_path)
            
            # 设置测试客户端
            tester.setup_test_mqtt_client()
            time.sleep(2)
            
            # 创建机器人
            robot_ids = tester.create_test_robots_with_different_configs(robot_count)
            if not robot_ids:
                return {'success': False, 'error': '无法创建机器人实例'}
            
            # 启动机器人
            tester.running = True
            for robot_instance in tester.robot_instances.values():
                robot_instance.start()
                time.sleep(1)
            
            time.sleep(5)  # 等待连接稳定
            
            # 运行路由测试
            topic_analysis = tester.analyze_topic_structure()
            delivery_results = tester.test_targeted_message_delivery()
            broadcast_results = tester.test_broadcast_vs_unicast()
            collision_results = tester.test_message_collision_handling()
            
            # 生成报告
            report = tester.generate_routing_report(
                topic_analysis, delivery_results,
                broadcast_results, collision_results
            )
            
            # 停止机器人
            tester.running = False
            for robot_instance in tester.robot_instances.values():
                robot_instance.stop()
            
            if tester.test_client:
                tester.test_client.loop_stop()
                tester.test_client.disconnect()
            
            return {
                'success': True,
                'report': report,
                'summary': {
                    'robot_count': len(robot_ids),
                    'messages_captured': report['test_info']['total_messages_captured'],
                    'successful_deliveries': sum(1 for r in delivery_results.values() if r.get('order_sent', False)),
                    'collision_detected': collision_results.get('collision_detected', False)
                }
            }
            
        except Exception as e:
            logger.error(f"消息路由测试失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_stress_test(self, robot_count: int = 10, duration: int = 60) -> Dict[str, Any]:
        """
        运行压力测试
        
        Args:
            robot_count: 机器人数量
            duration: 测试持续时间
            
        Returns:
            测试结果
        """
        logger.info(f"开始运行压力测试 (机器人数量: {robot_count}, 持续时间: {duration}秒)...")
        
        try:
            tester = MultiRobotMQTTTester(self.config_path)
            
            # 创建大量机器人
            robot_ids = tester.create_test_robots(robot_count)
            if len(robot_ids) < robot_count * 0.8:  # 至少80%成功创建
                return {'success': False, 'error': f'只成功创建了 {len(robot_ids)}/{robot_count} 个机器人'}
            
            # 启动所有机器人
            tester.start_all_robots()
            time.sleep(10)  # 更长的稳定时间
            
            # 运行长时间监控
            tester.monitor_robots(duration)
            
            # 测试连接性
            connectivity_results = tester.test_mqtt_connectivity()
            
            # 生成报告
            report = tester.generate_test_report()
            
            # 停止机器人
            tester.stop_all_robots()
            
            return {
                'success': True,
                'report': report,
                'summary': {
                    'robot_count': len(robot_ids),
                    'test_duration': duration,
                    'final_alive_count': sum(1 for r in connectivity_results.values() if r.get('is_alive', False)),
                    'stability_rate': sum(1 for r in connectivity_results.values() if r.get('is_alive', False)) / len(connectivity_results)
                }
            }
            
        except Exception as e:
            logger.error(f"压力测试失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_all_tests(self, basic_robots: int = 3, routing_robots: int = 4, 
                     stress_robots: int = 8, stress_duration: int = 45) -> Dict[str, Any]:
        """
        运行所有测试
        
        Args:
            basic_robots: 基础测试机器人数量
            routing_robots: 路由测试机器人数量
            stress_robots: 压力测试机器人数量
            stress_duration: 压力测试持续时间
            
        Returns:
            所有测试结果
        """
        logger.info("开始运行完整的多机器人测试套件...")
        
        all_results = {
            'test_suite_info': {
                'start_time': self.start_time.isoformat(),
                'config_path': self.config_path
            },
            'tests': {}
        }
        
        # 1. 检查MQTT服务器
        mqtt_available = self.check_mqtt_server()
        all_results['mqtt_server_available'] = mqtt_available
        
        if not mqtt_available:
            logger.error("MQTT服务器不可用，跳过所有测试")
            all_results['error'] = 'MQTT服务器不可用'
            return all_results
        
        # 2. 基础连接性测试
        logger.info("=" * 50)
        logger.info("运行基础连接性测试")
        logger.info("=" * 50)
        
        basic_result = self.run_basic_connectivity_test(basic_robots, 30)
        all_results['tests']['basic_connectivity'] = basic_result
        
        if basic_result['success']:
            logger.info("基础连接性测试通过")
        else:
            logger.error(f"基础连接性测试失败: {basic_result.get('error', 'Unknown error')}")
        
        # 等待系统稳定
        time.sleep(5)
        
        # 3. 消息路由测试
        logger.info("=" * 50)
        logger.info("运行消息路由测试")
        logger.info("=" * 50)
        
        routing_result = self.run_message_routing_test(routing_robots)
        all_results['tests']['message_routing'] = routing_result
        
        if routing_result['success']:
            logger.info("消息路由测试通过")
        else:
            logger.error(f"消息路由测试失败: {routing_result.get('error', 'Unknown error')}")
        
        # 等待系统稳定
        time.sleep(5)
        
        # 4. 压力测试
        logger.info("=" * 50)
        logger.info("运行压力测试")
        logger.info("=" * 50)
        
        stress_result = self.run_stress_test(stress_robots, stress_duration)
        all_results['tests']['stress_test'] = stress_result
        
        if stress_result['success']:
            logger.info("压力测试通过")
        else:
            logger.error(f"压力测试失败: {stress_result.get('error', 'Unknown error')}")
        
        # 5. 生成综合报告
        all_results['test_suite_info']['end_time'] = datetime.now().isoformat()
        all_results['summary'] = self._generate_suite_summary(all_results)
        
        # 保存综合报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multi_robot_test_suite_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            logger.info(f"综合测试报告已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存综合报告时出错: {e}")
        
        return all_results
    
    def _generate_suite_summary(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试套件摘要"""
        summary = {
            'total_tests': len(all_results['tests']),
            'passed_tests': sum(1 for test in all_results['tests'].values() if test.get('success', False)),
            'failed_tests': sum(1 for test in all_results['tests'].values() if not test.get('success', False)),
            'mqtt_server_available': all_results.get('mqtt_server_available', False)
        }
        
        # 计算总体成功率
        if summary['total_tests'] > 0:
            summary['success_rate'] = summary['passed_tests'] / summary['total_tests']
        else:
            summary['success_rate'] = 0.0
        
        return summary
    
    def print_final_summary(self, results: Dict[str, Any]):
        """打印最终摘要"""
        print("\n" + "=" * 80)
        print("多机器人MQTT通信测试套件 - 最终报告")
        print("=" * 80)
        
        test_info = results['test_suite_info']
        print(f"测试开始时间: {test_info['start_time']}")
        print(f"测试结束时间: {test_info['end_time']}")
        print(f"配置文件: {test_info['config_path']}")
        
        print(f"\nMQTT服务器状态: {'可用' if results.get('mqtt_server_available', False) else '不可用'}")
        
        summary = results.get('summary', {})
        print(f"\n测试概览:")
        print(f"  总测试数: {summary.get('total_tests', 0)}")
        print(f"  通过测试: {summary.get('passed_tests', 0)}")
        print(f"  失败测试: {summary.get('failed_tests', 0)}")
        print(f"  成功率: {summary.get('success_rate', 0.0):.2%}")
        
        print(f"\n详细结果:")
        for test_name, test_result in results.get('tests', {}).items():
            status = "✓ 通过" if test_result.get('success', False) else "✗ 失败"
            print(f"  {test_name}: {status}")
            
            if test_result.get('success', False) and 'summary' in test_result:
                test_summary = test_result['summary']
                if 'robot_count' in test_summary:
                    print(f"    机器人数量: {test_summary['robot_count']}")
                if 'connectivity_success_rate' in test_summary:
                    print(f"    连接成功率: {test_summary['connectivity_success_rate']:.2%}")
                if 'stability_rate' in test_summary:
                    print(f"    稳定性: {test_summary['stability_rate']:.2%}")
            elif not test_result.get('success', False):
                print(f"    错误: {test_result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多机器人MQTT通信测试套件')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--test', choices=['basic', 'routing', 'stress', 'all'], 
                       default='all', help='要运行的测试类型')
    parser.add_argument('--basic-robots', type=int, default=3, help='基础测试机器人数量')
    parser.add_argument('--routing-robots', type=int, default=4, help='路由测试机器人数量')
    parser.add_argument('--stress-robots', type=int, default=8, help='压力测试机器人数量')
    parser.add_argument('--stress-duration', type=int, default=45, help='压力测试持续时间(秒)')
    
    args = parser.parse_args()
    
    print("多机器人MQTT通信测试套件")
    print("=" * 50)
    print(f"配置文件: {args.config}")
    print(f"测试类型: {args.test}")
    print("按 Ctrl+C 可随时停止测试")
    print("=" * 50)
    
    # 创建测试套件
    test_suite = MultiRobotTestSuite(args.config)
    
    try:
        if args.test == 'basic':
            result = test_suite.run_basic_connectivity_test(args.basic_robots)
            print(f"\n基础连接性测试结果: {'成功' if result['success'] else '失败'}")
            
        elif args.test == 'routing':
            result = test_suite.run_message_routing_test(args.routing_robots)
            print(f"\n消息路由测试结果: {'成功' if result['success'] else '失败'}")
            
        elif args.test == 'stress':
            result = test_suite.run_stress_test(args.stress_robots, args.stress_duration)
            print(f"\n压力测试结果: {'成功' if result['success'] else '失败'}")
            
        elif args.test == 'all':
            results = test_suite.run_all_tests(
                args.basic_robots, args.routing_robots, 
                args.stress_robots, args.stress_duration
            )
            test_suite.print_final_summary(results)
            
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        logger.error(f"测试运行时出错: {e}")


if __name__ == "__main__":
    main()