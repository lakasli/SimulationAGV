"""
一键启动仿真小车和AGV地图查看器
"""
import os
import sys
import subprocess
import threading
import time
import signal
import http.server
import socketserver
from pathlib import Path

# 全局变量存储进程
processes = []
servers = []

def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭所有服务"""
    print("\n正在关闭所有服务...")
    
    # 停止HTTP服务器
    for server in servers:
        try:
            server.shutdown()
            print("HTTP服务器已停止")
        except:
            pass
    
    # 停止子进程
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass
    
    print("所有服务已停止")
    sys.exit(0)

def start_agv_simulator():
    """启动AGV仿真器"""
    try:
        simulator_script = Path("SimulatorAGV/main.py")
        if simulator_script.exists():
            print(f"正在启动AGV仿真器: {simulator_script}")
            cmd = [sys.executable, str(simulator_script)]
            process = subprocess.Popen(
                cmd, 
                cwd="SimulatorAGV",
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            processes.append(process)
            return True
        else:
            print(f"错误: AGV仿真器脚本不存在: {simulator_script}")
            return False
    except Exception as e:
        print(f"启动AGV仿真器失败: {e}")
        return False

def start_map_editor_api():
    """启动地图编辑器API服务器"""
    try:
        api_script = Path("SimulatorViewer/editor_python/main.py")
        scene_file = Path("SimulatorAGV/map_flie/testmap.scene")
        
        if not api_script.exists():
            print(f"错误: API脚本不存在: {api_script}")
            return False
            
        if not scene_file.exists():
            print(f"错误: 场景文件不存在: {scene_file}")
            return False
        
        print(f"正在启动地图编辑器API服务器...")
        cmd = [
            sys.executable, 
            str(api_script),
            "--host", "localhost",
            "--port", "8001", 
            "--scene-file", str(scene_file.absolute())
        ]
        
        process = subprocess.Popen(
            cmd, 
            cwd="SimulatorViewer/editor_python",
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        processes.append(process)
        return True
        
    except Exception as e:
        print(f"启动地图编辑器API服务器失败: {e}")
        return False

def start_http_server():
    """启动HTTP服务器提供地图查看器页面"""
    try:
        port = 8080
        web_root = Path("SimulatorViewer")
        
        if not web_root.exists():
            print(f"错误: Web根目录不存在: {web_root}")
            return False
        
        print(f"正在启动HTTP服务器 (端口: {port})...")
        
        class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(web_root), **kwargs)
            
            def log_message(self, format, *args):
                # 减少日志输出
                pass
        
        def run_server():
            with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
                servers.append(httpd)
                print(f"HTTP服务器已启动: http://localhost:{port}")
                print(f"地图查看器地址: http://localhost:{port}/map_viewer.html")
                httpd.serve_forever()
        
        # 在新线程中启动HTTP服务器
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        return True
        
    except Exception as e:
        print(f"启动HTTP服务器失败: {e}")
        return False

def main():
    """主函数"""
    print("=== AGV仿真系统一键启动 ===")
    print()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    success_count = 0
    
    # 1. 启动AGV仿真器
    print("1. 启动AGV仿真器...")
    if start_agv_simulator():
        success_count += 1
        print("   ✓ AGV仿真器启动成功")
    else:
        print("   ✗ AGV仿真器启动失败")
    
    # 等待一下让仿真器启动
    time.sleep(2)
    
    # 2. 启动地图编辑器API服务器
    print("\n2. 启动地图编辑器API服务器...")
    if start_map_editor_api():
        success_count += 1
        print("   ✓ API服务器启动成功")
    else:
        print("   ✗ API服务器启动失败")
    
    # 等待API服务器启动
    time.sleep(3)
    
    # 3. 启动HTTP服务器
    print("\n3. 启动HTTP服务器...")
    if start_http_server():
        success_count += 1
        print("   ✓ HTTP服务器启动成功")
    else:
        print("   ✗ HTTP服务器启动失败")
    
    # 等待HTTP服务器启动
    time.sleep(1)
    
    print(f"\n=== 启动完成 ({success_count}/3 个服务成功启动) ===")
    
    if success_count > 0:
        print("\n服务地址:")
        if success_count >= 2:  # API服务器启动成功
            print("  • API服务器: http://localhost:8001")
        if success_count >= 3:  # HTTP服务器启动成功
            print("  • 地图查看器: http://localhost:8080/map_viewer.html")
        
        print("\n按 Ctrl+C 停止所有服务")
        
        try:
            # 保持主程序运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("\n所有服务启动失败，程序退出")
        sys.exit(1)

if __name__ == "__main__":
    main()