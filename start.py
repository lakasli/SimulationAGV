#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 用于启动 Mosquitto MQTT broker 和虚拟 AGV 小车

本脚本会启动以下两个组件：
1. Mosquitto MQTT broker (D:\\mosquitto\\mosquitto.exe)
2. 虚拟 AGV 小车 (通过运行 SimulatorAGV/main.py)

使用方法：
    python start.py

注意事项：
1. 确保 Mosquitto 已安装在 D:\\mosquitto\\ 目录下
2. 确保已安装 Python 依赖包 (paho-mqtt)
3. 确保端口 1883 (MQTT) 未被其他程序占用
"""

import subprocess
import sys
import os
import time
import signal
import json

# 全局变量用于存储进程对象
mosquitto_process = None
agv_process = None


def get_mqtt_topics():
    """根据配置文件获取 MQTT 主题信息"""
    try:
        # 获取 SimulatorAGV 目录路径
        simulator_dir = os.path.join(os.path.dirname(__file__), "SimulatorAGV")
        config_path = os.path.join(simulator_dir, "config.json")
        
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            print(f"警告: 找不到配置文件: {config_path}")
            return None
        
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 生成基础主题
        base_topic = f"{config['mqtt_broker']['vda_interface']}/{config['vehicle']['vda_version']}/{config['vehicle']['manufacturer']}/{config['vehicle']['serial_number']}"
        
        # 生成各个主题
        topics = {
            'base': base_topic,
            'connection': f"{base_topic}/connection",
            'state': f"{base_topic}/state",
            'visualization': f"{base_topic}/visualization",
            'order': f"{base_topic}/order",
            'instantActions': f"{base_topic}/instantActions"
        }
        
        return topics, config
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return None, None

def signal_handler(sig, frame):
    """信号处理器，用于关闭所有进程"""
    print("\n接收到关闭信号，正在停止所有进程...")
    stop_processes()
    sys.exit(0)

def stop_processes():
    """停止所有启动的进程"""
    global mosquitto_process, agv_process
    
    if agv_process and agv_process.poll() is None:
        print("正在停止仿真 AGV 小车...")
        agv_process.terminate()
        try:
            agv_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agv_process.kill()
        print("仿真 AGV 小车已停止")
    
    if mosquitto_process and mosquitto_process.poll() is None:
        print("正在停止 Mosquitto MQTT broker...")
        mosquitto_process.terminate()
        try:
            mosquitto_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            mosquitto_process.kill()
        print("Mosquitto MQTT broker 已停止")

def start_mosquitto():
    """启动 Mosquitto MQTT broker"""
    global mosquitto_process
    
    mosquitto_path = r"D:\mosquitto\mosquitto.exe"
    
    # 检查 Mosquitto 是否存在
    if not os.path.exists(mosquitto_path):
        print(f"错误: 找不到 Mosquitto 可执行文件: {mosquitto_path}")
        print("请确保 Mosquitto 已安装在指定路径")
        return False
    
    try:
        print("正在启动 Mosquitto MQTT broker...")
        # 启动 Mosquitto 进程
        mosquitto_process = subprocess.Popen(
            [mosquitto_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Mosquitto MQTT broker 已启动")
        return True
    except Exception as e:
        print(f"启动 Mosquitto 失败: {e}")
        return False

def start_agv_simulator():
    """启动仿真 AGV 小车"""
    global agv_process
    
    # 获取 SimulatorAGV 目录路径
    simulator_dir = os.path.join(os.path.dirname(__file__), "SimulatorAGV")
    main_script = os.path.join(simulator_dir, "main.py")
    
    # 检查 main.py 是否存在
    if not os.path.exists(main_script):
        print(f"错误: 找不到 AGV 模拟器主脚本: {main_script}")
        return False
    
    try:
        print("正在启动仿真 AGV 小车...")
        # 启动 AGV 模拟器进程
        agv_process = subprocess.Popen(
            [sys.executable, main_script],
            cwd=simulator_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("仿真 AGV 小车已启动")
        return True
    except Exception as e:
        print(f"启动仿真 AGV 小车失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("启动 Mosquitto MQTT broker 和虚拟 AGV 小车")
    print("=" * 50)
    
    # 获取 MQTT 主题信息
    topics, config = get_mqtt_topics()
    if topics and config:
        print(f"AGV 小车信息:")
        print(f"  序列号: {config['vehicle']['serial_number']}")
        print(f"  制造商: {config['vehicle']['manufacturer']}")
        print(f"  VDA 版本: {config['vehicle']['vda_version']}")
        print(f"  MQTT Broker: {config['mqtt_broker']['host']}:{config['mqtt_broker']['port']}")
        print(f"  基础主题: {topics['base']}")
        print(f"  状态主题: {topics['state']}")
        print(f"  连接主题: {topics['connection']}")
        print(f"  可视化主题: {topics['visualization']}")
        print(f"  订单主题: {topics['order']}")
        print(f"  即时动作主题: {topics['instantActions']}")
        print("-" * 50)
    else:
        print("警告: 无法读取配置文件，将使用默认设置")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动 Mosquitto
    if not start_mosquitto():
        print("无法启动 Mosquitto，程序退出")
        return
    
    # 等待几秒钟让 Mosquitto 完全启动
    print("等待 Mosquitto 初始化...")
    time.sleep(3)
    
    # 启动 AGV 模拟器
    if not start_agv_simulator():
        print("无法启动虚拟 AGV 小车")
        stop_processes()
        return
    
    print("\n" + "=" * 50)
    print("所有组件已成功启动!")
    print("Mosquitto MQTT broker 运行在 localhost:1883")
    print("虚拟 AGV 小车已连接到 MQTT broker")
    if topics:
        print(f"状态主题: {topics['state']}")
        print("您可以订阅此主题以查看 AGV 状态")
    print("\n按 Ctrl+C 可以停止所有进程")
    print("=" * 50)
    
    # 等待进程结束或接收到中断信号
    try:
        while True:
            # 检查 Mosquitto 是否仍在运行
            if mosquitto_process and mosquitto_process.poll() is not None:
                print("Mosquitto MQTT broker 已退出")
                break
            
            # 检查 AGV 模拟器是否仍在运行
            if agv_process and agv_process.poll() is not None:
                print("仿真 AGV 小车已退出")
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_processes()

if __name__ == "__main__":
    main()