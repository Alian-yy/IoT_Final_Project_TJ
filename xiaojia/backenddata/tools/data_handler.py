# -*- coding: utf-8 -*-
"""
数据处理器 - 负责数据的存储和管理（JSON格式）
按类别（topic）分别存储到不同的JSON文件
"""
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataStorage:
    """数据存储管理器 - 按类别（topic）分别存储到不同的JSON文件"""
    
    def __init__(self, data_dir: Path):
        """
        初始化数据存储管理器
        
        Args:
            data_dir: 数据存储根目录
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()  # 线程锁确保文件操作安全
        
        # 定义topic到文件名的映射
        self.topic_to_file = {
            "sensor/temperature": "temperature.json",
            "sensor/humidity": "humidity.json",
            "sensor/pressure": "pressure.json"
        }
    
    def _get_filename(self, topic: str) -> Path:
        """
        根据topic获取对应的文件名
        
        Args:
            topic: MQTT主题，如 "sensor/temperature"
        
        Returns:
            文件路径
        """
        # 如果topic在映射中，使用映射的文件名
        if topic in self.topic_to_file:
            filename = self.topic_to_file[topic]
        else:
            # 否则从topic中提取类别名
            # 例如 "sensor/temperature" -> "temperature"
            parts = topic.split('/')
            category = parts[-1] if parts else "unknown"
            filename = f"{category}.json"
        
        return self.data_dir / filename
    
    def save_data(self, data: Dict) -> bool:
        """
        保存传感器数据到对应的JSON文件（追加模式，每行一个JSON对象）
        数据格式：时间、类别(topic)、值
        
        Args:
            data: 数据字典，包含 timestamp, topic, value 等字段
        
        Returns:
            是否保存成功
        """
        try:
            topic = data.get("topic", "")
            if not topic:
                logger.warning("数据缺少topic字段，无法保存")
                return False
            
            # 准备要保存的数据（简化格式：时间、类别、值）
            save_data = {
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "topic": topic,
                "value": data.get("value")
            }
            
            # 获取对应的文件路径
            file_path = self._get_filename(topic)
            
            # 使用线程锁确保文件操作安全
            with self.lock:
                # 以追加模式写入文件，每行一个JSON对象
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(save_data, ensure_ascii=False) + '\n')
            
            logger.debug(f"数据已保存: {topic} = {save_data['value']} -> {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False
    
    def load_data(self, topic: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        加载数据
        
        Args:
            topic: 可选，按topic过滤（如 "sensor/temperature"）
            limit: 可选，限制返回数量
        
        Returns:
            数据列表
        """
        data_list = []
        
        if topic:
            # 加载指定topic的数据
            file_path = self._get_filename(topic)
            if file_path.exists():
                data_list = self._load_from_file(file_path, limit)
        else:
            # 加载所有文件的数据
            for file_path in self.data_dir.glob("*.json"):
                if file_path.name in ["temperature.json", "humidity.json", "pressure.json"]:
                    file_data = self._load_from_file(file_path)
                    data_list.extend(file_data)
            
            # 如果指定了limit，返回最新的limit条
            if limit:
                data_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                data_list = data_list[:limit]
        
        return data_list
    
    def _load_from_file(self, file_path: Path, limit: Optional[int] = None) -> List[Dict]:
        """从单个文件加载数据"""
        data_list = []
        
        if not file_path.exists():
            return data_list
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line.strip())
                            data_list.append(data)
                        except json.JSONDecodeError:
                            continue
            
            # 如果指定了limit，返回最新的limit条
            if limit:
                data_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                data_list = data_list[:limit]
            
            return data_list
            
        except Exception as e:
            logger.error(f"加载文件失败 {file_path}: {e}")
            return []
    
    def get_latest_data(self, topic: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取最新的数据"""
        all_data = self.load_data(topic=topic)
        # 按时间戳排序（最新的在前）
        all_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return all_data[:limit]
    
    def get_data_count(self, topic: Optional[str] = None) -> int:
        """获取数据统计信息"""
        count = 0
        
        if topic:
            # 统计指定topic的数据
            file_path = self._get_filename(topic)
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        count = sum(1 for line in f if line.strip())
                except Exception as e:
                    logger.error(f"统计数据失败: {e}")
        else:
            # 统计所有文件的数据
            for file_path in self.data_dir.glob("*.json"):
                if file_path.name in ["temperature.json", "humidity.json", "pressure.json"]:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            count += sum(1 for line in f if line.strip())
                    except Exception as e:
                        logger.error(f"统计数据失败 {file_path}: {e}")
        
        return count
    
    def get_all_topics(self) -> List[str]:
        """获取所有不同的topic列表"""
        topics = set()
        
        for file_path in self.data_dir.glob("*.json"):
            if file_path.name in ["temperature.json", "humidity.json", "pressure.json"]:
                # 从文件名反推topic
                category = file_path.stem  # temperature, humidity, pressure
                topic = f"sensor/{category}"
                topics.add(topic)
        
        return sorted(list(topics))
