"""
机器人管理服务
"""
import json
import uuid
import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

# 添加父目录到路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from models.robot_models import RobotInfo, RobotGroup, RobotLabel, RobotStatus, RobotType


class RobotService:
    """机器人管理服务"""
    
    def __init__(self):
        self.robots: Dict[str, RobotInfo] = {}
        self.robot_groups: Dict[str, RobotGroup] = {}
        self.robot_labels: Dict[str, RobotLabel] = {}
    
    def load_initial_data(self, groups: Optional[List[RobotGroup]] = None, 
                         robots: Optional[List[RobotInfo]] = None,
                         labels: Optional[List[RobotLabel]] = None) -> None:
        """加载初始数据"""
        self.robots.clear()
        self.robot_groups.clear()
        self.robot_labels.clear()
        
        if robots:
            for robot in robots:
                self.robots[robot.id] = robot
        
        if groups:
            for group in groups:
                self.robot_groups[group.id] = group
        
        if labels:
            for label in labels:
                self.robot_labels[label.id] = label
    
    def get_robots(self) -> List[RobotInfo]:
        """获取所有机器人"""
        return list(self.robots.values())
    
    def get_robot_groups(self) -> List[RobotGroup]:
        """获取所有机器人组"""
        return list(self.robot_groups.values())
    
    def get_robot_labels(self) -> List[RobotLabel]:
        """获取所有机器人标签"""
        return list(self.robot_labels.values())
    
    def has_robot(self, robot_id: str) -> bool:
        """检查机器人是否存在"""
        return robot_id in self.robots
    
    def get_robot_by_id(self, robot_id: str) -> Optional[RobotInfo]:
        """根据ID获取机器人"""
        return self.robots.get(robot_id)
    
    def update_robot(self, robot_id: str, updates: Dict[str, Any]) -> bool:
        """更新机器人信息"""
        if robot_id not in self.robots:
            return False
        
        robot = self.robots[robot_id]
        for key, value in updates.items():
            if hasattr(robot, key):
                setattr(robot, key, value)
        
        robot.last_update = datetime.now().isoformat()
        return True
    
    def add_robots(self, group_id: str, robots: List[RobotInfo]) -> bool:
        """向机器人组添加机器人"""
        if group_id not in self.robot_groups:
            return False
        
        group = self.robot_groups[group_id]
        for robot in robots:
            if robot.id in self.robots:
                continue
            
            robot.gid = group_id
            self.robots[robot.id] = robot
            if robot.id not in group.robots:
                group.robots.append(robot.id)
        
        return True
    
    def remove_robots(self, robot_ids: List[str]) -> int:
        """删除机器人"""
        removed_count = 0
        for robot_id in robot_ids:
            if robot_id in self.robots:
                del self.robots[robot_id]
                removed_count += 1
        
        # 从组中移除
        for group in self.robot_groups.values():
            group.robots = [rid for rid in group.robots if rid in self.robots]
        
        # 从标签中移除
        for label in self.robot_labels.values():
            label.robots = [rid for rid in label.robots if rid in self.robots]
        
        return removed_count
    
    def update_robots(self, robot_ids: List[str], updates: Dict[str, Any]) -> int:
        """批量更新机器人"""
        updated_count = 0
        for robot_id in robot_ids:
            if self.update_robot(robot_id, updates):
                updated_count += 1
        return updated_count
    
    def create_robot_group(self, label: str = "新机器人组") -> str:
        """创建机器人组"""
        group_id = str(uuid.uuid4())
        group = RobotGroup(id=group_id, label=label)
        self.robot_groups[group_id] = group
        return group_id
    
    def delete_robot_group(self, group_id: str) -> bool:
        """删除机器人组"""
        if group_id not in self.robot_groups:
            return False
        
        # 删除组中的所有机器人
        group = self.robot_groups[group_id]
        self.remove_robots(group.robots)
        
        # 删除组
        del self.robot_groups[group_id]
        return True
    
    def update_robot_group_label(self, group_id: str, label: str) -> bool:
        """更新机器人组标签"""
        if group_id not in self.robot_groups:
            return False
        
        self.robot_groups[group_id].label = label
        return True
    
    def create_robot_label(self, label: str = "新标签") -> str:
        """创建机器人标签"""
        label_id = str(uuid.uuid4())
        robot_label = RobotLabel(id=label_id, label=label)
        self.robot_labels[label_id] = robot_label
        return label_id
    
    def delete_robot_label(self, label_id: str) -> bool:
        """删除机器人标签"""
        if label_id not in self.robot_labels:
            return False
        
        del self.robot_labels[label_id]
        return True
    
    def update_robot_label(self, label_id: str, label_name: str) -> bool:
        """更新机器人标签名称"""
        if label_id not in self.robot_labels:
            return False
        
        self.robot_labels[label_id].label = label_name
        return True
    
    def add_robots_to_label(self, label_id: str, robots: List[RobotInfo]) -> bool:
        """向标签添加机器人"""
        if label_id not in self.robot_labels:
            return False
        
        label = self.robot_labels[label_id]
        for robot in robots:
            if robot.id not in self.robots:
                continue
            if robot.id not in label.robots:
                label.robots.append(robot.id)
        
        return True
    
    def remove_robot_from_label(self, label_id: str, robot_id: str) -> bool:
        """从标签中移除机器人"""
        if label_id not in self.robot_labels:
            return False
        
        label = self.robot_labels[label_id]
        if robot_id in label.robots:
            label.robots.remove(robot_id)
            return True
        
        return False
    
    def remove_robots_from_all_labels(self, robot_ids: List[str]) -> None:
        """从所有标签中移除机器人"""
        for label in self.robot_labels.values():
            label.robots = [rid for rid in label.robots if rid not in robot_ids]
    
    def update_robot_status(self, robot_id: str, status: RobotStatus, 
                           position: Optional[Dict[str, float]] = None,
                           battery: Optional[float] = None,
                           speed: Optional[float] = None) -> bool:
        """更新机器人状态"""
        if robot_id not in self.robots:
            return False
        
        robot = self.robots[robot_id]
        robot.status = status
        robot.last_update = datetime.now().isoformat()
        
        if position:
            robot.position = position
        if battery is not None:
            robot.battery = battery
        if speed is not None:
            robot.speed = speed
        
        return True
    
    def get_robots_by_status(self, status: RobotStatus) -> List[RobotInfo]:
        """根据状态获取机器人"""
        return [robot for robot in self.robots.values() if robot.status == status]
    
    def get_robots_by_group(self, group_id: str) -> List[RobotInfo]:
        """根据组ID获取机器人"""
        if group_id not in self.robot_groups:
            return []
        
        group = self.robot_groups[group_id]
        return [self.robots[rid] for rid in group.robots if rid in self.robots]
    
    def get_robots_by_label(self, label_id: str) -> List[RobotInfo]:
        """根据标签ID获取机器人"""
        if label_id not in self.robot_labels:
            return []
        
        label = self.robot_labels[label_id]
        return [self.robots[rid] for rid in label.robots if rid in self.robots]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "robots": [robot.__dict__ for robot in self.robots.values()],
            "robot_groups": [group.__dict__ for group in self.robot_groups.values()],
            "robot_labels": [label.__dict__ for label in self.robot_labels.values()]
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)