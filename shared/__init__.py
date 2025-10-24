"""共享模块
提供项目中的共享功能和配置"""

from .config_manager import Config, get_config, reload_config
from .logger_config import setup_logger
from .models import *
from .serialization import *

__all__ = [
    'Config',
    'get_config', 
    'reload_config',
    'setup_logger'
]

# 版本信息
__version__ = "1.0.0"