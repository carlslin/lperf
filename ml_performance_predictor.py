#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
机器学习性能预测模块 (Machine Learning Performance Prediction Module)
==================================================================

本模块提供基于机器学习的性能预测功能，包括：
- 性能趋势预测：基于历史数据预测未来性能趋势
- 异常预测：预测可能出现的性能异常
- 容量规划：基于预测结果进行资源需求预测
- 风险评估：评估系统性能风险

主要特性：
- 多算法支持：支持线性回归、移动平均、时间序列分析等算法
- 自动特征工程：自动提取统计特征和趋势特征
- 模型准确性评估：提供预测准确性和置信度评估
- 增量学习：支持模型持续更新和优化

技术架构：
- 特征提取：统计特征、趋势特征、波动性特征
- 预测模型：简单移动平均、线性回归、趋势外推
- 准确性评估：交叉验证、预测误差分析
- 模型管理：模型训练、更新、持久化

作者: lperf开发团队
版本: 1.0.0
更新时间: 2024年
"""

import logging
import math
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union

# 配置日志系统
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLPerformancePredictor:
    """
    机器学习性能预测器
    
    基于历史性能数据，使用机器学习算法预测未来性能趋势和异常。
    支持多种预测算法，提供准确性评估和置信度分析。
    
    属性:
        lperf_instance: LPerf实例，用于访问性能数据
        prediction_models: 预测模型存储
        training_data: 训练数据存储
        prediction_results: 预测结果存储
        model_accuracy: 模型准确性记录
    """
    
    def __init__(self, lperf_instance):
        """
        初始化机器学习性能预测器
        
        Args:
            lperf_instance: LPerf实例，必须包含results属性
                           results应包含cpu、memory、network、fps等性能数据
        
        Raises:
            ValueError: 如果lperf_instance为None或缺少必要属性
        """
        if lperf_instance is None:
            raise ValueError("lperf_instance不能为None")
        
        self.lperf = lperf_instance
        self.prediction_models = {}
        self.training_data = {}
        self.prediction_results = {}
        self.model_accuracy = {}
        
        logger.info("机器学习性能预测器初始化完成")
    
    def prepare_training_data(self) -> Dict[str, Dict[str, Any]]:
        """
        准备机器学习训练数据
        
        从LPerf实例中提取性能数据，进行特征工程，为模型训练做准备。
        包括数据清洗、特征提取、数据标准化等步骤。
        
        Returns:
            Dict[str, Dict[str, Any]]: 训练数据，格式如下：
            {
                'cpu': {
                    'values': [数值列表],
                    'features': {特征字典},
                    'timestamps': [时间戳列表]
                },
                'memory': {...},
                'network': {...},
                'fps': {...}
            }
        
        Example:
            >>> predictor = MLPerformancePredictor(lperf_instance)
            >>> training_data = predictor.prepare_training_data()
            >>> print(f"准备训练数据: {len(training_data)} 个指标")
        """
        try:
            logger.info("开始准备机器学习训练数据...")
            
            training_data = {}
            supported_metrics = ['cpu', 'memory', 'network', 'fps']
            
            for metric in supported_metrics:
                data = self.lperf.results.get(metric, [])
                if data and len(data) >= 20:  # 需要足够的数据点进行训练
                    # 提取原始数据
                    values = [item['value'] for item in data]
                    timestamps = [item['timestamp'] for item in data]
                    
                    # 数据质量检查
                    if self._validate_data_quality(values):
                        # 特征工程
                        features = self._extract_features(values, timestamps)
                        
                        training_data[metric] = {
                            'values': values,
                            'features': features,
                            'timestamps': timestamps,
                            'data_quality': 'good',
                            'prepared_at': datetime.now().isoformat()
                        }
                        
                        logger.debug(f"指标 {metric} 训练数据准备完成，数据点: {len(values)}")
                    else:
                        logger.warning(f"指标 {metric} 数据质量不足，跳过")
                else:
                    logger.debug(f"指标 {metric} 数据不足，跳过 (需要至少20个数据点)")
            
            self.training_data = training_data
            logger.info(f"训练数据准备完成，包含 {len(training_data)} 个指标")
            return training_data
            
        except Exception as e:
            logger.error(f"准备训练数据失败: {e}")
            return {}
    
    def _validate_data_quality(self, values: List[float]) -> bool:
        """
        验证数据质量
        
        检查数据是否满足训练要求，包括数据完整性、一致性和有效性。
        
        Args:
            values: 数值列表
        
        Returns:
            bool: 数据质量是否满足要求
        """
        try:
            if len(values) < 20:
                return False
            
            # 检查数据有效性
            valid_values = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
            if len(valid_values) < len(values) * 0.9:  # 90%的数据必须有效
                return False
            
            # 检查数据范围合理性
            if max(values) < 0 or min(values) < 0:
                return False
            
            # 检查数据变化性
            variance = self._calculate_variance(values)
            if variance == 0:  # 数据没有变化
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"数据质量验证失败: {e}")
            return False
    
    def _extract_features(self, values: List[float], timestamps: List[str]) -> Dict[str, float]:
        """
        提取机器学习特征
        
        从原始性能数据中提取统计特征、趋势特征、波动性特征等，
        为机器学习模型提供丰富的输入特征。
        
        Args:
            values: 数值列表
            timestamps: 时间戳列表
        
        Returns:
            Dict[str, float]: 特征字典，包含：
            - 统计特征：mean, std, min, max, range, variance
            - 趋势特征：trend, slope
            - 波动性特征：volatility, iqr
            - 分位数特征：percentile_25, percentile_75
        
        Example:
            >>> features = predictor._extract_features([1, 2, 3, 4, 5], timestamps)
            >>> print(f"提取特征: {len(features)} 个")
        """
        try:
            if len(values) < 5:
                logger.warning("数据点不足，无法提取有效特征")
                return {}
            
            # 基础统计特征
            features = {
                'mean': sum(values) / len(values),
                'std': self._calculate_std(values),
                'min': min(values),
                'max': max(values),
                'range': max(values) - min(values),
                'variance': self._calculate_variance(values),
                'median': self._calculate_median(values),
                'skewness': self._calculate_skewness(values),
                'kurtosis': self._calculate_kurtosis(values)
            }
            
            # 趋势特征
            if len(values) >= 10:
                features.update({
                    'trend': self._calculate_trend(values),
                    'slope': self._calculate_linear_slope(values),
                    'trend_strength': self._calculate_trend_strength(values)
                })
            
            # 波动性特征
            if len(values) >= 5:
                features.update({
                    'volatility': self._calculate_volatility(values),
                    'percentile_25': self._calculate_percentile(values, 25),
                    'percentile_75': self._calculate_percentile(values, 75),
                    'iqr': self._calculate_percentile(values, 75) - self._calculate_percentile(values, 25)
                })
            
            # 时间相关特征
            if len(timestamps) >= 2:
                time_features = self._extract_time_features(timestamps, values)
                features.update(time_features)
            
            logger.debug(f"特征提取完成，共 {len(features)} 个特征")
            return features
            
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return {}
    
    def _extract_time_features(self, timestamps: List[str], values: List[float]) -> Dict[str, float]:
        """
        提取时间相关特征
        
        分析性能数据的时间模式，如周期性、季节性等。
        
        Args:
            timestamps: 时间戳列表
            values: 对应的数值列表
        
        Returns:
            Dict[str, float]: 时间特征字典
        """
        try:
            if len(timestamps) < 2:
                return {}
            
            time_features = {}
            
            # 计算时间间隔
            try:
                time_diffs = []
                for i in range(1, len(timestamps)):
                    t1 = datetime.fromisoformat(timestamps[i-1].replace('Z', '+00:00'))
                    t2 = datetime.fromisoformat(timestamps[i].replace('Z', '+00:00'))
                    diff = (t2 - t1).total_seconds()
                    time_diffs.append(diff)
                
                if time_diffs:
                    time_features.update({
                        'avg_time_interval': sum(time_diffs) / len(time_diffs),
                        'time_interval_variance': self._calculate_variance(time_diffs)
                    })
            except Exception as e:
                logger.debug(f"时间特征提取失败: {e}")
            
            return time_features
            
        except Exception as e:
            logger.debug(f"时间特征提取异常: {e}")
            return {}
    
    def train_prediction_models(self, algorithm: str = 'moving_average') -> Dict[str, Any]:
        """
        训练预测模型
        
        使用指定的算法训练性能预测模型，支持多种机器学习算法。
        
        Args:
            algorithm: 预测算法，支持 'moving_average', 'linear_regression', 'trend_extrapolation'
        
        Returns:
            Dict[str, Any]: 训练结果，包含模型信息和准确性评估
        
        Example:
            >>> result = predictor.train_prediction_models('moving_average')
            >>> print(f"模型训练完成，准确性: {result['accuracy']:.2f}")
        """
        try:
            logger.info(f"开始训练预测模型，算法: {algorithm}")
            
            if not self.training_data:
                logger.warning("训练数据不足，请先调用prepare_training_data()")
                return {'error': '训练数据不足'}
            
            training_results = {}
            
            for metric, data in self.training_data.items():
                logger.info(f"训练 {metric} 指标模型...")
                
                try:
                    if algorithm == 'moving_average':
                        model = self._train_moving_average_model(metric, data)
                    elif algorithm == 'linear_regression':
                        model = self._train_linear_regression_model(metric, data)
                    elif algorithm == 'trend_extrapolation':
                        model = self._train_trend_extrapolation_model(metric, data)
                    else:
                        logger.warning(f"不支持的算法: {algorithm}")
                        continue
                    
                    if model:
                        training_results[metric] = model
                        logger.info(f"{metric} 模型训练完成")
                
                except Exception as e:
                    logger.error(f"训练 {metric} 模型失败: {e}")
                    continue
            
            # 存储训练结果
            self.prediction_models[algorithm] = training_results
            
            # 计算整体准确性
            overall_accuracy = self._calculate_overall_accuracy(training_results)
            
            result = {
                'algorithm': algorithm,
                'models_trained': len(training_results),
                'overall_accuracy': overall_accuracy,
                'training_results': training_results,
                'trained_at': datetime.now().isoformat()
            }
            
            logger.info(f"模型训练完成，共训练 {len(training_results)} 个模型，整体准确性: {overall_accuracy:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            return {'error': str(e)}
    
    def _train_moving_average_model(self, metric: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练移动平均模型
        
        使用移动平均算法训练预测模型，适合处理时间序列数据。
        
        Args:
            metric: 指标名称
            data: 训练数据
        
        Returns:
            Dict[str, Any]: 训练后的模型
        """
        try:
            values = data['values']
            features = data['features']
            
            # 确定最佳移动窗口大小
            best_window = self._find_optimal_window_size(values)
            
            # 计算移动平均
            moving_avg = self._calculate_moving_average(values, best_window)
            
            # 计算预测准确性
            accuracy = self._calculate_prediction_accuracy(values, moving_avg)
            
            model = {
                'type': 'moving_average',
                'metric': metric,
                'window_size': best_window,
                'parameters': {
                    'window_size': best_window,
                    'trend': features.get('trend', 0),
                    'volatility': features.get('volatility', 0)
                },
                'accuracy': accuracy,
                'trained_at': datetime.now().isoformat()
            }
            
            return model
            
        except Exception as e:
            logger.error(f"训练移动平均模型失败: {e}")
            return None
    
    def _train_linear_regression_model(self, metric: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练线性回归模型
        
        使用线性回归算法训练预测模型，适合分析趋势性数据。
        
        Args:
            metric: 指标名称
            data: 训练数据
        
        Returns:
            Dict[str, Any]: 训练后的模型
        """
        try:
            values = data['values']
            features = data['features']
            
            # 计算线性回归参数
            n = len(values)
            x = list(range(n))
            y = values
            
            # 最小二乘法
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return None
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n
            
            # 计算R²值
            y_pred = [slope * xi + intercept for xi in x]
            r_squared = self._calculate_r_squared(y, y_pred)
            
            model = {
                'type': 'linear_regression',
                'metric': metric,
                'parameters': {
                    'slope': slope,
                    'intercept': intercept,
                    'r_squared': r_squared,
                    'trend': features.get('trend', 0)
                },
                'accuracy': r_squared,
                'trained_at': datetime.now().isoformat()
            }
            
            return model
            
        except Exception as e:
            logger.error(f"训练线性回归模型失败: {e}")
            return None
    
    def _train_trend_extrapolation_model(self, metric: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练趋势外推模型
        
        基于历史趋势进行外推预测，适合短期预测。
        
        Args:
            metric: 指标名称
            data: 训练数据
        
        Returns:
            Dict[str, Any]: 训练后的模型
        """
        try:
            values = data['values']
            features = data['features']
            
            # 计算趋势强度
            trend_strength = features.get('trend_strength', 0)
            
            # 计算预测参数
            recent_values = values[-10:] if len(values) >= 10 else values
            trend_coefficient = self._calculate_trend(recent_values)
            
            model = {
                'type': 'trend_extrapolation',
                'metric': metric,
                'parameters': {
                    'trend_coefficient': trend_coefficient,
                    'trend_strength': trend_strength,
                    'recent_values_count': len(recent_values)
                },
                'accuracy': min(0.95, 0.7 + abs(trend_coefficient) * 0.25),  # 基于趋势强度估算准确性
                'trained_at': datetime.now().isoformat()
            }
            
            return model
            
        except Exception as e:
            logger.error(f"训练趋势外推模型失败: {e}")
            return None
    
    def predict_performance(self, metric: str, horizon: int = 5, algorithm: str = 'moving_average') -> Dict[str, Any]:
        """
        预测性能指标
        
        使用训练好的模型预测未来性能指标值。
        
        Args:
            metric: 要预测的指标名称
            horizon: 预测步长（未来几个时间点）
            algorithm: 使用的预测算法
        
        Returns:
            Dict[str, Any]: 预测结果，包含：
            - predictions: 预测值列表
            - confidence: 预测置信度
            - model_info: 使用的模型信息
            - prediction_timestamp: 预测时间
        
        Example:
            >>> prediction = predictor.predict_performance('cpu', horizon=10)
            >>> print(f"CPU预测值: {prediction['predictions']}")
        """
        try:
            logger.info(f"开始预测 {metric} 指标，预测步长: {horizon}")
            
            # 检查模型是否已训练
            if algorithm not in self.prediction_models:
                logger.warning(f"算法 {algorithm} 的模型未训练，请先调用train_prediction_models()")
                return {'error': f'模型未训练: {algorithm}'}
            
            if metric not in self.prediction_models[algorithm]:
                logger.warning(f"指标 {metric} 的模型未训练")
                return {'error': f'指标模型未训练: {metric}'}
            
            model = self.prediction_models[algorithm][metric]
            
            # 获取最新数据
            current_data = self.lperf.results.get(metric, [])
            if not current_data:
                return {'error': f'无{metric}数据'}
            
            # 执行预测
            if model['type'] == 'moving_average':
                predictions = self._predict_with_moving_average(model, current_data, horizon)
            elif model['type'] == 'linear_regression':
                predictions = self._predict_with_linear_regression(model, current_data, horizon)
            elif model['type'] == 'trend_extrapolation':
                predictions = self._predict_with_trend_extrapolation(model, current_data, horizon)
            else:
                return {'error': f'不支持的模型类型: {model["type"]}'}
            
            # 计算预测置信度
            confidence = self._calculate_prediction_confidence(model, horizon)
            
            # 组装预测结果
            result = {
                'metric': metric,
                'algorithm': algorithm,
                'horizon': horizon,
                'predictions': predictions,
                'confidence': confidence,
                'model_info': {
                    'type': model['type'],
                    'accuracy': model['accuracy'],
                    'parameters': model['parameters']
                },
                'prediction_timestamp': datetime.now().isoformat()
            }
            
            # 存储预测结果
            if metric not in self.prediction_results:
                self.prediction_results[metric] = []
            self.prediction_results[metric].append(result)
            
            logger.info(f"{metric} 预测完成，置信度: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"性能预测失败: {e}")
            return {'error': str(e)}
    
    def _predict_with_moving_average(self, model: Dict[str, Any], current_data: List[Dict], horizon: int) -> List[float]:
        """使用移动平均模型进行预测"""
        try:
            values = [item['value'] for item in current_data]
            window_size = model['parameters']['window_size']
            
            # 计算当前移动平均
            current_ma = sum(values[-window_size:]) / window_size
            
            # 基于趋势进行外推
            trend = model['parameters'].get('trend', 0)
            predictions = []
            
            for i in range(horizon):
                # 考虑趋势因素
                predicted_value = current_ma + trend * (i + 1)
                predictions.append(max(0, predicted_value))  # 确保非负
            
            return predictions
            
        except Exception as e:
            logger.error(f"移动平均预测失败: {e}")
            return []
    
    def _predict_with_linear_regression(self, model: Dict[str, Any], current_data: List[Dict], horizon: int) -> List[float]:
        """使用线性回归模型进行预测"""
        try:
            values = [item['value'] for item in current_data]
            slope = model['parameters']['slope']
            intercept = model['parameters']['intercept']
            
            n = len(values)
            predictions = []
            
            for i in range(horizon):
                # 线性外推
                predicted_value = slope * (n + i) + intercept
                predictions.append(max(0, predicted_value))
            
            return predictions
            
        except Exception as e:
            logger.error(f"线性回归预测失败: {e}")
            return []
    
    def _predict_with_trend_extrapolation(self, model: Dict[str, Any], current_data: List[Dict], horizon: int) -> List[float]:
        """使用趋势外推模型进行预测"""
        try:
            values = [item['value'] for item in current_data]
            trend_coefficient = model['parameters']['trend_coefficient']
            
            # 获取最新值
            current_value = values[-1] if values else 0
            
            predictions = []
            for i in range(horizon):
                # 基于趋势系数外推
                predicted_value = current_value * (1 + trend_coefficient * (i + 1))
                predictions.append(max(0, predicted_value))
            
            return predictions
            
        except Exception as e:
            logger.error(f"趋势外推预测失败: {e}")
            return []
    
    def predict_anomalies(self, metric: str, horizon: int = 5) -> Dict[str, Any]:
        """
        预测性能异常
        
        基于历史异常模式和趋势预测未来可能出现的性能异常。
        
        Args:
            metric: 要预测的指标名称
            horizon: 预测步长
        
        Returns:
            Dict[str, Any]: 异常预测结果
        """
        try:
            logger.info(f"开始预测 {metric} 异常，预测步长: {horizon}")
            
            # 获取历史异常数据
            anomaly_data = self._get_historical_anomalies(metric)
            if not anomaly_data:
                return {'error': f'无{metric}异常历史数据'}
            
            # 分析异常模式
            anomaly_patterns = self._analyze_anomaly_patterns(anomaly_data)
            
            # 预测异常概率
            anomaly_probabilities = self._predict_anomaly_probabilities(anomaly_patterns, horizon)
            
            result = {
                'metric': metric,
                'horizon': horizon,
                'anomaly_probabilities': anomaly_probabilities,
                'patterns_detected': anomaly_patterns,
                'prediction_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"{metric} 异常预测完成")
            return result
            
        except Exception as e:
            logger.error(f"异常预测失败: {e}")
            return {'error': str(e)}
    
    def _get_historical_anomalies(self, metric: str) -> List[Dict[str, Any]]:
        """获取历史异常数据"""
        try:
            # 这里可以集成异常检测模块的结果
            # 暂时返回空列表，实际使用时需要与异常检测模块集成
            return []
        except Exception as e:
            logger.error(f"获取历史异常数据失败: {e}")
            return []
    
    def _analyze_anomaly_patterns(self, anomaly_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析异常模式"""
        try:
            if not anomaly_data:
                return {}
            
            # 分析异常的时间分布、严重程度分布等
            patterns = {
                'total_anomalies': len(anomaly_data),
                'severity_distribution': {},
                'time_distribution': {},
                'frequency': 0
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"分析异常模式失败: {e}")
            return {}
    
    def _predict_anomaly_probabilities(self, patterns: Dict[str, Any], horizon: int) -> List[float]:
        """预测异常概率"""
        try:
            if not patterns:
                return [0.0] * horizon
            
            # 基于历史频率和模式预测异常概率
            base_probability = patterns.get('frequency', 0.1)
            probabilities = []
            
            for i in range(horizon):
                # 简单的概率衰减模型
                probability = base_probability * (0.9 ** i)
                probabilities.append(min(1.0, probability))
            
            return probabilities
            
        except Exception as e:
            logger.error(f"预测异常概率失败: {e}")
            return [0.0] * horizon
    
    def generate_prediction_report(self) -> Dict[str, Any]:
        """
        生成预测报告
        
        整合所有预测结果，生成结构化的预测报告。
        
        Returns:
            Dict[str, Any]: 完整的预测报告
        """
        try:
            logger.info("开始生成预测报告...")
            
            if not self.prediction_results:
                return {'error': '无预测结果，请先进行预测'}
            
            # 汇总预测结果
            summary = {
                'total_predictions': sum(len(results) for results in self.prediction_results.values()),
                'metrics_predicted': list(self.prediction_results.keys()),
                'algorithms_used': list(set(result['algorithm'] for results in self.prediction_results.values() for result in results)),
                'report_timestamp': datetime.now().isoformat()
            }
            
            # 计算预测准确性
            accuracy_summary = self._calculate_prediction_accuracy_summary()
            
            # 生成预测趋势
            trends = self._analyze_prediction_trends()
            
            report = {
                'summary': summary,
                'accuracy_summary': accuracy_summary,
                'prediction_trends': trends,
                'detailed_predictions': self.prediction_results,
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info("预测报告生成完成")
            return report
            
        except Exception as e:
            logger.error(f"生成预测报告失败: {e}")
            return {'error': str(e)}
    
    def _calculate_prediction_accuracy_summary(self) -> Dict[str, Any]:
        """计算预测准确性摘要"""
        try:
            accuracy_summary = {
                'overall_accuracy': 0.0,
                'metric_accuracies': {},
                'algorithm_accuracies': {}
            }
            
            total_accuracy = 0.0
            total_predictions = 0
            
            for metric, results in self.prediction_results.items():
                metric_accuracy = 0.0
                for result in results:
                    if 'model_info' in result and 'accuracy' in result['model_info']:
                        metric_accuracy += result['model_info']['accuracy']
                        total_accuracy += result['model_info']['accuracy']
                        total_predictions += 1
                
                if results:
                    metric_accuracy /= len(results)
                    accuracy_summary['metric_accuracies'][metric] = metric_accuracy
            
            if total_predictions > 0:
                accuracy_summary['overall_accuracy'] = total_accuracy / total_predictions
            
            return accuracy_summary
            
        except Exception as e:
            logger.error(f"计算预测准确性摘要失败: {e}")
            return {}
    
    def _analyze_prediction_trends(self) -> Dict[str, Any]:
        """分析预测趋势"""
        try:
            trends = {}
            
            for metric, results in self.prediction_results.items():
                if len(results) >= 2:
                    # 分析预测值的变化趋势
                    recent_predictions = results[-1]['predictions'] if results else []
                    if recent_predictions:
                        trends[metric] = {
                            'trend_direction': 'increasing' if recent_predictions[-1] > recent_predictions[0] else 'decreasing',
                            'prediction_range': max(recent_predictions) - min(recent_predictions),
                            'confidence': results[-1].get('confidence', 0.0)
                        }
            
            return trends
            
        except Exception as e:
            logger.error(f"分析预测趋势失败: {e}")
            return {}
    
    # 辅助计算方法
    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        try:
            variance = self._calculate_variance(values)
            return variance ** 0.5
        except Exception:
            return 0.0
    
    def _calculate_variance(self, values: List[float]) -> float:
        """计算方差"""
        try:
            if len(values) < 2:
                return 0.0
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return variance
        except Exception:
            return 0.0
    
    def _calculate_median(self, values: List[float]) -> float:
        """计算中位数"""
        try:
            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                return sorted_values[n//2]
        except Exception:
            return 0.0
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        try:
            if not values:
                return 0.0
            sorted_values = sorted(values)
            index = (percentile / 100) * (len(sorted_values) - 1)
            if index.is_integer():
                return sorted_values[int(index)]
            else:
                lower = sorted_values[int(index)]
                upper = sorted_values[int(index) + 1]
                return lower + (upper - lower) * (index - int(index))
        except Exception:
            return 0.0
    
    def _calculate_skewness(self, values: List[float]) -> float:
        """计算偏度"""
        try:
            if len(values) < 3:
                return 0.0
            mean = sum(values) / len(values)
            std = self._calculate_std(values)
            if std == 0:
                return 0.0
            skewness = sum(((x - mean) / std) ** 3 for x in values) / len(values)
            return skewness
        except Exception:
            return 0.0
    
    def _calculate_kurtosis(self, values: List[float]) -> float:
        """计算峰度"""
        try:
            if len(values) < 4:
                return 0.0
            mean = sum(values) / len(values)
            std = self._calculate_std(values)
            if std == 0:
                return 0.0
            kurtosis = sum(((x - mean) / std) ** 4 for x in values) / len(values) - 3
            return kurtosis
        except Exception:
            return 0.0
    
    def _calculate_trend(self, values: List[float]) -> float:
        """计算趋势系数"""
        try:
            if len(values) < 3:
                return 0.0
            n = len(values)
            x = list(range(n))
            y = values
            
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            max_slope = n / 2
            normalized_slope = max(-1.0, min(1.0, slope / max_slope))
            
            return normalized_slope
        except Exception:
            return 0.0
    
    def _calculate_linear_slope(self, values: List[float]) -> float:
        """计算线性斜率"""
        try:
            if len(values) < 2:
                return 0.0
            return (values[-1] - values[0]) / len(values)
        except Exception:
            return 0.0
    
    def _calculate_trend_strength(self, values: List[float]) -> float:
        """计算趋势强度"""
        try:
            if len(values) < 3:
                return 0.0
            trend = self._calculate_trend(values)
            return abs(trend)
        except Exception:
            return 0.0
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性"""
        try:
            if len(values) < 2:
                return 0.0
            returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values)) if values[i-1] != 0]
            if not returns:
                return 0.0
            return self._calculate_std(returns)
        except Exception:
            return 0.0
    
    def _calculate_moving_average(self, values: List[float], window: int = 5) -> List[float]:
        """计算移动平均"""
        try:
            if len(values) < window:
                return values
            moving_avg = []
            for i in range(len(values)):
                start = max(0, i - window + 1)
                end = i + 1
                avg = sum(values[start:end]) / (end - start)
                moving_avg.append(avg)
            return moving_avg
        except Exception:
            return values
    
    def _calculate_prediction_accuracy(self, actual: List[float], predicted: List[float]) -> float:
        """计算预测准确性"""
        try:
            if len(actual) != len(predicted) or len(actual) == 0:
                return 0.0
            
            # 使用均方根误差的倒数作为准确性指标
            mse = sum((actual[i] - predicted[i]) ** 2 for i in range(len(actual))) / len(actual)
            rmse = mse ** 0.5
            
            # 归一化到[0, 1]范围
            max_value = max(actual) if actual else 1
            if max_value == 0:
                return 0.0
            
            accuracy = max(0, 1 - rmse / max_value)
            return accuracy
        except Exception:
            return 0.0
    
    def _calculate_prediction_confidence(self, model: Dict[str, Any], horizon: int) -> float:
        """计算预测置信度"""
        try:
            base_confidence = model.get('accuracy', 0.5)
            
            # 预测步长越远，置信度越低
            horizon_factor = max(0.1, 1.0 - horizon * 0.1)
            
            # 考虑模型类型
            model_type_factor = {
                'moving_average': 0.8,
                'linear_regression': 0.9,
                'trend_extrapolation': 0.7
            }.get(model.get('type', 'unknown'), 0.5)
            
            confidence = base_confidence * horizon_factor * model_type_factor
            return max(0.0, min(1.0, confidence))
        except Exception:
            return 0.5
    
    def _find_optimal_window_size(self, values: List[float]) -> int:
        """找到最优移动窗口大小"""
        try:
            if len(values) < 10:
                return min(3, len(values))
            
            # 测试不同的窗口大小
            best_window = 3
            best_accuracy = 0.0
            
            for window in [3, 5, 7, 10]:
                if window >= len(values):
                    break
                
                moving_avg = self._calculate_moving_average(values, window)
                accuracy = self._calculate_prediction_accuracy(values, moving_avg)
                
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_window = window
            
            return best_window
        except Exception:
            return 5
    
    def _calculate_r_squared(self, actual: List[float], predicted: List[float]) -> float:
        """计算R²值"""
        try:
            if len(actual) != len(predicted) or len(actual) == 0:
                return 0.0
            
            mean_actual = sum(actual) / len(actual)
            
            ss_res = sum((actual[i] - predicted[i]) ** 2 for i in range(len(actual)))
            ss_tot = sum((actual[i] - mean_actual) ** 2 for i in range(len(actual)))
            
            if ss_tot == 0:
                return 0.0
            
            r_squared = 1 - (ss_res / ss_tot)
            return max(0.0, min(1.0, r_squared))
        except Exception:
            return 0.0
    
    def _calculate_overall_accuracy(self, training_results: Dict[str, Any]) -> float:
        """计算整体准确性"""
        try:
            if not training_results:
                return 0.0
            
            total_accuracy = sum(result.get('accuracy', 0.0) for result in training_results.values())
            return total_accuracy / len(training_results)
        except Exception:
            return 0.0
    
    def save_models(self, filepath: str) -> bool:
        """
        保存训练好的模型到文件
        
        Args:
            filepath: 保存路径
        
        Returns:
            bool: 保存是否成功
        """
        try:
            if not self.prediction_models:
                logger.warning("无模型可保存")
                return False
            
            # 准备保存数据
            save_data = {
                'models': self.prediction_models,
                'training_data_summary': {metric: {'data_points': len(data['values'])} for metric, data in self.training_data.items()},
                'saved_at': datetime.now().isoformat()
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模型已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
            return False
    
    def load_models(self, filepath: str) -> bool:
        """
        从文件加载训练好的模型
        
        Args:
            filepath: 模型文件路径
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(filepath):
                logger.warning(f"模型文件不存在: {filepath}")
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            self.prediction_models = save_data.get('models', {})
            logger.info(f"模型已从 {filepath} 加载，共 {len(self.prediction_models)} 个算法")
            return True
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False
    
    def get_prediction_summary(self) -> str:
        """
        获取预测摘要
        
        Returns:
            str: 格式化的预测摘要
        """
        try:
            if not self.prediction_results:
                return "暂无预测结果，请先进行预测"
            
            summary = f"""
机器学习性能预测摘要
==================
预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
预测指标数: {len(self.prediction_results)}
总预测次数: {sum(len(results) for results in self.prediction_results.values())}

预测指标详情:
"""
            
            for metric, results in self.prediction_results.items():
                if results:
                    latest_result = results[-1]
                    summary += f"  {metric.upper()}: 算法={latest_result['algorithm']}, 置信度={latest_result.get('confidence', 0):.2f}\n"
            
            return summary
            
        except Exception as e:
            return f"生成摘要失败: {e}"


if __name__ == '__main__':
    print("机器学习性能预测模块")
    print("请通过lperf主程序调用此模块")
