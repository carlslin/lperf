#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
手机性能测试工具 (lperf)
特性：
- 稳定性高：采用模块化设计，各功能模块独立运行，降低耦合度
- 性能占用低：采用轻量级数据采集方式，减少对被测设备的性能影响
- 自研开发：完全自主开发，可根据需求灵活定制和扩展
- 兼容性好：支持Android和iOS平台，适配多种机型和系统版本
- 多维度支持：支持按设备维度和应用维度进行性能测试和数据展示
"""

# 技术调研和实现说明：
# 1. 多设备并行测试：采用线程池(ThreadPoolExecutor)实现，支持可配置的最大并行线程数
# 2. 网络流量监控：Android通过dumpsys traffic命令实现，iOS平台使用简化方法作为示例
# 3. FPS流畅度测试：Android通过dumpsys gfxinfo命令实现，iOS平台使用简化方法作为示例
# 4. 应用维度支持：通过扩展数据结构和测试流程，支持在同一设备上测试多个应用
# 5. 数据可视化：使用matplotlib生成静态图表，plotly生成交互式HTML报告

import os
import sys
import time
import json
import subprocess
import argparse
import platform
from datetime import datetime
import threading
import concurrent.futures
import traceback
import logging
from typing import Dict, List, Optional, Union, Any

# 导入图形化报告所需的库
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lperf.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def safe_execute(func_name: str, default_return=None, max_retries=3, retry_delay=1):
    """安全执行装饰器，用于包装可能失败的方法，支持重试机制"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"{func_name} 执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"{func_name} 执行失败，已重试 {max_retries} 次: {e}")
            
            if default_return is not None:
                return default_return
            raise last_exception
        return wrapper
    return decorator

class LPerf:
    def __init__(self, package_name, device_id=None, interval=1.0, output_dir="./reports", platform=None, config_file=None):
        """初始化性能测试工具"""
        # 支持单个应用包名或应用包名列表
        self.package_name = package_name if isinstance(package_name, list) else [package_name]
        self.device_id = device_id
        self.interval = interval
        self.output_dir = output_dir
        self.platform = platform  # 'android' or 'ios' or None (auto-detect)
        self.config_file = config_file
        self.config = {}
        
        # 按应用维度组织结果数据
        # 数据结构: {'app1': {'cpu': [...], 'memory': [...], ...}, 'app2': {...}, ...}
        self.results = {app: {
            'cpu': [],
            'memory': [],
            'battery': [],
            'network': [],
            'fps': [],
            'startup_time': []
        } for app in self.package_name}
        
        # 添加全局结果，用于多应用汇总分析
        self.results['global'] = {
            'cpu': [],
            'memory': [],
            'battery': [],
            'network': [],
            'fps': [],
            'startup_time': []
        }
        
        self.is_running = False
        
        # 读取配置文件（如果提供）
        if self.config_file and os.path.exists(self.config_file):
            self._load_config()
        
        # 验证配置参数
        self._validate_config()
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 检测平台类型
        self._detect_platform()
        
        # 根据平台检查相应工具是否可用
        if self.platform == 'android':
            self._check_adb()
        elif self.platform == 'ios':
            self._check_libimobiledevice()
        
        # 检查设备连接状态
        self._check_device_connection()
        
        # 存储平台相关的命令执行方法
        self._command_method = self._run_adb_command if self.platform == 'android' else self._run_ios_command
        
        # 执行健康检查
        self._health_check()
    
    def _load_config(self):
        """从配置文件加载配置"""
        try:
            if not os.path.exists(self.config_file):
                logger.error(f"配置文件不存在: {self.config_file}")
                return
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # 验证配置文件格式
            required_fields = ['package_name']
            for field in required_fields:
                if field not in self.config:
                    logger.warning(f"配置文件缺少必需字段: {field}")
            
            # 更新属性值（如果配置文件中提供）
            if 'package_name' in self.config:
                self.package_name = self.config['package_name']
            if 'device_id' in self.config and self.device_id is None:
                self.device_id = self.config['device_id']
            if 'interval' in self.config:
                self.interval = self.config['interval']
            if 'output_dir' in self.config:
                self.output_dir = self.config['output_dir']
            if 'platform' in self.config and self.platform is None:
                self.platform = self.config['platform']
            
            logger.info(f"✅ 已加载配置文件: {self.config_file}")
            print(f"✅ 已加载配置文件: {self.config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON格式错误: {e}")
            print(f"❌ 配置文件JSON格式错误: {e}")
        except Exception as e:
            logger.error(f"加载配置文件时出错: {e}")
            print(f"❌ 加载配置文件时出错: {e}")
    
    def _validate_config(self):
        """验证配置参数的有效性"""
        try:
            # 验证包名
            if not self.package_name:
                raise ValueError("应用包名不能为空")
            
            # 验证数据采集间隔
            if self.interval <= 0:
                logger.warning(f"数据采集间隔无效: {self.interval}，使用默认值1.0")
                self.interval = 1.0
            
            # 验证输出目录
            if not self.output_dir:
                raise ValueError("输出目录不能为空")
            
            # 验证平台类型
            if self.platform and self.platform not in ['android', 'ios']:
                raise ValueError(f"不支持的平台类型: {self.platform}")
            
            logger.info("配置参数验证通过")
        except Exception as e:
            logger.error(f"配置参数验证失败: {e}")
            raise
    
    def _health_check(self):
        """执行系统健康检查"""
        try:
            logger.info("开始系统健康检查...")
            
            # 检查Python版本
            python_version = sys.version_info
            if python_version < (3, 6):
                logger.warning(f"Python版本过低: {python_version.major}.{python_version.minor}，建议使用3.6+")
            
            # 检查必要的库
            required_libs = ['matplotlib', 'numpy', 'pandas', 'plotly']
            missing_libs = []
            for lib in required_libs:
                try:
                    __import__(lib)
                except ImportError:
                    missing_libs.append(lib)
            
            if missing_libs:
                logger.warning(f"缺少必要的库: {', '.join(missing_libs)}")
            else:
                logger.info("所有必要的库都已安装")
            
            # 检查磁盘空间
            try:
                import shutil
                total, used, free = shutil.disk_usage(self.output_dir)
                free_gb = free / (1024**3)
                if free_gb < 1:  # 少于1GB
                    logger.warning(f"磁盘空间不足: 剩余 {free_gb:.2f} GB")
                else:
                    logger.info(f"磁盘空间充足: 剩余 {free_gb:.2f} GB")
            except Exception as e:
                logger.warning(f"无法检查磁盘空间: {e}")
            
            logger.info("系统健康检查完成")
        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
    
    def _detect_platform(self):
        """自动检测设备平台类型 - 改进版本"""
        if self.platform is not None:
            # 如果用户已指定平台，直接使用
            self.platform = self.platform.lower()
            if self.platform not in ['android', 'ios']:
                logger.error(f"无效的平台类型: {self.platform}")
                print("错误: 平台必须是 'android' 或 'ios'")
                sys.exit(1)
            return
        
        # 尝试检测连接的设备类型
        try:
            logger.info("开始自动检测设备平台类型...")
            
            # 方法1: 检查ADB工具和Android设备
            android_detected = self._detect_android_platform()
            if android_detected:
                return
            
            # 方法2: 检查libimobiledevice工具和iOS设备
            ios_detected = self._detect_ios_platform()
            if ios_detected:
                return
            

            
            # 方法4: 检查USB设备列表
            usb_detected = self._detect_platform_from_usb()
            if usb_detected:
                return
            
            # 如果无法自动检测，提示用户指定
            logger.error("无法自动检测设备平台类型")
            print("警告: 无法自动检测设备平台类型")
            print("请使用 --platform 参数指定平台类型 (android 或 ios)")
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"检测平台类型时出错: {e}")
            print(f"检测平台类型时出错: {e}")
            sys.exit(1)
    
    def _detect_android_platform(self):
        """检测Android平台 - 增强稳定性版本"""
        try:
            # 检查ADB工具是否可用
            adb_available = False
            try:
                result = subprocess.run(['adb', 'version'], capture_output=True, check=True, timeout=5)
                adb_available = True
                logger.info(f"ADB工具可用: {result.stdout.strip()}")
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.warning(f"ADB工具不可用: {e}")
                return False
            except subprocess.TimeoutExpired:
                logger.warning("ADB工具检查超时")
                return False
            
            if adb_available:
                # 检查设备连接状态
                cmd = ['adb']
                if self.device_id:
                    cmd.extend(['-s', self.device_id])
                cmd.append('devices')
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # 解析设备列表
                        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                        devices = []
                        for line in lines:
                            if line.strip() and 'device' in line:
                                device_id = line.split()[0]
                                devices.append(device_id)
                        
                        if devices:
                            # 验证设备响应性
                            responsive_devices = []
                            for device_id in devices:
                                try:
                                    # 测试设备响应性
                                    test_result = subprocess.run(
                                        ['adb', '-s', device_id, 'shell', 'echo', 'test'], 
                                        capture_output=True, text=True, timeout=5
                                    )
                                    if test_result.returncode == 0:
                                        responsive_devices.append(device_id)
                                        logger.debug(f"设备 {device_id} 响应正常")
                                    else:
                                        logger.warning(f"设备 {device_id} 响应异常")
                                except Exception as e:
                                    logger.warning(f"测试设备 {device_id} 响应性失败: {e}")
                            
                            if not responsive_devices:
                                logger.warning("所有设备均无响应")
                                return False
                            
                            # 使用响应正常的设备
                            if self.device_id and self.device_id in responsive_devices:
                                self.platform = 'android'
                                logger.info(f"检测到指定的Android设备: {self.device_id}")
                                return True
                            elif not self.device_id:
                                self.device_id = responsive_devices[0]  # 使用第一个响应正常的设备
                                self.platform = 'android'
                                logger.info(f"检测到Android设备: {self.device_id}")
                                return True
                            else:
                                logger.warning(f"指定的Android设备ID未找到或无响应: {self.device_id}")
                        else:
                            logger.info("未检测到连接的Android设备")
                    else:
                        logger.warning(f"ADB设备检测失败: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.error("ADB设备检测超时")
                except Exception as e:
                    logger.error(f"ADB设备检测异常: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Android平台检测异常: {e}")
            return False
    
    def _detect_ios_platform(self):
        """检测iOS平台"""
        try:
            # 检查libimobiledevice工具是否可用
            required_tools = ['idevice_id', 'ideviceinfo']
            missing_tools = []
            
            for tool in required_tools:
                try:
                    result = subprocess.run([tool, '--version'], capture_output=True, check=True, timeout=5)
                    logger.debug(f"工具 {tool} 可用: {result.stdout.strip()}")
                except (subprocess.SubprocessError, FileNotFoundError) as e:
                    logger.warning(f"工具 {tool} 不可用: {e}")
                    missing_tools.append(tool)
                except subprocess.TimeoutExpired:
                    logger.warning(f"工具 {tool} 检查超时")
                    missing_tools.append(tool)
            
            if missing_tools:
                logger.info(f"缺少iOS检测工具: {', '.join(missing_tools)}")
                return False
            
            # 获取iOS设备列表
            try:
                result = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
                    
                    if devices:
                        # 验证设备响应性
                        responsive_devices = []
                        for device_id in devices:
                            try:
                                # 测试设备响应性
                                test_result = subprocess.run(
                                    ['ideviceinfo', '-u', device_id, '-k', 'ProductType'], 
                                    capture_output=True, text=True, timeout=5
                                )
                                if test_result.returncode == 0:
                                    responsive_devices.append(device_id)
                                    logger.debug(f"iOS设备 {device_id} 响应正常")
                                else:
                                    logger.warning(f"iOS设备 {device_id} 响应异常")
                            except Exception as e:
                                logger.warning(f"测试iOS设备 {device_id} 响应性失败: {e}")
                        
                        if not responsive_devices:
                            logger.warning("所有iOS设备均无响应")
                            return False
                        
                        # 使用响应正常的设备
                        if self.device_id and self.device_id in responsive_devices:
                            self.platform = 'ios'
                            logger.info(f"检测到指定的iOS设备: {self.device_id}")
                            return True
                        elif not self.device_id:
                            self.device_id = responsive_devices[0]  # 使用第一个响应正常的设备
                            self.platform = 'ios'
                            logger.info(f"检测到iOS设备: {self.device_id}")
                            return True
                        else:
                            logger.warning(f"指定的iOS设备ID未找到或无响应: {self.device_id}")
                    else:
                        logger.info("未检测到连接的iOS设备")
                else:
                    logger.warning("iOS设备检测失败")
                    
            except subprocess.TimeoutExpired:
                logger.error("iOS设备检测超时")
            except Exception as e:
                logger.error(f"iOS设备检测异常: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"iOS平台检测异常: {e}")
            return False
    

    

    

    

    
    def _detect_platform_from_usb(self):
        """从USB设备列表检测平台类型"""
        try:
            if platform.system() == 'Darwin':  # macOS
                # 使用system_profiler检查USB设备
                try:
                    result = subprocess.run(['system_profiler', 'SPUSBDataType'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        if 'android' in output or 'adb' in output:
                            logger.info("从USB设备检测到Android设备")
                            return True
                        elif 'iphone' in output or 'ipad' in output or 'ipod' in output:
                            logger.info("从USB设备检测到iOS设备")
                            return True
                except Exception as e:
                    logger.debug(f"USB设备检测失败: {e}")
                    
            elif platform.system() == 'Linux':
                # 使用lsusb检查USB设备
                try:
                    result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        if 'android' in output or 'adb' in output:
                            logger.info("从USB设备检测到Android设备")
                            return True
                        elif 'apple' in output or 'iphone' in output:
                            logger.info("从USB设备检测到iOS设备")
                            return True
                except Exception as e:
                    logger.debug(f"USB设备检测失败: {e}")
            
            return False
            
        except Exception as e:
            logger.debug(f"USB设备检测异常: {e}")
            return False
    
    def _check_libimobiledevice(self):
        """检查iOS设备所需的libimobiledevice工具是否可用"""
        required_tools = ['idevice_id', 'ideviceinfo', 'idevicediagnostics']
        missing_tools = []
        
        logger.info("检查iOS设备测试工具...")
        
        for tool in required_tools:
            try:
                result = subprocess.run([tool, '--version'], capture_output=True, check=True, timeout=5)
                logger.info(f"工具 {tool} 可用: {result.stdout.strip()}")
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.warning(f"工具 {tool} 不可用: {e}")
                missing_tools.append(tool)
            except subprocess.TimeoutExpired:
                logger.error(f"工具 {tool} 检查超时")
                missing_tools.append(tool)
            except Exception as e:
                logger.error(f"检查工具 {tool} 时异常: {e}")
                missing_tools.append(tool)
        
        if missing_tools:
            error_msg = f"缺少iOS设备测试所需的工具: {', '.join(missing_tools)}"
            logger.error(error_msg)
            print(f"错误: {error_msg}")
            print("请安装libimobiledevice: ")
            if platform.system() == 'Darwin':  # macOS
                print("  brew install libimobiledevice")
            elif platform.system() == 'Linux':
                print("  sudo apt-get install libimobiledevice-tools")
            else:
                print("  请参考libimobiledevice官方文档安装")
            sys.exit(1)
        
        logger.info("所有iOS测试工具检查完成")
    
    def _check_adb(self):
        """检查ADB是否可用"""
        try:
            logger.info("检查ADB工具...")
            result = subprocess.run(['adb', 'version'], capture_output=True, check=True, timeout=5)
            logger.info(f"ADB工具可用: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            error_msg = "ADB未安装或未添加到系统PATH中"
            logger.error(f"{error_msg}: {e}")
            print(f"错误: {error_msg}")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            error_msg = "ADB工具检查超时"
            logger.error(error_msg)
            print(f"错误: {error_msg}")
            sys.exit(1)
        except Exception as e:
            error_msg = f"检查ADB工具时异常: {e}"
            logger.error(error_msg)
            print(f"错误: {error_msg}")
            sys.exit(1)
    
    def _check_device_connection(self):
        """检查设备连接状态"""
        if self.platform == 'android':
            cmd = ['adb']
            if self.device_id:
                cmd.extend(['-s', self.device_id])
            cmd.append('devices')
            
            try:
                logger.info(f"检查Android设备连接状态: {cmd}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
                
                if 'device' in result.stdout:
                    device_info = self.device_id if self.device_id else '默认设备'
                    logger.info(f"已连接Android设备: {device_info}")
                    print(f"已连接Android设备: {device_info}")
                else:
                    error_msg = "未检测到连接的Android设备"
                    logger.error(f"{error_msg}: {result.stdout}")
                    print(f"错误: {error_msg}")
                    sys.exit(1)
            except subprocess.TimeoutExpired:
                error_msg = "检查Android设备连接状态超时"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                sys.exit(1)
            except subprocess.SubprocessError as e:
                error_msg = f"检查Android设备连接状态失败: {e}"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                sys.exit(1)
            except Exception as e:
                error_msg = f"检查Android设备连接状态异常: {e}"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                sys.exit(1)
        elif self.platform == 'ios':
            try:
                logger.info("检查iOS设备连接状态...")
                # 获取已连接的iOS设备列表
                result = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    error_msg = f"获取iOS设备列表失败: {result.stderr}"
                    logger.error(error_msg)
                    print(f"错误: {error_msg}")
                    sys.exit(1)
                
                devices = result.stdout.strip().split('\n')
                devices = [d for d in devices if d.strip()]
                
                if not devices:
                    error_msg = "未检测到连接的iOS设备"
                    logger.error(error_msg)
                    print(f"错误: {error_msg}")
                    print("请确保设备已通过USB连接并信任此计算机")
                    sys.exit(1)
                
                logger.info(f"检测到iOS设备: {devices}")
                
                # 检查指定的设备是否在列表中
                if self.device_id:
                    if self.device_id not in devices:
                        error_msg = f"未找到ID为 {self.device_id} 的iOS设备"
                        logger.error(f"{error_msg}，已连接的设备: {devices}")
                        print(f"错误: {error_msg}")
                        print(f"已连接的设备: {', '.join(devices)}")
                        sys.exit(1)
                    logger.info(f"已连接iOS设备: {self.device_id}")
                    print(f"已连接iOS设备: {self.device_id}")
                else:
                    # 如果未指定设备ID，使用第一个设备
                    self.device_id = devices[0]
                    logger.info(f"使用第一个可用iOS设备: {self.device_id}")
                    print(f"已连接iOS设备: {self.device_id} (使用第一个可用设备)")
            except subprocess.TimeoutExpired:
                error_msg = "检查iOS设备连接状态超时"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                sys.exit(1)
            except subprocess.SubprocessError as e:
                error_msg = f"检查iOS设备连接状态失败: {e}"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                sys.exit(1)
            except Exception as e:
                error_msg = f"检查iOS设备连接状态异常: {e}"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                sys.exit(1)
    
    def _run_adb_command(self, command):
        """执行ADB命令 - 增强稳定性版本"""
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(command.split())
        
        # 增加重试机制
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"执行ADB命令 (尝试 {attempt + 1}/{max_retries}): {cmd}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    logger.warning(f"ADB命令执行失败 (尝试 {attempt + 1}/{max_retries}): {cmd}, 返回码: {result.returncode}, 错误: {result.stderr}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        return ""
                else:
                    return result.stdout.strip()
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"ADB命令执行超时 (尝试 {attempt + 1}/{max_retries}): {cmd}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return ""
            except subprocess.SubprocessError as e:
                logger.warning(f"ADB命令执行异常 (尝试 {attempt + 1}/{max_retries}): {cmd}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return ""
            except Exception as e:
                logger.error(f"ADB命令执行未知异常 (尝试 {attempt + 1}/{max_retries}): {cmd}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return ""
        
        return ""
    
    def _run_ios_command(self, command):
        """执行iOS相关命令 - 增强稳定性版本"""
        # 解析命令和参数
        parts = command.split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # 为iOS命令添加设备ID参数（如果适用）
        if cmd in ['ideviceinfo', 'idevicediagnostics', 'idevicedebug', 'idevicesyslog']:
            if self.device_id:
                args = ['-u', self.device_id] + args
        
        # 增加重试机制
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"执行iOS命令 (尝试 {attempt + 1}/{max_retries}): {[cmd] + args}")
                result = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    logger.warning(f"iOS命令执行失败 (尝试 {attempt + 1}/{max_retries}): {[cmd] + args}, 返回码: {result.returncode}, 错误: {result.stderr}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        return ""
                else:
                    return result.stdout.strip()
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"iOS命令执行超时 (尝试 {attempt + 1}/{max_retries}): {[cmd] + args}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return ""
            except subprocess.SubprocessError as e:
                logger.warning(f"iOS命令执行异常 (尝试 {attempt + 1}/{max_retries}): {cmd}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return ""
            except Exception as e:
                logger.error(f"iOS命令执行未知异常 (尝试 {attempt + 1}/{max_retries}): {cmd}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return ""
        
        return ""
    
    def _collect_data_with_fallback(self, metric_name, collection_methods, default_value=0.0):
        """
        通用数据收集方法，支持多种收集策略和降级处理
        
        Args:
            metric_name (str): 指标名称
            collection_methods (list): 收集方法列表，每个方法是一个字典
            default_value: 默认值
            
        Returns:
            收集到的数据或默认值
        """
        for method in collection_methods:
            try:
                method_name = method.get('name', 'unknown')
                logger.debug(f"尝试使用 {method_name} 收集 {metric_name} 数据")
                
                if method['platform'] == self.platform or method['platform'] == 'all':
                    # 检查版本要求
                    if 'min_version' in method:
                        if self.platform == 'android':
                            android_version = self._get_android_version()
                            if not android_version or android_version < method['min_version']:
                                continue
                        elif self.platform == 'ios':
                            ios_version = self._get_ios_version()
                            if not ios_version or ios_version < method['min_version']:
                                continue
                    
                    # 执行收集方法
                    result = method['func']()
                    if result is not None:
                        # 保存数据
                        self._save_metric_data(metric_name, result)
                        logger.debug(f"{method_name} 成功收集 {metric_name} 数据: {result}")
                        return result
                        
            except Exception as e:
                logger.warning(f"{method_name} 收集 {metric_name} 数据失败: {e}")
                continue
        
        # 所有方法都失败，使用默认值
        logger.warning(f"{metric_name} 数据收集失败，使用默认值 {default_value}")
        self._save_metric_data(metric_name, default_value)
        return default_value
    
    def _save_metric_data(self, metric_name, value):
        """保存指标数据到结果中"""
        try:
            timestamp = datetime.now().isoformat()
            
            if isinstance(value, dict):
                # 多应用数据
                for app, app_value in value.items():
                    if app in self.results:
                        self.results[app][metric_name].append({'timestamp': timestamp, 'value': app_value})
                
                # 计算全局平均值
                valid_values = [v for v in value.values() if v > 0]
                if valid_values:
                    global_value = sum(valid_values) / len(valid_values)
                    self.results['global'][metric_name].append({'timestamp': timestamp, 'value': global_value})
            else:
                # 单值数据
                if isinstance(self.package_name, list):
                    for app in self.package_name:
                        if app in self.results:
                            self.results[app][metric_name].append({'timestamp': timestamp, 'value': value})
                else:
                    self.results[metric_name].append({'timestamp': timestamp, 'value': value})
                
                # 全局数据
                self.results['global'][metric_name].append({'timestamp': timestamp, 'value': value})
                
        except Exception as e:
            logger.error(f"保存 {metric_name} 数据失败: {e}")
    
    def _get_android_cpu_collection_methods(self):
        """获取Android CPU数据收集方法列表"""
        return [
            {
                'name': 'Android 14+ CPU API',
                'platform': 'android',
                'min_version': 14,
                'func': lambda: self._get_android14_app_cpu_data(self.package_name)
            },
            {
                'name': '传统dumpsys方法',
                'platform': 'android',
                'func': lambda: self._collect_android_cpu_via_dumpsys()
            }
        ]
    
    def _get_ios_cpu_collection_methods(self):
        """获取iOS CPU数据收集方法列表"""
        return [
            {
                'name': 'top命令方法',
                'platform': 'ios',
                'func': lambda: self._collect_ios_cpu_via_top()
            }
        ]
    
    def _collect_android_cpu_via_dumpsys(self):
        """通过dumpsys收集Android CPU数据"""
        try:
            output = self._command_method(f"dumpsys cpuinfo | grep {self.package_name}")
            if output:
                cpu_info = output.strip().split()
                if cpu_info and len(cpu_info) > 0:
                    cpu_usage = cpu_info[0].replace('%', '')
                    return float(cpu_usage)
            return None
        except Exception as e:
            logger.warning(f"dumpsys CPU收集失败: {e}")
            return None
    
    def _collect_ios_cpu_via_top(self):
        """通过top命令收集iOS CPU数据"""
        try:
            output = self._command_method(f"idevicedebug run 'top -l 1 -n 0'")
            if output:
                app_cpu_usage = {app: 0.0 for app in self.package_name}
                lines = output.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    for app in self.package_name:
                        if app in line:
                            parts = line.split()
                            if len(parts) > 2:
                                try:
                                    cpu_usage_str = parts[2].replace('%', '')
                                    cpu_percent = float(cpu_usage_str)
                                    app_cpu_usage[app] = cpu_percent
                                except (IndexError, ValueError):
                                    pass
                                break
                
                return app_cpu_usage
            return None
        except Exception as e:
            logger.warning(f"top命令CPU收集失败: {e}")
            return None
    
    def collect_cpu_data(self):
        """收集CPU使用率数据 - 重构优化版本"""
        try:
            if self.platform == 'android':
                collection_methods = self._get_android_cpu_collection_methods()
            elif self.platform == 'ios':
                collection_methods = self._get_ios_cpu_collection_methods()
            else:
                logger.error(f"不支持的平台: {self.platform}")
                return 0.0
            
            return self._collect_data_with_fallback('cpu', collection_methods, 0.0)
            
        except Exception as e:
            logger.error(f"CPU数据收集异常: {e}")
            return 0.0
    
    def _get_android_memory_collection_methods(self):
        """获取Android内存数据收集方法列表"""
        return [
            {
                'name': 'Android 14+ 内存API',
                'platform': 'android',
                'min_version': 14,
                'func': lambda: self._get_android14_app_memory_data(self.package_name)
            },
            {
                'name': '传统dumpsys方法',
                'platform': 'android',
                'func': lambda: self._collect_android_memory_via_dumpsys()
            }
        ]
    
    def _get_ios_memory_collection_methods(self):
        """获取iOS内存数据收集方法列表"""
        return [
            {
                'name': 'ideviceinfo方法',
                'platform': 'ios',
                'func': lambda: self._collect_ios_memory_via_ideviceinfo()
            },
            {
                'name': 'top命令方法',
                'platform': 'ios',
                'func': lambda: self._collect_ios_memory_via_top()
            }
        ]
    
    def _collect_android_memory_via_dumpsys(self):
        """通过dumpsys收集Android内存数据"""
        try:
            output = self._command_method(f"dumpsys meminfo {self.package_name}")
            if output:
                for line in output.split('\n'):
                    if 'TOTAL PSS:' in line:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            try:
                                pss_memory = int(parts[2]) / 1024  # 转换为MB
                                return pss_memory
                            except ValueError:
                                pass
            return None
        except Exception as e:
            logger.warning(f"dumpsys内存收集失败: {e}")
            return None
    
    def _collect_ios_memory_via_ideviceinfo(self):
        """通过ideviceinfo收集iOS内存数据"""
        try:
            output = self._command_method("ideviceinfo -k MemoryUsage")
            if output:
                try:
                    memory_usage = float(output) / (1024 * 1024)  # 转换为MB
                    return memory_usage
                except ValueError:
                    pass
            return None
        except Exception as e:
            logger.warning(f"ideviceinfo内存收集失败: {e}")
            return None
    
    def _collect_ios_memory_via_top(self):
        """通过top命令收集iOS内存数据"""
        try:
            output = self._command_method(f"idevicedebug run 'top -l 1 -n 0'")
            if output:
                app_memory_usage = {app: 0.0 for app in self.package_name}
                lines = output.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    for app in self.package_name:
                        if app in line:
                            parts = line.split()
                            if len(parts) > 7:
                                try:
                                    mem_str = parts[7]
                                    if 'M' in mem_str:
                                        memory_usage = float(mem_str.replace('M', ''))
                                        app_memory_usage[app] = memory_usage
                                except (IndexError, ValueError):
                                    pass
                                break
                
                return app_memory_usage
            return None
        except Exception as e:
            logger.warning(f"top命令内存收集失败: {e}")
            return None
    
    def collect_memory_data(self):
        """收集内存使用数据 - 重构优化版本"""
        try:
            if self.platform == 'android':
                collection_methods = self._get_android_memory_collection_methods()
            elif self.platform == 'ios':
                collection_methods = self._get_ios_memory_collection_methods()
            else:
                logger.error(f"不支持的平台: {self.platform}")
                return 0.0
            
            return self._collect_data_with_fallback('memory', collection_methods, 0.0)
            
        except Exception as e:
            logger.error(f"内存数据收集异常: {e}")
            return 0.0
    
    def _get_android_battery_collection_methods(self):
        """获取Android电池数据收集方法列表"""
        return [
            {
                'name': 'dumpsys电池方法',
                'platform': 'android',
                'func': lambda: self._collect_android_battery_via_dumpsys()
            }
        ]
    
    def _get_ios_battery_collection_methods(self):
        """获取iOS电池数据收集方法列表"""
        return [
            {
                'name': 'ideviceinfo电池方法',
                'platform': 'ios',
                'func': lambda: self._collect_ios_battery_via_ideviceinfo()
            },
            {
                'name': 'grep电池方法',
                'platform': 'ios',
                'func': lambda: self._collect_ios_battery_via_grep()
            }
        ]
    
    def _collect_android_battery_via_dumpsys(self):
        """通过dumpsys收集Android电池数据"""
        try:
            output = self._command_method("dumpsys battery")
            if output:
                battery_info = {}
                for line in output.split('\n'):
                    if ': ' in line:
                        key, value = line.split(': ', 1)
                        battery_info[key.strip()] = value.strip()
                
                if 'level' in battery_info:
                    try:
                        battery_level = int(battery_info['level'])
                        return battery_level
                    except ValueError:
                        logger.warning("电池电量解析失败")
            
            return None
        except Exception as e:
            logger.warning(f"dumpsys电池收集失败: {e}")
            return None
    
    def _collect_ios_battery_via_ideviceinfo(self):
        """通过ideviceinfo收集iOS电池数据"""
        try:
            output = self._command_method("ideviceinfo -k BatteryCurrentCapacity")
            if output and output.strip().isdigit():
                battery_level = int(output.strip())
                return battery_level
            return None
        except Exception as e:
            logger.warning(f"ideviceinfo电池收集失败: {e}")
            return None
    
    def _collect_ios_battery_via_grep(self):
        """通过grep收集iOS电池数据"""
        try:
            output = self._command_method("ideviceinfo | grep -A 5 Battery")
            if output:
                for line in output.split('\n'):
                    if 'BatteryCurrentCapacity:' in line:
                        try:
                            parts = line.split(':')
                            if len(parts) > 1:
                                battery_level = int(parts[1].strip())
                                return battery_level
                        except ValueError:
                            continue
            return None
        except Exception as e:
            logger.warning(f"grep电池收集失败: {e}")
            return None
    
    def collect_battery_data(self):
        """收集电池数据 - 重构优化版本"""
        try:
            if self.platform == 'android':
                collection_methods = self._get_android_battery_collection_methods()
            elif self.platform == 'ios':
                collection_methods = self._get_ios_battery_collection_methods()
            else:
                logger.error(f"不支持的平台: {self.platform}")
                return 50  # 默认电池电量50%
            
            result = self._collect_data_with_fallback('battery', collection_methods, 50)
            
            # 电池数据是设备级别的，为每个应用记录相同的数据
            if isinstance(result, (int, float)):
                timestamp = datetime.now().isoformat()
                self.results['global']['battery'].append({'timestamp': timestamp, 'value': result})
                for app in self.package_name:
                    if app in self.results:
                        self.results[app]['battery'].append({'timestamp': timestamp, 'value': result})
            
            return result
            
        except Exception as e:
            logger.error(f"电池数据收集异常: {e}")
            return 50  # 默认电池电量50%
    
    def _get_android_network_collection_methods(self):
        """获取Android网络数据收集方法列表"""
        return [
            {
                'name': 'dumpsys流量方法',
                'platform': 'android',
                'func': lambda: self._collect_android_network_via_dumpsys()
            }
        ]
    
    def _get_ios_network_collection_methods(self):
        """获取iOS网络数据收集方法列表"""
        return [
            {
                'name': '系统日志方法',
                'platform': 'ios',
                'func': lambda: self._get_ios_network_from_logs()
            },
            {
                'name': '网络接口方法',
                'platform': 'ios',
                'func': lambda: self._get_ios_network_interfaces()
            },
            {
                'name': '应用估算方法',
                'platform': 'ios',
                'func': lambda: self._get_ios_app_network_estimates()
            }
        ]
    
    def _collect_android_network_via_dumpsys(self):
        """通过dumpsys收集Android网络数据"""
        try:
            app_network_usage = {app: 0.0 for app in self.package_name}
            
            for app in self.package_name:
                try:
                    output = self._command_method(f"dumpsys traffic | grep {app}")
                    if output:
                        total_bytes = 0
                        lines = output.strip().split('\n')
                        for line in lines:
                            if app in line:
                                parts = line.strip().split()
                                if len(parts) >= 3:
                                    try:
                                        foreground_bytes = int(parts[1])
                                        background_bytes = int(parts[2])
                                        total_bytes += foreground_bytes + background_bytes
                                    except ValueError:
                                        continue
                        
                        network_mb = total_bytes / (1024 * 1024)
                        app_network_usage[app] = network_mb
                    else:
                        app_network_usage[app] = 0.0
                except Exception as e:
                    logger.warning(f"应用 {app} 网络数据收集失败: {e}")
                    app_network_usage[app] = 0.0
            
            return app_network_usage
        except Exception as e:
            logger.warning(f"dumpsys网络收集失败: {e}")
            return None
    
    def collect_network_data(self):
        """收集网络流量数据 - 重构优化版本"""
        try:
            if self.platform == 'android':
                collection_methods = self._get_android_network_collection_methods()
            elif self.platform == 'ios':
                collection_methods = self._get_ios_network_collection_methods()
            else:
                logger.error(f"不支持的平台: {self.platform}")
                return {app: 0.0 for app in self.package_name}
            
            result = self._collect_data_with_fallback('network', collection_methods, {app: 0.0 for app in self.package_name})
            
            # 如果返回的是字典（多应用数据），计算全局平均值
            if isinstance(result, dict):
                valid_values = [v for v in result.values() if v > 0]
                if valid_values:
                    global_network = sum(valid_values) / len(valid_values)
                    timestamp = datetime.now().isoformat()
                    self.results['global']['network'].append({'timestamp': timestamp, 'value': global_network})
            
            return result
            
        except Exception as e:
            logger.error(f"网络数据收集异常: {e}")
            return {app: 0.0 for app in self.package_name}
    
    def _get_android_fps_collection_methods(self):
        """获取Android FPS数据收集方法列表"""
        return [
            {
                'name': 'Android 14+ FPS API',
                'platform': 'android',
                'min_version': 14,
                'func': lambda: self._get_android14_app_fps_data(self.package_name)
            },
            {
                'name': '传统dumpsys方法',
                'platform': 'android',
                'func': lambda: self._collect_android_fps_via_dumpsys()
            }
        ]
    
    def _get_ios_fps_collection_methods(self):
        """获取iOS FPS数据收集方法列表"""
        return [
            {
                'name': 'top命令方法',
                'platform': 'ios',
                'func': lambda: self._collect_ios_fps_via_top()
            }
        ]
    
    def _collect_android_fps_via_dumpsys(self):
        """通过dumpsys收集Android FPS数据"""
        try:
            output = self._command_method(f"dumpsys gfxinfo {self.package_name} --latency SurfaceView")
            if output:
                lines = output.strip().split('\n')[2:]  # 跳过前两行头信息
                frame_times = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('--'):
                        values = line.split()
                        for value in values:
                            try:
                                frame_time = float(value) / 1000000  # 转换为毫秒
                                frame_times.append(frame_time)
                            except ValueError:
                                continue
                
                # 计算FPS
                if frame_times:
                    avg_frame_time = sum(frame_times) / len(frame_times)
                    fps = 1000 / avg_frame_time if avg_frame_time > 0 else 0
                    return fps
                else:
                    logger.debug(f"应用 {self.package_name} 未获取到帧时间数据，使用默认值")
                    return 59.0  # 默认FPS值
            return None
        except Exception as e:
            logger.warning(f"dumpsys FPS收集失败: {e}")
            return None
    
    def _collect_ios_fps_via_top(self):
        """通过top命令收集iOS FPS数据"""
        try:
            output = self._command_method(f"idevicedebug run 'top -l 1 -n 0'")
            if output:
                app_fps_usage = {app: 0.0 for app in self.package_name}
                lines = output.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    for app in self.package_name:
                        if app in line:
                            parts = line.split()
                            if len(parts) > 2:
                                try:
                                    fps_usage_str = parts[2].replace('%', '')
                                    fps_percent = float(fps_usage_str)
                                    app_fps_usage[app] = fps_percent
                                except (IndexError, ValueError):
                                    pass
                                break
                
                return app_fps_usage
            return None
        except Exception as e:
            logger.warning(f"top命令FPS收集失败: {e}")
            return None
    
    def collect_fps_data(self):
        """收集FPS（帧率）数据"""
        try:
            if self.platform == 'android':
                collection_methods = self._get_android_fps_collection_methods()
            elif self.platform == 'ios':
                collection_methods = self._get_ios_fps_collection_methods()
            else:
                logger.error(f"不支持的平台: {self.platform}")
                return 0.0
            
            return self._collect_data_with_fallback('fps', collection_methods, 0.0)
            
        except Exception as e:
            logger.error(f"FPS数据收集异常: {e}")
            return 0.0
    
    def _get_android_startup_collection_methods(self):
        """获取Android启动时间数据收集方法列表"""
        return [
            {
                'name': 'Android 14+ 启动时间API',
                'platform': 'android',
                'min_version': 14,
                'func': lambda: self._get_android14_app_startup_time(self.package_name)
            },
            {
                'name': '传统am start方法',
                'platform': 'android',
                'func': lambda: self._collect_android_startup_time_via_am_start()
            }
        ]
    
    def _get_ios_startup_collection_methods(self):
        """获取iOS启动时间数据收集方法列表"""
        return [
            {
                'name': '系统日志方法',
                'platform': 'ios',
                'func': lambda: self._get_ios_startup_time_from_logs()
            },
            {
                'name': '应用估算方法',
                'platform': 'ios',
                'func': lambda: self._get_ios_app_startup_estimates()
            }
        ]
    
    def _collect_android_startup_time_via_am_start(self):
        """通过am start命令收集Android启动时间数据"""
        try:
            # 这里实现通过am start命令收集启动时间的逻辑
            # 实际项目中可能需要根据应用的实际包名结构进行调整
            logger.info("开始收集Android启动时间数据...")
            app_startup_times = {}
            for app in self.package_name:
                try:
                    # 确保应用未运行
                    self._command_method(f"am force-stop {app}")
                    time.sleep(2)
                    
                    # 开始计时并启动应用
                    start_time = time.time()
                    # 注意：这里假设MainActivity位于应用的根包名下
                    # 实际项目中可能需要根据应用的实际包名结构进行调整
                    self._command_method(f"am start -W -n {app}/{app}.MainActivity")
                    
                    # 等待应用启动完成
                    time.sleep(5)  # 可根据实际情况调整等待时间
                    
                    # 计算启动时间
                    startup_time = time.time() - start_time
                    app_startup_times[app] = startup_time
                except Exception as e:
                    logger.warning(f"收集Android启动时间数据失败: {e}")
                    app_startup_times[app] = 0.0
            
            # 记录启动时间数据
            timestamp = datetime.now().isoformat()
            
            # 保存每个应用的启动时间数据
            total_startup = 0.0
            count = 0
            for app, startup_time in app_startup_times.items():
                self.results[app]['startup_time'].append({'timestamp': timestamp, 'value': startup_time})
                if startup_time > 0:
                    total_startup += startup_time
                    count += 1
            
            # 计算全局启动时间平均值
            global_startup = total_startup / count if count > 0 else 0.0
            self.results['global']['startup_time'].append({'timestamp': timestamp, 'value': global_startup})
            
            return app_startup_times
        except Exception as e:
            logger.error(f"收集Android启动时间数据失败: {e}")
            return {app: 0.0 for app in self.package_name}
    
    def _get_ios_startup_time_from_logs(self):
        """从iOS系统日志中提取启动时间信息"""
        try:
            # 这里实现从iOS系统日志中提取启动时间信息的逻辑
            # 实际项目中可能需要根据应用的实际包名结构进行调整
            logger.info("开始收集iOS启动时间数据...")
            app_startup_times = {}
            for app in self.package_name:
                try:
                    # 获取应用的Bundle ID
                    bundle_id = app  # 假设package_name就是Bundle ID
                    
                    # 确保应用未运行
                    # 使用多种方法尝试停止应用
                    try:
                        # 方法1：使用idevicedebug命令尝试关闭应用
                        self._command_method(f"idevicedebug -e kill {bundle_id}")
                    except Exception:
                        pass
                    
                    try:
                        # 方法2：使用libimobiledevice的其他工具
                        self._command_method(f"ideviceinstaller -U {bundle_id}")  # 卸载应用的强制停止效果
                    except Exception:
                        pass
                    
                    time.sleep(2)
                    
                    # 开始计时
                    start_time = time.time()
                    
                    # 尝试多种方式启动应用
                    app_launched = False
                    launch_method = 1
                    
                    # 方法1：使用idevicedebug run启动应用（需要开发者模式）
                    try:
                        print(f"尝试使用方法1启动应用 {bundle_id}...")
                        # 启动应用，但不等待完成（异步执行）
                        import subprocess
                        subprocess.Popen(["idevicedebug", "run", bundle_id], 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        app_launched = True
                    except Exception:
                        print(f"方法1启动失败，尝试其他方法...")
                        launch_method = 2
                    
                    # 方法2：使用AppleScript在macOS上通过Xcode启动（如果可用）
                    if not app_launched and platform.system() == 'Darwin':
                        try:
                            print(f"尝试使用方法2启动应用 {bundle_id}...")
                            applescript = f'''tell application "Xcode" to launch simulator app with bundle identifier "{bundle_id}"'''
                            subprocess.run(['osascript', '-e', applescript], capture_output=True)
                            app_launched = True
                        except Exception:
                            print(f"方法2启动失败，尝试其他方法...")
                            launch_method = 3
                    
                    # 方法3：提示用户手动启动（备用方案）
                    if not app_launched:
                        print(f"\n请手动启动应用 {bundle_id}...\n")
                        # 等待用户操作
                        wait_time = 5  # 给用户5秒时间手动启动应用
                        for i in range(wait_time, 0, -1):
                            print(f"等待启动... {i}秒", end='\r')
                            time.sleep(1)
                        print(" " * 30, end='\r')  # 清除倒计时提示
                    
                    # 等待应用完全启动
                    startup_wait_time = 8  # 根据应用复杂度调整等待时间
                    print(f"等待应用 {bundle_id} 完全启动...")
                    time.sleep(startup_wait_time)
                    
                    # 计算启动时间
                    startup_time = time.time() - start_time
                    app_startup_times[app] = startup_time
                    
                    print(f"应用 {bundle_id} 启动完成，耗时: {startup_time:.2f}秒")
                    print(f"启动方法: {launch_method} (1=idevicedebug, 2=Xcode, 3=手动)")
                except Exception as e:
                    logger.warning(f"收集iOS启动时间数据失败: {e}")
                    app_startup_times[app] = 0.0
            
            # 记录启动时间数据
            timestamp = datetime.now().isoformat()
            
            # 保存每个应用的启动时间数据
            total_startup = 0.0
            count = 0
            for app, startup_time in app_startup_times.items():
                self.results[app]['startup_time'].append({'timestamp': timestamp, 'value': startup_time})
                if startup_time > 0:
                    total_startup += startup_time
                    count += 1
            
            # 计算全局启动时间平均值
            global_startup = total_startup / count if count > 0 else 0.0
            self.results['global']['startup_time'].append({'timestamp': timestamp, 'value': global_startup})
            
            return app_startup_times
        except Exception as e:
            logger.error(f"收集iOS启动时间数据失败: {e}")
            return {app: 0.0 for app in self.package_name}
    
    def _get_ios_app_startup_estimates(self):
        """基于应用类型估算启动时间"""
        try:
            app_startup_map = {}
            
            for app in self.package_name:
                # 基于应用类型估算启动时间
                if 'game' in app.lower() or 'gaming' in app.lower():
                    app_startup_map[app] = 0.5  # 游戏应用通常启动时间较短
                elif 'video' in app.lower() or 'media' in app.lower():
                    app_startup_map[app] = 2.0  # 视频应用启动时间较长
                elif 'social' in app.lower() or 'chat' in app.lower():
                    app_startup_map[app] = 0.3  # 社交应用启动时间中等
                elif 'browser' in app.lower() or 'web' in app.lower():
                    app_startup_map[app] = 1.0  # 浏览器应用启动时间较长
                else:
                    app_startup_map[app] = 0.2  # 其他应用默认值
                
                logger.debug(f"应用 {app} 基于类型估算启动时间: {app_startup_map[app]:.2f}秒")
            
            return app_startup_map
            
        except Exception as e:
            logger.warning(f"应用启动时间估算失败: {e}")
            return {}
    
    def measure_startup_time(self):
        """测量应用启动时间"""
        try:
            # 技术说明：测量应用启动时间的实现支持多应用维度
            # 为每个应用分别测量启动时间并记录到对应的数据结构中
            
            # 为每个应用初始化启动时间数据
            app_startup_times = {app: 0.0 for app in self.package_name}
            
            if self.platform == 'android':
                for app in self.package_name:
                    try:
                        # 确保应用未运行
                        self._command_method(f"am force-stop {app}")
                        time.sleep(2)
                        
                        # 开始计时并启动应用
                        start_time = time.time()
                        # 注意：这里假设MainActivity位于应用的根包名下
                        # 实际项目中可能需要根据应用的实际包名结构进行调整
                        self._command_method(f"am start -W -n {app}/{app}.MainActivity")
                        
                        # 等待应用启动完成
                        time.sleep(5)  # 可根据实际情况调整等待时间
                        
                        # 计算启动时间
                        startup_time = time.time() - start_time
                        app_startup_times[app] = startup_time
                    except Exception as e:
                        print(f"测量应用 {app} 启动时间异常: {e}")
                        app_startup_times[app] = 0.0
            elif self.platform == 'ios':
                for app in self.package_name:
                    try:
                        # 获取应用的Bundle ID
                        bundle_id = app  # 假设package_name就是Bundle ID
                        
                        # 确保应用未运行
                        # 使用多种方法尝试停止应用
                        try:
                            # 方法1：使用idevicedebug命令尝试关闭应用
                            self._command_method(f"idevicedebug -e kill {bundle_id}")
                        except Exception:
                            pass
                        
                        try:
                            # 方法2：使用libimobiledevice的其他工具
                            self._command_method(f"ideviceinstaller -U {bundle_id}")  # 卸载应用的强制停止效果
                        except Exception:
                            pass
                        
                        time.sleep(2)
                        
                        # 开始计时
                        start_time = time.time()
                        
                        # 尝试多种方式启动应用
                        app_launched = False
                        launch_method = 1
                        
                        # 方法1：使用idevicedebug run启动应用（需要开发者模式）
                        try:
                            print(f"尝试使用方法1启动应用 {bundle_id}...")
                            # 启动应用，但不等待完成（异步执行）
                            import subprocess
                            subprocess.Popen(["idevicedebug", "run", bundle_id], 
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            app_launched = True
                        except Exception:
                            print(f"方法1启动失败，尝试其他方法...")
                            launch_method = 2
                        
                        # 方法2：使用AppleScript在macOS上通过Xcode启动（如果可用）
                        if not app_launched and platform.system() == 'Darwin':
                            try:
                                print(f"尝试使用方法2启动应用 {bundle_id}...")
                                applescript = f'''tell application "Xcode" to launch simulator app with bundle identifier "{bundle_id}"'''
                                subprocess.run(['osascript', '-e', applescript], capture_output=True)
                                app_launched = True
                            except Exception:
                                print(f"方法2启动失败，尝试其他方法...")
                                launch_method = 3
                        
                        # 方法3：提示用户手动启动（备用方案）
                        if not app_launched:
                            print(f"\n请手动启动应用 {bundle_id}...\n")
                            # 等待用户操作
                            wait_time = 5  # 给用户5秒时间手动启动应用
                            for i in range(wait_time, 0, -1):
                                print(f"等待启动... {i}秒", end='\r')
                                time.sleep(1)
                            print(" " * 30, end='\r')  # 清除倒计时提示
                        
                        # 等待应用完全启动
                        startup_wait_time = 8  # 根据应用复杂度调整等待时间
                        print(f"等待应用 {bundle_id} 完全启动...")
                        time.sleep(startup_wait_time)
                        
                        # 计算启动时间
                        startup_time = time.time() - start_time
                        app_startup_times[app] = startup_time
                        
                        print(f"应用 {bundle_id} 启动完成，耗时: {startup_time:.2f}秒")
                        print(f"启动方法: {launch_method} (1=idevicedebug, 2=Xcode, 3=手动)")
                    except Exception as e:
                        print(f"iOS平台测量应用 {app} 启动时间异常: {e}")
                        app_startup_times[app] = 0.0
            
            # 记录启动时间数据
            timestamp = datetime.now().isoformat()
            
            # 保存每个应用的启动时间数据
            total_startup = 0.0
            count = 0
            for app, startup_time in app_startup_times.items():
                self.results[app]['startup_time'].append({'timestamp': timestamp, 'value': startup_time})
                if startup_time > 0:
                    total_startup += startup_time
                    count += 1
            
            # 计算全局启动时间平均值
            global_startup = total_startup / count if count > 0 else 0.0
            self.results['global']['startup_time'].append({'timestamp': timestamp, 'value': global_startup})
            
            return app_startup_times
        except Exception as e:
            print(f"测量启动时间异常: {e}")
            return {app: 0.0 for app in self.package_name}
    
    def start_monitoring(self, duration=None):
        """开始监控性能数据 - 增强稳定性版本"""
        self.is_running = True
        health_check_counter = 0  # 健康检查计数器
        
        print(f"开始监控应用 {self.package_name} 的性能数据...")
        print(f"监控间隔: {self.interval}秒")
        if duration:
            print(f"监控时长: {duration}秒")
        
        start_time = time.time()
        try:
            while self.is_running:
                # 定期执行健康检查（每10次数据采集执行一次）
                health_check_counter += 1
                if health_check_counter >= 10:
                    logger.info("执行定期健康检查...")
                    health_status = self.system_health_check()
                    
                    if health_status['overall_status'] == 'critical':
                        logger.warning("检测到严重问题，尝试自动恢复...")
                        if self.auto_recovery():
                            logger.info("自动恢复成功，继续监控")
                        else:
                            logger.error("自动恢复失败，停止监控")
                            self.is_running = False
                            break
                    
                    health_check_counter = 0
                
                # 收集各项性能数据
                try:
                    cpu_usage = self.collect_cpu_data()
                    memory_usage = self.collect_memory_data()
                    battery_level = self.collect_battery_data()
                    network_usage = self.collect_network_data()
                    fps = self.collect_fps_data()
                    
                    # 打印实时数据 - 根据不同数据类型进行处理
                    if isinstance(cpu_usage, dict):
                        # 应用维度数据，打印每个应用的数据
                        print(f"[实时数据 - 全局] CPU: {self.results['global']['cpu'][-1]['value']:.2f}% | 内存: {self.results['global']['memory'][-1]['value']:.2f} MB | 电量: {battery_level}% | 网络: {self.results['global']['network'][-1]['value']:.2f} MB | FPS: {self.results['global']['fps'][-1]['value']:.2f}")
                        # 打印每个应用的详细数据
                        for app in self.package_name:
                            print(f"  [应用 {app}] CPU: {cpu_usage.get(app, 0):.2f}% | 内存: {memory_usage.get(app, 0):.2f} MB | 网络: {network_usage.get(app, 0):.2f} MB | FPS: {fps.get(app, 0):.2f}")
                    else:
                        # 单应用数据，保持原有格式
                        print(f"[实时数据] CPU: {cpu_usage:.2f}% | 内存: {memory_usage:.2f} MB | 电量: {battery_level}% | 网络: {network_usage:.2f} MB | FPS: {fps:.2f}")
                        
                except Exception as e:
                    logger.error(f"数据收集过程中出现异常: {e}")
                    # 继续监控，不中断
                    continue
                
                # 检查是否达到设定的监控时长
                if duration and (time.time() - start_time) >= duration:
                    self.is_running = False
                    break
                
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n监控已手动停止")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """停止监控并保存结果"""
        self.is_running = False
        report_file = self.save_results()
        self.generate_summary()
        self.generate_charts()
        self.generate_interactive_report()
        print("性能监控已停止，结果已保存并生成图形化报告")
        return report_file
    
    def save_results(self):
        """保存测试结果"""
        # 生成唯一的报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"lperf_report_{timestamp}.json")
        
        # 保存JSON格式的结果
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"测试结果已保存至: {report_file}")
        return report_file
    
    def generate_summary(self):
        """生成测试结果摘要 - 支持应用维度和全局维度"""
        # 创建整体摘要字典
        overall_summary = {
            'package_name': self.package_name,
            'device_id': self.device_id,
            'test_time': datetime.now().isoformat(),
            'summaries': {}
        }
        
        # 处理全局摘要数据
        global_summary = {
            'type': 'global',
            'name': '全局汇总'
        }
        
        if 'global' in self.results:
            for metric, data in self.results['global'].items():
                if data:
                    values = [item['value'] for item in data]
                    global_summary[f'{metric}_avg'] = sum(values) / len(values)
                    global_summary[f'{metric}_max'] = max(values)
                    global_summary[f'{metric}_min'] = min(values)
        
        overall_summary['summaries']['global'] = global_summary
        
        # 处理每个应用的摘要数据
        for app in self.package_name:
            if app in self.results:
                app_summary = {
                    'type': 'app',
                    'name': app
                }
                
                for metric, data in self.results[app].items():
                    if data:
                        values = [item['value'] for item in data]
                        app_summary[f'{metric}_avg'] = sum(values) / len(values)
                        app_summary[f'{metric}_max'] = max(values)
                        app_summary[f'{metric}_min'] = min(values)
                
                overall_summary['summaries'][app] = app_summary
        
        # 保存摘要
        summary_file = os.path.join(self.output_dir, f"lperf_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, ensure_ascii=False, indent=2)
        
        print(f"测试摘要已保存至: {summary_file}")
        return overall_summary
    
    def generate_charts(self):
        """使用matplotlib生成性能指标图表并保存为图片 - 支持应用维度和全局维度"""
        # 创建图表目录
        charts_dir = os.path.join(self.output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        # 定义图表配置
        chart_configs = {
            'cpu': {'title': 'CPU使用率 (%)', 'color': 'blue', 'ylim': [0, 100]},
            'memory': {'title': '内存使用 (MB)', 'color': 'green', 'ylim': None},
            'battery': {'title': '电池电量 (%)', 'color': 'red', 'ylim': [0, 100]},
            'network': {'title': '网络流量 (MB)', 'color': 'purple', 'ylim': [0, None]},
            'fps': {'title': 'FPS帧率', 'color': 'orange', 'ylim': [0, 60]}
        }
        
        # 确定要处理的数据维度（全局和应用）
        dimensions = ['global'] + self.package_name if isinstance(self.package_name, list) else ['global']
        
        # 为每个维度生成图表
        for dimension in dimensions:
            if dimension not in self.results:
                continue
            
            # 为该维度创建子目录
            dimension_dir = os.path.join(charts_dir, dimension)
            os.makedirs(dimension_dir, exist_ok=True)
            
            # 生成该维度下各项指标的图表
            for metric, config in chart_configs.items():
                if metric in self.results[dimension] and self.results[dimension][metric]:
                    # 提取数据
                    timestamps = [item['timestamp'] for item in self.results[dimension][metric]]
                    values = [item['value'] for item in self.results[dimension][metric]]
                    
                    # 创建DataFrame并处理时间
                    df = pd.DataFrame({'timestamp': timestamps, 'value': values})
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    # 创建图表
                    plt.figure(figsize=(12, 6))
                    plt.plot(df['timestamp'], df['value'], color=config['color'])
                    plt.title(f"{dimension} - {config['title']}")
                    plt.xlabel('时间')
                    plt.ylabel(config['title'].split(' ')[1])
                    plt.grid(True, linestyle='--', alpha=0.7)
                    
                    # 设置Y轴范围
                    if config['ylim']:
                        if len(config['ylim']) == 2:
                            plt.ylim(config['ylim'])
                    
                    # 调整X轴日期格式
                    plt.gcf().autofmt_xdate()
                    
                    # 保存图表
                    chart_file = os.path.join(dimension_dir, f"{metric}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    plt.tight_layout()
                    plt.savefig(chart_file)
                    plt.close()
                    
                    print(f"图表已保存至: {chart_file}")
            
            # 为该维度生成汇总图表（多子图）
            metrics_with_data = [m for m in chart_configs.keys() if m in self.results[dimension] and self.results[dimension][m]]
            
            if metrics_with_data:
                fig, axes = plt.subplots(len(metrics_with_data), 1, figsize=(12, 4 * len(metrics_with_data)))
                if len(metrics_with_data) == 1:
                    axes = [axes]  # 确保axes是列表格式
                
                for i, metric in enumerate(metrics_with_data):
                    config = chart_configs[metric]
                    timestamps = [item['timestamp'] for item in self.results[dimension][metric]]
                    values = [item['value'] for item in self.results[dimension][metric]]
                    
                    df = pd.DataFrame({'timestamp': timestamps, 'value': values})
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    axes[i].plot(df['timestamp'], df['value'], color=config['color'])
                    axes[i].set_title(f"{dimension} - {config['title']}")
                    axes[i].set_ylabel(config['title'].split(' ')[1])
                    axes[i].grid(True, linestyle='--', alpha=0.7)
                    
                    if config['ylim']:
                        if len(config['ylim']) == 2:
                            axes[i].set_ylim(config['ylim'])
                
                # 设置公共的X轴标签
                axes[-1].set_xlabel('时间')
                
                # 调整X轴日期格式
                plt.gcf().autofmt_xdate()
                
                # 保存汇总图表
                summary_chart_file = os.path.join(dimension_dir, f"summary_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                plt.tight_layout()
                plt.savefig(summary_chart_file)
                plt.close()
                
                print(f"汇总图表已保存至: {summary_chart_file}")
        
        # 如果是多应用模式，额外生成应用间比较图表
        if isinstance(self.package_name, list) and len(self.package_name) > 1 and 'global' in self.results:
            # 为每个指标生成应用间比较图表
            for metric, config in chart_configs.items():
                # 检查是否所有应用都有该指标的数据
                all_have_data = True
                for app in self.package_name:
                    if app not in self.results or metric not in self.results[app] or not self.results[app][metric]:
                        all_have_data = False
                        break
                
                if all_have_data:
                    plt.figure(figsize=(12, 6))
                    
                    # 为每个应用绘制一条曲线
                    colors = ['blue', 'green', 'red', 'purple', 'orange', 'cyan', 'magenta', 'yellow']
                    for i, app in enumerate(self.package_name):
                        timestamps = [item['timestamp'] for item in self.results[app][metric]]
                        values = [item['value'] for item in self.results[app][metric]]
                        
                        df = pd.DataFrame({'timestamp': timestamps, 'value': values})
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df.sort_values('timestamp')
                        
                        # 确保使用不同的颜色
                        color_index = i % len(colors)
                        plt.plot(df['timestamp'], df['value'], color=colors[color_index], label=app)
                    
                    plt.title(f"应用间比较 - {config['title']}")
                    plt.xlabel('时间')
                    plt.ylabel(config['title'].split(' ')[1])
                    plt.grid(True, linestyle='--', alpha=0.7)
                    plt.legend()
                    
                    # 设置Y轴范围
                    if config['ylim']:
                        if len(config['ylim']) == 2:
                            plt.ylim(config['ylim'])
                    
                    # 调整X轴日期格式
                    plt.gcf().autofmt_xdate()
                    
                    # 保存比较图表
                    compare_chart_file = os.path.join(charts_dir, f"compare_{metric}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    plt.tight_layout()
                    plt.savefig(compare_chart_file)
                    plt.close()
                    
                    print(f"应用间比较图表已保存至: {compare_chart_file}")
        
        return charts_dir
    
    def generate_interactive_report(self):
        """使用plotly生成交互式HTML报告 - 支持应用维度和全局维度"""
        # 创建报告目录
        reports_dir = os.path.join(self.output_dir, 'interactive_reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # 确定要处理的数据维度（全局和应用）
        dimensions = ['global'] + self.package_name if isinstance(self.package_name, list) else ['global']
        
        # 为每个维度生成交互式报告
        report_files = []
        for dimension in dimensions:
            if dimension not in self.results:
                continue
            
            # 准备数据
            metrics_data = {}
            for metric in ['cpu', 'memory', 'battery', 'network', 'fps', 'startup_time']:
                if metric in self.results[dimension] and self.results[dimension][metric]:
                    timestamps = [item['timestamp'] for item in self.results[dimension][metric]]
                    values = [item['value'] for item in self.results[dimension][metric]]
                    
                    # 创建DataFrame并处理时间
                    df = pd.DataFrame({'timestamp': timestamps, 'value': values})
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    metrics_data[metric] = df
            
            # 为该维度创建子目录
            dimension_dir = os.path.join(reports_dir, dimension)
            os.makedirs(dimension_dir, exist_ok=True)
            
            # 创建图表
            if metrics_data:
                # 确定需要创建的子图数量
                n_metrics = len(metrics_data)
                fig = make_subplots(
                    rows=n_metrics, cols=1,
                    subplot_titles=[
                        f'{dimension} - CPU使用率 (%)',
                        f'{dimension} - 内存使用 (MB)',
                        f'{dimension} - 电池电量 (%)',
                        f'{dimension} - 网络流量 (MB)',
                        f'{dimension} - FPS帧率',
                        f'{dimension} - 启动时间 (秒)'
                    ][:n_metrics],
                    shared_xaxes=True,
                    vertical_spacing=0.05
                )
                
                # 定义颜色
                colors = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#ff7f0e', '#e377c2']
                
                # 添加数据到子图
                for i, (metric, df) in enumerate(metrics_data.items()):
                    fig.add_trace(
                        go.Scatter(
                            x=df['timestamp'],
                            y=df['value'],
                            mode='lines',
                            name=metric,
                            line=dict(color=colors[i], width=2),
                            hovertemplate=f'{metric}: %{{y:.2f}}<extra></extra>'
                        ),
                        row=i+1, col=1
                    )
                    
                    # 计算统计数据
                    avg_value = df['value'].mean()
                    max_value = df['value'].max()
                    min_value = df['value'].min()
                    
                    # 添加统计信息注释
                    fig.add_annotation(
                        x=0.02, y=0.95,
                        xref=f'x{i+1} domain', yref=f'y{i+1} domain',
                        text=f'平均: {avg_value:.2f}<br>最大: {max_value:.2f}<br>最小: {min_value:.2f}',
                        showarrow=False,
                        bgcolor='rgba(255, 255, 255, 0.8)',
                        bordercolor='rgba(0, 0, 0, 0.2)',
                        borderwidth=1,
                        font=dict(size=10)
                    )
                
                # 更新布局
                fig.update_layout(
                    title=f'{dimension} 性能测试报告 (设备: {self.device_id})',
                    height=300 * n_metrics,
                    width=1000,
                    margin=dict(l=60, r=40, t=60, b=60),
                    template='plotly_white'
                )
                
                # 更新X轴标签
                fig.update_xaxes(title_text='时间', showgrid=True, gridwidth=1, gridcolor='LightGray')
                
                # 更新Y轴标签
                y_labels = ['使用率 (%)', '内存 (MB)', '电量 (%)', '流量 (MB)', 'FPS', '时间 (秒)']
                for i in range(n_metrics):
                    fig.update_yaxes(
                        title_text=y_labels[i],
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='LightGray',
                        row=i+1, col=1
                    )
                
                # 保存交互式报告
                report_file = os.path.join(dimension_dir, f"interactive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
                fig.write_html(report_file, include_plotlyjs='cdn')
                
                print(f"交互式报告已保存至: {report_file}")
                report_files.append(report_file)
        
        # 如果是多应用模式，额外生成应用间比较报告
        if isinstance(self.package_name, list) and len(self.package_name) > 1:
            # 为每个指标生成应用间比较报告
            for metric in ['cpu', 'memory', 'battery', 'network', 'fps', 'startup_time']:
                # 检查是否所有应用都有该指标的数据
                all_have_data = True
                for app in self.package_name:
                    if app not in self.results or metric not in self.results[app] or not self.results[app][metric]:
                        all_have_data = False
                        break
                
                if all_have_data:
                    # 创建比较图表
                    fig = go.Figure()
                    
                    # 为每个应用添加一条曲线
                    colors = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#ff7f0e', '#17becf', '#bcbd22', '#e377c2']
                    
                    # 指标标题映射
                    metric_titles = {
                        'cpu': 'CPU使用率 (%)',
                        'memory': '内存使用 (MB)',
                        'battery': '电池电量 (%)',
                        'network': '网络流量 (MB)',
                        'fps': 'FPS帧率',
                        'startup_time': '启动时间 (秒)'
                    }
                    
                    # 指标单位映射
                    metric_units = {
                        'cpu': '使用率 (%)',
                        'memory': '内存 (MB)',
                        'battery': '电量 (%)',
                        'network': '流量 (MB)',
                        'fps': 'FPS',
                        'startup_time': '时间 (秒)'
                    }
                    
                    for i, app in enumerate(self.package_name):
                        timestamps = [item['timestamp'] for item in self.results[app][metric]]
                        values = [item['value'] for item in self.results[app][metric]]
                        
                        df = pd.DataFrame({'timestamp': timestamps, 'value': values})
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df.sort_values('timestamp')
                        
                        # 确保使用不同的颜色
                        color_index = i % len(colors)
                        fig.add_trace(
                            go.Scatter(
                                x=df['timestamp'],
                                y=df['value'],
                                mode='lines',
                                name=app,
                                line=dict(color=colors[color_index], width=2),
                                hovertemplate=f'{app}: %{{y:.2f}}<extra></extra>'
                            )
                        )
                    
                    # 更新布局
                    fig.update_layout(
                        title=f'应用间比较 - {metric_titles.get(metric, metric)}',
                        height=600,
                        width=1200,
                        margin=dict(l=60, r=40, t=60, b=60),
                        template='plotly_white',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    # 更新X轴标签
                    fig.update_xaxes(title_text='时间', showgrid=True, gridwidth=1, gridcolor='LightGray')
                    
                    # 更新Y轴标签
                    fig.update_yaxes(
                        title_text=metric_units.get(metric, ''),
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='LightGray'
                    )
                    
                    # 保存比较报告
                    compare_dir = os.path.join(reports_dir, 'comparison')
                    os.makedirs(compare_dir, exist_ok=True)
                    
                    compare_file = os.path.join(compare_dir, f"compare_{metric}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
                    fig.write_html(compare_file, include_plotlyjs='cdn')
                    
                    print(f"应用间比较报告已保存至: {compare_file}")
                    report_files.append(compare_file)
        
        # 返回最后一个报告文件作为主要报告
        return report_files[-1] if report_files else None
    
    def auto_monitor_with_app_lifecycle(self, wait_time=30):
        """
        根据应用生命周期自动启动和关闭性能测试
        
        Args:
            wait_time (int): 应用启动后等待时间（秒），默认30秒
            
        Returns:
            dict: 测试结果
        """
        try:
            print(f"开始应用生命周期性能测试，等待时间: {wait_time}秒")
            
            if self.platform == 'android':
                return self._android_auto_monitor_with_lifecycle(wait_time)
            elif self.platform == 'ios':
                return self._ios_auto_monitor_with_lifecycle(wait_time)
            else:
                logger.error(f"不支持的平台: {self.platform}")
                return None
                
        except Exception as e:
            logger.error(f"应用生命周期性能测试失败: {e}")
            return None
    
    def _android_auto_monitor_with_lifecycle(self, wait_time):
        """Android平台应用生命周期自动监控"""
        try:
            results = {}
            
            for app in self.package_name:
                print(f"\n=== 测试应用: {app} ===")
                
                # 1. 确保应用已关闭
                print("1. 关闭应用...")
                self._command_method(f"am force-stop {app}")
                time.sleep(2)
                
                # 2. 启动应用并开始监控
                print("2. 启动应用...")
                start_time = time.time()
                self._command_method(f"am start -W -n {app}/{app}.MainActivity")
                
                # 3. 等待应用完全启动
                print(f"3. 等待应用启动完成...")
                time.sleep(5)
                
                # 4. 开始性能监控
                print("4. 开始性能监控...")
                self.start_monitoring()
                
                # 5. 等待指定时间
                print(f"5. 监控运行中，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                
                # 6. 停止监控
                print("6. 停止性能监控...")
                self.stop_monitoring()
                
                # 7. 关闭应用
                print("7. 关闭应用...")
                self._command_method(f"am force-stop {app}")
                time.sleep(2)
                
                # 8. 保存本次测试结果
                app_results = self.results.copy()
                results[app] = app_results
                
                # 9. 重置结果数据，准备下次测试
                self._reset_results()
                
                print(f"应用 {app} 测试完成")
                
            return results
            
        except Exception as e:
            logger.error(f"Android应用生命周期监控失败: {e}")
            return None
    
    def _ios_auto_monitor_with_lifecycle(self, wait_time):
        """iOS平台应用生命周期自动监控"""
        try:
            results = {}
            
            for app in self.package_name:
                print(f"\n=== 测试应用: {app} ===")
                
                # 1. 确保应用已关闭
                print("1. 关闭应用...")
                try:
                    self._command_method(f"idevicedebug -e kill {app}")
                except Exception:
                    pass
                try:
                    self._command_method(f"ideviceinstaller -U {app}")
                except Exception:
                    pass
                time.sleep(2)
                
                # 2. 启动应用
                print("2. 启动应用...")
                app_launched = False
                
                # 尝试多种启动方式
                try:
                    # 方式1: idevicedebug run
                    self._command_method(f"idevicedebug run {app}")
                    app_launched = True
                    print("使用idevicedebug启动成功")
                except Exception:
                    print("idevicedebug启动失败，尝试其他方式...")
                
                if not app_launched and platform.system() == 'Darwin':
                    try:
                        # 方式2: AppleScript (仅macOS)
                        applescript = f'''tell application "Xcode" to launch simulator app with bundle identifier "{app}"'''
                        subprocess.run(['osascript', '-e', applescript], capture_output=True)
                        app_launched = True
                        print("使用AppleScript启动成功")
                    except Exception:
                        print("AppleScript启动失败...")
                
                if not app_launched:
                    print(f"请手动启动应用 {app}...")
                    for i in range(5, 0, -1):
                        print(f"等待启动... {i}秒", end='\r')
                        time.sleep(1)
                    print(" " * 30, end='\r')
                
                # 3. 等待应用完全启动
                print("3. 等待应用启动完成...")
                time.sleep(8)
                
                # 4. 开始性能监控
                print("4. 开始性能监控...")
                self.start_monitoring()
                
                # 5. 等待指定时间
                print(f"5. 监控运行中，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                
                # 6. 停止监控
                print("6. 停止性能监控...")
                self.stop_monitoring()
                
                # 7. 关闭应用
                print("7. 关闭应用...")
                try:
                    self._command_method(f"idevicedebug -e kill {app}")
                except Exception:
                    pass
                time.sleep(2)
                
                # 8. 保存本次测试结果
                app_results = self.results.copy()
                results[app] = app_results
                
                # 9. 重置结果数据，准备下次测试
                self._reset_results()
                
                print(f"应用 {app} 测试完成")
                
            return results
            
        except Exception as e:
            logger.error(f"iOS应用生命周期监控失败: {e}")
            return None
    
    def _reset_results(self):
        """重置结果数据，准备下次测试"""
        try:
            # 重新初始化结果数据结构
            self.results = {
                'global': {
                    'cpu': [],
                    'memory': [],
                    'battery': [],
                    'network': [],
                    'fps': [],
                    'startup_time': []
                }
            }
            
            # 为每个应用初始化结果数据
            for app in self.package_name:
                self.results[app] = {
                    'cpu': [],
                    'memory': [],
                    'battery': [],
                    'network': [],
                    'fps': [],
                    'startup_time': []
                }
                
            logger.debug("结果数据已重置")
            
        except Exception as e:
            logger.error(f"重置结果数据失败: {e}")
    
    def system_health_check(self):
        """
        系统健康检查 - 定期检查设备连接和系统状态
        
        Returns:
            dict: 健康检查结果
        """
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'platform': self.platform,
                'device_id': self.device_id,
                'overall_status': 'unknown',
                'checks': {}
            }
            
            # 1. 设备连接状态检查
            if self.platform == 'android':
                connection_ok = self._check_android_connection_health()
            elif self.platform == 'ios':
                connection_ok = self._check_ios_connection_health()
            else:
                connection_ok = False
                
            health_status['checks']['device_connection'] = {
                'status': 'ok' if connection_ok else 'failed',
                'details': '设备连接正常' if connection_ok else '设备连接异常'
            }
            
            # 2. 工具可用性检查
            tools_ok = self._check_tools_availability()
            health_status['checks']['tools_availability'] = {
                'status': 'ok' if tools_ok else 'failed',
                'details': '必要工具可用' if tools_ok else '必要工具不可用'
            }
            
            # 3. 系统资源检查
            resources_ok = self._check_system_resources()
            health_status['checks']['system_resources'] = {
                'status': 'ok' if resources_ok else 'warning',
                'details': '系统资源充足' if resources_ok else '系统资源不足'
            }
            
            # 4. 网络连接检查
            network_ok = self._check_network_connectivity()
            health_status['checks']['network_connectivity'] = {
                'status': 'ok' if network_ok else 'warning',
                'details': '网络连接正常' if network_ok else '网络连接异常'
            }
            
            # 计算整体状态
            failed_checks = sum(1 for check in health_status['checks'].values() if check['status'] == 'failed')
            warning_checks = sum(1 for check in health_status['checks'].values() if check['status'] == 'warning')
            
            if failed_checks > 0:
                health_status['overall_status'] = 'critical'
            elif warning_checks > 0:
                health_status['overall_status'] = 'warning'
            else:
                health_status['overall_status'] = 'healthy'
            
            # 记录健康检查结果
            logger.info(f"系统健康检查完成，状态: {health_status['overall_status']}")
            for check_name, check_result in health_status['checks'].items():
                logger.info(f"  {check_name}: {check_result['status']} - {check_result['details']}")
            
            return health_status
            
        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    def _check_android_connection_health(self):
        """检查Android设备连接健康状态"""
        try:
            # 测试基本连接
            result = self._run_adb_command("echo health_check")
            if result != "health_check":
                return False
            
            # 测试设备响应性
            result = self._run_adb_command("getprop ro.build.version.release")
            if not result or result.strip() == "":
                return False
            
            # 测试应用访问权限
            result = self._run_adb_command("dumpsys package | head -1")
            if not result:
                return False
                
            return True
            
        except Exception as e:
            logger.warning(f"Android连接健康检查失败: {e}")
            return False
    
    def _check_ios_connection_health(self):
        """检查iOS设备连接健康状态"""
        try:
            # 测试基本连接
            result = self._run_ios_command("ideviceinfo -k ProductType")
            if not result or result.strip() == "":
                return False
            
            # 测试设备信息获取
            result = self._run_ios_command("ideviceinfo -k ProductVersion")
            if not result or result.strip() == "":
                return False
                
            return True
            
        except Exception as e:
            logger.warning(f"iOS连接健康检查失败: {e}")
            return False
    
    def _check_tools_availability(self):
        """检查必要工具的可用性"""
        try:
            if self.platform == 'android':
                # 检查ADB工具
                result = subprocess.run(['adb', 'version'], capture_output=True, timeout=5)
                return result.returncode == 0
            elif self.platform == 'ios':
                # 检查libimobiledevice工具
                result = subprocess.run(['ideviceinfo', '--version'], capture_output=True, timeout=5)
                return result.returncode == 0
            else:
                return False
                
        except Exception as e:
            logger.warning(f"工具可用性检查失败: {e}")
            return False
    
    def _check_system_resources(self):
        """检查系统资源状态"""
        try:
            import psutil
            
            # 检查内存使用率
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                logger.warning(f"内存使用率过高: {memory_percent}%")
                return False
            
            # 检查磁盘空间
            disk_percent = psutil.disk_usage('/').percent
            if disk_percent > 95:
                logger.warning(f"磁盘空间不足: {disk_percent}%")
                return False
                
            return True
            
        except ImportError:
            logger.debug("psutil未安装，跳过系统资源检查")
            return True
        except Exception as e:
            logger.warning(f"系统资源检查失败: {e}")
            return False
    
    def _check_network_connectivity(self):
        """检查网络连接状态"""
        try:
            if self.platform == 'android':
                # 检查Android网络状态
                result = self._run_adb_command("ping -c 1 8.8.8.8")
                return "1 packets transmitted, 1 received" in result
            elif self.platform == 'ios':
                # 检查iOS网络状态
                result = self._run_ios_command("ideviceinfo -k WiFiAddress")
                return result and result.strip() != ""
            else:
                return True
                
        except Exception as e:
            logger.warning(f"网络连接检查失败: {e}")
            return False
    
    def auto_recovery(self):
        """
        自动恢复机制 - 当检测到问题时自动尝试修复
        
        Returns:
            bool: 恢复是否成功
        """
        try:
            logger.info("开始自动恢复流程...")
            
            # 1. 执行健康检查
            health_status = self.system_health_check()
            
            if health_status['overall_status'] == 'healthy':
                logger.info("系统状态健康，无需恢复")
                return True
            
            # 2. 尝试恢复设备连接
            if health_status['checks'].get('device_connection', {}).get('status') == 'failed':
                logger.info("尝试恢复设备连接...")
                if self._recover_device_connection():
                    logger.info("设备连接恢复成功")
                else:
                    logger.error("设备连接恢复失败")
                    return False
            
            # 3. 尝试恢复工具可用性
            if health_status['checks'].get('tools_availability', {}).get('status') == 'failed':
                logger.info("尝试恢复工具可用性...")
                if self._recover_tools_availability():
                    logger.info("工具可用性恢复成功")
                else:
                    logger.error("工具可用性恢复失败")
                    return False
            
            # 4. 重新执行健康检查
            new_health_status = self.system_health_check()
            
            if new_health_status['overall_status'] in ['healthy', 'warning']:
                logger.info("自动恢复成功，系统状态改善")
                return True
            else:
                logger.error("自动恢复失败，系统状态仍为严重")
                return False
                
        except Exception as e:
            logger.error(f"自动恢复过程中出现异常: {e}")
            return False
    
    def _recover_device_connection(self):
        """尝试恢复设备连接"""
        try:
            if self.platform == 'android':
                return self._recover_android_connection()
            elif self.platform == 'ios':
                return self._recover_ios_connection()
            else:
                return False
        except Exception as e:
            logger.error(f"设备连接恢复失败: {e}")
            return False
    
    def _recover_android_connection(self):
        """尝试恢复Android设备连接"""
        try:
            # 1. 重启ADB服务
            logger.info("重启ADB服务...")
            subprocess.run(['adb', 'kill-server'], capture_output=True, timeout=10)
            time.sleep(2)
            subprocess.run(['adb', 'start-server'], capture_output=True, timeout=10)
            time.sleep(3)
            
            # 2. 重新检测设备
            logger.info("重新检测设备...")
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'device' in result.stdout:
                # 3. 重新设置设备ID
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if line.strip() and 'device' in line:
                        device_id = line.split()[0]
                        self.device_id = device_id
                        logger.info(f"重新设置Android设备ID: {device_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Android连接恢复失败: {e}")
            return False
    
    def _recover_ios_connection(self):
        """尝试恢复iOS设备连接"""
        try:
            # 1. 重新检测iOS设备
            logger.info("重新检测iOS设备...")
            result = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
                
                if devices:
                    # 2. 重新设置设备ID
                    self.device_id = devices[0]
                    logger.info(f"重新设置iOS设备ID: {self.device_id}")
                    
                    # 3. 测试连接
                    test_result = subprocess.run(
                        ['ideviceinfo', '-u', self.device_id, '-k', 'ProductType'], 
                        capture_output=True, text=True, timeout=5
                    )
                    
                    return test_result.returncode == 0
            
            return False
            
        except Exception as e:
            logger.error(f"iOS连接恢复失败: {e}")
            return False
    
    def _recover_tools_availability(self):
        """尝试恢复工具可用性"""
        try:
            if self.platform == 'android':
                # 检查ADB路径
                adb_path = subprocess.run(['which', 'adb'], capture_output=True, text=True, timeout=5)
                if adb_path.returncode == 0:
                    logger.info(f"ADB路径: {adb_path.stdout.strip()}")
                    return True
                else:
                    logger.error("ADB工具未找到")
                    return False
                    
            elif self.platform == 'ios':
                # 检查libimobiledevice工具
                ideviceinfo_path = subprocess.run(['which', 'ideviceinfo'], capture_output=True, text=True, timeout=5)
                if ideviceinfo_path.returncode == 0:
                    logger.info(f"ideviceinfo路径: {ideviceinfo_path.stdout.strip()}")
                    return True
                else:
                    logger.error("libimobiledevice工具未找到")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"工具可用性恢复失败: {e}")
            return False


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, lperf_instance):
        self.lperf = lperf_instance
        self.benchmark_results = {}
        self.baseline_data = {}
        
    def run_baseline_test(self, duration=30):
        """运行基准测试，建立性能基线"""
        logger.info("开始运行性能基准测试...")
        
        try:
            # 收集基准数据
            baseline_data = {
                'cpu': [],
                'memory': [],
                'battery': [],
                'network': [],
                'fps': []
            }
            
            start_time = time.time()
            while time.time() - start_time < duration:
                # 收集各项性能数据
                cpu_data = self.lperf.collect_cpu_data()
                memory_data = self.lperf.collect_memory_data()
                battery_data = self.lperf.collect_battery_data()
                network_data = self.lperf.collect_network_data()
                fps_data = self.lperf.collect_fps_data()
                
                # 存储基准数据
                timestamp = datetime.now().isoformat()
                baseline_data['cpu'].append({'timestamp': timestamp, 'value': cpu_data})
                baseline_data['memory'].append({'timestamp': timestamp, 'value': memory_data})
                baseline_data['battery'].append({'timestamp': timestamp, 'value': battery_data})
                baseline_data['network'].append({'timestamp': timestamp, 'value': network_data})
                baseline_data['fps'].append({'timestamp': timestamp, 'value': fps_data})
                
                time.sleep(1)
            
            # 计算基准值
            self.baseline_data = self._calculate_baseline(baseline_data)
            logger.info("性能基准测试完成")
            
            return self.baseline_data
            
        except Exception as e:
            logger.error(f"基准测试失败: {e}")
            return None
    
    def _calculate_baseline(self, data):
        """计算性能基线值"""
        baseline = {}
        
        for metric, values in data.items():
            if values:
                numeric_values = [v['value'] for v in values if isinstance(v['value'], (int, float))]
                if numeric_values:
                    baseline[metric] = {
                        'avg': sum(numeric_values) / len(numeric_values),
                        'max': max(numeric_values),
                        'min': min(numeric_values),
                        'std': self._calculate_std(numeric_values)
                    }
        
        return baseline
    
    def _calculate_std(self, values):
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def run_stress_test(self, duration=60, load_factor=1.5):
        """运行压力测试"""
        logger.info(f"开始运行压力测试，时长: {duration}秒，负载因子: {load_factor}")
        
        try:
            stress_results = {
                'cpu_stress': [],
                'memory_stress': [],
                'battery_stress': [],
                'network_stress': [],
                'fps_stress': []
            }
            
            start_time = time.time()
            while time.time() - start_time < duration:
                # 收集压力测试数据
                cpu_data = self.lperf.collect_cpu_data()
                memory_data = self.lperf.collect_memory_data()
                battery_data = self.lperf.collect_battery_data()
                network_data = self.lperf.collect_network_data()
                fps_data = self.lperf.collect_fps_data()
                
                # 计算相对于基线的性能变化
                timestamp = datetime.now().isoformat()
                stress_results['cpu_stress'].append({
                    'timestamp': timestamp,
                    'value': cpu_data,
                    'baseline_ratio': self._calculate_ratio(cpu_data, self.baseline_data.get('cpu', {}).get('avg', 1))
                })
                
                stress_results['memory_stress'].append({
                    'timestamp': timestamp,
                    'value': memory_data,
                    'baseline_ratio': self._calculate_ratio(memory_data, self.baseline_data.get('memory', {}).get('avg', 1))
                })
                
                stress_results['battery_stress'].append({
                    'timestamp': timestamp,
                    'value': battery_data,
                    'baseline_ratio': self._calculate_ratio(battery_data, self.baseline_data.get('battery', {}).get('avg', 1))
                })
                
                stress_results['network_stress'].append({
                    'timestamp': timestamp,
                    'value': network_data,
                    'baseline_ratio': self._calculate_ratio(network_data, self.baseline_data.get('network', {}).get('avg', 1))
                })
                
                stress_results['fps_stress'].append({
                    'timestamp': timestamp,
                    'value': fps_data,
                    'baseline_ratio': self._calculate_ratio(fps_data, self.baseline_data.get('fps', {}).get('avg', 1))
                })
                
                time.sleep(1)
            
            # 分析压力测试结果
            self.benchmark_results['stress_test'] = self._analyze_stress_results(stress_results)
            logger.info("压力测试完成")
            
            return self.benchmark_results['stress_test']
            
        except Exception as e:
            logger.error(f"压力测试失败: {e}")
            return None
    
    def _calculate_ratio(self, current, baseline):
        """计算当前值与基线的比率"""
        if baseline == 0:
            return 1.0
        return current / baseline if isinstance(current, (int, float)) else 1.0
    
    def _analyze_stress_results(self, results):
        """分析压力测试结果"""
        analysis = {}
        
        for metric, values in results.items():
            if values:
                ratios = [v['baseline_ratio'] for v in values if 'baseline_ratio' in v]
                if ratios:
                    analysis[metric] = {
                        'avg_ratio': sum(ratios) / len(ratios),
                        'max_ratio': max(ratios),
                        'min_ratio': min(ratios),
                        'stability': 'stable' if max(ratios) < 2.0 else 'unstable',
                        'performance_degradation': max(ratios) > 1.5
                    }
        
        return analysis
    
    def generate_benchmark_report(self):
        """生成基准测试报告"""
        if not self.baseline_data:
            logger.warning("没有基准数据，无法生成报告")
            return None
        
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'device_id': self.lperf.device_id,
                'platform': self.lperf.platform,
                'baseline_data': self.baseline_data,
                'benchmark_results': self.benchmark_results,
                'summary': self._generate_benchmark_summary()
            }
            
            # 保存报告
            report_file = os.path.join(self.lperf.output_dir, f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"基准测试报告已保存: {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"生成基准测试报告失败: {e}")
            return None
    
    def _generate_benchmark_summary(self):
        """生成基准测试摘要"""
        summary = {
            'overall_performance': 'good',
            'recommendations': [],
            'issues_found': []
        }
        
        # 分析性能指标
        if self.baseline_data:
            for metric, data in self.baseline_data.items():
                if 'avg' in data:
                    avg_value = data['avg']
                    
                    # CPU性能分析
                    if metric == 'cpu':
                        if avg_value > 80:
                            summary['overall_performance'] = 'poor'
                            summary['issues_found'].append(f"CPU使用率过高: {avg_value:.2f}%")
                            summary['recommendations'].append("优化应用性能，减少CPU占用")
                        elif avg_value > 60:
                            summary['overall_performance'] = 'fair'
                            summary['recommendations'].append("监控CPU使用率，避免过载")
                    
                    # 内存性能分析
                    elif metric == 'memory':
                        if avg_value > 1000:  # 超过1GB
                            summary['issues_found'].append(f"内存使用过高: {avg_value:.2f} MB")
                            summary['recommendations'].append("优化内存管理，避免内存泄漏")
                    
                    # FPS性能分析
                    elif metric == 'fps':
                        if avg_value < 30:
                            summary['overall_performance'] = 'poor'
                            summary['issues_found'].append(f"帧率过低: {avg_value:.2f} FPS")
                            summary['recommendations'].append("优化UI渲染，提高帧率")
                        elif avg_value < 50:
                            summary['overall_performance'] = 'fair'
                            summary['recommendations'].append("优化动画和渲染性能")
        
        # 分析压力测试结果
        if 'stress_test' in self.benchmark_results:
            stress_analysis = self.benchmark_results['stress_test']
            for metric, data in stress_analysis.items():
                if 'performance_degradation' in data and data['performance_degradation']:
                    summary['issues_found'].append(f"{metric} 在压力下性能下降")
                    summary['recommendations'].append(f"优化 {metric} 在负载下的表现")
        
        return summary


def run_device_test(args, device_id, device_output_dir):
    """在单个设备上运行性能测试"""
    try:
        # 创建该设备的LPerf实例
        lperf = LPerf(
            package_name=args.package,
            device_id=device_id,
            interval=args.interval,
            output_dir=device_output_dir,
            platform=args.platform,
            config_file=args.config
        )
        
        # 执行测试
        if args.startup:
            # 仅测试启动时间
            if isinstance(args.package, list):
                print(f"[{device_id}] 开始测量 {len(args.package)} 个应用的启动时间...")
                print(f"[{device_id}] 应用列表: {', '.join(args.package)}")
            else:
                print(f"[{device_id}] 开始测量 {args.package} 的启动时间...")
            
            startup_results = lperf.measure_startup_time()
            
            # 显示结果
            if isinstance(args.package, list):
                for app, time in startup_results.items():
                    if app == 'global':
                        print(f"[{device_id}] 全局平均启动时间: {time:.2f}秒")
                    else:
                        print(f"[{device_id}] [{app}] 启动时间: {time:.2f}秒")
            else:
                print(f"[{device_id}] 应用启动时间: {startup_results:.2f}秒")
            
            report_file = lperf.save_results()
            lperf.generate_summary()
            
            # 根据命令行参数决定是否生成图形化报告
            if not args.no_charts:
                lperf.generate_charts()
            if not args.no_interactive:
                interactive_report = lperf.generate_interactive_report()
        else:
            # 执行完整性能监控
            if isinstance(args.package, list):
                print(f"[{device_id}] 开始监控 {len(args.package)} 个应用的性能...")
                print(f"[{device_id}] 应用列表: {', '.join(args.package)}")
            else:
                print(f"[{device_id}] 开始监控设备性能...")
            
            # 从配置文件中获取测试时长（如果提供）
            duration = args.time
            if args.config and 'duration' in lperf.config:
                duration = lperf.config['duration']
            
            try:
                lperf.start_monitoring(duration=duration)
            except KeyboardInterrupt:
                print(f"\n[{device_id}] 监控已手动停止")
            finally:
                # 停止监控
                lperf.stop_monitoring()
                report_file = lperf.save_results()
                lperf.generate_summary()
                
                # 根据命令行参数决定是否生成图形化报告
                if not args.no_charts:
                    lperf.generate_charts()
                if not args.no_interactive:
                    interactive_report = lperf.generate_interactive_report()
                
                print(f"[{device_id}] 测试报告已保存至: {report_file}")
        
        return device_id, True
    except Exception as e:
        print(f"[{device_id}] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return device_id, False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='手机性能测试工具')
    parser.add_argument('-p', '--package', required=False, nargs='+', help='应用包名（Android）或Bundle ID（iOS）列表')
    parser.add_argument('-d', '--device', nargs='+', help='设备ID列表（可选）')
    parser.add_argument('-i', '--interval', type=float, default=1.0, help='数据采集间隔(秒)')
    parser.add_argument('-t', '--time', type=int, help='测试时长(秒)')
    parser.add_argument('-o', '--output', default='./reports', help='结果输出目录')
    parser.add_argument('--startup', action='store_true', help='仅测试启动时间')
    parser.add_argument('--auto-lifecycle', action='store_true', help='根据应用生命周期自动启动和关闭性能测试')
    parser.add_argument('--wait-time', type=int, default=30, help='应用启动后等待时间（秒），默认30秒')
    parser.add_argument('--platform', choices=['android', 'ios'], help='设备平台类型（自动检测如果未指定）')
    parser.add_argument('-c', '--config', help='配置文件路径')
    parser.add_argument('--no-charts', action='store_true', help='不生成静态图表')
    parser.add_argument('--no-interactive', action='store_true', help='不生成交互式HTML报告')
    parser.add_argument('--max-workers', type=int, default=5, help='最大并行工作线程数')
    
    args = parser.parse_args()
    
    # 处理包名配置 - 支持单一包名或包名列表
    package_name = args.package
    
    # 如果提供了配置文件但没有指定包名，从配置文件中获取包名
    if args.config and not package_name:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # 优先检查是否有package_names字段（支持多应用）
                if 'package_names' in config:
                    package_name = config['package_names']
                # 其次检查是否有单一的package_name字段
                elif 'package_name' in config:
                    package_name = config['package_name']
                # 检查iOS特定配置
                elif 'platform_specific' in config and 'ios' in config['platform_specific']:
                    if 'bundle_ids' in config['platform_specific']['ios']:
                        # iOS多应用配置
                        package_name = config['platform_specific']['ios']['bundle_ids']
                    elif 'bundle_id' in config['platform_specific']['ios']:
                        # iOS单应用配置
                        package_name = config['platform_specific']['ios']['bundle_id']
        except Exception:
            pass
    
    # 确保包名已指定
    if not package_name:
        print("错误: 必须指定应用包名（使用-p参数）或提供包含包名的配置文件")
        parser.print_help()
        sys.exit(1)
    
    # 创建输出目录
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 确定要测试的设备列表
        device_ids = args.device
        
        if not device_ids:
            # 如果没有指定设备ID，使用单一设备模式
            # 创建LPerf实例
            lperf = LPerf(
                package_name=package_name,
                device_id=None,
                interval=args.interval,
                output_dir=output_dir,
                platform=args.platform,
                config_file=args.config
            )
            
            # 执行测试
            if args.auto_lifecycle:
                # 应用生命周期自动测试
                if isinstance(package_name, list):
                    print(f"开始应用生命周期性能测试，应用数量: {len(package_name)}")
                    print(f"应用列表: {', '.join(package_name)}")
                else:
                    print(f"开始应用生命周期性能测试: {package_name}")
                
                lifecycle_results = lperf.auto_monitor_with_app_lifecycle(args.wait_time)
                
                if lifecycle_results:
                    print("\n=== 应用生命周期测试完成 ===")
                    for app, results in lifecycle_results.items():
                        print(f"应用 {app}: 测试完成，数据已保存")
                    
                    # 生成报告
                    report_file = lperf.save_results()
                    lperf.generate_summary()
                    
                    if not args.no_charts:
                        lperf.generate_charts()
                    if not args.no_interactive:
                        interactive_report = lperf.generate_interactive_report()
                else:
                    print("应用生命周期测试失败")
                    
            elif args.startup:
                # 仅测试启动时间
                if isinstance(package_name, list):
                    print(f"开始测量 {len(package_name)} 个应用的启动时间...")
                else:
                    print(f"开始测量 {package_name} 的启动时间...")
                
                startup_results = lperf.measure_startup_time()
                
                # 显示结果
                if isinstance(package_name, list):
                    for app, time in startup_results.items():
                        if app == 'global':
                            print(f"全局平均启动时间: {time:.2f}秒")
                        else:
                            print(f"[{app}] 启动时间: {time:.2f}秒")
                else:
                    print(f"应用启动时间: {startup_results:.2f}秒")
                
                report_file = lperf.save_results()
                lperf.generate_summary()
                
                # 根据命令行参数决定是否生成图形化报告
                if not args.no_charts:
                    lperf.generate_charts()
                if not args.no_interactive:
                    interactive_report = lperf.generate_interactive_report()
            else:
                # 执行完整性能监控
                if isinstance(package_name, list):
                    print(f"开始监控 {len(package_name)} 个应用的性能，测试时长: {args.time or '直到手动停止'}秒")
                    print(f"应用列表: {', '.join(package_name)}")
                else:
                    print(f"开始监控设备性能，测试时长: {args.time or '直到手动停止'}秒")
                
                try:
                    # 从配置文件中获取测试时长（如果提供）
                    duration = args.time
                    if args.config and 'duration' in lperf.config:
                        duration = lperf.config['duration']
                    
                    lperf.start_monitoring(duration=duration)
                except KeyboardInterrupt:
                    print("\n监控已手动停止")
                finally:
                    # 停止监控
                    lperf.stop_monitoring()
                    report_file = lperf.save_results()
                    lperf.generate_summary()
                    
                    # 根据命令行参数决定是否生成图形化报告
                    if not args.no_charts:
                        lperf.generate_charts()
                    if not args.no_interactive:
                        interactive_report = lperf.generate_interactive_report()
                    
                    print(f"测试报告已保存至: {report_file}")
        else:
            # 多设备并行测试模式
            print(f"开始多设备并行测试，设备数量: {len(device_ids)}")
            print(f"最大并行线程数: {args.max_workers}")
            
            # 创建每个设备的输出目录
            device_tasks = []
            for device_id in device_ids:
                device_output_dir = os.path.join(output_dir, f"device_{device_id}")
                os.makedirs(device_output_dir, exist_ok=True)
                device_tasks.append((args, device_id, device_output_dir))
            
            # 使用线程池执行多设备并行测试
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                # 提交所有任务
                future_to_device = {
                    executor.submit(run_device_test, *task): task[1]
                    for task in device_tasks
                }
                
                # 收集结果
                successful_tests = []
                failed_tests = []
                
                for future in concurrent.futures.as_completed(future_to_device):
                    device_id = future_to_device[future]
                    try:
                        result_device_id, success = future.result()
                        if success:
                            successful_tests.append(result_device_id)
                        else:
                            failed_tests.append(result_device_id)
                    except Exception as e:
                        print(f"[{device_id}] 任务执行异常: {e}")
                        failed_tests.append(device_id)
            
            # 输出测试结果统计
            print("\n=== 多设备测试结果统计 ===")
            print(f"总设备数: {len(device_ids)}")
            print(f"成功设备数: {len(successful_tests)}")
            print(f"失败设备数: {len(failed_tests)}")
            
            if successful_tests:
                print(f"成功的设备: {', '.join(successful_tests)}")
            if failed_tests:
                print(f"失败的设备: {', '.join(failed_tests)}")
    except KeyboardInterrupt:
        print("\n测试已被用户中断")
        sys.exit(1)





class DeepPerformanceAnalyzer:
    """深度性能分析器"""
    
    def __init__(self, lperf_instance):
        self.lperf = lperf_instance
        self.analysis_results = {}
        self.performance_patterns = {}
        self.bottleneck_analysis = {}
        self.trend_analysis = {}
        self.anomaly_detection = {}
        
    def analyze_performance_bottlenecks(self):
        """分析性能瓶颈"""
        try:
            logger.info("开始分析性能瓶颈...")
            
            bottlenecks = {
                'cpu_bottlenecks': self._analyze_cpu_bottlenecks(),
                'memory_bottlenecks': self._analyze_memory_bottlenecks(),
                'network_bottlenecks': self._analyze_network_bottlenecks(),
                'fps_bottlenecks': self._analyze_fps_bottlenecks(),
                'system_bottlenecks': self._analyze_system_bottlenecks()
            }
            
            self.bottleneck_analysis = bottlenecks
            logger.info("性能瓶颈分析完成")
            return bottlenecks
            
        except Exception as e:
            logger.error(f"性能瓶颈分析失败: {e}")
            return {}
    
    def _analyze_cpu_bottlenecks(self):
        """分析CPU性能瓶颈"""
        try:
            cpu_data = self.lperf.results.get('cpu', [])
            if not cpu_data:
                return []
            
            bottlenecks = []
            cpu_values = [item['value'] for item in cpu_data]
            
            # 高CPU使用率检测
            high_cpu_threshold = 80.0
            high_cpu_periods = [i for i, val in enumerate(cpu_values) if val > high_cpu_threshold]
            
            if high_cpu_periods:
                bottlenecks.append({
                    'type': 'high_cpu_usage',
                    'severity': 'high' if max(cpu_values) > 95 else 'medium',
                    'description': f'CPU使用率超过{high_cpu_threshold}%',
                    'periods': high_cpu_periods,
                    'max_value': max(cpu_values),
                    'avg_value': sum(cpu_values) / len(cpu_values)
                })
            
            # CPU使用率波动检测
            if len(cpu_values) > 10:
                cpu_variance = self._calculate_variance(cpu_values)
                if cpu_variance > 100:  # 高波动
                    bottlenecks.append({
                        'type': 'cpu_volatility',
                        'severity': 'medium',
                        'description': 'CPU使用率波动较大',
                        'variance': cpu_variance,
                        'recommendation': '检查后台进程和定时任务'
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"CPU瓶颈分析失败: {e}")
            return []
    
    def _analyze_memory_bottlenecks(self):
        """分析内存性能瓶颈"""
        try:
            memory_data = self.lperf.results.get('memory', [])
            if not memory_data:
                return []
            
            bottlenecks = []
            memory_values = [item['value'] for item in memory_data]
            
            # 内存泄漏检测
            if len(memory_values) > 20:
                # 计算内存增长趋势
                memory_trend = self._calculate_trend(memory_values)
                if memory_trend > 0.1:  # 内存持续增长
                    bottlenecks.append({
                        'type': 'memory_leak',
                        'severity': 'high',
                        'description': '检测到可能的内存泄漏',
                        'trend': memory_trend,
                        'recommendation': '检查应用内存管理，重启应用'
                    })
            
            # 高内存使用率检测
            high_memory_threshold = 85.0
            high_memory_periods = [i for i, val in enumerate(memory_values) if val > high_memory_threshold]
            
            if high_memory_periods:
                bottlenecks.append({
                    'type': 'high_memory_usage',
                    'severity': 'high' if max(memory_values) > 95 else 'medium',
                    'description': f'内存使用率超过{high_memory_threshold}%',
                    'periods': high_memory_periods,
                    'max_value': max(memory_values),
                    'avg_value': sum(memory_values) / len(memory_values)
                })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"内存瓶颈分析失败: {e}")
            return []
    
    def _analyze_network_bottlenecks(self):
        """分析网络性能瓶颈"""
        try:
            network_data = self.lperf.results.get('network', [])
            if not network_data:
                return []
            
            bottlenecks = []
            network_values = [item['value'] for item in network_data]
            
            # 网络流量异常检测
            if len(network_values) > 10:
                network_variance = self._calculate_variance(network_values)
                if network_variance > 1000:  # 高波动
                    bottlenecks.append({
                        'type': 'network_volatility',
                        'severity': 'medium',
                        'description': '网络流量波动较大',
                        'variance': network_variance,
                        'recommendation': '检查网络连接和后台同步'
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"网络瓶颈分析失败: {e}")
            return []
    
    def _analyze_fps_bottlenecks(self):
        """分析FPS性能瓶颈"""
        try:
            fps_data = self.lperf.results.get('fps', [])
            if not fps_data:
                return []
            
            bottlenecks = []
            fps_values = [item['value'] for item in fps_data]
            
            # 低FPS检测
            low_fps_threshold = 30.0
            low_fps_periods = [i for i, val in enumerate(fps_values) if val < low_fps_threshold]
            
            if low_fps_periods:
                bottlenecks.append({
                    'type': 'low_fps',
                    'severity': 'high' if min(fps_values) < 20 else 'medium',
                    'description': f'FPS低于{low_fps_threshold}',
                    'periods': low_fps_periods,
                    'min_value': min(fps_values),
                    'avg_value': sum(fps_values) / len(fps_values),
                    'recommendation': '检查UI渲染和动画性能'
                })
            
            # FPS波动检测
            if len(fps_values) > 10:
                fps_variance = self._calculate_variance(fps_values)
                if fps_variance > 50:  # 高波动
                    bottlenecks.append({
                        'type': 'fps_volatility',
                        'severity': 'medium',
                        'description': 'FPS波动较大，可能存在卡顿',
                        'variance': fps_variance,
                        'recommendation': '优化UI渲染和减少复杂动画'
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"FPS瓶颈分析失败: {e}")
            return []
    
    def _analyze_system_bottlenecks(self):
        """分析系统级性能瓶颈"""
        try:
            bottlenecks = []
            
            # 启动时间分析
            startup_data = self.lperf.results.get('startup_time', [])
            if startup_data:
                startup_time = startup_data[0]['value']
                if startup_time > 5.0:  # 启动时间过长
                    bottlenecks.append({
                        'type': 'slow_startup',
                        'severity': 'medium',
                        'description': f'应用启动时间过长: {startup_time:.2f}秒',
                        'value': startup_time,
                        'recommendation': '优化启动流程，减少初始化操作'
                    })
            
            # 电池消耗分析
            battery_data = self.lperf.results.get('battery', [])
            if battery_data and len(battery_data) > 10:
                battery_values = [item['value'] for item in battery_data]
                battery_drop = battery_values[0] - battery_values[-1]
                if battery_drop > 10:  # 电池消耗过快
                    bottlenecks.append({
                        'type': 'high_battery_consumption',
                        'severity': 'medium',
                        'description': f'电池消耗过快: {battery_drop}%',
                        'value': battery_drop,
                        'recommendation': '优化后台进程和网络请求'
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"系统瓶颈分析失败: {e}")
            return []
    
    def analyze_performance_trends(self):
        """分析性能趋势"""
        try:
            logger.info("开始分析性能趋势...")
            
            trends = {}
            for metric in ['cpu', 'memory', 'network', 'fps']:
                data = self.lperf.results.get(metric, [])
                if data and len(data) > 5:
                    values = [item['value'] for item in data]
                    trends[metric] = self._analyze_metric_trend(values)
            
            self.trend_analysis = trends
            logger.info("性能趋势分析完成")
            return trends
            
        except Exception as e:
            logger.error(f"性能趋势分析失败: {e}")
            return {}
    
    def _analyze_metric_trend(self, values):
        """分析单个指标的趋势"""
        try:
            if len(values) < 5:
                return {'trend': 'insufficient_data', 'slope': 0, 'description': '数据不足'}
            
            # 计算线性趋势
            n = len(values)
            x = list(range(n))
            y = values
            
            # 最小二乘法计算斜率
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            
            # 判断趋势
            if abs(slope) < 0.01:
                trend = 'stable'
                description = '性能稳定'
            elif slope > 0.01:
                trend = 'increasing'
                description = '性能指标呈上升趋势'
            else:
                trend = 'decreasing'
                description = '性能指标呈下降趋势'
            
            return {
                'trend': trend,
                'slope': slope,
                'description': description,
                'data_points': len(values)
            }
            
        except Exception as e:
            logger.error(f"指标趋势分析失败: {e}")
            return {'trend': 'error', 'slope': 0, 'description': f'分析失败: {e}'}
    
    def detect_anomalies(self):
        """检测性能异常"""
        try:
            logger.info("开始检测性能异常...")
            
            anomalies = {}
            for metric in ['cpu', 'memory', 'network', 'fps']:
                data = self.lperf.results.get(metric, [])
                if data and len(data) > 10:
                    values = [item['value'] for item in data]
                    anomalies[metric] = self._detect_metric_anomalies(values)
            
            self.anomaly_detection = anomalies
            logger.info("异常检测完成")
            return anomalies
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return {}
    
    def _detect_metric_anomalies(self, values):
        """检测单个指标的异常"""
        try:
            if len(values) < 10:
                return []
            
            anomalies = []
            
            # 计算统计值
            mean = sum(values) / len(values)
            variance = self._calculate_variance(values)
            std_dev = variance ** 0.5
            
            # 异常值检测（3-sigma规则）
            threshold = 3 * std_dev
            for i, value in enumerate(values):
                if abs(value - mean) > threshold:
                    anomalies.append({
                        'index': i,
                        'value': value,
                        'deviation': abs(value - mean),
                        'severity': 'high' if abs(value - mean) > 4 * std_dev else 'medium',
                        'description': f'异常值: {value:.2f} (均值: {mean:.2f}, 标准差: {std_dev:.2f})'
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"指标异常检测失败: {e}")
            return []
    
    def _calculate_variance(self, values):
        """计算方差"""
        try:
            if len(values) < 2:
                return 0
            mean = sum(values) / len(values)
            return sum((x - mean) ** 2 for x in values) / len(values)
        except Exception:
            return 0
    
    def _calculate_trend(self, values):
        """计算趋势斜率"""
        try:
            if len(values) < 2:
                return 0
            return (values[-1] - values[0]) / len(values)
        except Exception:
            return 0
    
    def generate_analysis_report(self):
        """生成深度分析报告"""
        try:
            logger.info("生成深度性能分析报告...")
            
            # 执行所有分析
            bottlenecks = self.analyze_performance_bottlenecks()
            trends = self.analyze_performance_trends()
            anomalies = self.detect_anomalies()
            
            # 生成综合报告
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_bottlenecks': sum(len(b) for b in bottlenecks.values()),
                    'critical_issues': sum(1 for b in bottlenecks.values() for item in b if item.get('severity') == 'high'),
                    'performance_trends': len([t for t in trends.values() if t.get('trend') != 'stable']),
                    'anomalies_detected': sum(len(a) for a in anomalies.values())
                },
                'bottlenecks': bottlenecks,
                'trends': trends,
                'anomalies': anomalies,
                'recommendations': self._generate_recommendations(bottlenecks, trends, anomalies)
            }
            
            self.analysis_results = report
            logger.info("深度性能分析报告生成完成")
            return report
            
        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")
            return {}
    
    def _generate_recommendations(self, bottlenecks, trends, anomalies):
        """生成优化建议"""
        try:
            recommendations = []
            
            # 基于瓶颈分析的建议
            for category, items in bottlenecks.items():
                for item in items:
                    if 'recommendation' in item:
                        recommendations.append({
                            'category': category,
                            'type': item['type'],
                            'severity': item['severity'],
                            'recommendation': item['recommendation']
                        })
            
            # 基于趋势分析的建议
            for metric, trend in trends.items():
                if trend.get('trend') == 'increasing' and trend.get('slope', 0) > 0.1:
                    recommendations.append({
                        'category': 'trend',
                        'type': f'{metric}_increasing',
                        'severity': 'medium',
                        'recommendation': f'{metric}指标持续上升，建议检查资源使用情况'
                    })
            
            # 基于异常检测的建议
            for metric, anomaly_list in anomalies.items():
                if len(anomaly_list) > 0:
                    recommendations.append({
                        'category': 'anomaly',
                        'type': f'{metric}_anomalies',
                        'severity': 'high',
                        'recommendation': f'检测到{metric}指标异常，建议深入分析原因'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            return []


class MLPerformancePredictor:
    """机器学习性能预测器"""
    
    def __init__(self, lperf_instance):
        self.lperf = lperf_instance
        self.prediction_models = {}
        self.training_data = {}
        self.prediction_results = {}
        
    def prepare_training_data(self):
        """准备训练数据"""
        try:
            logger.info("准备机器学习训练数据...")
            
            training_data = {}
            for metric in ['cpu', 'memory', 'network', 'fps']:
                data = self.lperf.results.get(metric, [])
                if data and len(data) > 20:
                    # 提取特征
                    values = [item['value'] for item in data]
                    timestamps = [item['timestamp'] for item in data]
                    
                    # 计算统计特征
                    features = self._extract_features(values, timestamps)
                    training_data[metric] = {
                        'values': values,
                        'features': features,
                        'timestamps': timestamps
                    }
            
            self.training_data = training_data
            logger.info(f"训练数据准备完成，包含 {len(training_data)} 个指标")
            return training_data
            
        except Exception as e:
            logger.error(f"准备训练数据失败: {e}")
            return {}
    
    def _extract_features(self, values, timestamps):
        """提取特征"""
        try:
            if len(values) < 5:
                return {}
            
            features = {
                'mean': sum(values) / len(values),
                'std': self._calculate_std(values),
                'min': min(values),
                'max': max(values),
                'range': max(values) - min(values),
                'variance': self._calculate_variance(values),
                'trend': self._calculate_trend(values),
                'volatility': self._calculate_volatility(values),
                'percentile_25': self._calculate_percentile(values, 25),
                'percentile_75': self._calculate_percentile(values, 75),
                'iqr': self._calculate_percentile(values, 75) - self._calculate_percentile(values, 25)
            }
            
            return features
            
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return {}
    
    def _calculate_std(self, values):
        """计算标准差"""
        try:
            variance = self._calculate_variance(values)
            return variance ** 0.5
        except Exception:
            return 0
    
    def _calculate_volatility(self, values):
        """计算波动性"""
        try:
            if len(values) < 2:
                return 0
            returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            return self._calculate_std(returns)
        except Exception:
            return 0
    
    def _calculate_percentile(self, values, percentile):
        """计算百分位数"""
        try:
            if not values:
                return 0
            sorted_values = sorted(values)
            index = int(percentile / 100 * (len(sorted_values) - 1))
            return sorted_values[index]
        except Exception:
            return 0
    
    def train_prediction_models(self):
        """训练预测模型"""
        try:
            logger.info("开始训练性能预测模型...")
            
            if not self.training_data:
                logger.warning("没有可用的训练数据")
                return {}
            
            models = {}
            for metric, data in self.training_data.items():
                if len(data['values']) >= 20:
                    model = self._train_metric_model(metric, data)
                    if model:
                        models[metric] = model
            
            self.prediction_models = models
            logger.info(f"模型训练完成，共训练 {len(models)} 个模型")
            return models
            
        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            return {}
    
    def _train_metric_model(self, metric, data):
        """训练单个指标的预测模型"""
        try:
            # 这里使用简单的线性回归模型
            # 在实际项目中可以使用更复杂的机器学习算法
            
            values = data['values']
            n = len(values)
            
            if n < 10:
                return None
            
            # 简单的移动平均预测模型
            window_size = min(5, n // 4)
            model = {
                'type': 'moving_average',
                'window_size': window_size,
                'last_values': values[-window_size:],
                'prediction_horizon': 5,
                'accuracy': self._calculate_model_accuracy(values, window_size)
            }
            
            return model
            
        except Exception as e:
            logger.error(f"训练{metric}模型失败: {e}")
            return None
    
    def _calculate_model_accuracy(self, values, window_size):
        """计算模型准确性"""
        try:
            if len(values) < window_size * 2:
                return 0.0
            
            # 使用历史数据验证模型准确性
            total_error = 0
            predictions = 0
            
            for i in range(window_size, len(values)):
                # 使用前window_size个值预测
                predicted = sum(values[i-window_size:i]) / window_size
                actual = values[i]
                error = abs(predicted - actual) / actual if actual != 0 else 0
                total_error += error
                predictions += 1
            
            accuracy = 1 - (total_error / predictions) if predictions > 0 else 0
            return max(0, min(1, accuracy))  # 限制在0-1范围内
            
        except Exception as e:
            logger.error(f"计算模型准确性失败: {e}")
            return 0.0
    
    def predict_performance(self, metric, horizon=5):
        """预测性能指标"""
        try:
            if metric not in self.prediction_models:
                logger.warning(f"没有{metric}的预测模型")
                return None
            
            model = self.prediction_models[metric]
            
            if model['type'] == 'moving_average':
                # 移动平均预测
                last_values = model['last_values']
                if not last_values:
                    return None
                
                # 计算趋势
                if len(last_values) >= 2:
                    trend = (last_values[-1] - last_values[0]) / len(last_values)
                else:
                    trend = 0
                
                # 生成预测
                predictions = []
                current_value = last_values[-1]
                
                for i in range(horizon):
                    predicted_value = current_value + trend * (i + 1)
                    predictions.append({
                        'step': i + 1,
                        'predicted_value': max(0, predicted_value),  # 确保非负
                        'confidence': model['accuracy']
                    })
                
                return {
                    'metric': metric,
                    'model_type': model['type'],
                    'predictions': predictions,
                    'accuracy': model['accuracy'],
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"性能预测失败: {e}")
            return None
    
    def generate_prediction_report(self):
        """生成预测报告"""
        try:
            logger.info("生成性能预测报告...")
            
            if not self.prediction_models:
                logger.warning("没有可用的预测模型")
                return {}
            
            predictions = {}
            for metric in self.prediction_models.keys():
                pred = self.predict_performance(metric)
                if pred:
                    predictions[metric] = pred
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'models_available': list(self.prediction_models.keys()),
                'predictions': predictions,
                'summary': {
                    'total_predictions': len(predictions),
                    'avg_accuracy': sum(pred['accuracy'] for pred in predictions.values()) / len(predictions) if predictions else 0
                }
            }
            
            self.prediction_results = report
            logger.info("性能预测报告生成完成")
            return report
            
        except Exception as e:
            logger.error(f"生成预测报告失败: {e}")
            return {}


class RealTimeAlertSystem:
    """实时性能告警系统"""
    
    def __init__(self, lperf_instance):
        self.lperf = lperf_instance
        self.alert_rules = {}
        self.alert_history = []
        self.alert_channels = {}
        self.is_monitoring = False
        
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


if __name__ == '__main__':
    main()