# -*- coding: utf-8 -*-
"""
数据分析工具 - 使用最小二乘法等方法进行历史数据和未来数据预测分析
"""
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
import warnings
warnings.filterwarnings('ignore')

# 可选导入 - 数据分析功能需要这些库
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logger = logging.getLogger(__name__)
    logger.warning("pandas未安装，数据分析功能将不可用。请运行: pip install pandas")

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger = logging.getLogger(__name__)
    logger.warning("scikit-learn未安装，回归分析功能将不可用。请运行: pip install scikit-learn")

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger = logging.getLogger(__name__)
    logger.warning("scipy未安装，统计分析功能将不可用。请运行: pip install scipy")

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """数据分析器 - 提供多种数据分析方法"""
    
    def __init__(self, data_dir: Path):
        """
        初始化数据分析器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
    
    def load_data_from_storage(self, sensor_type: str, start_date: str, end_date: str):
        """
        从存储中加载数据并转换为DataFrame
        
        Args:
            sensor_type: 传感器类型 (temperature, humidity, pressure)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame with columns: timestamp, value, unit
        """
        data_list = []
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            year = date_str[:4]
            month = date_str[5:7]
            day = date_str[8:10]
            
            date_path = self.data_dir / year / month / day
            
            if date_path.exists():
                pattern = f"{sensor_type}_*.json"
                for file_path in date_path.glob(pattern):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    data = json.loads(line.strip())
                                    data_list.append({
                                        'timestamp': data['timestamp'],
                                        'value': float(data['value']),
                                        'unit': data.get('unit', '')
                                    })
                    except Exception as e:
                        logger.warning(f"加载文件失败 {file_path}: {e}")
            
            current_dt += timedelta(days=1)
        
        if not data_list:
            if not HAS_PANDAS:
                raise ImportError("pandas未安装，无法进行数据分析。请运行: pip install pandas")
            return pd.DataFrame()
        
        if not HAS_PANDAS:
            raise ImportError("pandas未安装，无法进行数据分析。请运行: pip install pandas")
        
        df = pd.DataFrame(data_list)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def prepare_time_series(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备时间序列数据用于分析
        
        Returns:
            (time_indices, values) - 时间索引数组和值数组
        """
        if df.empty:
            return np.array([]), np.array([])
        
        # 将时间戳转换为数值（从第一个时间点开始的秒数）
        start_time = df['timestamp'].iloc[0]
        time_deltas = (df['timestamp'] - start_time).dt.total_seconds()
        time_indices = time_deltas.values
        values = df['value'].values
        
        return time_indices, values
    
    def linear_regression_analysis(self, df: pd.DataFrame, predict_hours: int = 24) -> Dict:
        """
        使用最小二乘法进行线性回归分析和预测
        
        Args:
            df: 数据DataFrame
            predict_hours: 预测未来多少小时的数据
        
        Returns:
            分析结果字典
        """
        if df.empty or len(df) < 2:
            return {"error": "数据不足，无法进行分析"}
        
        time_indices, values = self.prepare_time_series(df)
        
        # 使用sklearn进行线性回归
        X = time_indices.reshape(-1, 1)
        y = values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # 计算拟合值
        y_pred = model.predict(X)
        
        # 计算统计指标
        r_squared = model.score(X, y)
        mse = np.mean((y - y_pred) ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(y - y_pred))
        
        # 预测未来数据
        last_time = time_indices[-1]
        time_interval = time_indices[1] - time_indices[0] if len(time_indices) > 1 else 3600
        future_times = []
        future_predictions = []
        
        for i in range(1, predict_hours + 1):
            future_time = last_time + i * time_interval
            future_times.append(future_time)
            future_pred = model.predict([[future_time]])[0]
            future_predictions.append(float(future_pred))
        
        # 计算未来时间戳
        last_timestamp = df['timestamp'].iloc[-1]
        future_timestamps = [
            (last_timestamp + timedelta(seconds=int(t - last_time))).isoformat()
            for t in future_times
        ]
        
        return {
            "method": "linear_regression",
            "coefficients": {
                "slope": float(model.coef_[0]),
                "intercept": float(model.intercept_)
            },
            "statistics": {
                "r_squared": float(r_squared),
                "mse": float(mse),
                "rmse": float(rmse),
                "mae": float(mae),
                "data_points": len(df)
            },
            "historical_fit": [
                {
                    "timestamp": ts.isoformat(),
                    "actual": float(act),
                    "predicted": float(pred)
                }
                for ts, act, pred in zip(df['timestamp'], values, y_pred)
            ],
            "future_predictions": [
                {
                    "timestamp": ts,
                    "predicted_value": pred
                }
                for ts, pred in zip(future_timestamps, future_predictions)
            ]
        }
    
    def polynomial_regression_analysis(self, df: pd.DataFrame, degree: int = 2, predict_hours: int = 24) -> Dict:
        """
        多项式回归分析
        
        Args:
            df: 数据DataFrame
            degree: 多项式次数
            predict_hours: 预测未来多少小时的数据
        
        Returns:
            分析结果字典
        """
        if df.empty or len(df) < degree + 1:
            return {"error": f"数据不足，至少需要{degree + 1}个数据点"}
        
        time_indices, values = self.prepare_time_series(df)
        
        # 多项式特征
        poly_features = PolynomialFeatures(degree=degree)
        X = time_indices.reshape(-1, 1)
        X_poly = poly_features.fit_transform(X)
        y = values
        
        # 线性回归
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # 拟合值
        y_pred = model.predict(X_poly)
        
        # 统计指标
        r_squared = model.score(X_poly, y)
        mse = np.mean((y - y_pred) ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(y - y_pred))
        
        # 预测未来
        last_time = time_indices[-1]
        time_interval = time_indices[1] - time_indices[0] if len(time_indices) > 1 else 3600
        future_times = []
        future_predictions = []
        
        for i in range(1, predict_hours + 1):
            future_time = last_time + i * time_interval
            future_times.append(future_time)
            X_future = poly_features.transform([[future_time]])
            future_pred = model.predict(X_future)[0]
            future_predictions.append(float(future_pred))
        
        # 未来时间戳
        last_timestamp = df['timestamp'].iloc[-1]
        future_timestamps = [
            (last_timestamp + timedelta(seconds=int(t - last_time))).isoformat()
            for t in future_times
        ]
        
        return {
            "method": f"polynomial_regression_degree_{degree}",
            "degree": degree,
            "statistics": {
                "r_squared": float(r_squared),
                "mse": float(mse),
                "rmse": float(rmse),
                "mae": float(mae),
                "data_points": len(df)
            },
            "historical_fit": [
                {
                    "timestamp": ts.isoformat(),
                    "actual": float(act),
                    "predicted": float(pred)
                }
                for ts, act, pred in zip(df['timestamp'], values, y_pred)
            ],
            "future_predictions": [
                {
                    "timestamp": ts,
                    "predicted_value": pred
                }
                for ts, pred in zip(future_timestamps, future_predictions)
            ]
        }
    
    def moving_average_analysis(self, df: pd.DataFrame, window: int = 10, predict_hours: int = 24) -> Dict:
        """
        移动平均分析和预测
        
        Args:
            df: 数据DataFrame
            window: 移动平均窗口大小
            predict_hours: 预测未来多少小时的数据
        
        Returns:
            分析结果字典
        """
        if df.empty or len(df) < window:
            return {"error": f"数据不足，至少需要{window}个数据点"}
        
        values = df['value'].values
        
        # 计算移动平均
        ma_values = pd.Series(values).rolling(window=window, center=True).mean().values
        
        # 预测未来（使用最近的趋势）
        recent_trend = np.mean(np.diff(values[-window:])) if len(values) >= window else 0
        last_value = values[-1]
        
        future_predictions = []
        for i in range(1, predict_hours + 1):
            pred = last_value + recent_trend * i
            future_predictions.append(float(pred))
        
        # 未来时间戳
        last_timestamp = df['timestamp'].iloc[-1]
        time_interval = (df['timestamp'].iloc[1] - df['timestamp'].iloc[0]).total_seconds() if len(df) > 1 else 3600
        future_timestamps = [
            (last_timestamp + timedelta(seconds=int(time_interval * i))).isoformat()
            for i in range(1, predict_hours + 1)
        ]
        
        return {
            "method": "moving_average",
            "window": window,
            "statistics": {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "data_points": len(df)
            },
            "historical_smoothed": [
                {
                    "timestamp": ts.isoformat(),
                    "actual": float(act),
                    "smoothed": float(ma) if not np.isnan(ma) else None
                }
                for ts, act, ma in zip(df['timestamp'], values, ma_values)
            ],
            "future_predictions": [
                {
                    "timestamp": ts,
                    "predicted_value": pred
                }
                for ts, pred in zip(future_timestamps, future_predictions)
            ]
        }
    
    def statistical_analysis(self, df: pd.DataFrame) -> Dict:
        """
        统计分析 - 计算基本统计指标
        
        Args:
            df: 数据DataFrame
        
        Returns:
            统计结果字典
        """
        if df.empty:
            return {"error": "数据为空"}
        
        values = df['value'].values
        
        return {
            "method": "statistical_analysis",
            "count": len(values),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "variance": float(np.var(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "q1": float(np.percentile(values, 25)),
            "q3": float(np.percentile(values, 75)),
            "iqr": float(np.percentile(values, 75) - np.percentile(values, 25)),
            "skewness": float(stats.skew(values)),
            "kurtosis": float(stats.kurtosis(values)),
            "time_range": {
                "start": df['timestamp'].iloc[0].isoformat(),
                "end": df['timestamp'].iloc[-1].isoformat()
            }
        }
    
    def trend_analysis(self, df: pd.DataFrame) -> Dict:
        """
        趋势分析 - 检测数据趋势
        
        Args:
            df: 数据DataFrame
        
        Returns:
            趋势分析结果
        """
        if df.empty or len(df) < 2:
            return {"error": "数据不足"}
        
        time_indices, values = self.prepare_time_series(df)
        
        # 线性回归计算趋势
        slope, intercept, r_value, p_value, std_err = stats.linregress(time_indices, values)
        
        # 判断趋势方向
        if abs(slope) < std_err:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        return {
            "method": "trend_analysis",
            "trend": trend,
            "slope": float(slope),
            "intercept": float(intercept),
            "correlation": float(r_value),
            "p_value": float(p_value),
            "std_error": float(std_err),
            "data_points": len(df)
        }
    
    def comprehensive_analysis(self, sensor_type: str, start_date: str, end_date: str,
                              predict_hours: int = 24, polynomial_degree: int = 2) -> Dict:
        """
        综合分析 - 执行所有分析方法
        
        Args:
            sensor_type: 传感器类型
            start_date: 开始日期
            end_date: 结束日期
            predict_hours: 预测小时数
            polynomial_degree: 多项式次数
        
        Returns:
            完整的分析结果
        """
        # 加载数据
        df = self.load_data_from_storage(sensor_type, start_date, end_date)
        
        if df.empty:
            return {
                "error": "没有找到数据",
                "sensor_type": sensor_type,
                "date_range": {"start": start_date, "end": end_date}
            }
        
        results = {
            "sensor_type": sensor_type,
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "data_summary": {
                "total_points": len(df),
                "time_range": {
                    "start": df['timestamp'].iloc[0].isoformat(),
                    "end": df['timestamp'].iloc[-1].isoformat()
                }
            }
        }
        
        # 统计分析
        try:
            results["statistical"] = self.statistical_analysis(df)
        except Exception as e:
            results["statistical"] = {"error": str(e)}
        
        # 趋势分析
        try:
            results["trend"] = self.trend_analysis(df)
        except Exception as e:
            results["trend"] = {"error": str(e)}
        
        # 线性回归
        try:
            results["linear_regression"] = self.linear_regression_analysis(df, predict_hours)
        except Exception as e:
            results["linear_regression"] = {"error": str(e)}
        
        # 多项式回归
        try:
            results["polynomial_regression"] = self.polynomial_regression_analysis(
                df, polynomial_degree, predict_hours
            )
        except Exception as e:
            results["polynomial_regression"] = {"error": str(e)}
        
        # 移动平均
        try:
            results["moving_average"] = self.moving_average_analysis(df, window=10, predict_hours=predict_hours)
        except Exception as e:
            results["moving_average"] = {"error": str(e)}
        
        return results

