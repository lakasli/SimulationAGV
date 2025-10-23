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

# 添加当前脚本目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SimulatorViewer', 'editor_python'))
import logging

# 简单日志配置，避免外部依赖
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("start")

# 全局变量存储进程
processes = []
servers = []

class DetailedHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """带详细日志的HTTP请求处理器"""
    
    def log_message(self, format, *args):
        """重写日志方法，添加更详细的信息"""
        timestamp = self.log_date_time_string()
        client_ip = self.client_address[0]
        
        # 解析请求信息
        if hasattr(self, 'requestline'):
            method, path, version = self.requestline.split() if len(self.requestline.split()) >= 3 else ('', '', '')
        else:
            method, path, version = '', '', ''
        
        # 获取响应状态码
        status_code = args[1] if len(args) > 1 else 'unknown'
        
        # 详细日志输出
        logger.info(f"[HTTP] {client_ip} - {method} {path} - Status: {status_code}")
        
        # 特殊处理某些请求
        if path.endswith('.well-known/appspecific/com.chrome.devtools.json'):
            logger.info(f"[HTTP] Chrome开发者工具自动请求 (正常404): {path}")
        elif path.startswith('/api/'):
            logger.info(f"[HTTP] API请求: {path}")
        elif path.endswith('.html'):
            logger.info(f"[HTTP] 页面请求: {path}")
        elif path.endswith(('.js', '.css', '.png', '.jpg', '.svg')):
            logger.info(f"[HTTP] 静态资源请求: {path}")
        
        # 调用原始日志方法
        super().log_message(format, *args)
    
    def do_GET(self):
        """重写GET方法，添加请求开始日志"""
        logger.info(f"[HTTP] 开始处理请求: {self.requestline}")
        start_time = time.time()
        
        try:
            result = super().do_GET()
            end_time = time.time()
            logger.info(f"[HTTP] 请求处理完成，耗时: {(end_time - start_time)*1000:.2f}ms")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"[HTTP] 请求处理失败，耗时: {(end_time - start_time)*1000:.2f}ms, 错误: {e}")
            raise

def get_pid_using_port(port):
    """获取占用指定端口的进程PID"""
    try:
        # 使用 netstat -ano 查找占用端口的进程
        # 在Windows上，netstat -ano 可以显示PID
        command = f"netstat -ano | findstr :{port}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 解析输出，提取PID
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        if pid.isdigit():
                            return int(pid)
        return None
    except Exception as e:
        logger.error(f"获取端口 {port} 占用PID失败: {e}")
        return None

def kill_process_by_pid(pid):
    """根据PID终止进程"""
    try:
        # 在Windows上使用 taskkill /F 强制终止进程
        command = f"taskkill /PID {pid} /F"
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"已终止进程 PID {pid}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"终止进程 PID {pid} 失败: {e.stderr.strip()}")
        return False
    except Exception as e:
        logger.error(f"终止进程 PID {pid} 失败: {e}")
        return False

def clear_port_usage(ports):
    """清理指定端口的占用"""
    logger.info("正在检查并清理端口占用...")
    for port in ports:
        pid = get_pid_using_port(port)
        if pid:
            logger.warning(f"端口 {port} 被进程 PID {pid} 占用，尝试终止...")
            kill_process_by_pid(pid)
        else:
            logger.info(f"端口 {port} 未被占用。")
    logger.info("端口清理完成。")

def signal_handler(signum, frame):
    """信号处理器，用于优雅地关闭所有服务"""
    logger.info("\n正在关闭所有服务...")
    
    # 停止HTTP服务器
    for server in servers:
        try:
            server.shutdown()
            logger.info("HTTP服务器已停止")
        except Exception:
            pass
    
    # 终止所有子进程
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception:
            pass
    
    logger.info("所有服务已停止")
    sys.exit(0)

def start_agv_simulator():
    """启动AGV仿真器"""
    try:
        # 获取当前脚本目录
        current_dir = Path(__file__).parent
        simulator_script = current_dir / "SimulatorAGV" / "main.py"
        
        logger.info(f"正在启动AGV仿真器: {simulator_script}")
        
        # 检查文件是否存在
        if not simulator_script.exists():
            logger.error(f"错误: AGV仿真器脚本不存在: {simulator_script}")
            return False
        
        # 启动AGV仿真器，指定正确的注册文件路径
        process = subprocess.Popen([
            sys.executable, 
            str(simulator_script),
            "--registry", "registered_robots.json"  # 指定正确的注册文件名
        ])
        processes.append(process)
        return True
        
    except Exception as e:
        logger.error(f"启动AGV仿真器失败: {e}")
        return False

def start_map_editor_api():
    """启动地图编辑器API服务器"""
    try:
        # 获取当前脚本目录
        current_dir = Path(__file__).parent
        api_script = current_dir / "SimulatorViewer" / "editor_python" / "main.py"
        scene_file = current_dir / "SimulatorAGV" / "map_flie" / "testmap.scene"
        
        # 检查文件是否存在
        if not api_script.exists():
            logger.error(f"错误: API脚本不存在: {api_script}")
            return False
        
        if not scene_file.exists():
            logger.error(f"错误: 场景文件不存在: {scene_file}")
            return False
        
        logger.info(f"正在启动地图编辑器API服务器...")
        
        # 启动API服务器
        process = subprocess.Popen([
            sys.executable, 
            str(api_script),
            "--host", "0.0.0.0",
            "--port", "8001",
            "--scene-file", str(scene_file)
        ])
        processes.append(process)
        
        # 等待一下让服务器启动
        logger.info("等待API服务器启动...")
        time.sleep(2)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            logger.info("API服务器进程正在运行")
            return True
        else:
            logger.error("API服务器进程已退出")
            return False
        
    except Exception as e:
        logger.error(f"启动地图编辑器API服务器失败: {e}")
        return False

def start_http_server():
    """启动HTTP服务器"""
    try:
        # 获取当前脚本目录
        current_dir = Path(__file__).parent
        web_root = current_dir / "SimulatorViewer" 
        
        # 检查web目录是否存在
        if not web_root.exists():
            logger.error(f"错误: Web根目录不存在: {web_root}")
            return False
        
        logger.info(f"正在启动HTTP服务器 (端口: {8080})...")
        
        # 切换到web目录
        os.chdir(str(web_root))
        
        def run_server(port):
            try:
                with socketserver.TCPServer(("", port), DetailedHTTPRequestHandler) as httpd:
                    servers.append(httpd)
                    logger.info(f"HTTP服务器已启动: http://localhost:{port}")
                    logger.info(f"地图查看器地址: http://localhost:{port}/map_viewer.html")
                    httpd.serve_forever()
            except OSError as e:
                if e.errno == 10048:  # 端口被占用
                    logger.warning(f"端口 {port} 被占用，尝试使用其他端口...")
                    # 尝试其他端口
                    for new_port in range(8081, 8090):
                        try:
                            with socketserver.TCPServer(("", new_port), DetailedHTTPRequestHandler) as httpd:
                                servers.append(httpd)
                                logger.info(f"HTTP服务器已启动: http://localhost:{new_port}")
                                logger.info(f"地图查看器地址: http://localhost:{new_port}/map_viewer.html")
                                httpd.serve_forever()
                                break
                        except OSError:
                            continue
                    else:
                        logger.error("无法找到可用端口启动HTTP服务器")
                else:
                    logger.error(f"启动HTTP服务器失败: {e}")
            except Exception as e:
                logger.error(f"HTTP服务器运行时错误: {e}")
        
        # 在新线程中启动HTTP服务器
        server_thread = threading.Thread(target=run_server, args=(8080,), daemon=True)
        server_thread.start()
        
        # 等待一下让服务器启动
        time.sleep(1)
        return True
        
    except Exception as e:
        logger.error(f"启动HTTP服务器失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=== AGV仿真系统一键启动 ===")
    logger.info("")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 清理端口占用
    clear_port_usage([8001, 8080])
    
    success_count = 0
    
    # 1. 启动AGV仿真器
    logger.info("1. 启动AGV仿真器...")
    if start_agv_simulator():
        logger.info("   ✓ AGV仿真器启动成功")
        success_count += 1
    else:
        logger.error("   ✗ AGV仿真器启动失败")
    
    # 等待一下
    time.sleep(1)
    
    # 2. 启动地图编辑器API服务器
    logger.info("\n2. 启动地图编辑器API服务器...")
    if start_map_editor_api():
        logger.info("   ✓ API服务器启动成功")
        success_count += 1
    else:
        logger.error("   ✗ API服务器启动失败")
    
    # 等待一下
    time.sleep(1)
    
    # 3. 启动HTTP服务器
    logger.info("\n3. 启动HTTP服务器...")
    if start_http_server():
        logger.info("   ✓ HTTP服务器启动成功")
        success_count += 1
    else:
        logger.error("   ✗ HTTP服务器启动失败")
    
    # 显示启动结果
    logger.info(f"\n=== 启动完成 ({success_count}/3 个服务成功启动) ===")
    
    if success_count > 0:
        logger.info("\n服务地址:")
        if success_count >= 2:  # API服务器启动成功
            logger.info("  • API服务器: http://localhost:8001")
        if success_count >= 3:  # HTTP服务器启动成功
            logger.info("  • 地图查看器: http://localhost:8080/map_viewer.html")
        
        logger.info("\n按 Ctrl+C 停止所有服务")
        
        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
    else:
        logger.error("\n所有服务启动失败，程序退出")

if __name__ == "__main__":
    main()