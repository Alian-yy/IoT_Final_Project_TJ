# -*- coding: utf-8 -*-
"""
小嘉智能环境监控系统 - 订阅端后端服务
FastAPI + MQTT 实现数据订阅、存储和分析
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 导入自定义模块
from tools.mqtt_subscriber import MQTTSubscriber
from tools.data_handler import DataStorage
from tools.data_analyzer import DataAnalyzer

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="小嘉订阅端API", version="1.0.0")

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
    broker: str = "118.31.63.5"  # 默认MQTT服务器地址
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None


class SubscribeRequest(BaseModel):
    sensor_types: List[str]  # ["temperature", "humidity", "pressure"]
    mqtt_config: Optional[MQTTConfig] = None


class AnalysisRequest(BaseModel):
    sensor_type: str  # temperature, humidity, pressure
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    predict_hours: int = 24
    polynomial_degree: int = 2
    analysis_methods: Optional[List[str]] = None  # ["linear", "polynomial", "moving_average", "statistical", "trend"]


class SubscriptionStatus(BaseModel):
    is_connected: bool
    is_subscribing: bool
    subscribed_types: List[str]
    total_received: Dict[str, int]  # {sensor_type: count}


# ==================== 全局变量 ====================
class SubscriberState:
    def __init__(self):
        self.mqtt_subscriber: Optional[MQTTSubscriber] = None
        self.data_storage: Optional[DataStorage] = None
        self.data_analyzer: Optional[DataAnalyzer] = None
        self.status = SubscriptionStatus(
            is_connected=False,
            is_subscribing=False,
            subscribed_types=[],
            total_received={"temperature": 0, "humidity": 0, "pressure": 0}
        )
        self.websocket_clients: List[WebSocket] = []
        self.data_callback_set = False
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None

state = SubscriberState()

# 初始化数据存储和分析器
data_dir = Path(__file__).parent / "data"
state.data_storage = DataStorage(data_dir)
state.data_analyzer = DataAnalyzer(data_dir)


# ==================== 数据接收回调 ====================
def on_data_received(data: Dict):
    """MQTT数据接收回调函数（在MQTT线程中执行）"""
    try:
        sensor_type = data.get('sensor_type', 'unknown')
        topic = data.get('topic', '')
        
        # 准备存储的数据（只保存：时间、类别、值）
        save_data = {
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "topic": topic,
            "value": data.get("value")
        }
        
        # 保存数据
        if state.data_storage:
            state.data_storage.save_data(save_data)
        
        # 更新统计（按topic统计）
        if topic:
            topic_key = topic.split('/')[-1] if '/' in topic else topic
            if topic_key in state.status.total_received:
                state.status.total_received[topic_key] += 1
        
        # 通知WebSocket客户端（线程安全的方式）
        if state.event_loop and not state.event_loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(broadcast_data(data), state.event_loop)
            except Exception as e:
                logger.warning(f"广播数据失败: {e}")
        
        logger.info(f"📥 收到数据: {topic} = {data.get('value')}{data.get('unit', '')}")
        
    except Exception as e:
        logger.error(f"处理接收数据失败: {e}")


async def broadcast_data(data: Dict):
    """向所有WebSocket客户端广播数据"""
    if state.websocket_clients:
        message = {
            "type": "data",
            "data": data,
            "statistics": state.status.total_received
        }
        
        disconnected = []
        for ws in state.websocket_clients:
            try:
                await ws.send_json(message)
            except:
                disconnected.append(ws)
        
        # 移除断开的连接
        for ws in disconnected:
            state.websocket_clients.remove(ws)


async def broadcast_status():
    """向所有WebSocket客户端广播状态"""
    if state.websocket_clients:
        status_data = {
            "type": "status",
            "status": state.status.model_dump()
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
        "service": "小嘉订阅端 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/mqtt/connect")
async def mqtt_connect(config: MQTTConfig):
    """连接MQTT Broker"""
    try:
        # 如果已有连接，先断开
        if state.mqtt_subscriber:
            state.mqtt_subscriber.disconnect()
            state.mqtt_subscriber = None
        
        # 创建新的订阅客户端
        subscriber = MQTTSubscriber(
            broker=config.broker,
            port=config.port,
            username=config.username,
            password=config.password
        )
        
        # 设置数据回调
        subscriber.set_data_callback(on_data_received)
        
        # 连接
        if subscriber.connect():
            state.mqtt_subscriber = subscriber
            state.status.is_connected = True
            await broadcast_status()
            
            return {
                "status": "success",
                "message": f"已连接到 {config.broker}:{config.port}"
            }
        else:
            raise HTTPException(status_code=500, detail="连接失败")
            
    except Exception as e:
        logger.error(f"连接异常: {e}")
        raise HTTPException(status_code=500, detail=f"连接失败: {str(e)}")


@app.post("/mqtt/disconnect")
async def mqtt_disconnect():
    """断开MQTT连接"""
    if state.mqtt_subscriber:
        state.mqtt_subscriber.disconnect()
        state.mqtt_subscriber = None
        state.status.is_connected = False
        state.status.is_subscribing = False
        state.status.subscribed_types = []
        await broadcast_status()
        
        return {"status": "success", "message": "已断开连接"}
    return {"status": "success", "message": "未连接"}


@app.post("/subscribe/start")
async def start_subscribe(request: SubscribeRequest):
    """开始订阅指定的传感器类型"""
    if not state.mqtt_subscriber or not state.status.is_connected:
        raise HTTPException(status_code=400, detail="请先连接MQTT Broker")
    
    # 验证传感器类型
    valid_types = ["temperature", "humidity", "pressure"]
    invalid_types = [t for t in request.sensor_types if t not in valid_types]
    if invalid_types:
        raise HTTPException(status_code=400, detail=f"无效的传感器类型: {invalid_types}")
    
    # 订阅
    if state.mqtt_subscriber.subscribe(request.sensor_types):
        state.status.is_subscribing = True
        state.status.subscribed_types = state.mqtt_subscriber.get_subscribed_types()
        await broadcast_status()
        
        return {
            "status": "success",
            "message": f"已开始订阅: {', '.join(request.sensor_types)}",
            "subscribed_types": state.status.subscribed_types
        }
    else:
        raise HTTPException(status_code=500, detail="订阅失败")


@app.post("/subscribe/stop")
async def stop_subscribe():
    """停止订阅"""
    if not state.mqtt_subscriber:
        raise HTTPException(status_code=400, detail="未连接MQTT Broker")
    
    if not state.status.is_subscribing:
        raise HTTPException(status_code=400, detail="当前没有订阅")
    
    # 取消所有订阅
    state.mqtt_subscriber.unsubscribe_all()
    state.status.is_subscribing = False
    state.status.subscribed_types = []
    await broadcast_status()
    
    return {
        "status": "success",
        "message": "已停止订阅"
    }


@app.post("/subscribe/update")
async def update_subscribe(request: SubscribeRequest):
    """更新订阅（先取消所有，再订阅新的）"""
    if not state.mqtt_subscriber or not state.status.is_connected:
        raise HTTPException(status_code=400, detail="请先连接MQTT Broker")
    
    # 取消所有订阅
    state.mqtt_subscriber.unsubscribe_all()
    
    # 订阅新的类型
    if request.sensor_types:
        valid_types = ["temperature", "humidity", "pressure"]
        invalid_types = [t for t in request.sensor_types if t not in valid_types]
        if invalid_types:
            raise HTTPException(status_code=400, detail=f"无效的传感器类型: {invalid_types}")
        
        if state.mqtt_subscriber.subscribe(request.sensor_types):
            state.status.is_subscribing = True
            state.status.subscribed_types = state.mqtt_subscriber.get_subscribed_types()
        else:
            state.status.is_subscribing = False
            state.status.subscribed_types = []
    else:
        state.status.is_subscribing = False
        state.status.subscribed_types = []
    
    await broadcast_status()
    
    return {
        "status": "success",
        "message": f"订阅已更新: {', '.join(state.status.subscribed_types) if state.status.subscribed_types else '无'}"
    }


@app.get("/subscribe/status")
async def get_subscribe_status():
    """获取订阅状态"""
    if state.mqtt_subscriber:
        state.status.subscribed_types = state.mqtt_subscriber.get_subscribed_types()
        state.status.is_connected = state.mqtt_subscriber.is_connected
    
    return state.status.model_dump()


@app.get("/data/count")
async def get_data_count(sensor_type: Optional[str] = None):
    """获取数据统计"""
    if not state.data_storage:
        raise HTTPException(status_code=500, detail="数据存储未初始化")
    
    counts = state.data_storage.get_data_count(sensor_type)
    return {
        "sensor_type": sensor_type or "all",
        "counts": counts,
        "total": sum(counts.values())
    }


@app.get("/data/latest")
async def get_latest_data(sensor_type: str, limit: int = 100):
    """获取最新数据"""
    if not state.data_storage:
        raise HTTPException(status_code=500, detail="数据存储未初始化")
    
    if sensor_type not in ["temperature", "humidity", "pressure"]:
        raise HTTPException(status_code=400, detail="无效的传感器类型")
    
    data = state.data_storage.get_latest_data(sensor_type, limit)
    return {
        "sensor_type": sensor_type,
        "count": len(data),
        "data": data
    }


@app.get("/data/range")
async def get_data_range(sensor_type: str, start_date: str, end_date: str):
    """获取指定日期范围的数据"""
    if not state.data_storage:
        raise HTTPException(status_code=500, detail="数据存储未初始化")
    
    if sensor_type not in ["temperature", "humidity", "pressure"]:
        raise HTTPException(status_code=400, detail="无效的传感器类型")
    
    try:
        # 验证日期格式
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    
    data = state.data_storage.load_data(sensor_type, start_date, end_date)
    return {
        "sensor_type": sensor_type,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(data),
        "data": data
    }


@app.post("/analysis/comprehensive")
async def comprehensive_analysis(request: AnalysisRequest):
    """综合分析"""
    if not state.data_analyzer:
        raise HTTPException(status_code=500, detail="数据分析器未初始化")
    
    if request.sensor_type not in ["temperature", "humidity", "pressure"]:
        raise HTTPException(status_code=400, detail="无效的传感器类型")
    
    try:
        # 验证日期格式
        datetime.strptime(request.start_date, "%Y-%m-%d")
        datetime.strptime(request.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    
    # 执行分析
    results = state.data_analyzer.comprehensive_analysis(
        sensor_type=request.sensor_type,
        start_date=request.start_date,
        end_date=request.end_date,
        predict_hours=request.predict_hours,
        polynomial_degree=request.polynomial_degree
    )
    
    return results


@app.post("/analysis/linear")
async def linear_analysis(request: AnalysisRequest):
    """线性回归分析"""
    if not state.data_analyzer:
        raise HTTPException(status_code=500, detail="数据分析器未初始化")
    
    # 加载数据
    df = state.data_analyzer.load_data_from_storage(
        request.sensor_type,
        request.start_date,
        request.end_date
    )
    
    if df.empty:
        raise HTTPException(status_code=400, detail="没有找到数据")
    
    # 执行分析
    results = state.data_analyzer.linear_regression_analysis(df, request.predict_hours)
    return results


@app.post("/analysis/polynomial")
async def polynomial_analysis(request: AnalysisRequest):
    """多项式回归分析"""
    if not state.data_analyzer:
        raise HTTPException(status_code=500, detail="数据分析器未初始化")
    
    # 加载数据
    df = state.data_analyzer.load_data_from_storage(
        request.sensor_type,
        request.start_date,
        request.end_date
    )
    
    if df.empty:
        raise HTTPException(status_code=400, detail="没有找到数据")
    
    # 执行分析
    results = state.data_analyzer.polynomial_regression_analysis(
        df, request.polynomial_degree, request.predict_hours
    )
    return results


@app.post("/analysis/moving_average")
async def moving_average_analysis(request: AnalysisRequest):
    """移动平均分析"""
    if not state.data_analyzer:
        raise HTTPException(status_code=500, detail="数据分析器未初始化")
    
    # 加载数据
    df = state.data_analyzer.load_data_from_storage(
        request.sensor_type,
        request.start_date,
        request.end_date
    )
    
    if df.empty:
        raise HTTPException(status_code=400, detail="没有找到数据")
    
    # 执行分析
    results = state.data_analyzer.moving_average_analysis(df, window=10, predict_hours=request.predict_hours)
    return results


@app.post("/analysis/statistical")
async def statistical_analysis(request: AnalysisRequest):
    """统计分析"""
    if not state.data_analyzer:
        raise HTTPException(status_code=500, detail="数据分析器未初始化")
    
    # 加载数据
    df = state.data_analyzer.load_data_from_storage(
        request.sensor_type,
        request.start_date,
        request.end_date
    )
    
    if df.empty:
        raise HTTPException(status_code=400, detail="没有找到数据")
    
    # 执行分析
    results = state.data_analyzer.statistical_analysis(df)
    return results


@app.post("/analysis/trend")
async def trend_analysis(request: AnalysisRequest):
    """趋势分析"""
    if not state.data_analyzer:
        raise HTTPException(status_code=500, detail="数据分析器未初始化")
    
    # 加载数据
    df = state.data_analyzer.load_data_from_storage(
        request.sensor_type,
        request.start_date,
        request.end_date
    )
    
    if df.empty:
        raise HTTPException(status_code=400, detail="没有找到数据")
    
    # 执行分析
    results = state.data_analyzer.trend_analysis(df)
    return results


@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时数据推送"""
    await websocket.accept()
    state.websocket_clients.append(websocket)
    
    try:
        # 发送初始状态
        await websocket.send_json({
            "type": "status",
            "status": state.status.model_dump()
        })
        
        # 保持连接
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in state.websocket_clients:
            state.websocket_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    
    # 获取事件循环以便在MQTT回调中使用
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    state.event_loop = loop
    
    uvicorn.run(app, host="0.0.0.0", port=8002)

