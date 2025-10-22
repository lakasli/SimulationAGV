"""
异步架构演示启动脚本
快速启动和测试 asyncio + aioredis + asyncio-mqtt 技术架构
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from examples.async_architecture_demo import AsyncArchitectureDemo

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/async_demo.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def check_prerequisites():
    """检查运行前提条件"""
    logger.info("检查运行前提条件...")
    
    # 检查Python版本
    if sys.version_info < (3.7, 0):
        logger.error("需要Python 3.7或更高版本")
        return False
        
    # 检查必要的包
    required_packages = [
        'asyncio',
        'aioredis', 
        'asyncio_mqtt',
        'paho.mqtt.client'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} 未安装")
            
    if missing_packages:
        logger.error("缺少必要的包，请运行以下命令安装:")
        logger.error(f"pip install {' '.join(missing_packages)}")
        return False
        
    # 检查配置文件
    config_file = project_root / "config" / "async_config.json"
    if not config_file.exists():
        logger.warning(f"配置文件不存在: {config_file}")
        logger.info("将使用默认配置")
        
    # 创建日志目录
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logger.info("前提条件检查完成")
    return True


async def run_demo():
    """运行演示"""
    logger.info("=" * 60)
    logger.info("异步架构演示开始")
    logger.info("=" * 60)
    
    try:
        demo = AsyncArchitectureDemo()
        await demo.run_demo()
        
        logger.info("=" * 60)
        logger.info("异步架构演示成功完成")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("用户中断演示")
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        logger.exception("详细错误信息:")
        raise


def main():
    """主函数"""
    print("异步架构演示启动器")
    print("=" * 40)
    
    # 检查前提条件
    if not check_prerequisites():
        print("前提条件检查失败，请解决上述问题后重试")
        sys.exit(1)
        
    print("\n开始运行异步架构演示...")
    print("按 Ctrl+C 可以随时停止演示\n")
    
    try:
        # 运行异步演示
        asyncio.run(run_demo())
        
    except KeyboardInterrupt:
        print("\n演示已被用户中断")
    except Exception as e:
        print(f"\n演示失败: {e}")
        sys.exit(1)
        
    print("\n演示结束，感谢使用！")


if __name__ == "__main__":
    main()