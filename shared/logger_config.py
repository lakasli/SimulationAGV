"""
共享的日志配置模块
统一SimulatorAGV和SimulatorViewer的日志配置
"""
import logging
import os
from typing import Optional


def setup_logger(name: Optional[str] = None, log_file: Optional[str] = None, 
                log_level: int = logging.INFO) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        name: 日志器名称，默认为调用模块的名称
        log_file: 日志文件名，默认根据name生成
        log_level: 日志级别，默认为INFO
        
    Returns:
        配置好的日志器
    """
    if name is None:
        # 自动检测调用模块
        import inspect
        frame = inspect.currentframe().f_back
        module_name = frame.f_globals.get('__name__', 'unknown')
        if 'SimulatorAGV' in module_name:
            name = "SimulatorAGV"
        elif 'SimulatorViewer' in module_name:
            name = "SimulatorViewer"
        else:
            name = "SimulationAGV"
    
    if log_file is None:
        log_file = f"{name}.logs"
    
    # 确保logs目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    
    # 创建日志器
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# 默认日志器实例
logger = setup_logger()