# -*- coding: utf-8 -*-
"""
MQTT订阅服务 - 从服务器订阅传感器数据
"""
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Callable
import paho.mqtt.client as mqtt
import logging

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """MQTT订阅客户端"""
    
    # 传感器类型映射
    SENSOR_TOPICS = {
        "temperature": "sensor/temperature",
        "humidity": "sensor/humidity",
        "pressure": "sensor/pressure",
        "all": "sensor/#"  # 支持全部订阅
    }
    
    def __init__(self, broker: str = "localhost", port: int = 1883,
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        初始化MQTT订阅客户端
        
        Args:
            broker: MQTT Broker地址
            port: MQTT端口
            username: 用户名（可选）
            password: 密码（可选）
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self.subscribed_topics: List[str] = []
        self.data_callback: Optional[Callable] = None
        
    def set_data_callback(self, callback: Callable):
        """设置数据接收回调函数"""
        self.data_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.is_connected = True
            logger.info(f"✅ 已连接到 MQTT Broker: {self.broker}:{self.port}")
            
            # 重新订阅之前订阅的主题
            for topic in self.subscribed_topics:
                client.subscribe(topic, qos=1)
                logger.info(f"📡 已订阅主题: {topic}")
        else:
            self.is_connected = False
            logger.error(f"❌ 连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"⚠️  意外断开连接，返回码: {rc}")
        else:
            logger.info("🔌 已断开MQTT连接")
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            # 解析消息
            payload = json.loads(msg.payload.decode('utf-8'))
            topic = msg.topic
            
            # 提取传感器类型
            sensor_type = topic.split('/')[-1]  # temperature, humidity, pressure
            
            # 构建数据对象
            data = {
                "timestamp": payload.get("timestamp"),
                "value": payload.get("value"),
                "unit": payload.get("unit"),
                "sensor_type": sensor_type,
                "received_at": datetime.now().isoformat(),
                "topic": topic
            }
            
            # 调用回调函数
            if self.data_callback:
                self.data_callback(data)
            
            logger.debug(f"📥 收到数据: {sensor_type} = {payload.get('value')}{payload.get('unit')}")
            
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
    
    def connect(self) -> bool:
        """连接到MQTT Broker"""
        try:
            if self.client and self.is_connected:
                logger.warning("⚠️  已经连接到MQTT Broker")
                return True
            
            # 创建客户端
            client_id = f"subscriber_{datetime.now().timestamp()}"
            self.client = mqtt.Client(client_id=client_id)
            
            # 设置认证
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # 设置回调
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # 连接
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            # 等待连接建立
            import time
            for _ in range(10):  # 最多等待5秒
                if self.is_connected:
                    return True
                time.sleep(0.5)
            
            logger.error("❌ 连接超时")
            return False
            
        except Exception as e:
            logger.error(f"❌ 连接异常: {e}")
            return False
    
    def subscribe(self, sensor_types: List[str]) -> bool:
        """
        订阅指定的传感器类型
        
        Args:
            sensor_types: 传感器类型列表，如 ["temperature", "humidity", "pressure", "all"]
                          "all" 表示订阅 sensor/# (全部传感器数据)
        
        Returns:
            是否订阅成功
        """
        if not self.is_connected:
            logger.error("❌ 未连接到MQTT Broker，请先连接")
            return False
        
        subscribed = []
        for sensor_type in sensor_types:
            if sensor_type not in self.SENSOR_TOPICS:
                logger.warning(f"⚠️  未知的传感器类型: {sensor_type}")
                continue
            
            topic = self.SENSOR_TOPICS[sensor_type]
            if topic not in self.subscribed_topics:
                result = self.client.subscribe(topic, qos=1)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    self.subscribed_topics.append(topic)
                    subscribed.append(sensor_type)
                    if sensor_type == "all":
                        logger.info(f"📡 已订阅: 全部传感器 ({topic})")
                    else:
                        logger.info(f"📡 已订阅: {sensor_type} ({topic})")
                else:
                    logger.error(f"❌ 订阅失败: {sensor_type}")
        
        return len(subscribed) > 0
    
    def unsubscribe(self, sensor_types: List[str]) -> bool:
        """
        取消订阅指定的传感器类型
        
        Args:
            sensor_types: 传感器类型列表
        
        Returns:
            是否取消订阅成功
        """
        if not self.is_connected:
            return False
        
        unsubscribed = []
        for sensor_type in sensor_types:
            if sensor_type not in self.SENSOR_TOPICS:
                continue
            
            topic = self.SENSOR_TOPICS[sensor_type]
            if topic in self.subscribed_topics:
                self.client.unsubscribe(topic)
                self.subscribed_topics.remove(topic)
                unsubscribed.append(sensor_type)
                logger.info(f"🔇 已取消订阅: {sensor_type}")
        
        return len(unsubscribed) > 0
    
    def unsubscribe_all(self):
        """取消所有订阅"""
        if self.client and self.is_connected:
            for topic in self.subscribed_topics.copy():
                self.client.unsubscribe(topic)
            self.subscribed_topics.clear()
            logger.info("🔇 已取消所有订阅")
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            self.unsubscribe_all()
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
            self.is_connected = False
            logger.info("🔌 已断开MQTT连接")
    
    def get_subscribed_types(self) -> List[str]:
        """获取当前订阅的传感器类型列表"""
        types = []
        for topic in self.subscribed_topics:
            if topic == "sensor/#":
                types.append("all")
            else:
                sensor_type = topic.split('/')[-1]
                types.append(sensor_type)
        return types

