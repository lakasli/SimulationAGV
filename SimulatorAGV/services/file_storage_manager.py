"""
文件存储管理器 - 替代Redis存储
用于存储机器人的MQTT数据到文件系统
"""

import os
import json
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared import setup_logger

logger = setup_logger()


class FileStorageManager:
    """文件存储管理器"""
    
    def __init__(self, base_path: str = "robot_data"):
        """
        初始化文件存储管理器
        
        Args:
            base_path: 基础存储路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self._locks = {}  # 为每个机器人创建独立的锁
        self._global_lock = threading.Lock()
        
        logger.info(f"文件存储管理器初始化完成，存储路径: {self.base_path.absolute()}")
    
    def _get_robot_lock(self, robot_id: str) -> threading.Lock:
        """获取机器人专用的锁"""
        with self._global_lock:
            if robot_id not in self._locks:
                self._locks[robot_id] = threading.Lock()
            return self._locks[robot_id]
    
    def create_robot_folder(self, robot_id: str) -> str:
        """
        为机器人创建存储文件夹
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            机器人文件夹路径
        """
        robot_path = self.base_path / robot_id
        robot_path.mkdir(exist_ok=True)
        
        # 创建子文件夹
        (robot_path / "state").mkdir(exist_ok=True)
        (robot_path / "connection").mkdir(exist_ok=True)
        (robot_path / "visualization").mkdir(exist_ok=True)
        (robot_path / "orders").mkdir(exist_ok=True)
        (robot_path / "instant_actions").mkdir(exist_ok=True)
        (robot_path / "history").mkdir(exist_ok=True)
        
        logger.info(f"为机器人 {robot_id} 创建存储文件夹: {robot_path}")
        return str(robot_path)
    
    def remove_robot_folder(self, robot_id: str) -> bool:
        """
        删除机器人存储文件夹
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            删除是否成功
        """
        try:
            robot_path = self.base_path / robot_id
            if robot_path.exists():
                import shutil
                shutil.rmtree(robot_path)
                logger.info(f"删除机器人 {robot_id} 存储文件夹成功")
                
                # 清理锁
                with self._global_lock:
                    if robot_id in self._locks:
                        del self._locks[robot_id]
                
                return True
            return False
        except Exception as e:
            logger.error(f"删除机器人 {robot_id} 存储文件夹失败: {e}")
            return False
    
    def save_state(self, robot_id: str, state_data: Dict[str, Any]) -> bool:
        """
        保存机器人状态数据
        
        Args:
            robot_id: 机器人ID
            state_data: 状态数据
            
        Returns:
            保存是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                robot_path = self.base_path / robot_id
                if not robot_path.exists():
                    self.create_robot_folder(robot_id)
                
                state_file = robot_path / "state" / "current_state.json"
                
                # 添加时间戳
                state_data["timestamp"] = datetime.now().isoformat()
                
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.error(f"保存机器人 {robot_id} 状态失败: {e}")
            return False
    
    def get_state(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人状态数据
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            状态数据
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                state_file = self.base_path / robot_id / "state" / "current_state.json"
                
                if not state_file.exists():
                    return None
                
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 状态失败: {e}")
            return None
    
    def save_connection(self, robot_id: str, connection_data: Dict[str, Any]) -> bool:
        """
        保存机器人连接数据
        
        Args:
            robot_id: 机器人ID
            connection_data: 连接数据
            
        Returns:
            保存是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                robot_path = self.base_path / robot_id
                if not robot_path.exists():
                    self.create_robot_folder(robot_id)
                
                connection_file = robot_path / "connection" / "current_connection.json"
                
                # 添加时间戳
                connection_data["timestamp"] = datetime.now().isoformat()
                
                with open(connection_file, 'w', encoding='utf-8') as f:
                    json.dump(connection_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.error(f"保存机器人 {robot_id} 连接数据失败: {e}")
            return False
    
    def get_connection(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人连接数据
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            连接数据
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                connection_file = self.base_path / robot_id / "connection" / "current_connection.json"
                
                if not connection_file.exists():
                    return None
                
                with open(connection_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 连接数据失败: {e}")
            return None
    
    def save_visualization(self, robot_id: str, visualization_data: Dict[str, Any]) -> bool:
        """
        保存机器人可视化数据
        
        Args:
            robot_id: 机器人ID
            visualization_data: 可视化数据
            
        Returns:
            保存是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                robot_path = self.base_path / robot_id
                if not robot_path.exists():
                    self.create_robot_folder(robot_id)
                
                visualization_file = robot_path / "visualization" / "current_visualization.json"
                
                # 添加时间戳
                visualization_data["timestamp"] = datetime.now().isoformat()
                
                with open(visualization_file, 'w', encoding='utf-8') as f:
                    json.dump(visualization_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.error(f"保存机器人 {robot_id} 可视化数据失败: {e}")
            return False
    
    def get_visualization(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人可视化数据
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            可视化数据
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                visualization_file = self.base_path / robot_id / "visualization" / "current_visualization.json"
                
                if not visualization_file.exists():
                    return None
                
                with open(visualization_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 可视化数据失败: {e}")
            return None
    
    def save_order(self, robot_id: str, order_id: str, order_data: Dict[str, Any]) -> bool:
        """
        保存机器人订单数据
        
        Args:
            robot_id: 机器人ID
            order_id: 订单ID
            order_data: 订单数据
            
        Returns:
            保存是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                robot_path = self.base_path / robot_id
                if not robot_path.exists():
                    self.create_robot_folder(robot_id)
                
                order_file = robot_path / "orders" / f"{order_id}.json"
                
                # 添加时间戳
                order_data["timestamp"] = datetime.now().isoformat()
                order_data["order_id"] = order_id
                
                with open(order_file, 'w', encoding='utf-8') as f:
                    json.dump(order_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.error(f"保存机器人 {robot_id} 订单 {order_id} 失败: {e}")
            return False
    
    def get_order(self, robot_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人订单数据
        
        Args:
            robot_id: 机器人ID
            order_id: 订单ID
            
        Returns:
            订单数据
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                order_file = self.base_path / robot_id / "orders" / f"{order_id}.json"
                
                if not order_file.exists():
                    return None
                
                with open(order_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 订单 {order_id} 失败: {e}")
            return None
    
    def get_all_orders(self, robot_id: str) -> List[Dict[str, Any]]:
        """
        获取机器人所有订单数据
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            订单数据列表
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                orders_path = self.base_path / robot_id / "orders"
                
                if not orders_path.exists():
                    return []
                
                orders = []
                for order_file in orders_path.glob("*.json"):
                    try:
                        with open(order_file, 'r', encoding='utf-8') as f:
                            order_data = json.load(f)
                            orders.append(order_data)
                    except Exception as e:
                        logger.warning(f"读取订单文件 {order_file} 失败: {e}")
                
                # 按时间戳排序
                orders.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                return orders
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 所有订单失败: {e}")
            return []
    
    def delete_order(self, robot_id: str, order_id: str) -> bool:
        """
        删除机器人订单数据
        
        Args:
            robot_id: 机器人ID
            order_id: 订单ID
            
        Returns:
            删除是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                order_file = self.base_path / robot_id / "orders" / f"{order_id}.json"
                
                if order_file.exists():
                    order_file.unlink()
                    return True
                return False
        except Exception as e:
            logger.error(f"删除机器人 {robot_id} 订单 {order_id} 失败: {e}")
            return False
    
    def save_instant_action(self, robot_id: str, action_id: str, action_data: Dict[str, Any]) -> bool:
        """
        保存机器人即时动作数据
        
        Args:
            robot_id: 机器人ID
            action_id: 动作ID
            action_data: 动作数据
            
        Returns:
            保存是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                robot_path = self.base_path / robot_id
                if not robot_path.exists():
                    self.create_robot_folder(robot_id)
                
                action_file = robot_path / "instant_actions" / f"{action_id}.json"
                
                # 添加时间戳
                action_data["timestamp"] = datetime.now().isoformat()
                action_data["action_id"] = action_id
                
                with open(action_file, 'w', encoding='utf-8') as f:
                    json.dump(action_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.error(f"保存机器人 {robot_id} 即时动作 {action_id} 失败: {e}")
            return False
    
    def get_instant_action(self, robot_id: str, action_id: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人即时动作数据
        
        Args:
            robot_id: 机器人ID
            action_id: 动作ID
            
        Returns:
            动作数据
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                action_file = self.base_path / robot_id / "instant_actions" / f"{action_id}.json"
                
                if not action_file.exists():
                    return None
                
                with open(action_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 即时动作 {action_id} 失败: {e}")
            return None
    
    def add_history_entry(self, robot_id: str, entry_data: Dict[str, Any], max_history: int = 100) -> bool:
        """
        添加历史记录条目
        
        Args:
            robot_id: 机器人ID
            entry_data: 历史记录数据
            max_history: 最大历史记录数量
            
        Returns:
            添加是否成功
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                robot_path = self.base_path / robot_id
                if not robot_path.exists():
                    self.create_robot_folder(robot_id)
                
                history_file = robot_path / "history" / "history.json"
                
                # 读取现有历史记录
                history_list = []
                if history_file.exists():
                    try:
                        with open(history_file, 'r', encoding='utf-8') as f:
                            history_list = json.load(f)
                    except:
                        history_list = []
                
                # 添加新记录
                entry_data["timestamp"] = datetime.now().isoformat()
                history_list.insert(0, entry_data)  # 插入到开头
                
                # 限制历史记录数量
                if len(history_list) > max_history:
                    history_list = history_list[:max_history]
                
                # 保存历史记录
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(history_list, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.error(f"添加机器人 {robot_id} 历史记录失败: {e}")
            return False
    
    def get_history(self, robot_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取机器人历史记录
        
        Args:
            robot_id: 机器人ID
            limit: 限制返回数量
            
        Returns:
            历史记录列表
        """
        try:
            lock = self._get_robot_lock(robot_id)
            with lock:
                history_file = self.base_path / robot_id / "history" / "history.json"
                
                if not history_file.exists():
                    return []
                
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_list = json.load(f)
                
                return history_list[:limit]
        except Exception as e:
            logger.error(f"获取机器人 {robot_id} 历史记录失败: {e}")
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            存储统计信息
        """
        try:
            stats = {
                "total_robots": 0,
                "total_files": 0,
                "storage_size": 0,
                "robots": {}
            }
            
            for robot_path in self.base_path.iterdir():
                if robot_path.is_dir():
                    robot_id = robot_path.name
                    stats["total_robots"] += 1
                    
                    robot_stats = {
                        "files": 0,
                        "size": 0
                    }
                    
                    for file_path in robot_path.rglob("*.json"):
                        robot_stats["files"] += 1
                        robot_stats["size"] += file_path.stat().st_size
                    
                    stats["robots"][robot_id] = robot_stats
                    stats["total_files"] += robot_stats["files"]
                    stats["storage_size"] += robot_stats["size"]
            
            return stats
        except Exception as e:
            logger.error(f"获取存储统计信息失败: {e}")
            return {}


# 全局文件存储管理器实例
_file_storage_manager = None


def get_file_storage_manager() -> FileStorageManager:
    """获取全局文件存储管理器实例"""
    global _file_storage_manager
    if _file_storage_manager is None:
        _file_storage_manager = FileStorageManager()
    return _file_storage_manager