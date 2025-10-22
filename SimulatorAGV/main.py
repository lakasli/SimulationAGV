import json
import time
import signal
import sys
import os
import argparse

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.instance_manager import InstanceManager
from logger_config import logger
from api import start_api_server, register_all_routes


def main():
    """主函数，启动多机器人模拟器"""
    parser = argparse.ArgumentParser(description='VDA5050 多机器人AGV模拟器')
    parser.add_argument('--config', '-c', type=str, default='config.json',
                        help='基础配置文件路径 (默认: config.json)')
    parser.add_argument('--registry', '-r', type=str, default='registered_robots.json',
                        help='机器人注册文件路径 (默认: registered_robots.json)')
    parser.add_argument('--single', '-s', type=str, 
                        help='单机器人模式，指定机器人ID')
    parser.add_argument('--robots', '-n', type=int, default=None,
                        help='创建指定数量的测试机器人')
    parser.add_argument('--api-host', type=str, default='localhost',
                        help='API服务器主机地址 (默认: localhost)')
    parser.add_argument('--api-port', type=int, default=8000,
                        help='API服务器端口 (默认: 8000)')
    
    args = parser.parse_args()
    
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 处理配置文件路径
    if not os.path.isabs(args.config):
        config_path = os.path.join(current_dir, args.config)
    else:
        config_path = args.config
    
    # 处理注册文件路径
    if not os.path.isabs(args.registry):
        registry_path = os.path.join(current_dir, args.registry)
    else:
        registry_path = args.registry
    
    try:
        # 创建实例管理器
        manager = InstanceManager(config_path, registry_path)
        
        # 启动API服务器并注册路由
        logger.info(f"启动API服务器: {args.api_host}:{args.api_port}")
        api_server = start_api_server(args.api_host, args.api_port)
        register_all_routes(manager)
        
        # 显示注册的API路由
        try:
            routes = api_server.get_registry().get_routes()
            logger.info("已注册的API路由:")
            for route in routes:
                logger.info(f"  {route['method']} {route['path']}")
        except Exception as e:
            logger.error(f"获取API路由信息失败: {e}")
            # 继续执行，不因为这个错误而停止
        
        if args.single:
            # 单机器人模式
            logger.info(f"启动单机器人模式，机器人ID: {args.single}")
            success = manager.start_robot(args.single)
            if not success:
                logger.error(f"无法启动机器人 {args.single}")
                return 1
        elif args.robots:
            # 创建指定数量的测试机器人
            logger.info(f"创建 {args.robots} 个测试机器人")
            for i in range(args.robots):
                robot_info = {
                    "id": f"test_robot_{i+1:03d}",
                    "serialNumber": f"TEST{i+1:03d}",
                    "manufacturer": "TestManufacturer",
                    "type": "AGV",
                    "ip": "127.0.0.1",
                    "status": "IDLE",
                    "position": {"x": i * 10, "y": 0, "theta": 0, "mapId": "test_map"},
                    "battery": 100,
                    "maxSpeed": 2.0,
                    "gid": f"test_gid_{i+1}",
                    "is_warning": False,
                    "is_fault": False,
                    "config": {
                        "mqtt": {
                            "port": 1883 + (i % 10)  # 使用不同端口避免冲突
                        },
                        "vehicle": {
                            "serial_number": f"TEST{i+1:03d}",
                            "manufacturer": "TestManufacturer"
                        }
                    }
                }
                manager.add_robot(robot_info)
            
            # 启动所有机器人
            manager.start_all()
        else:
            # 从注册文件加载机器人
            logger.info(f"从注册文件加载机器人: {registry_path}")
            manager.load_robots_from_registry()
            
            # 启动所有机器人
            manager.start_all()
        
        # 显示运行状态
        status = manager.get_robot_status()
        logger.info(f"成功启动 {manager.get_robot_count()} 个机器人实例")
        for robot_id in manager.get_robot_list():
            robot_status = manager.get_robot_status(robot_id)
            logger.info(f"  - {robot_id}: {robot_status['status']}")
        
        logger.info("多机器人模拟器已启动，按 Ctrl+C 停止...")
        
        # 保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n接收到停止信号...")
        
        # 优雅关闭
        logger.info("正在停止所有机器人实例...")
        manager.stop_all()
        
        # 停止API服务器
        from api import stop_api_server
        stop_api_server()
        logger.info("API服务器已停止")
        
        logger.info("多机器人模拟器已停止")
        
        return 0
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)