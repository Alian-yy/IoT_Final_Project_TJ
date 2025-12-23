# -*- coding: utf-8 -*-
"""
小嘉智能环境监控系统 - 发布端后端服务
FastAPI + MQTT 实现数据发布
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="小嘉发布端API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据模型 ====================
class MQTTConfig(BaseModel):
    broker: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None


class PublishRequest(BaseModel):
    start_date: Optional[str] = None  # 格式: YYYY-MM-DD
    end_date: Optional[str] = None
    interval: float = 1.0  # 发布间隔（秒）
    sensor_id: Optional[str] = "JX_Teach_01"
    location: Optional[str] = "教学楼A"
    extra: Optional[str] = ""
    mqtt_config: Optional[MQTTConfig] = None


class PublishStatus(BaseModel):
    is_publishing: bool
    total_records: int
    published_count: int
    skipped_count: int
    current_timestamp: Optional[str]
    progress: float


# ==================== 全局变量 ====================
class PublisherState:
    def __init__(self):
        self.is_publishing = False
        self.should_stop = False
        self.mqtt_client: Optional[mqtt.Client] = None
        self.status = PublishStatus(
            is_publishing=False,
            total_records=0,
            published_count=0,
            skipped_count=0,
            current_timestamp=None,
            progress=0.0
        )
        self.websocket_clients: List[WebSocket] = []
        self.current_index = 0  # 当前发布到的位置（断点续传）
        self.cached_data: List[Dict] = []  # 缓存的数据列表

state = PublisherState()


# ==================== 数据文件处理 ====================
def parse_data_file(file_path: str) -> Dict[str, str]:
    """解析数据文件，返回 {timestamp: value} 字典"""
    data = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 每行是一个 JSON 对象
                day_data = json.loads(line)
                for timestamp, value in day_data.items():
                    if value and value.strip():  # 过滤空值
                        data[timestamp] = value
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return data


def load_sensor_data() -> Dict[str, Dict[str, str]]:
    """加载所有传感器数据"""
    base_path = Path(__file__).parent / "data"  # 修正：加上 data 子目录

    return {
        "temperature": parse_data_file(base_path / "temperature.txt"),
        "humidity": parse_data_file(base_path / "humidity.txt"),
        "pressure": parse_data_file(base_path / "pressure.txt")
    }

def align_data(
    all_data: Dict[str, Dict[str, str]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict]:
    """
    对齐三种传感器数据，返回按时间戳排序的列表
    每个元素格式: {
        "timestamp": "2014-02-13T06:20:00",
        "temperature": "3.0",
        "humidity": "93",
        "pressure": "989"
    }
    """
    # 获取所有时间戳的交集
    temp_timestamps = set(all_data["temperature"].keys())
    humi_timestamps = set(all_data["humidity"].keys())
    pres_timestamps = set(all_data["pressure"].keys())
    
    # 使用交集确保三个数据都存在
    common_timestamps = temp_timestamps & humi_timestamps & pres_timestamps
    
    # 日期过滤
    if start_date or end_date:
        filtered_timestamps = []
        for ts in common_timestamps:
            ts_date = ts.split('T')[0]
            if start_date and ts_date < start_date:
                continue
            if end_date and ts_date > end_date:
                continue
            filtered_timestamps.append(ts)
        common_timestamps = set(filtered_timestamps)
    
    # 构建对齐的数据列表
    aligned_data = []
    for ts in sorted(common_timestamps):
        aligned_data.append({
            "timestamp": ts,
            "temperature": all_data["temperature"][ts],
            "humidity": all_data["humidity"][ts],
            "pressure": all_data["pressure"][ts]
        })
    
    return aligned_data


# ==================== MQTT 客户端 ====================
def create_mqtt_client(config: MQTTConfig) -> mqtt.Client:
    """创建并配置 MQTT 客户端"""
    client = mqtt.Client(client_id=f"publisher_{datetime.now().timestamp()}")
    
    if config.username and config.password:
        client.username_pw_set(config.username, config.password)
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ 已连接到 MQTT Broker: {config.broker}:{config.port}")
        else:
            print(f"❌ 连接失败，返回码: {rc}")
    
    def on_publish(client, userdata, mid):
        print(f"✅ 消息已发布: {mid}")
    
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        client.connect(config.broker, config.port, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        raise
    
    return client


async def publish_sensor_data(data: List[Dict], interval: float, start_index: int = 0, sensor_id: str = "JX_Teach_01", location: str = "", extra: str = ""):
    """发布传感器数据（支持断点续传）"""
    if not state.mqtt_client:
        raise Exception("未连接到MQTT Broker")
    
    state.is_publishing = True
    state.should_stop = False
    state.status.total_records = len(data)
    
    # 如果是从头开始，重置计数器；否则保持之前的计数
    if start_index == 0:
        state.status.published_count = 0
        state.status.skipped_count = 0
    
    state.status.progress = start_index / len(data) * 100 if len(data) > 0 else 0.0
    
    print(f"📊 开始发布: 从第 {start_index + 1} 条开始，共 {len(data)} 条数据")
    
    try:
        for idx in range(start_index, len(data)):
            if state.should_stop:
                # 保存停止时的位置
                state.current_index = idx
                print(f"⏸️  发布已停止，位置: {idx}/{len(data)}")
                break
            
            record = data[idx]
            
            timestamp = record["timestamp"]
            state.status.current_timestamp = timestamp
            
            # 发布到三个独立主题
            topics = {
                "sensor/temperature": {
                    "timestamp": timestamp,
                    "value": float(record["temperature"]),
                    "unit": "°C"
                },
                "sensor/humidity": {
                    "timestamp": timestamp,
                    "value": float(record["humidity"]),
                    "unit": "%"
                },
                "sensor/pressure": {
                    "timestamp": timestamp,
                    "value": float(record["pressure"]),
                    "unit": "hPa"
                }
            }
            
            # 同步发布到三个主题
            published_messages = []
            for topic, payload in topics.items():
                message = json.dumps(payload, ensure_ascii=False)
                result = state.mqtt_client.publish(topic, message, qos=1)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f"❌ 发布失败: {topic}")
                    state.status.skipped_count += 1
                else:
                    # 记录成功发布的消息详情
                    data_type = topic.split('/')[-1]  # 提取 temperature/humidity/pressure
                    published_messages.append({
                        "topic": topic,
                        "type": data_type,
                        "value": payload["value"],
                        "timestamp": timestamp
                    })
            
            state.status.published_count += 1
            state.status.progress = (idx + 1) / len(data) * 100
            state.current_index = idx + 1  # 更新当前位置
            
            # 通知所有 WebSocket 客户端，传递所有三条消息的详情
            if published_messages:
                await broadcast_status(published_messages)
            
            # 等待指定间隔
            await asyncio.sleep(interval)
        
        # 如果完整发布完成，重置索引
        if not state.should_stop:
            state.current_index = 0
            print(f"✅ 发布完成！总计: {state.status.published_count}, 跳过: {state.status.skipped_count}")
        else:
            print(f"⏸️  已发布 {state.status.published_count} 条，停止在第 {state.current_index} 条")
    
    except Exception as e:
        print(f"❌ 发布异常: {e}")
        raise
    
    finally:
        state.is_publishing = False
        state.status.is_publishing = False
        # 不要断开连接，保持MQTT客户端以便后续使用
        # 用户可以通过"断开"按钮主动断开连接
        # 发送完成状态（不需要消息详情）
        await broadcast_status(None)


async def broadcast_status(message_details=None):
    """向所有 WebSocket 客户端广播状态"""
    if state.websocket_clients:
        # 构建前端期待的消息格式
        if state.is_publishing:
            status_data = {
                "type": "progress",
                "published": state.status.published_count,
                "total": state.status.total_records,
                "progress": state.status.progress,
                "current_message": message_details  # 现在是一个列表（包含三条消息）
            }
        elif state.status.published_count > 0 and not state.is_publishing:
            # 区分"停止"和"完成"
            if state.current_index > 0 and state.current_index < state.status.total_records:
                # 手动停止（还有未发布的数据）
                status_data = {
                    "type": "stopped",
                    "published": state.status.published_count,
                    "total": state.status.total_records,
                    "current_index": state.current_index
                }
            else:
                # 自然完成（全部发布完成）
                status_data = {
                    "type": "complete",
                    "published": state.status.published_count,
                    "total": state.status.total_records
                }
        else:
            # 初始状态
            status_data = {
                "type": "status",
                "is_publishing": state.is_publishing,
                "published": state.status.published_count,
                "total": state.status.total_records,
                "progress": state.status.progress
            }
        
        disconnected = []
        for ws in state.websocket_clients:
            try:
                await ws.send_json(status_data)
            except:
                disconnected.append(ws)
        
        # 移除断开的连接
        for ws in disconnected:
            state.websocket_clients.remove(ws)


# ==================== API 端点 ====================
@app.get("/")
async def root():
    return {
        "service": "小嘉发布端 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/mqtt/connect")
async def mqtt_connect(config: MQTTConfig):
    """连接MQTT Broker"""
    try:
        # 如果已有客户端连接，先断开
        if state.mqtt_client:
            print("⚠️  检测到旧的MQTT连接，先断开...")
            try:
                state.mqtt_client.loop_stop()
                state.mqtt_client.disconnect()
            except:
                pass
            state.mqtt_client = None
        
        # 创建MQTT客户端
        print(f"🔗 正在连接到 {config.broker}:{config.port}...")
        client = mqtt.Client()
        
        if config.username and config.password:
            client.username_pw_set(config.username, config.password)
        
        # 连接回调
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"✅ 已连接到 MQTT Broker: {config.broker}:{config.port}")
            else:
                print(f"❌ 连接失败，返回码: {rc}")
        
        def on_disconnect(client, userdata, rc):
            if rc != 0:
                print(f"⚠️  意外断开连接，返回码: {rc}")
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        
        # 连接broker
        client.connect(config.broker, config.port, 60)
        client.loop_start()
        
        state.mqtt_client = client
        
        return {
            "status": "success",
            "message": f"Connected to {config.broker}:{config.port}"
        }
    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@app.post("/mqtt/disconnect")
async def mqtt_disconnect():
    """断开MQTT连接"""
    if state.mqtt_client:
        state.mqtt_client.loop_stop()
        state.mqtt_client.disconnect()
        state.mqtt_client = None
        return {"status": "success", "message": "Disconnected"}
    return {"status": "success", "message": "Already disconnected"}


@app.get("/data/info")
async def get_data_info():
    """获取数据文件信息"""
    all_data = load_sensor_data()
    aligned_data = align_data(all_data)
    
    return {
        "temperature_count": len(all_data["temperature"]),
        "humidity_count": len(all_data["humidity"]),
        "pressure_count": len(all_data["pressure"]),
        "total_records": len(aligned_data),
        "date_range": {
            "start": min(all_data["temperature"].keys()) if all_data["temperature"] else None,
            "end": max(all_data["temperature"].keys()) if all_data["temperature"] else None
        }
    }


@app.post("/publish/start")
async def start_publish(request: PublishRequest):
    """开始发布数据（支持断点续传）"""
    if state.is_publishing:
        raise HTTPException(status_code=400, detail="发布任务正在进行中")
    
    if not state.mqtt_client:
        raise HTTPException(status_code=400, detail="请先连接MQTT Broker")
    
    # 如果没有缓存数据或者current_index为0，重新加载数据
    if not state.cached_data or state.current_index == 0:
        all_data = load_sensor_data()
        aligned_data = align_data(all_data, request.start_date, request.end_date)
        
        if not aligned_data:
            raise HTTPException(status_code=400, detail="没有可发布的数据")
        
        # 缓存数据
        state.cached_data = aligned_data
        state.current_index = 0
        start_msg = "发布任务已启动（从头开始）"
    else:
        # 使用缓存数据，从上次停止的位置继续
        aligned_data = state.cached_data
        start_msg = f"发布任务已启动（从第 {state.current_index + 1} 条继续）"
    
    # 异步启动发布任务，从保存的位置开始
    asyncio.create_task(publish_sensor_data(
        aligned_data, 
        request.interval,
        state.current_index,  # 从保存的位置开始
        request.sensor_id or "JX_Teach_01",
        request.location or "",
        request.extra or ""
    ))
    
    return {
        "message": start_msg,
        "total_records": len(aligned_data),
        "start_index": state.current_index,
        "remaining": len(aligned_data) - state.current_index
    }


@app.post("/publish/stop")
async def stop_publish():
    """停止发布"""
    if not state.is_publishing:
        raise HTTPException(status_code=400, detail="没有正在进行的发布任务")
    
    state.should_stop = True
    return {
        "message": "正在停止发布...",
        "current_index": state.current_index
    }


@app.post("/publish/reset")
async def reset_publish():
    """重置发布进度（从头开始）"""
    if state.is_publishing:
        raise HTTPException(status_code=400, detail="请先停止当前发布任务")
    
    state.current_index = 0
    state.cached_data = []
    state.status.published_count = 0
    state.status.skipped_count = 0
    state.status.progress = 0.0
    
    print("🔄 发布进度已重置")
    
    return {
        "message": "发布进度已重置，下次将从头开始",
        "current_index": 0
    }


@app.get("/publish/status")
async def get_status():
    """获取发布状态"""
    return state.status.model_dump()


@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时状态推送"""
    await websocket.accept()
    state.websocket_clients.append(websocket)
    
    try:
        # 发送初始状态
        await websocket.send_json(state.status.model_dump())
        
        # 保持连接
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.websocket_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
