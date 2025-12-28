# -*- coding: utf-8 -*-
"""
简单的MQTT订阅测试脚本 - 用于测试数据订阅和存储功能
运行此脚本可以快速测试订阅功能，数据会自动保存到data文件夹
"""
import time
import json
from pathlib import Path
from tools.mqtt_subscriber import MQTTSubscriber
from tools.data_handler import DataStorage

# 配置
MQTT_BROKER = "118.31.63.5"  # MQTT服务器地址
MQTT_PORT = 1883
MQTT_USERNAME = None  # 如果有用户名，填写这里
MQTT_PASSWORD = None  # 如果有密码，填写这里

# 要订阅的传感器类型
# 选项：["temperature", "humidity", "pressure"] 或 ["all"] 表示订阅全部
SENSOR_TYPES = ["all"]  # 订阅全部传感器数据 (sensor/#)

# 数据存储目录
DATA_DIR = Path(__file__).parent / "data"

# 初始化
print("=" * 60)
print("小嘉智能环境监控系统 - MQTT订阅测试")
print("=" * 60)

# 创建数据存储
storage = DataStorage(DATA_DIR)
print(f"✅ 数据存储目录: {DATA_DIR}")

# 数据接收回调
received_count = {"temperature": 0, "humidity": 0, "pressure": 0}

def on_data_received(data: dict):
    """数据接收回调函数"""
    topic = data.get('topic', 'unknown')
    sensor_type = topic.split('/')[-1] if '/' in topic else topic
    
    # 准备存储的数据（只保存：时间、类别、值）
    save_data = {
        "timestamp": data.get("timestamp"),
        "topic": topic,
        "value": data.get("value")
    }
    
    # 保存数据
    if storage.save_data(save_data):
        received_count[sensor_type] = received_count.get(sensor_type, 0) + 1
        
        # 显示接收到的数据
        print(f"📥 [{sensor_type:12s}] {data.get('value')}{data.get('unit', ''):3s} | "
              f"时间: {data.get('timestamp')} | "
              f"总计: {received_count[sensor_type]}")
    else:
        print(f"❌ 保存数据失败: {sensor_type}")

# 创建MQTT订阅客户端
print(f"\n🔗 正在连接到 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}...")
subscriber = MQTTSubscriber(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD
)

# 设置数据回调
subscriber.set_data_callback(on_data_received)

# 连接
if not subscriber.connect():
    print("❌ 连接失败！请检查：")
    print("   1. MQTT Broker是否运行")
    print("   2. Broker地址和端口是否正确")
    print("   3. 网络连接是否正常")
    exit(1)

print("✅ 连接成功！\n")

# 订阅传感器数据
print(f"📡 开始订阅传感器类型: {', '.join(SENSOR_TYPES)}")
if subscriber.subscribe(SENSOR_TYPES):
    print("✅ 订阅成功！\n")
    print("=" * 60)
    print("开始接收数据... (按 Ctrl+C 停止)")
    print("=" * 60)
    print()
    
    try:
        # 保持运行
        while True:
            time.sleep(1)
            
            # 每10秒显示一次统计
            if sum(received_count.values()) > 0 and sum(received_count.values()) % 10 == 0:
                print(f"\n📊 统计: 温度={received_count['temperature']}, "
                      f"湿度={received_count['humidity']}, "
                      f"气压={received_count['pressure']}\n")
                
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("正在停止订阅...")
        print("=" * 60)
        
        # 停止订阅
        subscriber.unsubscribe_all()
        subscriber.disconnect()
        
        # 显示最终统计
        print(f"\n📊 最终统计:")
        print(f"   温度数据: {received_count['temperature']} 条")
        print(f"   湿度数据: {received_count['humidity']} 条")
        print(f"   气压数据: {received_count['pressure']} 条")
        print(f"   总计: {sum(received_count.values())} 条")
        
        # 显示数据存储位置
        print(f"\n💾 数据已保存到: {DATA_DIR}")
        print("   文件: temperature.json, humidity.json, pressure.json")
        print("   数据格式: 时间、类别(topic)、值")
        print()
        
else:
    print("❌ 订阅失败！")
    subscriber.disconnect()
    exit(1)

