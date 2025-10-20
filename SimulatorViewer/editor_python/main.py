"""
地图编辑器Python模块主程序
启动API服务器，为HTML地图查看器提供服务
"""
import sys
import os
import argparse
import signal
from typing import Optional

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api.web_api import start_api_server, stop_api_server, get_api_server


def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭服务器"""
    print("\n正在关闭服务器...")
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
        print(f"正在启动地图编辑器API服务器...")
        print(f"主机: {args.host}")
        print(f"端口: {args.port}")
        
        server = start_api_server(args.host, args.port)
        
        # 如果指定了场景文件，加载它
        if args.scene_file:
            if os.path.exists(args.scene_file):
                print(f"正在加载场景文件: {args.scene_file}")
                success = server.load_scene_file(args.scene_file)
                if success:
                    print("场景文件加载成功")
                else:
                    print("场景文件加载失败")
            else:
                print(f"警告: 场景文件不存在: {args.scene_file}")
        
        # 显示服务器信息
        server_info = server.get_server_info()
        print(f"\n服务器已启动!")
        print(f"API基础URL: {server_info['api_base_url']}")
        print(f"状态: {'运行中' if server_info['is_running'] else '已停止'}")
        
        print("\n可用的API端点:")
        print("  GET  /api/scene/data     - 获取场景数据")
        print("  POST /api/scene/load     - 加载场景")
        print("  POST /api/scene/save     - 保存场景")
        print("  GET  /api/points         - 获取点位列表")
        print("  POST /api/points         - 创建点位")
        print("  PUT  /api/points/{id}    - 更新点位")
        print("  DEL  /api/points/{id}    - 删除点位")
        print("  GET  /api/routes         - 获取路径列表")
        print("  POST /api/routes         - 创建路径")
        print("  PUT  /api/routes/{id}    - 更新路径")
        print("  DEL  /api/routes/{id}    - 删除路径")
        print("  GET  /api/areas          - 获取区域列表")
        print("  POST /api/areas          - 创建区域")
        print("  PUT  /api/areas/{id}     - 更新区域")
        print("  DEL  /api/areas/{id}     - 删除区域")
        print("  GET  /api/robots         - 获取机器人列表")
        print("  GET  /api/statistics     - 获取统计信息")
        print("  GET  /api/search?q=关键词 - 搜索")
        
        print(f"\n按 Ctrl+C 停止服务器")
        
        # 保持服务器运行
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        print(f"启动服务器失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # 确保服务器被关闭
        stop_api_server()


if __name__ == '__main__':
    main()