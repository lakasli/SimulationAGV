import paho.mqtt.client as mqtt
import time
import json

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print("成功连接到MQTT代理")
        # 订阅测试主题
        client.subscribe("test/topic")
        print("已订阅测试主题: test/topic")
        # 发布一条测试消息
        client.publish("test/topic", "Hello from MQTT test script!")
    else:
        print(f"连接失败，错误代码: {rc}")

def on_message(client, userdata, msg):
    """消息回调"""
    payload = msg.payload.decode('utf-8')
    print(f"收到消息 - 主题: {msg.topic}, 内容: {payload}")

def on_disconnect(client, userdata, rc):
    """断开连接回调"""
    print("与MQTT代理断开连接")

def main():
    # 创建MQTT客户端
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # 尝试连接到MQTT代理
        print("正在连接到MQTT代理 localhost:1883...")
        client.connect("localhost", 1883, 60)
        
        # 开始循环
        client.loop_start()
        
        # 保持运行30秒
        print("MQTT客户端运行中... 按Ctrl+C停止")
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\n收到停止信号")
    except Exception as e:
        print(f"连接MQTT代理时出错: {e}")
    finally:
        # 停止循环并断开连接
        client.loop_stop()
        client.disconnect()
        print("MQTT客户端已停止")

if __name__ == "__main__":
    main()