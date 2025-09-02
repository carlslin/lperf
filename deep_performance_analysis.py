#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
深度性能分析模块 (Deep Performance Analysis Module)
==================================================

本模块提供全面的性能分析功能，包括：
- 性能瓶颈分析：识别CPU、内存、网络、FPS等性能瓶颈
- 趋势分析：分析性能指标的变化趋势和模式
- 异常检测：基于统计方法检测性能异常
- 智能建议：提供性能优化建议

主要特性：
- 多维度瓶颈分析：支持CPU、内存、网络、FPS、系统等多个维度
- 智能阈值检测：自动识别高使用率、高波动性等异常情况
- 趋势预测：基于历史数据分析性能变化趋势
- 可配置分析：支持自定义阈值和分析参数

作者: lperf开发团队
版本: 1.0.0
更新时间: 2024年
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# 配置日志系统
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepPerformanceAnalyzer:
    """
    深度性能分析器
    
    提供全面的性能分析功能，包括瓶颈分析、趋势分析、异常检测等。
    基于统计学和机器学习算法，能够智能识别性能问题并提供优化建议。
    
    属性:
        lperf_instance: LPerf实例，用于访问性能数据
        analysis_results: 分析结果存储
        performance_patterns: 性能模式识别结果
        bottleneck_analysis: 瓶颈分析结果
        trend_analysis: 趋势分析结果
        anomaly_detection: 异常检测结果
    """
    
    def __init__(self, lperf_instance):
        """
        初始化深度性能分析器
        
        Args:
            lperf_instance: LPerf实例，必须包含results属性
                           results应包含cpu、memory、network、fps等性能数据
        
        Raises:
            ValueError: 如果lperf_instance为None或缺少必要属性
        """
        if lperf_instance is None:
            raise ValueError("lperf_instance不能为None")
        
        self.lperf = lperf_instance
        self.analysis_results = {}
        self.performance_patterns = {}
        self.bottleneck_analysis = {}
        self.trend_analysis = {}
        self.anomaly_detection = {}
        
        logger.info("深度性能分析器初始化完成")
    
    def analyze_performance_bottlenecks(self) -> Dict[str, List[Dict]]:
        """
        分析性能瓶颈
        
        综合分析CPU、内存、网络、FPS、系统等各个维度的性能瓶颈，
        识别高使用率、高波动性、异常模式等问题。
        
        Returns:
            Dict[str, List[Dict]]: 瓶颈分析结果，格式如下：
            {
                'cpu_bottlenecks': [CPU瓶颈列表],
                'memory_bottlenecks': [内存瓶颈列表],
                'network_bottlenecks': [网络瓶颈列表],
                'fps_bottlenecks': [FPS瓶颈列表],
                'system_bottlenecks': [系统瓶颈列表]
            }
        
        Example:
            >>> analyzer = DeepPerformanceAnalyzer(lperf_instance)
            >>> bottlenecks = analyzer.analyze_performance_bottlenecks()
            >>> print(f"发现 {len(bottlenecks['cpu_bottlenecks'])} 个CPU瓶颈")
        """
        try:
            logger.info("开始分析性能瓶颈...")
            
            # 并行分析各个维度的性能瓶颈
            bottlenecks = {
                'cpu_bottlenecks': self._analyze_cpu_bottlenecks(),
                'memory_bottlenecks': self._analyze_memory_bottlenecks(),
                'network_bottlenecks': self._analyze_network_bottlenecks(),
                'fps_bottlenecks': self._analyze_fps_bottlenecks(),
                'system_bottlenecks': self._analyze_system_bottlenecks()
            }
            
            # 存储分析结果
            self.bottleneck_analysis = bottlenecks
            
            # 统计瓶颈数量
            total_bottlenecks = sum(len(bottlenecks[key]) for key in bottlenecks)
            logger.info(f"性能瓶颈分析完成，共发现 {total_bottlenecks} 个瓶颈")
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"性能瓶颈分析失败: {e}")
            return {}
    
    def _analyze_cpu_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        分析CPU性能瓶颈
        
        检测CPU使用率过高、波动性过大等问题，识别可能导致性能下降的CPU瓶颈。
        
        Returns:
            List[Dict[str, Any]]: CPU瓶颈列表，每个瓶颈包含：
            - type: 瓶颈类型 (high_cpu_usage, cpu_volatility等)
            - severity: 严重程度 (high, medium, low)
            - description: 瓶颈描述
            - periods: 问题发生的时间段
            - max_value: 最大值
            - avg_value: 平均值
            - recommendation: 优化建议
        
        Example:
            >>> bottlenecks = analyzer._analyze_cpu_bottlenecks()
            >>> for bottleneck in bottlenecks:
            ...     print(f"CPU瓶颈: {bottleneck['description']}")
        """
        try:
            # 获取CPU性能数据
            cpu_data = self.lperf.results.get('cpu', [])
            if not cpu_data:
                logger.debug("未找到CPU数据，跳过CPU瓶颈分析")
                return []
            
            bottlenecks = []
            cpu_values = [item['value'] for item in cpu_data]
            
            # 检测1: 高CPU使用率
            high_cpu_threshold = 80.0  # 可配置的阈值
            high_cpu_periods = [i for i, val in enumerate(cpu_values) if val > high_cpu_threshold]
            
            if high_cpu_periods:
                max_cpu = max(cpu_values)
                avg_cpu = sum(cpu_values) / len(cpu_values)
                
                bottlenecks.append({
                    'type': 'high_cpu_usage',
                    'severity': 'high' if max_cpu > 95 else 'medium',
                    'description': f'CPU使用率超过{high_cpu_threshold}%',
                    'periods': high_cpu_periods,
                    'max_value': max_cpu,
                    'avg_value': avg_cpu,
                    'threshold': high_cpu_threshold,
                    'recommendation': '检查后台进程、定时任务和CPU密集型操作',
                    'detected_at': datetime.now().isoformat()
                })
                
                logger.info(f"检测到高CPU使用率瓶颈: 最大值={max_cpu:.1f}%, 平均值={avg_cpu:.1f}%")
            
            # 检测2: CPU使用率波动性
            if len(cpu_values) > 10:  # 需要足够的数据点进行分析
                cpu_variance = self._calculate_variance(cpu_values)
                volatility_threshold = 100  # 波动性阈值
                
                if cpu_variance > volatility_threshold:
                    bottlenecks.append({
                        'type': 'cpu_volatility',
                        'severity': 'medium',
                        'description': 'CPU使用率波动较大',
                        'variance': cpu_variance,
                        'threshold': volatility_threshold,
                        'recommendation': '检查后台进程和定时任务，优化CPU调度',
                        'detected_at': datetime.now().isoformat()
                    })
                    
                    logger.info(f"检测到CPU波动性瓶颈: 方差={cpu_variance:.2f}")
            
            # 检测3: CPU使用率趋势异常
            if len(cpu_values) > 20:
                trend = self._calculate_trend(cpu_values)
                if trend > 0.5:  # 上升趋势明显
                    bottlenecks.append({
                        'type': 'cpu_trend_increase',
                        'severity': 'medium',
                        'description': 'CPU使用率呈上升趋势',
                        'trend': trend,
                        'recommendation': '检查是否存在内存泄漏或资源竞争',
                        'detected_at': datetime.now().isoformat()
                    })
                    
                    logger.info(f"检测到CPU上升趋势: 趋势系数={trend:.3f}")
            
            logger.debug(f"CPU瓶颈分析完成，发现 {len(bottlenecks)} 个瓶颈")
            return bottlenecks
            
        except Exception as e:
            logger.error(f"CPU瓶颈分析失败: {e}")
            return []
    
    def _analyze_memory_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        分析内存性能瓶颈
        
        检测内存使用过高、内存泄漏、内存碎片化等问题。
        
        Returns:
            List[Dict[str, Any]]: 内存瓶颈列表
        """
        try:
            memory_data = self.lperf.results.get('memory', [])
            if not memory_data:
                return []
            
            bottlenecks = []
            memory_values = [item['value'] for item in memory_data]
            
            # 检测高内存使用率
            high_memory_threshold = 85.0  # MB
            high_memory_periods = [i for i, val in enumerate(memory_values) if val > high_memory_threshold]
            
            if high_memory_periods:
                max_memory = max(memory_values)
                avg_memory = sum(memory_values) / len(memory_values)
                
                bottlenecks.append({
                    'type': 'high_memory_usage',
                    'severity': 'high' if max_memory > 200 else 'medium',
                    'description': f'内存使用超过{high_memory_threshold}MB',
                    'periods': high_memory_periods,
                    'max_value': max_memory,
                    'avg_value': avg_memory,
                    'threshold': high_memory_threshold,
                    'recommendation': '检查内存泄漏、优化内存分配策略',
                    'detected_at': datetime.now().isoformat()
                })
            
            # 检测内存增长趋势
            if len(memory_values) > 15:
                trend = self._calculate_trend(memory_values)
                if trend > 0.3:  # 内存持续增长
                    bottlenecks.append({
                        'type': 'memory_growth_trend',
                        'severity': 'high',
                        'description': '内存使用呈持续增长趋势',
                        'trend': trend,
                        'recommendation': '可能存在内存泄漏，建议检查对象引用',
                        'detected_at': datetime.now().isoformat()
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"内存瓶颈分析失败: {e}")
            return []
    
    def _analyze_network_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        分析网络性能瓶颈
        
        检测网络流量异常、连接问题、延迟过高等问题。
        
        Returns:
            List[Dict[str, Any]]: 网络瓶颈列表
        """
        try:
            network_data = self.lperf.results.get('network', [])
            if not network_data:
                return []
            
            bottlenecks = []
            network_values = [item['value'] for item in network_data]
            
            # 检测网络流量异常
            if len(network_values) > 10:
                avg_network = sum(network_values) / len(network_values)
                network_variance = self._calculate_variance(network_values)
                
                # 检测流量突增
                if network_variance > 1000:  # 流量波动较大
                    bottlenecks.append({
                        'type': 'network_volatility',
                        'severity': 'medium',
                        'description': '网络流量波动较大',
                        'variance': network_variance,
                        'avg_value': avg_network,
                        'recommendation': '检查网络连接稳定性和后台网络活动',
                        'detected_at': datetime.now().isoformat()
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"网络瓶颈分析失败: {e}")
            return []
    
    def _analyze_fps_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        分析FPS性能瓶颈
        
        检测帧率过低、卡顿、掉帧等问题。
        
        Returns:
            List[Dict[str, Any]]: FPS瓶颈列表
        """
        try:
            fps_data = self.lperf.results.get('fps', [])
            if not fps_data:
                return []
            
            bottlenecks = []
            fps_values = [item['value'] for item in fps_data]
            
            # 检测低帧率
            low_fps_threshold = 30.0
            low_fps_periods = [i for i, val in enumerate(fps_values) if val < low_fps_threshold]
            
            if low_fps_periods:
                min_fps = min(fps_values)
                avg_fps = sum(fps_values) / len(fps_values)
                
                bottlenecks.append({
                    'type': 'low_fps',
                    'severity': 'high' if min_fps < 20 else 'medium',
                    'description': f'FPS低于{low_fps_threshold}帧',
                    'periods': low_fps_periods,
                    'min_value': min_fps,
                    'avg_value': avg_fps,
                    'threshold': low_fps_threshold,
                    'recommendation': '优化渲染性能、减少UI复杂度、检查GPU使用',
                    'detected_at': datetime.now().isoformat()
                })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"FPS瓶颈分析失败: {e}")
            return []
    
    def _analyze_system_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        分析系统级性能瓶颈
        
        检测启动时间过长、电池消耗过快、系统负载过高等问题。
        
        Returns:
            List[Dict[str, Any]]: 系统瓶颈列表
        """
        try:
            bottlenecks = []
            
            # 检测启动时间问题
            startup_data = self.lperf.results.get('startup_time', [])
            if startup_data:
                startup_time = startup_data[0]['value'] if startup_data else 0
                if startup_time > 5.0:  # 启动时间超过5秒
                    bottlenecks.append({
                        'type': 'slow_startup',
                        'severity': 'medium',
                        'description': f'应用启动时间过长: {startup_time:.2f}秒',
                        'value': startup_time,
                        'threshold': 5.0,
                        'recommendation': '优化启动流程、延迟加载非关键资源',
                        'detected_at': datetime.now().isoformat()
                    })
            
            # 检测电池消耗问题
            battery_data = self.lperf.results.get('battery', [])
            if battery_data and len(battery_data) > 10:
                battery_values = [item['value'] for item in battery_data]
                battery_drop = battery_values[0] - battery_values[-1]
                
                if battery_drop > 20:  # 电池消耗过快
                    bottlenecks.append({
                        'type': 'high_battery_consumption',
                        'severity': 'medium',
                        'description': f'电池消耗过快: {battery_drop:.1f}%',
                        'value': battery_drop,
                        'threshold': 20.0,
                        'recommendation': '优化后台进程、减少网络和定位服务使用',
                        'detected_at': datetime.now().isoformat()
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"系统瓶颈分析失败: {e}")
            return []
    
    def analyze_performance_trends(self) -> Dict[str, Dict[str, Any]]:
        """
        分析性能趋势
        
        分析各个性能指标的变化趋势，识别性能改善或恶化模式。
        
        Returns:
            Dict[str, Dict[str, Any]]: 趋势分析结果
        """
        try:
            logger.info("开始分析性能趋势...")
            
            trends = {}
            for metric in ['cpu', 'memory', 'network', 'fps']:
                data = self.lperf.results.get(metric, [])
                if data and len(data) > 10:
                    values = [item['value'] for item in data]
                    trend_info = self._analyze_single_trend(metric, values)
                    trends[metric] = trend_info
            
            self.trend_analysis = trends
            logger.info("性能趋势分析完成")
            return trends
            
        except Exception as e:
            logger.error(f"性能趋势分析失败: {e}")
            return {}
    
    def _analyze_single_trend(self, metric: str, values: List[float]) -> Dict[str, Any]:
        """
        分析单个指标的趋势
        
        Args:
            metric: 指标名称
            values: 指标值列表
        
        Returns:
            Dict[str, Any]: 趋势分析结果
        """
        try:
            if len(values) < 5:
                return {'status': 'insufficient_data'}
            
            # 计算趋势系数
            trend_coefficient = self._calculate_trend(values)
            
            # 计算移动平均
            moving_avg = self._calculate_moving_average(values, window=5)
            
            # 判断趋势方向
            if trend_coefficient > 0.1:
                trend_direction = 'increasing'
                trend_description = '性能指标呈上升趋势'
            elif trend_coefficient < -0.1:
                trend_direction = 'decreasing'
                trend_description = '性能指标呈下降趋势'
            else:
                trend_direction = 'stable'
                trend_description = '性能指标相对稳定'
            
            return {
                'metric': metric,
                'trend_coefficient': trend_coefficient,
                'trend_direction': trend_direction,
                'trend_description': trend_description,
                'moving_average': moving_avg,
                'data_points': len(values),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"分析{metric}趋势失败: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def detect_anomalies(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        检测性能异常
        
        基于3-sigma规则和统计方法检测性能异常。
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: 异常检测结果
        """
        try:
            logger.info("开始检测性能异常...")
            
            anomalies = {}
            for metric in ['cpu', 'memory', 'network', 'fps']:
                data = self.lperf.results.get(metric, [])
                if data and len(data) > 20:
                    values = [item['value'] for item in data]
                    metric_anomalies = self._detect_metric_anomalies(metric, values)
                    if metric_anomalies:
                        anomalies[metric] = metric_anomalies
            
            self.anomaly_detection = anomalies
            logger.info("性能异常检测完成")
            return anomalies
            
        except Exception as e:
            logger.error(f"性能异常检测失败: {e}")
            return {}
    
    def _detect_metric_anomalies(self, metric: str, values: List[float]) -> List[Dict[str, Any]]:
        """
        检测单个指标的异常
        
        使用3-sigma规则检测异常值。
        
        Args:
            metric: 指标名称
            values: 指标值列表
        
        Returns:
            List[Dict[str, Any]]: 异常列表
        """
        try:
            if len(values) < 20:
                return []
            
            mean = sum(values) / len(values)
            std = self._calculate_std(values)
            
            if std == 0:
                return []
            
            anomalies = []
            threshold = 3  # 3-sigma规则
            
            for i, value in enumerate(values):
                z_score = abs((value - mean) / std)
                if z_score > threshold:
                    anomalies.append({
                        'metric': metric,
                        'index': i,
                        'value': value,
                        'z_score': z_score,
                        'mean': mean,
                        'std': std,
                        'threshold': threshold,
                        'description': f'{metric}异常值: {value:.2f} (Z-score: {z_score:.2f})',
                        'detected_at': datetime.now().isoformat()
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测{metric}异常失败: {e}")
            return []
    
    def generate_analysis_report(self) -> Dict[str, Any]:
        """
        生成完整的分析报告
        
        整合所有分析结果，生成结构化的分析报告。
        
        Returns:
            Dict[str, Any]: 完整的分析报告
        """
        try:
            logger.info("生成性能分析报告...")
            
            # 执行所有分析
            bottlenecks = self.analyze_performance_bottlenecks()
            trends = self.analyze_performance_trends()
            anomalies = self.detect_anomalies()
            
            # 生成摘要统计
            summary = {
                'total_bottlenecks': sum(len(bottlenecks[key]) for key in bottlenecks),
                'total_anomalies': sum(len(anomalies[key]) for key in anomalies),
                'analysis_timestamp': datetime.now().isoformat(),
                'data_points': self._count_total_data_points()
            }
            
            # 生成优化建议
            recommendations = self._generate_recommendations(bottlenecks, trends, anomalies)
            
            # 组装完整报告
            report = {
                'summary': summary,
                'bottlenecks': bottlenecks,
                'trends': trends,
                'anomalies': anomalies,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
            self.analysis_results = report
            logger.info("性能分析报告生成完成")
            return report
            
        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, bottlenecks: Dict, trends: Dict, anomalies: Dict) -> List[str]:
        """
        生成优化建议
        
        基于分析结果生成具体的优化建议。
        
        Args:
            bottlenecks: 瓶颈分析结果
            trends: 趋势分析结果
            anomalies: 异常检测结果
        
        Returns:
            List[str]: 优化建议列表
        """
        recommendations = []
        
        # 基于瓶颈分析生成建议
        for metric, metric_bottlenecks in bottlenecks.items():
            for bottleneck in metric_bottlenecks:
                if 'recommendation' in bottleneck:
                    recommendations.append(f"[{metric.upper()}] {bottleneck['recommendation']}")
        
        # 基于趋势分析生成建议
        for metric, trend_info in trends.items():
            if trend_info.get('trend_direction') == 'decreasing':
                recommendations.append(f"[{metric.upper()}] 性能呈下降趋势，建议检查资源使用和优化策略")
        
        # 基于异常检测生成建议
        for metric, metric_anomalies in anomalies.items():
            if metric_anomalies:
                recommendations.append(f"[{metric.upper()}] 检测到{len(metric_anomalies)}个异常值，建议检查数据质量和系统状态")
        
        # 添加通用建议
        if not recommendations:
            recommendations.append("性能表现良好，建议继续保持当前的优化策略")
        
        return recommendations
    
    def _count_total_data_points(self) -> int:
        """统计总数据点数"""
        total = 0
        for metric in ['cpu', 'memory', 'network', 'fps', 'battery']:
            data = self.lperf.results.get(metric, [])
            total += len(data)
        return total
    
    # 统计计算方法
    def _calculate_variance(self, values: List[float]) -> float:
        """
        计算方差
        
        Args:
            values: 数值列表
        
        Returns:
            float: 方差值
        """
        try:
            if len(values) < 2:
                return 0.0
            
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return variance
            
        except Exception:
            return 0.0
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        计算趋势系数
        
        使用线性回归计算趋势，正值表示上升趋势，负值表示下降趋势。
        
        Args:
            values: 数值列表
        
        Returns:
            float: 趋势系数，范围通常在[-1, 1]之间
        """
        try:
            if len(values) < 3:
                return 0.0
            
            n = len(values)
            x = list(range(n))
            y = values
            
            # 计算线性回归系数
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            # 避免除零错误
            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            
            # 归一化到[-1, 1]范围
            max_slope = n / 2
            normalized_slope = max(-1.0, min(1.0, slope / max_slope))
            
            return normalized_slope
            
        except Exception:
            return 0.0
    
    def _calculate_moving_average(self, values: List[float], window: int = 5) -> List[float]:
        """
        计算移动平均
        
        Args:
            values: 数值列表
            window: 移动窗口大小
        
        Returns:
            List[float]: 移动平均值列表
        """
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
    
    def get_analysis_summary(self) -> str:
        """
        获取分析摘要
        
        Returns:
            str: 格式化的分析摘要
        """
        try:
            if not self.analysis_results:
                return "暂无分析结果，请先运行分析"
            
            summary = self.analysis_results.get('summary', {})
            bottlenecks = self.analysis_results.get('bottlenecks', {})
            anomalies = self.analysis_results.get('anomalies', {})
            
            report = f"""
性能分析摘要
============
分析时间: {summary.get('analysis_timestamp', 'N/A')}
数据点数: {summary.get('data_points', 0)}
发现瓶颈: {summary.get('total_bottlenecks', 0)}个
发现异常: {summary.get('total_anomalies', 0)}个

瓶颈分布:
"""
            
            for metric, metric_bottlenecks in bottlenecks.items():
                if metric_bottlenecks:
                    report += f"  {metric.upper()}: {len(metric_bottlenecks)}个\n"
            
            if anomalies:
                report += "\n异常分布:\n"
                for metric, metric_anomalies in anomalies.items():
                    if metric_anomalies:
                        report += f"  {metric.upper()}: {len(metric_anomalies)}个\n"
            
            return report
            
        except Exception as e:
            return f"生成摘要失败: {e}"
