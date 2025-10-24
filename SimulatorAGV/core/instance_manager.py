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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from SimulatorAGV.services.file_storage_manager import get_file_storage_manager
from SimulatorAGV.core.robot_factory import RobotFactory
from SimulatorAGV.instances.robot_instance import RobotInstance
from shared import setup_logger

logger = setup_logger()


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
            base_config_path: 基础配置文件路径 (已弃用，建议使用共享配置)
            registry_path: 机器人注册文件路径
        """
        logger.info(f"Debug InstanceManager init: base_config_path='{base_config_path}', registry_path='{registry_path}'")
        
        self.robots: Dict[str, RobotInstance] = {}
        
        # 尝试使用新的配置管理，如果失败则回退到原始方式
        try:
            from shared import get_config
            self.config = get_config()
            self.robot_factory = RobotFactory()  # 使用默认配置
        except Exception:
            # 回退到原始实现
            self.robot_factory = RobotFactory(base_config_path)
            self.config = None
            
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
            for serial_number, robot_instance in new_robots.items():
                if serial_number not in self.robots:
                    self.robots[serial_number] = robot_instance
                    logger.info(f"加载机器人实例: {serial_number}")
                else:
                    logger.warning(f"机器人实例已存在，跳过: {serial_number}")
        
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
            
            serial_number = robot_info["serialNumber"]
            
            with self._lock:
                # 检查是否已存在
                if serial_number in self.robots:
                    logger.warning(f"机器人实例已存在: {serial_number}")
                    return False
                
                # 创建机器人实例
                robot_instance = self.robot_factory.create_robot_instance(robot_info)
                if robot_instance:
                    self.robots[serial_number] = robot_instance
                    
                    # 如果管理器正在运行，立即启动新机器人
                    if self._running:
                        robot_instance.start()
                    
                    logger.info(f"成功添加机器人实例: {serial_number}")
                    return True
                else:
                    logger.error(f"创建机器人实例失败: {serial_number}")
                    return False
        
        except Exception as e:
            logger.error(f"添加机器人实例时出错: {e}")
            return False
    
    def remove_robot(self, serial_number: str) -> bool:
        """
        移除机器人实例
        
        Args:
            serial_number: 机器人序列号
            
        Returns:
            移除是否成功
        """
        try:
            with self._lock:
                if serial_number not in self.robots:
                    logger.warning(f"机器人实例不存在: {serial_number}")
                    return False
                
                # 停止机器人实例
                robot_instance = self.robots[serial_number]
                robot_instance.stop()
                
                # 从管理器中移除
                del self.robots[serial_number]
                
                # 删除对应的文件存储目录
                try:
                    storage = get_file_storage_manager()
                    storage.remove_robot_folder(serial_number)
                except Exception as e:
                    logger.error(f"删除机器人 {serial_number} 数据目录失败: {e}")
                
                logger.info(f"成功移除机器人实例: {serial_number}")
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
            for serial_number, robot_instance in self.robots.items():
                try:
                    robot_instance.start()
                    logger.info(f"机器人实例 {serial_number} 启动成功")
                except Exception as e:
                    logger.error(f"机器人实例 {serial_number} 启动失败: {e}")
            
            # 启动文件监控
            try:
                self._start_file_monitoring()
            except Exception as e:
                logger.error(f"启动文件监控失败: {e}")
            
            # 启动API服务器
            try:
                self.start_api_server()
            except Exception as e:
                logger.error(f"启动API服务器失败: {e}")
    
    def start_robot(self, serial_number: str) -> bool:
        """启动指定机器人实例"""
        try:
            with self._lock:
                if serial_number not in self.robots:
                    logger.warning(f"机器人实例不存在: {serial_number}")
                    return False
                
                robot_instance = self.robots[serial_number]
                robot_instance.start()
                logger.info(f"机器人实例 {serial_number} 启动成功")
                return True
        except Exception as e:
            logger.error(f"启动机器人实例失败: {e}")
            return False
    
    def stop_robot(self, serial_number: str) -> bool:
        """停止指定机器人实例"""
        try:
            with self._lock:
                if serial_number not in self.robots:
                    logger.warning(f"机器人实例不存在: {serial_number}")
                    return False
                
                robot_instance = self.robots[serial_number]
                robot_instance.stop()
                logger.info(f"机器人实例 {serial_number} 已停止")
                return True
        except Exception as e:
            logger.error(f"停止机器人实例失败: {e}")
            return False
    
    def stop_all(self):
        """停止所有机器人实例"""
        logger.info("正在停止所有机器人实例...")
        
        with self._lock:
            for serial_number, robot_instance in list(self.robots.items()):
                try:
                    robot_instance.stop()
                    logger.info(f"机器人实例 {serial_number} 已停止")
                except Exception as e:
                    logger.error(f"停止机器人实例 {serial_number} 失败: {e}")
            
            # 停止文件监控
            try:
                self._stop_file_monitoring()
            except Exception as e:
                logger.error(f"停止文件监控失败: {e}")
            
            # 停止API服务器
            try:
                self.stop_api_server()
            except Exception as e:
                logger.error(f"停止API服务器失败: {e}")
            
            self._running = False
    
    def restart_robot(self, serial_number: str) -> bool:
        """重启指定机器人实例"""
        try:
            with self._lock:
                if serial_number not in self.robots:
                    logger.warning(f"机器人实例不存在: {serial_number}")
                    return False
                
                robot_instance = self.robots[serial_number]
                robot_instance.stop()
                time.sleep(1)
                robot_instance.start()
                logger.info(f"机器人实例 {serial_number} 重启成功")
                return True
        except Exception as e:
            logger.error(f"重启机器人实例失败: {e}")
            return False
    
    def get_robot_status(self, serial_number: str = None) -> Dict[str, Any]:
        """获取机器人状态信息"""
        with self._lock:
            if serial_number:
                robot = self.robots.get(serial_number)
                if robot:
                    return robot.get_status()
                else:
                    return {
                        "error": "Robot not found",
                        "serial_number": serial_number
                    }
            else:
                status = {
                    "total_robots": len(self.robots),
                    "running_robots": sum(1 for r in self.robots.values() if r.is_alive()),
                    "manager_running": self._running,
                    "robots": {}
                }
                for sn, robot in self.robots.items():
                    status["robots"][sn] = robot.get_status()
                return status
    
    def get_robot_list(self) -> List[str]:
        """获取机器人列表"""
        with self._lock:
            return list(self.robots.keys())
    
    def get_robot_instance(self, serial_number: str) -> Optional[RobotInstance]:
        """获取机器人实例对象"""
        with self._lock:
            return self.robots.get(serial_number)
    
    def send_order_to_robot(self, serial_number: str, order_data: Dict[str, Any]) -> bool:
        """向指定机器人发送订单"""
        try:
            with self._lock:
                robot = self.robots.get(serial_number)
                if robot:
                    robot.send_order(order_data)
                    return True
                else:
                    logger.warning(f"机器人实例不存在: {serial_number}")
                    return False
        except Exception as e:
            logger.error(f"发送订单失败: {e}")
            return False
    
    def send_instant_action_to_robot(self, serial_number: str, action_data: Dict[str, Any]) -> bool:
        """向指定机器人发送即时动作"""
        try:
            with self._lock:
                robot = self.robots.get(serial_number)
                if robot:
                    robot.send_instant_action(action_data)
                    return True
                else:
                    logger.warning(f"机器人实例不存在: {serial_number}")
                    return False
        except Exception as e:
            logger.error(f"发送即时动作失败: {e}")
            return False
    
    def _monitor_robots(self):
        """监控机器人实例状态"""
        while self._running:
            try:
                with self._lock:
                    for serial_number, robot in list(self.robots.items()):
                        if not robot.is_alive():
                            logger.warning(f"检测到机器人实例不存活，尝试重启: {serial_number}")
                            try:
                                robot.start()
                                logger.info(f"机器人实例 {serial_number} 重启成功")
                            except Exception as e:
                                logger.error(f"机器人实例 {serial_number} 重启失败: {e}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"监控线程出错: {e}")
                time.sleep(5)
    
    def is_running(self) -> bool:
        """检查管理器是否正在运行"""
        return self._running
    
    def get_robot_count(self) -> int:
        """获取机器人数量"""
        with self._lock:
            return len(self.robots)
    
    def start_api_server(self):
        """启动状态API服务器"""
        try:
            server_address = ('', self.api_port)
            self.api_server = HTTPServer(server_address, lambda *args, **kwargs: StatusAPIHandler(*args, instance_manager=self, **kwargs))
            self.api_thread = threading.Thread(target=self.api_server.serve_forever, daemon=True)
            self.api_thread.start()
            logger.info(f"状态API服务器已启动，端口: {self.api_port}")
        except Exception as e:
            logger.error(f"启动状态API服务器失败: {e}")
    
    def stop_api_server(self):
        """停止状态API服务器"""
        try:
            if self.api_server:
                self.api_server.shutdown()
                self.api_server.server_close()
                self.api_server = None
                logger.info("状态API服务器已停止")
        except Exception as e:
            logger.error(f"停止状态API服务器失败: {e}")
    
    def _start_file_monitoring(self):
        """启动文件监控"""
        logger.info(f"Debug: registry_path = '{self.registry_path}'")
        logger.info(f"Debug: registry_path exists = {os.path.exists(self.registry_path) if self.registry_path else False}")
        
        # 检查registry_path是否为None或空字符串
        if not self.registry_path:
            logger.warning("注册文件路径为空，跳过文件监控")
            return
            
        # 检查文件是否存在
        if not os.path.exists(self.registry_path):
            logger.warning(f"注册文件不存在: {self.registry_path}，跳过文件监控")
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
        """重新加载注册文件中的机器人配置（仅热加载配置，不重新注册）"""
        try:
            logger.info("开始重新加载机器人注册文件配置...")
            
            if not self.registry_path or not os.path.exists(self.registry_path):
                logger.warning("注册文件不存在，跳过重新加载")
                return
            
            # 读取注册文件
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                robots_data = json.load(f)
            
            # 获取当前已存在的机器人ID
            existing_robot_ids = set(self.robots.keys())
            
            # 获取注册文件中的机器人serialNumber
            registry_robot_ids = set(robot_info.get('serialNumber') for robot_info in robots_data if robot_info.get('serialNumber'))
            
            # 找出已删除的机器人（从注册文件中移除的）
            removed_robot_ids = existing_robot_ids - registry_robot_ids
            
            # 只处理已删除的机器人，不自动添加新机器人
            for robot_id in removed_robot_ids:
                success = self.remove_robot(robot_id)
                if success:
                    logger.info(f"动态移除机器人: {robot_id}")
                else:
                    logger.error(f"动态移除机器人失败: {robot_id}")
            
            # 对于现有机器人，只更新配置（热加载）
            updated_count = 0
            for robot_info in robots_data:
                robot_id = robot_info.get('serialNumber')
                if robot_id in existing_robot_ids:
                    # 热加载配置
                    if self._hot_reload_robot_config(robot_id, robot_info):
                        updated_count += 1
            
            # 计算新增机器人并启动
            new_robot_ids = registry_robot_ids - existing_robot_ids
            added_count = 0
            for robot_info in robots_data:
                serial = robot_info.get('serialNumber')
                if serial and serial in new_robot_ids:
                    try:
                        if self.add_robot(robot_info):
                            added_count += 1
                            logger.info(f"动态添加并启动新机器人: {serial}")
                    except Exception as e:
                        logger.error(f"动态添加新机器人失败 {serial}: {e}")
            
            logger.info(f"机器人注册文件重新加载完成，移除: {len(removed_robot_ids)}, 新增: {added_count}, 配置更新: {updated_count}")
            if added_count > 0:
                logger.info(f"已自动启动{added_count}个新注册机器人")
            else:
                logger.info("未检测到新的机器人注册，仅对现有实例进行配置热加载")
            
        except Exception as e:
            logger.error(f"重新加载机器人注册文件失败: {e}")
    
    def _hot_reload_robot_config(self, robot_id: str, new_config: Dict[str, Any]) -> bool:
        """热加载机器人配置，不重启机器人实例"""
        try:
            if robot_id not in self.robots:
                return False
            
            robot_instance = self.robots[robot_id]
            
            # 更新机器人配置（这里可以根据需要实现具体的配置更新逻辑）
            # 例如更新MQTT配置、车辆信息等
            if hasattr(robot_instance, 'update_config'):
                robot_instance.update_config(new_config)
                logger.info(f"热加载机器人配置成功: {robot_id}")
                return True
            else:
                logger.warning(f"机器人实例不支持配置热加载: {robot_id}")
                return False
                
        except Exception as e:
            logger.error(f"热加载机器人配置失败 {robot_id}: {e}")
            return False


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