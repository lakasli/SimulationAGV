"""
机器人实例服务
负责管理机器人实例的生命周期，包括启动、停止、状态监控等
"""

import os
import sys
import threading
import time
import subprocess
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# 添加SimulatorAGV路径到系统路径
simulator_agv_parent_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.append(os.path.abspath(simulator_agv_parent_path))

try:
    # 尝试从 SimulatorAGV 的 core 模块导入 InstanceManager，若失败则留空
    from SimulatorAGV.core.instance_manager import InstanceManager
    from SimulatorAGV.core.robot_factory import RobotFactory
except ImportError as e:
    logging.warning(f"无法导入SimulatorAGV模块: {e}")
    InstanceManager = None
    RobotFactory = None

logger = logging.getLogger(__name__)


# 全局实例管理器，确保所有服务实例共享同一个管理器
_global_instance_manager = None
_global_manager_lock = threading.Lock()

def get_global_instance_manager():
    """获取全局实例管理器"""
    global _global_instance_manager
    with _global_manager_lock:
        if _global_instance_manager is None and InstanceManager is not None:
            try:
                # 获取正确的配置和注册文件路径
                current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                simulator_agv_dir = os.path.join(current_dir, 'SimulatorAGV')
                config_path = os.path.join(simulator_agv_dir, 'config.json')
                registry_path = os.path.join(simulator_agv_dir, 'registered_robots.json')
                
                _global_instance_manager = InstanceManager(config_path, registry_path)
                # 启动全局实例管理器
                _global_instance_manager.start_all()
                logger.info("全局实例管理器初始化并启动成功")
            except Exception as e:
                logger.error(f"全局实例管理器初始化失败: {e}")
                _global_instance_manager = None
        return _global_instance_manager

class RobotInstanceService:
    """机器人实例服务"""
    
    def __init__(self):
        """初始化机器人实例服务"""
        self.running_instances: Dict[str, Dict[str, Any]] = {}
        self.instance_processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self.backend_api_url = "http://localhost:8002/api/status"  # 后端API地址
        
        # 使用全局实例管理器
        self.use_internal_manager = InstanceManager is not None
        if self.use_internal_manager:
            self.instance_manager = get_global_instance_manager()
            if self.instance_manager:
                logger.info("使用全局内置实例管理器")
            else:
                logger.warning("全局实例管理器不可用，回退到外部进程管理器")
                self.use_internal_manager = False
        
        if not self.use_internal_manager:
            logger.info("使用外部进程管理器")
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_instances, daemon=True)
        self.monitor_thread.start()
    
    def start_robot_instance(self, robot_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        启动机器人实例
        
        Args:
            robot_info: 机器人信息
            
        Returns:
            启动结果
        """
        robot_id = robot_info.get('id')
        if not robot_id:
            return {"success": False, "message": "机器人ID不能为空"}
        
        with self._lock:
            # 检查是否已经在运行
            if robot_id in self.running_instances:
                return {"success": False, "message": f"机器人实例 {robot_id} 已在运行"}
            
            try:
                if self.use_internal_manager:
                    # 使用内置实例管理器
                    success = self._start_with_internal_manager(robot_info)
                else:
                    # 使用外部进程
                    success = self._start_with_external_process(robot_info)
                
                if success:
                    self.running_instances[robot_id] = {
                        "robot_info": robot_info,
                        "start_time": datetime.now().isoformat(),
                        "status": "starting",
                        "pid": self.instance_processes.get(robot_id, {}).get("pid") if not self.use_internal_manager else None
                    }
                    
                    logger.info(f"机器人实例 {robot_id} 启动成功")
                    return {"success": True, "message": f"机器人实例 {robot_id} 启动成功"}
                else:
                    return {"success": False, "message": f"机器人实例 {robot_id} 启动失败"}
                    
            except Exception as e:
                logger.error(f"启动机器人实例 {robot_id} 时出错: {e}")
                return {"success": False, "message": f"启动失败: {str(e)}"}
    
    def stop_robot_instance(self, robot_id: str) -> Dict[str, Any]:
        """
        停止机器人实例
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            停止结果
        """
        with self._lock:
            if robot_id not in self.running_instances:
                return {"success": False, "message": f"机器人实例 {robot_id} 未在运行"}
            
            try:
                if self.use_internal_manager:
                    # 使用内置实例管理器
                    success = self._stop_with_internal_manager(robot_id)
                else:
                    # 停止外部进程
                    success = self._stop_external_process(robot_id)
                
                if success:
                    # 从运行实例中移除
                    del self.running_instances[robot_id]
                    if robot_id in self.instance_processes:
                        del self.instance_processes[robot_id]
                    
                    logger.info(f"机器人实例 {robot_id} 停止成功")
                    return {"success": True, "message": f"机器人实例 {robot_id} 停止成功"}
                else:
                    return {"success": False, "message": f"机器人实例 {robot_id} 停止失败"}
                    
            except Exception as e:
                logger.error(f"停止机器人实例 {robot_id} 时出错: {e}")
                return {"success": False, "message": f"停止失败: {str(e)}"}
    
    def get_instance_status(self, robot_id: str = None) -> Dict[str, Any]:
        """
        获取机器人实例状态
        
        Args:
            robot_id: 机器人ID，如果为None则返回所有机器人状态
            
        Returns:
            机器人状态信息
        """
        # 首先尝试从后端API获取状态
        try:
            response = requests.get(self.backend_api_url, timeout=2)
            if response.status_code == 200:
                backend_status = response.json()
                
                # 转换后端状态格式为前端格式
                if robot_id:
                    # 返回单个机器人状态
                    if robot_id in backend_status.get("robots", {}):
                        robot_status = backend_status["robots"][robot_id]
                        return {
                            "total_instances": 1,
                            "instances": [robot_status]
                        }
                    else:
                        return {
                            "total_instances": 0,
                            "instances": []
                        }
                else:
                    # 返回所有机器人状态
                    instances = []
                    for rid, robot_status in backend_status.get("robots", {}).items():
                        instances.append(robot_status)
                    
                    return {
                        "total_instances": len(instances),
                        "instances": instances
                    }
        except Exception as e:
            logger.warning(f"无法连接到后端API: {e}")
        
        # 回退到内置管理器
        if self.use_internal_manager and self.instance_manager:
            try:
                status = self.instance_manager.get_robot_status(robot_id)
                
                if robot_id:
                    # 返回单个机器人状态
                    if "error" not in status:
                        return {
                            "total_instances": 1,
                            "instances": [status]
                        }
                    else:
                        return {
                            "total_instances": 0,
                            "instances": []
                        }
                else:
                    # 返回所有机器人状态
                    instances = []
                    for robot_status in status.get("robots", {}).values():
                        instances.append(robot_status)
                    
                    return {
                        "total_instances": len(instances),
                        "instances": instances
                    }
            except Exception as e:
                logger.error(f"从内置管理器获取状态失败: {e}")
        
        # 最后回退到本地状态管理
        with self._lock:
            if robot_id:
                # 返回单个机器人状态
                if robot_id in self.running_instances:
                    return {
                        "total_instances": 1,
                        "instances": [self.running_instances[robot_id]]
                    }
                else:
                    return {
                        "total_instances": 0,
                        "instances": []
                    }
            else:
                # 返回所有机器人状态
                instances = list(self.running_instances.values())
                return {
                    "total_instances": len(instances),
                    "instances": instances
                }
    
    def get_all_instances_status(self) -> Dict[str, Any]:
        """
        获取所有机器人实例状态
        
        Returns:
            所有实例状态信息
        """
        return self.get_instance_status()
    
    def _start_with_internal_manager(self, robot_info: Dict[str, Any]) -> bool:
        """使用内置实例管理器启动机器人"""
        try:
            # 添加机器人到实例管理器
            success = self.instance_manager.add_robot(robot_info)
            if success:
                # 启动机器人
                return self.instance_manager.start_robot(robot_info['id'])
            return False
        except Exception as e:
            logger.error(f"内置管理器启动机器人失败: {e}")
            return False
    
    def _stop_with_internal_manager(self, robot_id: str) -> bool:
        """使用内置实例管理器停止机器人"""
        try:
            return self.instance_manager.stop_robot(robot_id)
        except Exception as e:
            logger.error(f"内置管理器停止机器人失败: {e}")
            return False
    
    def _start_with_external_process(self, robot_info: Dict[str, Any]) -> bool:
        """使用外部进程启动机器人"""
        try:
            robot_id = robot_info['id']
            
            # 创建临时配置文件
            temp_config_path = self._create_temp_config(robot_info)
            
            # 构建启动命令
            simulator_agv_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', '..', '..', 'SimulatorAGV'
            ))
            
            cmd = [
                sys.executable,
                os.path.join(simulator_agv_path, 'main.py'),
                '--single', robot_id,
                '--registry', temp_config_path
            ]
            
            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=simulator_agv_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.instance_processes[robot_id] = {
                "process": process,
                "pid": process.pid,
                "config_path": temp_config_path
            }
            
            logger.info(f"启动外部进程 PID: {process.pid} for robot {robot_id}")
            return True
            
        except Exception as e:
            logger.error(f"外部进程启动失败: {e}")
            return False
    
    def _stop_external_process(self, robot_id: str) -> bool:
        """停止外部进程"""
        try:
            if robot_id not in self.instance_processes:
                return False
            
            process_info = self.instance_processes[robot_id]
            process = process_info["process"]
            
            # 终止进程
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # 强制杀死进程
                process.kill()
                process.wait()
            
            # 清理临时配置文件
            config_path = process_info.get("config_path")
            if config_path and os.path.exists(config_path):
                os.remove(config_path)
            
            return True
            
        except Exception as e:
            logger.error(f"停止外部进程失败: {e}")
            return False
    
    def _create_temp_config(self, robot_info: Dict[str, Any]) -> str:
        """创建临时配置文件"""
        temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_config_path = os.path.join(temp_dir, f"robot_{robot_info['id']}_config.json")
        
        # 创建机器人配置
        config_data = [robot_info]
        
        with open(temp_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        return temp_config_path
    
    def _monitor_instances(self):
        """监控机器人实例状态"""
        while True:
            try:
                with self._lock:
                    dead_instances = []
                    
                    for robot_id, instance_info in self.running_instances.items():
                        if self.use_internal_manager:
                            # 检查内置管理器中的实例状态
                            if hasattr(self.instance_manager, 'get_robot_status'):
                                status = self.instance_manager.get_robot_status(robot_id)
                                if status and status.get('status') == 'offline':
                                    dead_instances.append(robot_id)
                                elif status:
                                    instance_info['status'] = status.get('status', 'unknown')
                        else:
                            # 检查外部进程状态
                            if robot_id in self.instance_processes:
                                process = self.instance_processes[robot_id]["process"]
                                if process.poll() is not None:
                                    dead_instances.append(robot_id)
                                else:
                                    instance_info['status'] = 'running'
                    
                    # 清理死亡的实例
                    for robot_id in dead_instances:
                        logger.warning(f"检测到机器人实例异常停止: {robot_id}")
                        if robot_id in self.running_instances:
                            del self.running_instances[robot_id]
                        if robot_id in self.instance_processes:
                            # 清理临时配置文件
                            config_path = self.instance_processes[robot_id].get("config_path")
                            if config_path and os.path.exists(config_path):
                                try:
                                    os.remove(config_path)
                                except:
                                    pass
                            del self.instance_processes[robot_id]
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"监控实例时出错: {e}")
                time.sleep(10)
    
    def cleanup(self):
        """清理所有运行的实例"""
        logger.info("清理所有机器人实例...")
        
        with self._lock:
            # 停止所有实例
            for robot_id in list(self.running_instances.keys()):
                try:
                    self.stop_robot_instance(robot_id)
                except Exception as e:
                    logger.error(f"清理实例 {robot_id} 时出错: {e}")
        
        logger.info("机器人实例清理完成")