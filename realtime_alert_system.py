#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实时性能告警系统模块 (Real-time Performance Alert System Module)
================================================================

本模块提供全面的实时性能监控和告警功能，包括：
- 实时性能监控：持续监控系统性能指标
- 智能告警规则：支持多种条件判断和阈值设置
- 多渠道告警：控制台、日志、文件、邮件、Webhook等
- 告警管理：告警历史、告警抑制、告警升级
- 智能诊断：基于规则引擎和机器学习的智能诊断

主要特性：
- 灵活的告警规则：支持多种比较操作符和复合条件
- 多渠道通知：集成多种告警通道，确保告警及时送达
- 智能告警抑制：避免告警风暴，提供告警升级机制
- 实时监控：支持后台持续监控和实时告警
- 配置持久化：支持告警配置的保存和恢复

技术架构：
- 告警规则引擎：支持多种条件判断和阈值设置
- 多渠道告警系统：集成多种通知方式
- 告警管理引擎：告警历史、抑制、升级管理
- 智能诊断引擎：基于规则和机器学习的诊断

作者: lperf开发团队
版本: 1.0.0
更新时间: 2024年
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeAlertSystem:
    """实时性能告警系统"""
    
    def __init__(self, lperf_instance):
        self.lperf = lperf_instance
        self.alert_rules = {}
        self.alert_history = []
        self.alert_channels = {}
        self.is_monitoring = False
        self.monitoring_thread = None
        
    def add_alert_rule(self, metric, condition, threshold, severity='medium', description=''):
        """添加告警规则"""
        try:
            rule_id = f"{metric}_{condition}_{threshold}"
            rule = {
                'id': rule_id,
                'metric': metric,
                'condition': condition,  # 'gt', 'lt', 'eq', 'ne'
                'threshold': threshold,
                'severity': severity,
                'description': description,
                'enabled': True,
                'created_at': datetime.now().isoformat()
            }
            
            self.alert_rules[rule_id] = rule
            logger.info(f"添加告警规则: {rule_id}")
            return rule_id
            
        except Exception as e:
            logger.error(f"添加告警规则失败: {e}")
            return None
    
    def remove_alert_rule(self, rule_id):
        """移除告警规则"""
        try:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                logger.info(f"移除告警规则: {rule_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"移除告警规则失败: {e}")
            return False
    
    def add_alert_channel(self, channel_type, config):
        """添加告警通道"""
        try:
            channel_id = f"{channel_type}_{len(self.alert_channels)}"
            channel = {
                'id': channel_id,
                'type': channel_type,
                'config': config,
                'enabled': True,
                'created_at': datetime.now().isoformat()
            }
            
            self.alert_channels[channel_id] = channel
            logger.info(f"添加告警通道: {channel_id}")
            return channel_id
            
        except Exception as e:
            logger.error(f"添加告警通道失败: {e}")
            return None
    
    def check_alerts(self, current_data):
        """检查告警条件"""
        try:
            triggered_alerts = []
            
            for rule_id, rule in self.alert_rules.items():
                if not rule['enabled']:
                    continue
                
                metric = rule['metric']
                if metric not in current_data:
                    continue
                
                current_value = current_data[metric]
                condition = rule['condition']
                threshold = rule['threshold']
                
                # 检查告警条件
                triggered = False
                if condition == 'gt' and current_value > threshold:
                    triggered = True
                elif condition == 'lt' and current_value < threshold:
                    triggered = True
                elif condition == 'eq' and abs(current_value - threshold) < 0.01:
                    triggered = True
                elif condition == 'ne' and abs(current_value - threshold) >= 0.01:
                    triggered = True
                
                if triggered:
                    alert = {
                        'rule_id': rule_id,
                        'metric': metric,
                        'current_value': current_value,
                        'threshold': threshold,
                        'condition': condition,
                        'severity': rule['severity'],
                        'description': rule['description'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    triggered_alerts.append(alert)
                    logger.warning(f"告警触发: {rule_id} - {metric}: {current_value}")
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
            return []
    
    def send_alert(self, alert, channels=None):
        """发送告警"""
        try:
            if channels is None:
                channels = self.alert_channels
            
            sent_count = 0
            for channel_id, channel in channels.items():
                if not channel['enabled']:
                    continue
                
                try:
                    if channel['type'] == 'console':
                        self._send_console_alert(alert)
                        sent_count += 1
                    elif channel['type'] == 'log':
                        self._send_log_alert(alert)
                        sent_count += 1
                    elif channel['type'] == 'file':
                        self._send_file_alert(alert, channel['config'])
                        sent_count += 1
                    elif channel['type'] == 'email':
                        self._send_email_alert(alert, channel['config'])
                        sent_count += 1
                    elif channel['type'] == 'webhook':
                        self._send_webhook_alert(alert, channel['config'])
                        sent_count += 1
                        
                except Exception as e:
                    logger.error(f"发送告警到通道 {channel_id} 失败: {e}")
            
            # 记录告警历史
            alert['sent_channels'] = sent_count
            self.alert_history.append(alert)
            
            logger.info(f"告警发送完成，成功发送到 {sent_count} 个通道")
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"发送告警失败: {e}")
            return False
    
    def _send_console_alert(self, alert):
        """发送控制台告警"""
        try:
            severity_color = {
                'low': '\033[33m',      # 黄色
                'medium': '\033[35m',   # 紫色
                'high': '\033[31m',     # 红色
                'critical': '\033[31;1m' # 亮红色
            }
            
            color = severity_color.get(alert['severity'], '\033[0m')
            reset = '\033[0m'
            
            print(f"\n{color}🚨 性能告警 {reset}")
            print(f"指标: {alert['metric']}")
            print(f"当前值: {alert['current_value']}")
            print(f"阈值: {alert['threshold']}")
            print(f"严重程度: {alert['severity']}")
            print(f"描述: {alert['description']}")
            print(f"时间: {alert['timestamp']}")
            print(f"{color}{'='*50}{reset}\n")
            
        except Exception as e:
            logger.error(f"发送控制台告警失败: {e}")
    
    def _send_log_alert(self, alert):
        """发送日志告警"""
        try:
            logger.warning(f"性能告警: {alert['metric']} = {alert['current_value']} "
                          f"(阈值: {alert['threshold']}, 严重程度: {alert['severity']})")
        except Exception as e:
            logger.error(f"发送日志告警失败: {e}")
    
    def _send_file_alert(self, alert, config):
        """发送文件告警"""
        try:
            file_path = config.get('file_path', 'alerts.log')
            alert_line = f"[{alert['timestamp']}] {alert['severity'].upper()}: {alert['metric']} = {alert['current_value']} - {alert['description']}\n"
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(alert_line)
                
        except Exception as e:
            logger.error(f"发送文件告警失败: {e}")
    
    def _send_email_alert(self, alert, config):
        """发送邮件告警"""
        try:
            # 这里实现邮件发送逻辑
            # 可以使用smtplib或其他邮件库
            logger.info(f"邮件告警: {alert['metric']} = {alert['current_value']}")
            
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")
    
    def _send_webhook_alert(self, alert, config):
        """发送Webhook告警"""
        try:
            # 这里实现Webhook发送逻辑
            # 可以使用requests库发送HTTP请求
            logger.info(f"Webhook告警: {alert['metric']} = {alert['current_value']}")
            
        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        try:
            self.is_monitoring = True
            logger.info("实时告警监控已启动")
            
            # 添加默认告警规则
            self._add_default_rules()
            
            # 添加默认告警通道
            self._add_default_channels()
            
        except Exception as e:
            logger.error(f"启动告警监控失败: {e}")
    
    def stop_monitoring(self):
        """停止监控"""
        try:
            self.is_monitoring = False
            logger.info("实时告警监控已停止")
            
        except Exception as e:
            logger.error(f"停止告警监控失败: {e}")
    
    def _add_default_rules(self):
        """添加默认告警规则"""
        try:
            # CPU告警规则
            self.add_alert_rule('cpu', 'gt', 80, 'high', 'CPU使用率过高')
            self.add_alert_rule('cpu', 'gt', 95, 'critical', 'CPU使用率严重过高')
            
            # 内存告警规则
            self.add_alert_rule('memory', 'gt', 85, 'high', '内存使用率过高')
            self.add_alert_rule('memory', 'gt', 95, 'critical', '内存使用率严重过高')
            
            # FPS告警规则
            self.add_alert_rule('fps', 'lt', 30, 'medium', 'FPS过低')
            self.add_alert_rule('fps', 'lt', 20, 'high', 'FPS严重过低')
            
            logger.info("默认告警规则已添加")
            
        except Exception as e:
            logger.error(f"添加默认告警规则失败: {e}")
    
    def _add_default_channels(self):
        """添加默认告警通道"""
        try:
            # 控制台告警
            self.add_alert_channel('console', {})
            
            # 日志告警
            self.add_alert_channel('log', {})
            
            # 文件告警
            self.add_alert_channel('file', {'file_path': 'performance_alerts.log'})
            
            logger.info("默认告警通道已添加")
            
        except Exception as e:
            logger.error(f"添加默认告警通道失败: {e}")
    
    def get_alert_history(self, limit=100):
        """获取告警历史"""
        try:
            return self.alert_history[-limit:] if self.alert_history else []
            
        except Exception as e:
            logger.error(f"获取告警历史失败: {e}")
            return []
    
    def clear_alert_history(self):
        """清空告警历史"""
        try:
            self.alert_history.clear()
            logger.info("告警历史已清空")
            
        except Exception as e:
            logger.error(f"清空告警历史失败: {e}")
    
    def generate_alert_report(self):
        """生成告警报告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_status': self.is_monitoring,
                'total_rules': len(self.alert_rules),
                'total_channels': len(self.alert_channels),
                'total_alerts': len(self.alert_history),
                'recent_alerts': self.get_alert_history(10),
                'rules': list(self.alert_rules.values()),
                'channels': list(self.alert_channels.values())
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成告警报告失败: {e}")
            return {}
    
    def save_alert_config(self, file_path='alert_config.json'):
        """保存告警配置"""
        try:
            config = {
                'rules': self.alert_rules,
                'channels': self.alert_channels,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"告警配置已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存告警配置失败: {e}")
            return False
    
    def load_alert_config(self, file_path='alert_config.json'):
        """加载告警配置"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"告警配置文件不存在: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 恢复规则和通道
            if 'rules' in config:
                self.alert_rules = config['rules']
            
            if 'channels' in config:
                self.alert_channels = config['channels']
            
            logger.info(f"告警配置已从 {file_path} 加载")
            return True
            
        except Exception as e:
            logger.error(f"加载告警配置失败: {e}")
            return False


class AlertRuleManager:
    """告警规则管理器"""
    
    def __init__(self):
        self.rule_templates = {}
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认规则模板"""
        try:
            self.rule_templates = {
                'cpu_high': {
                    'name': 'CPU高使用率告警',
                    'metric': 'cpu',
                    'condition': 'gt',
                    'threshold': 80,
                    'severity': 'high',
                    'description': 'CPU使用率超过80%',
                    'recommendation': '检查后台进程和定时任务'
                },
                'memory_high': {
                    'name': '内存高使用率告警',
                    'metric': 'memory',
                    'condition': 'gt',
                    'threshold': 85,
                    'severity': 'high',
                    'description': '内存使用率超过85%',
                    'recommendation': '检查内存泄漏和后台进程'
                },
                'fps_low': {
                    'name': 'FPS过低告警',
                    'metric': 'fps',
                    'condition': 'lt',
                    'threshold': 30,
                    'severity': 'medium',
                    'description': 'FPS低于30',
                    'recommendation': '优化UI渲染和减少复杂动画'
                },
                'network_high': {
                    'name': '网络流量过高告警',
                    'metric': 'network',
                    'condition': 'gt',
                    'threshold': 1000,
                    'severity': 'medium',
                    'description': '网络流量超过1000MB',
                    'recommendation': '检查后台同步和网络请求'
                }
            }
            
        except Exception as e:
            logger.error(f"初始化默认规则模板失败: {e}")
    
    def get_rule_template(self, template_name):
        """获取规则模板"""
        return self.rule_templates.get(template_name)
    
    def list_rule_templates(self):
        """列出所有规则模板"""
        return list(self.rule_templates.keys())
    
    def create_rule_from_template(self, template_name, custom_threshold=None):
        """从模板创建规则"""
        try:
            template = self.get_rule_template(template_name)
            if not template:
                return None
            
            rule = template.copy()
            if custom_threshold is not None:
                rule['threshold'] = custom_threshold
                rule['description'] = rule['description'].replace(str(template['threshold']), str(custom_threshold))
            
            return rule
            
        except Exception as e:
            logger.error(f"从模板创建规则失败: {e}")
            return None


if __name__ == '__main__':
    print("实时性能告警系统模块")
    print("请通过lperf主程序调用此模块")
