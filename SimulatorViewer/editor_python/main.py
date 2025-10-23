"""
地图编辑器Python模块主程序
启动API服务器，为HTML地图查看器提供服务
"""
import sys
import os
import argparse
import signal
from typing import Optional

# 添加当前目录和项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # 获取项目根目录
sys.path.insert(0, current_dir)
sys.path.insert(0, project_root)  # 添加项目根目录以访问shared模块

from api.web_api import start_api_server, stop_api_server, get_api_server
from shared import setup_logger

logger = setup_logger()


def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭服务器"""
    logger.info("\n正在关闭服务器...")
    stop_api_server()
    sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='地图编辑器')
    parser.add_argument('--host', default='localhost', help='服务器主机地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=8001, help='服务器端口 (默认: 8001)')
    parser.add_argument('--scene-file', help='要加载的场景文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动API服务器
        logger.info(f"正在启动地图编辑器API服务器...")
        logger.info(f"主机: {args.host}")
        logger.info(f"端口: {args.port}")
        
        server = start_api_server(args.host, args.port)
        
        # 如果指定了场景文件，加载它
        if args.scene_file:
            if os.path.exists(args.scene_file):
                logger.info(f"正在加载场景文件: {args.scene_file}")
                success = server.load_scene_file(args.scene_file)
                if success:
                    logger.info("场景文件加载成功")
                else:
                    logger.error("场景文件加载失败")
            else:
                logger.warning(f"警告: 场景文件不存在: {args.scene_file}")
        
        # 显示服务器信息
        server_info = server.get_server_info()
        logger.info(f"\n服务器已启动!")
        logger.info(f"API基础URL: {server_info['api_base_url']}")
        logger.info(f"状态: {'运行中' if server_info['is_running'] else '已停止'}")
        
        # 保持服务器运行
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # 确保服务器被关闭
        stop_api_server()


if __name__ == '__main__':
    main()