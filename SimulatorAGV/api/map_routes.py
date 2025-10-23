"""
地图相关API路由
"""

import json
import os
from typing import Dict, Any, List
from pathlib import Path
from .registry import get_api_server
from shared import setup_logger

logger = setup_logger()


def register_map_routes(instance_manager):
    """注册地图相关的API路由"""
    
    server = get_api_server()
    registry = server.get_registry()
    
    @registry.get("/api/maps", "获取所有地图文件列表")
    def get_map_files(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取map_flie目录下的所有地图文件"""
        try:
            # 获取map_flie目录路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            map_dir = os.path.join(current_dir, "map_flie")
            
            if not os.path.exists(map_dir):
                return {"error": "地图目录不存在"}
            
            # 获取所有.scene文件
            map_files = []
            for file in os.listdir(map_dir):
                if file.endswith('.scene'):
                    file_path = os.path.join(map_dir, file)
                    file_name = os.path.splitext(file)[0]  # 去掉扩展名
                    
                    # 获取文件信息
                    stat = os.stat(file_path)
                    map_files.append({
                        "id": file_name,
                        "name": file_name,
                        "filename": file,
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
            
            return {
                "success": True,
                "maps": map_files,
                "total": len(map_files)
            }
            
        except Exception as e:
            logger.error(f"获取地图文件列表失败: {e}")
            return {"error": str(e)}
    
    @registry.get("/api/maps/{map_id}/stations", "获取指定地图的所有站点")
    def get_map_stations(request: Dict[str, Any]) -> Dict[str, Any]:
        """获取指定地图文件的所有站点信息"""
        try:
            map_id = request["path_params"]["map_id"]
            
            # 获取map_flie目录路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            map_file_path = os.path.join(current_dir, "map_flie", f"{map_id}.scene")
            
            if not os.path.exists(map_file_path):
                return {"error": f"地图文件 {map_id}.scene 不存在"}
            
            # 读取并解析地图文件
            with open(map_file_path, 'r', encoding='utf-8') as f:
                map_data = json.load(f)
            
            # 提取站点信息
            stations = []
            if 'points' in map_data:
                for point in map_data['points']:
                    if 'name' in point and 'x' in point and 'y' in point:
                        stations.append({
                            "id": point.get('id', ''),
                            "name": point['name'],
                            "x": point['x'],
                            "y": point['y'],
                            "type": point.get('type', 0)
                        })
            
            return {
                "success": True,
                "map_id": map_id,
                "stations": stations,
                "total": len(stations)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"解析地图文件失败: {e}")
            return {"error": f"地图文件格式错误: {str(e)}"}
        except Exception as e:
            logger.error(f"获取地图站点失败: {e}")
            return {"error": str(e)}
    
    logger.info("地图API路由注册完成")