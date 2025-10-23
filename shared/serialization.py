"""
统一的序列化工具
简化项目中的JSON序列化/反序列化逻辑
"""
import json
from typing import Any, Dict, List, Union, Type, TypeVar
from dataclasses import is_dataclass, asdict
from datetime import datetime
from enum import Enum

T = TypeVar('T')


class SerializationMixin:
    """序列化混入类"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if hasattr(self, '__dict__'):
            return safe_serialize(self.__dict__)
        return {}
    
    def to_json(self, indent: int = None, ensure_ascii: bool = False) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """从字典创建实例（需要子类实现）"""
        raise NotImplementedError("子类需要实现 from_dict 方法")
    
    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


def safe_serialize(obj: Any) -> Any:
    """
    安全序列化对象
    处理各种Python对象类型，转换为JSON可序列化的格式
    """
    if obj is None:
        return None
    
    # 基本类型直接返回
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # 日期时间类型
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # 枚举类型
    if isinstance(obj, Enum):
        return obj.value
    
    # 有to_dict方法的对象
    if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
        return obj.to_dict()
    
    # dataclass对象
    if is_dataclass(obj):
        return safe_serialize(asdict(obj))
    
    # 字典类型
    if isinstance(obj, dict):
        return {key: safe_serialize(value) for key, value in obj.items()}
    
    # 列表/元组类型
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    
    # 集合类型
    if isinstance(obj, set):
        return [safe_serialize(item) for item in obj]
    
    # 其他对象，尝试使用__dict__
    if hasattr(obj, '__dict__'):
        return safe_serialize(obj.__dict__)
    
    # 无法序列化的对象，转换为字符串
    return str(obj)


def safe_deserialize(data: Any, target_type: Type[T] = None) -> Any:
    """
    安全反序列化数据
    """
    if data is None:
        return None
    
    # 如果指定了目标类型且有from_dict方法
    if target_type and hasattr(target_type, 'from_dict'):
        if isinstance(data, dict):
            return target_type.from_dict(data)
    
    # 基本类型直接返回
    if isinstance(data, (str, int, float, bool)):
        return data
    
    # 字典类型递归处理
    if isinstance(data, dict):
        return {key: safe_deserialize(value) for key, value in data.items()}
    
    # 列表类型递归处理
    if isinstance(data, list):
        return [safe_deserialize(item) for item in data]
    
    return data


def to_json(obj: Any, indent: int = None, ensure_ascii: bool = False) -> str:
    """
    将对象转换为JSON字符串
    """
    try:
        serialized = safe_serialize(obj)
        return json.dumps(serialized, indent=indent, ensure_ascii=ensure_ascii)
    except Exception as e:
        raise ValueError(f"序列化失败: {e}")


def from_json(json_str: str, target_type: Type[T] = None) -> Union[Any, T]:
    """
    从JSON字符串反序列化对象
    """
    try:
        data = json.loads(json_str)
        return safe_deserialize(data, target_type)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}")
    except Exception as e:
        raise ValueError(f"反序列化失败: {e}")


class JSONEncoder(json.JSONEncoder):
    """自定义JSON编码器"""
    
    def default(self, obj):
        """处理默认JSON编码器无法处理的对象"""
        return safe_serialize(obj)


def create_json_response(data: Any, status_code: int = 200, 
                        indent: int = 2, ensure_ascii: bool = False) -> tuple:
    """
    创建JSON响应
    返回 (json_string, status_code)
    """
    try:
        json_data = to_json(data, indent=indent, ensure_ascii=ensure_ascii)
        return json_data, status_code
    except Exception as e:
        error_data = {
            "error": "序列化失败",
            "message": str(e),
            "status": 500
        }
        json_data = json.dumps(error_data, indent=indent, ensure_ascii=ensure_ascii)
        return json_data, 500


def batch_serialize(objects: List[Any]) -> List[Dict[str, Any]]:
    """
    批量序列化对象列表
    """
    return [safe_serialize(obj) for obj in objects]


def batch_deserialize(data_list: List[Dict[str, Any]], 
                     target_type: Type[T] = None) -> List[Any]:
    """
    批量反序列化数据列表
    """
    return [safe_deserialize(data, target_type) for data in data_list]