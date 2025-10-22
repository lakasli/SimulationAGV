import threading
import time
import signal
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.robot_factory import RobotFactory
from instances.robot_instance import RobotInstance
from logger_config import logger


class StatusAPIHandler(BaseHTTPRequestHandler):
    """状态API处理器"""
    
    def __init__(self, *args, instance_manager=None, **kwargs):
        self.instance_manager = instance_manager
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/api/status':
            try:
                status = self.instance_manager.get_robot_status()
                
                # 确保所有对象都能被正确序列化
                def serialize_object(obj):
                    if hasattr(obj, 'to_dict'):
                        return obj.to_dict()
                    elif hasattr(obj, '__dict__'):
                        return obj.__dict__
                    return obj
                
                # 递归处理状态数据中的所有对象
                def process_status_data(data):
                    if isinstance(data, dict):
                        result = {}
                        for key, value in data.items():
                            if key == 'position' and value is not None:
                                result[key] = serialize_object(value)
                            else:
                                result[key] = process_status_data(value)
                        return result
                    elif isinstance(data, list):
                        return [process_status_data(item) for item in data]
                    else:
                        return serialize_object(data) if hasattr(data, 'to_dict') or hasattr(data, '__dict__') else data
                
                processed_status = process_status_data(status)
                response = json.dumps(processed_status, ensure_ascii=False, indent=2)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Internal Server Error: {e}")
        else:
            self.send_error(404, "Not Found")
    
    def log_message(self, format, *args):
        """重写日志方法，使用项目的logger"""
        logger.info(f"[API] {format % args}")


class InstanceManager:
    """实例管理器，管理多个机器人实例的生命周期"""
    
    def __init__(self, base_config_path: str = "config.json", registry_path: str = None):
        """
        初始化实例管理器
        
        Args:
            base_config_path: 基础配置文件路径
            registry_path: 机器人注册文件路径
        """
        self.robots: Dict[str, RobotInstance] = {}
        self.robot_factory = RobotFactory(base_config_path)
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread = None
        self.base_config_path = base_config_path
        self.registry_path = registry_path
        
        # 文件监控相关
        self.file_observer = None
        self.registry_handler = None
        
        # HTTP API服务器
        self.api_server = None
        self.api_thread = None
        self.api_port = 8002  # 使用不同的端口避免冲突
        
        # 注册信号处理器（仅在主线程中）
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            logger.info("信号处理器注册成功")
        else:
            logger.info("非主线程环境，跳过信号处理器注册")
        
        logger.info("实例管理器初始化完成")
    
    def _signal_handler(self, signum, frame):
        """信号处理器，用于优雅关闭"""
        logger.info(f"接收到信号 {signum}，正在关闭所有机器人实例...")
        self.stop_all()
        sys.exit(0)
    
    def load_robots_from_registry(self) -> int:
        """
        从注册文件加载机器人实例
        
        Returns:
            成功加载的机器人数量
        """
        if not self.registry_path:
            logger.warning("未指定注册文件路径")
            return 0
        
        with self._lock:
            # 创建机器人实例
            new_robots = self.robot_factory.create_robots_from_registry(self.registry_path)
            
            # 添加到管理器中
            for robot_id, robot_instance in new_robots.items():
                if robot_id not in self.robots:
                    self.robots[robot_id] = robot_instance
                    logger.info(f"加载机器人实例: {robot_id}")
                else:
                    logger.warning(f"机器人实例已存在，跳过: {robot_id}")
        
        return len(new_robots)
    
    def add_robot(self, robot_info: Dict[str, Any]) -> bool:
        """
        添加单个机器人实例
        
        Args:
            robot_info: 机器人信息
            
        Returns:
            添加是否成功
        """
        try:
            # 验证机器人信息
            if not self.robot_factory.validate_robot_info(robot_info):
                return False
            
            robot_id = robot_info["id"]
            
            with self._lock:
                # 检查是否已存在
                if robot_id in self.robots:
                    logger.warning(f"机器人实例已存在: {robot_id}")
                    return False
                
                # 创建机器人实例
                robot_instance = self.robot_factory.create_robot_instance(robot_info)
                if robot_instance:
                    self.robots[robot_id] = robot_instance
                    
                    # 如果管理器正在运行，立即启动新机器人
                    if self._running:
                        robot_instance.start()
                    
                    logger.info(f"成功添加机器人实例: {robot_id}")
                    return True
                else:
                    logger.error(f"创建机器人实例失败: {robot_id}")
                    return False
        
        except Exception as e:
            logger.error(f"添加机器人实例时出错: {e}")
            return False
    
    def remove_robot(self, robot_id: str) -> bool:
        """
        移除机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            移除是否成功
        """
        try:
            with self._lock:
                if robot_id not in self.robots:
                    logger.warning(f"机器人实例不存在: {robot_id}")
                    return False
                
                # 停止机器人实例
                robot_instance = self.robots[robot_id]
                robot_instance.stop()
                
                # 从管理器中移除
                del self.robots[robot_id]
                
                logger.info(f"成功移除机器人实例: {robot_id}")
                return True
        
        except Exception as e:
            logger.error(f"移除机器人实例时出错: {e}")
            return False
    
    def start_all(self):
        """启动所有机器人实例"""
        logger.info("正在启动所有机器人实例...")
        
        with self._lock:
            self._running = True
            
            # 启动所有机器人实例
            for robot_id, robot_instance in self.robots.items():
                try:
                    robot_instance.start()
                    logger.info(f"机器人实例 {robot_id} 启动成功")
                except Exception as e:
                    logger.error(f"启动机器人实例 {robot_id} 失败: {e}")
            
            # 启动监控线程
            if self._monitor_thread is None or not self._monitor_thread.is_alive():
                self._monitor_thread = threading.Thread(target=self._monitor_robots, daemon=True)
                self._monitor_thread.start()
                logger.info("机器人监控线程已启动")
            
            # 启动文件监控
            self._start_file_monitoring()
            
            # 启动API服务器
            self.start_api_server()
        
        logger.info(f"所有机器人实例启动完成，共 {len(self.robots)} 个实例")
    
    def start_robot(self, robot_id: str) -> bool:
        """
        启动指定的机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            启动是否成功
        """
        try:
            with self._lock:
                if robot_id not in self.robots:
                    logger.warning(f"机器人实例不存在: {robot_id}")
                    return False
                
                robot_instance = self.robots[robot_id]
                
                # 启动机器人实例
                robot_instance.start()
                
                logger.info(f"成功启动机器人实例: {robot_id}")
                return True
        
        except Exception as e:
            logger.error(f"启动机器人实例时出错: {e}")
            return False
    
    def stop_robot(self, robot_id: str) -> bool:
        """
        停止指定的机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            停止是否成功
        """
        try:
            with self._lock:
                if robot_id not in self.robots:
                    logger.warning(f"机器人实例不存在: {robot_id}")
                    return False
                
                robot_instance = self.robots[robot_id]
                
                # 停止机器人实例
                robot_instance.stop()
                
                logger.info(f"成功停止机器人实例: {robot_id}")
                return True
        
        except Exception as e:
            logger.error(f"停止机器人实例时出错: {e}")
            return False

    def stop_all(self):
        """停止所有机器人实例"""
        logger.info("正在停止所有机器人实例...")
        
        with self._lock:
            self._running = False
            
            # 停止文件监控
            self._stop_file_monitoring()
            
            # 停止API服务器
            self.stop_api_server()
            
            # 停止所有机器人实例
            for robot_id, robot_instance in self.robots.items():
                try:
                    robot_instance.stop()
                    logger.info(f"机器人实例 {robot_id} 停止成功")
                except Exception as e:
                    logger.error(f"停止机器人实例 {robot_id} 失败: {e}")
        
        logger.info("所有机器人实例停止完成")
    
    def restart_robot(self, robot_id: str) -> bool:
        """
        重启指定的机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            重启是否成功
        """
        try:
            with self._lock:
                if robot_id not in self.robots:
                    logger.warning(f"机器人实例不存在: {robot_id}")
                    return False
                
                robot_instance = self.robots[robot_id]
                
                # 停止机器人实例
                robot_instance.stop()
                
                # 等待一段时间
                time.sleep(1)
                
                # 重新启动
                robot_instance.start()
                
                logger.info(f"成功重启机器人实例: {robot_id}")
                return True
        
        except Exception as e:
            logger.error(f"重启机器人实例时出错: {e}")
            return False
    
    def get_robot_status(self, robot_id: str = None) -> Dict[str, Any]:
        """
        获取机器人状态信息
        
        Args:
            robot_id: 机器人ID，如果为None则返回所有机器人状态
            
        Returns:
            机器人状态信息
        """
        with self._lock:
            if robot_id:
                if robot_id in self.robots:
                    return self.robots[robot_id].get_status()
                else:
                    return {"error": f"机器人实例不存在: {robot_id}"}
            else:
                # 返回所有机器人状态
                status = {
                    "total_robots": len(self.robots),
                    "running_robots": sum(1 for r in self.robots.values() if r.is_alive()),
                    "manager_running": self._running,
                    "robots": {}
                }
                
                for rid, robot_instance in self.robots.items():
                    status["robots"][rid] = robot_instance.get_status()
                
                return status
    
    def get_robot_list(self) -> List[str]:
        """获取所有机器人ID列表"""
        with self._lock:
            return list(self.robots.keys())
    
    def get_robot_instance(self, robot_id: str) -> Optional[RobotInstance]:
        """
        获取机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            机器人实例，如果不存在返回None
        """
        with self._lock:
            return self.robots.get(robot_id)
    
    def send_order_to_robot(self, robot_id: str, order_data: Dict[str, Any]) -> bool:
        """
        向指定机器人发送订单
        
        Args:
            robot_id: 机器人ID
            order_data: 订单数据
            
        Returns:
            发送是否成功
        """
        robot_instance = self.get_robot_instance(robot_id)
        if robot_instance:
            robot_instance.send_order(order_data)
            return True
        else:
            logger.warning(f"机器人实例不存在: {robot_id}")
            return False
    
    def send_instant_action_to_robot(self, robot_id: str, action_data: Dict[str, Any]) -> bool:
        """
        向指定机器人发送即时动作
        
        Args:
            robot_id: 机器人ID
            action_data: 动作数据
            
        Returns:
            发送是否成功
        """
        robot_instance = self.get_robot_instance(robot_id)
        if robot_instance:
            robot_instance.send_instant_action(action_data)
            return True
        else:
            logger.warning(f"机器人实例不存在: {robot_id}")
            return False
    
    def _monitor_robots(self):
        """监控机器人实例状态"""
        logger.info("启动机器人监控线程")
        
        while self._running:
            try:
                with self._lock:
                    dead_robots = []
                    
                    # 检查每个机器人实例的状态
                    for robot_id, robot_instance in self.robots.items():
                        if not robot_instance.is_alive():
                            dead_robots.append(robot_id)
                    
                    # 记录死亡的机器人实例
                    for robot_id in dead_robots:
                        logger.warning(f"检测到机器人实例异常停止: {robot_id}")
                
                # 等待一段时间再次检查
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"监控机器人实例时出错: {e}")
                time.sleep(5)
        
        logger.info("机器人监控线程已停止")
    
    def is_running(self) -> bool:
         """检查管理器是否正在运行"""
         return self._running
    
    def get_robot_count(self) -> int:
        """获取机器人实例数量"""
        with self._lock:
            return len(self.robots)

    def start_api_server(self):
        """启动API服务器"""
        if self.api_server is not None:
            return
        
        try:
            def create_handler(*args, **kwargs):
                return StatusAPIHandler(*args, instance_manager=self, **kwargs)
            
            self.api_server = HTTPServer(('localhost', self.api_port), create_handler)
            
            def run_server():
                logger.info(f"状态API服务器启动在 http://localhost:{self.api_port}")
                self.api_server.serve_forever()
            
            self.api_thread = threading.Thread(target=run_server, daemon=True)
            self.api_thread.start()
            
            logger.info(f"API服务器已启动，端口: {self.api_port}")
        except Exception as e:
            logger.error(f"启动API服务器失败: {e}")
    
    def stop_api_server(self):
        """停止API服务器"""
        if self.api_server:
            try:
                self.api_server.shutdown()
                self.api_server.server_close()
                self.api_server = None
                logger.info("API服务器已停止")
            except Exception as e:
                logger.error(f"停止API服务器失败: {e}")


    def _start_file_monitoring(self):
        """启动文件监控"""
        if not self.registry_path or not os.path.exists(self.registry_path):
            logger.warning("注册文件路径无效，跳过文件监控")
            return
        
        try:
            # 创建文件监控处理器
            self.registry_handler = RobotRegistryHandler(self)
            
            # 创建观察者
            self.file_observer = Observer()
            
            # 监控注册文件所在的目录
            registry_dir = os.path.dirname(os.path.abspath(self.registry_path))
            self.file_observer.schedule(self.registry_handler, registry_dir, recursive=False)
            
            # 启动观察者
            self.file_observer.start()
            
            logger.info(f"文件监控已启动，监控目录: {registry_dir}")
            
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}")
    
    def _stop_file_monitoring(self):
        """停止文件监控"""
        if self.file_observer:
            try:
                self.file_observer.stop()
                self.file_observer.join()
                self.file_observer = None
                self.registry_handler = None
                logger.info("文件监控已停止")
            except Exception as e:
                logger.error(f"停止文件监控失败: {e}")
    
    def _reload_robots_from_registry(self):
        """重新加载注册文件中的机器人"""
        try:
            logger.info("开始重新加载机器人注册文件...")
            
            if not self.registry_path or not os.path.exists(self.registry_path):
                logger.warning("注册文件不存在，跳过重新加载")
                return
            
            # 读取注册文件
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                robots_data = json.load(f)
            
            # 获取当前已存在的机器人ID
            existing_robot_ids = set(self.robots.keys())
            
            # 获取注册文件中的机器人ID
            registry_robot_ids = set(robot_info.get('id') for robot_info in robots_data if robot_info.get('id'))
            
            # 找出新增的机器人
            new_robot_ids = registry_robot_ids - existing_robot_ids
            
            # 找出已删除的机器人
            removed_robot_ids = existing_robot_ids - registry_robot_ids
            
            # 处理新增的机器人
            for robot_info in robots_data:
                robot_id = robot_info.get('id')
                if robot_id in new_robot_ids:
                    success = self.add_robot(robot_info)
                    if success:
                        logger.info(f"动态添加新机器人: {robot_id}")
                    else:
                        logger.error(f"动态添加机器人失败: {robot_id}")
            
            # 处理已删除的机器人
            for robot_id in removed_robot_ids:
                success = self.remove_robot(robot_id)
                if success:
                    logger.info(f"动态移除机器人: {robot_id}")
                else:
                    logger.error(f"动态移除机器人失败: {robot_id}")
            
            logger.info(f"机器人注册文件重新加载完成，新增: {len(new_robot_ids)}, 移除: {len(removed_robot_ids)}")
            
        except Exception as e:
            logger.error(f"重新加载机器人注册文件失败: {e}")


class RobotRegistryHandler(FileSystemEventHandler):
    """机器人注册文件监控处理器"""
    
    def __init__(self, instance_manager):
        super().__init__()
        self.instance_manager = instance_manager
        self.last_modified = 0
        
    def on_modified(self, event):
        """文件修改时的处理"""
        if event.is_directory:
            return
            
        # 检查是否是注册文件
        if event.src_path.endswith('registered_robots.json'):
            # 防止重复触发
            current_time = time.time()
            if current_time - self.last_modified < 1:  # 1秒内的重复事件忽略
                return
            self.last_modified = current_time
            
            logger.info(f"检测到注册文件变更: {event.src_path}")
            # 延迟一点时间确保文件写入完成
            threading.Timer(0.5, self.instance_manager._reload_robots_from_registry).start()