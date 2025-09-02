# lperf - 高性能手机性能测试工具

一款高性能、稳定性强、兼容性好的手机性能测试工具，参考了字节跳动和快手等一线互联网公司的性能测试实践。

## 特性

- **稳定性高**：采用模块化设计，各功能模块独立运行，降低耦合度，提高系统稳定性
- **性能占用低**：采用轻量级数据采集方式，减少对被测设备的性能影响
- **自研开发**：完全自主开发，可根据需求灵活定制和扩展
- **兼容性好**：支持Android 8-16+和iOS 10-18+，适配多种机型和系统版本
- **多维度指标**：支持CPU、内存、电池、网络流量、FPS帧率、启动时间等多维度性能指标采集
- **多应用并行测试**：支持同时对多个应用进行并行性能测试，提高测试效率
- **应用生命周期自动测试**：支持根据应用启动和关闭来自动启动和关闭性能测试
- **增强稳定性**：设备连接检测、命令执行重试、数据收集降级等机制
- **可视化报告**：生成静态图表和交互式HTML报告，直观展示性能数据

## 功能

- **CPU使用率监控**：实时监控应用的CPU占用情况（支持Android和iOS）
- **内存使用监控**：跟踪应用的PSS内存使用量（支持Android和iOS）
- **电池电量监控**：监控设备电池电量变化（支持Android和iOS）
- **网络流量监控**：采集应用的网络流量数据（前台和后台流量），以MB为单位进行统计和展示
- **FPS帧率监控**：采集应用的帧率数据，评估应用的流畅度和卡顿情况
- **应用启动时间测量**：精确测量应用的启动耗时（支持Android和iOS）
- **实时数据展示**：提供实时性能数据展示
- **测试结果保存**：将测试数据保存为JSON格式，便于后续分析
- **测试报告生成**：自动生成测试摘要报告
- **图形化测试报告**：自动生成静态图表和交互式HTML报告，包含CPU、内存、电池等指标的可视化展示
- **多应用并行测试**：支持同时对多个应用进行并行性能测试，提高测试效率

## 版本兼容性说明

### 支持的版本范围
- **Android**: 8.0 (API 26) - 16.0+ (API 34+)
- **iOS**: 10.0 - 18.0+

### 兼容性策略
- **基础功能**: 所有版本都支持核心性能指标采集
- **增强功能**: 新版本系统提供更多API和优化选项
- **降级处理**: 旧版本系统自动使用兼容的命令和方法
- **智能检测**: 自动识别系统版本并选择最佳采集策略

## 平台支持详解

### Android平台
- **CPU监控**：
  - 命令：`dumpsys cpuinfo | grep {package_name}` (Android 8-13)
  - 新命令：`dumpsys cpuinfo --total` (Android 14+)
  - 实现原理：解析输出结果中的CPU使用率百分比
  - 输出示例："  5.2% 1234:com.example.app/ (pid 1234)"
  - 版本支持：Android 8-13使用基础命令，Android 14+使用增强API

- **内存监控**：
  - 命令：`dumpsys meminfo {package_name}` (Android 8-13)
  - 新命令：`dumpsys meminfo --total` (Android 14+)
  - 实现原理：查找"TOTAL PSS:"行，将KB转换为MB单位
  - 输出示例："TOTAL PSS:  123456 kB"
  - 版本支持：Android 8-13使用基础命令，Android 14+支持procstats和/proc/meminfo

- **电池监控**：
  - 命令：`dumpsys battery`
  - 实现原理：从输出中提取"level"字段的值
  - 数据类型：设备级指标，所有应用共享相同数据
  - 版本支持：Android 8-13使用基础命令，Android 14+支持`dumpsys power`命令

- **网络流量**：
  - 命令：`dumpsys traffic | grep {package_name}`
  - 实现原理：提取前台和后台流量数据，转换为MB单位
  - 输出示例："com.example.app\tForeground: 12345678\tBackground: 87654321"
  - 版本支持：Android 8-13使用基础命令，Android 14+支持`dumpsys netstats detail`

- **FPS帧率**：
  - 命令：`dumpsys gfxinfo {package_name} --latency SurfaceView` (Android 8-13)
  - 新命令：`dumpsys SurfaceFlinger --latency` (Android 14+)
  - 实现原理：分析每一帧的绘制时间（毫秒），计算平均帧率
  - 数据处理：1000ms / 平均帧时间 = FPS值

- **启动时间**：
  - 停止命令：`am force-stop {package_name}`
  - 启动命令：`am start -W -n {package_name}/{package_name}.MainActivity`
  - 计算方式：记录从启动命令执行到应用加载完成的时间差
  - 等待时间：启动后等待5秒确保应用完全加载

### Android版本支持矩阵
| 功能 | Android 8-11 | Android 12-13 | Android 14+ |
|------|--------------|---------------|-------------|
| CPU监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| 内存监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| 网络监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| FPS监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| 电池监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |

### iOS平台
- **CPU监控**：
  - 命令：`idevicedebug run 'top -l 1 -n 0'`
  - 实现原理：从top命令输出中查找应用相关行，提取CPU使用率
  - 数据处理：支持多应用维度的CPU使用率采集和记录
  - 版本支持：iOS 10-16使用基础命令，iOS 17+使用增强API

- **内存监控**：
  - 方法1：`ideviceinfo -k MemoryUsage`（基础方法）
    - 命令示例：`ideviceinfo -k MemoryUsage`
    - 输出格式：`MemoryUsage: 1234 MB`
    - 适用场景：快速获取设备总内存使用情况
  - 方法2：`idevicedebug run 'top -l 1 -n 0'`（推荐，获取应用级内存）
    - 命令示例：`idevicedebug run 'top -l 1 -n 0 | grep "AppName"'`
    - 输出格式：`AppName  123.4M  45.2%  0.0  0.0  0.0  0.0  0.0  0.0`
    - 适用场景：获取特定应用的详细内存使用情况
  - 实现原理：从输出中提取内存使用量，转换为MB单位
  - 输出示例解析：识别类似"123.4M"的内存表示
  - 版本支持：iOS 10-15使用基础方法，iOS 16+支持更详细的内存统计

- **电池监控**：
  - 方法1：`ideviceinfo -k BatteryCurrentCapacity`（直接获取电量）
    - 命令示例：`ideviceinfo -k BatteryCurrentCapacity`
    - 输出格式：`BatteryCurrentCapacity: 85`
    - 适用场景：快速获取当前电池电量百分比
  - 方法2：`ideviceinfo | grep -A 5 Battery`（备用方案）
    - 命令示例：`ideviceinfo | grep -A 5 Battery`
    - 输出格式：
      ```
      BatteryCurrentCapacity: 85
      BatteryIsCharging: true
      ExternalChargeCapable: true
      ExternalConnected: true
      FullExternalChargeCapable: true
      ```
    - 适用场景：获取详细的电池状态信息
  - 数据类型：设备级指标，所有应用共享相同数据
  - 版本支持：iOS 10-16使用基础方法，iOS 17+支持更精确的电池监控

- **网络流量**：
  - 方法1：`idevicesyslog -n 200`（适用于所有iOS设备）
    - 命令示例：`idevicesyslog -n 200 | grep -E "network|wifi|cellular"`
    - 输出格式：
      ```
      Dec 01 14:30:22 iPhone kernel[0] <Notice>: network: WiFi connected
      Dec 01 14:30:23 iPhone kernel[0] <Notice>: network: Data usage: 1.2MB
      ```
    - 实现原理：分析网络相关日志，提取流量信息
    - 适用场景：适用于所有iOS版本，通过日志分析获取网络状态
  - 方法2：`idevicedebug run 'netstat -i'`（适用于iOS 10+）
    - 命令示例：`idevicedebug run 'netstat -i'`
    - 输出格式：
      ```
      Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Drop
      lo0   16384 <Link#1>                          0     0          0        0     0          0     0
      en0   1500  <Link#2>     xx:xx:xx:xx:xx:xx  12345    0   12345678   12345    0   87654321     0
      ```
    - 实现原理：解析网络接口统计信息
    - 适用场景：iOS 10+设备，获取详细的网络接口统计
  - 方法3：`idevicedebug run 'ifconfig -a'`（适用于iOS 17+）
    - 命令示例：`idevicedebug run 'ifconfig -a'`
    - 输出格式：
      ```
      en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
        inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
        inet6 fe80::1234:5678:9abc:def0%en0 prefixlen 64 scopeid 0x4
        ether xx:xx:xx:xx:xx:xx txqueuelen 1000 (Ethernet)
        RX packets 12345 bytes 12345678 (11.8 MB)
        TX packets 12345 bytes 87654321 (83.6 MB)
      ```
    - 实现原理：解析网络接口信息，提取RX和TX字节数
    - 适用场景：iOS 17+设备，获取最详细的网络接口信息
  - 注意事项：iOS限制了应用级网络流量的直接访问，获取的主要是设备级数据

- **FPS帧率**：
  - 命令：`idevicesyslog -n 200`
  - 实现原理：分析与UI渲染相关的日志信息（如fps、display、animation、render等关键字）
  - 智能估算：基于设备型号、iOS版本和应用类型进行智能FPS估算
  - 版本支持：iOS 10-16使用基础算法，iOS 17+支持更准确的性能估算算法

- **启动时间**：
  - 停止应用（双重保障）：
    1. 命令1：`idevicedebug -e kill {bundle_id}`
    2. 命令2：`ideviceinstaller -U {bundle_id}`（利用卸载的强制停止效果）
  - 启动应用（三级方案）：
    1. 命令1：`idevicedebug run {bundle_id}`（需要开发者模式）
    2. 命令2：AppleScript通过Xcode启动（仅macOS环境）
    3. 手动启动：带5秒倒计时提示的用户操作
  - 计算方式：记录从启动命令执行到应用完全加载的时间差
  - 等待时间：启动后等待8秒确保应用完全加载

### iOS版本支持矩阵
| 功能 | iOS 10-14 | iOS 15-16 | iOS 17+ |
|------|------------|-----------|---------|
| CPU监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| 内存监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| 网络监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |
| FPS监控 | ✅ 估算 | ✅ 智能估算 | ✅ 智能估算+ |
| 电池监控 | ✅ 基础 | ✅ 增强 | ✅ 最新API |



### 移动平台支持矩阵
| 功能 | Android | iOS |
|------|---------|-------|
| CPU监控 | ✅ dumpsys/top | ✅ ideviceinfo |
| 内存监控 | ✅ dumpsys meminfo | ✅ ideviceinfo |
| 网络监控 | ✅ dumpsys netstats | ✅ ideviceinfo |
| FPS监控 | ✅ dumpsys gfxinfo | ✅ 系统API |
| 电池监控 | ✅ dumpsys battery | ✅ ideviceinfo |
| 启动时间 | ✅ am start -W | ✅ idevicedebug |

## 安装

### 环境要求

- Python 3.6+ 
- Android设备（Android 8.0+，通过ADB连接）
- iOS设备（iOS 10.0+，通过libimobiledevice连接）
- ADB工具（已添加到系统PATH）
- libimobiledevice工具包（用于iOS设备测试）

### 依赖安装

```bash
# 安装基础依赖（必需）
pip install matplotlib numpy pandas plotly

# 安装iOS支持依赖（可选）
pip install libimobiledevice

# 安装完整依赖
pip install -r requirements.txt
```

### 安装步骤

1. 克隆或下载本项目

```bash
# 克隆项目
git clone [项目地址]
cd lperf
```

2. 安装依赖

```bash
# 安装基础依赖
pip install matplotlib numpy pandas plotly

# 安装完整依赖（可选）
pip install -r requirements.txt
```

#### iOS平台额外依赖
对于iOS设备测试，还需要安装`libimobiledevice`工具包：

- **macOS**: `brew install libimobiledevice`
- **Linux**: `sudo apt-get install libimobiledevice-tools`
- **Windows**: 请参考[libimobiledevice官方文档](https://libimobiledevice.org/)进行安装

3. 验证安装

```bash
# 检查Python版本
python --version

# 检查依赖
python -c "import matplotlib, numpy, pandas, plotly; print('依赖安装成功')"
```

## 使用指南

### 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 连接设备（Android或iOS）
# Android: 确保ADB可用，设备已连接
# iOS: 确保libimobiledevice工具已安装，设备已连接

# 3. 基本测试
# Android设备测试
python lperf.py -p com.example.app

# iOS设备测试
python lperf.py -p com.example.bundleid --platform ios

# 4. 启动时间测试
python lperf.py -p com.example.app --startup

# 5. 多应用测试
python lperf.py -p com.example.app1 com.example.app2 -t 60

# 6. 应用生命周期自动测试
python lperf.py -p com.example.app --auto-lifecycle --wait-time 30
```

### 应用生命周期自动测试

lperf支持根据应用启动和关闭来自动启动和关闭性能测试，特别适合自动化测试场景：

```bash
# 基本用法：等待30秒（默认）
python lperf.py -p com.example.app --auto-lifecycle

# 自定义等待时间：等待60秒
python lperf.py -p com.example.app --auto-lifecycle --wait-time 60

# 多应用生命周期测试
python lperf.py -p com.example.app1 com.example.app2 --auto-lifecycle --wait-time 45
```

**工作流程：**
1. **自动关闭应用** - 确保应用处于关闭状态
2. **启动应用** - 自动启动目标应用
3. **等待启动完成** - 等待应用完全加载
4. **开始性能监控** - 自动开始收集性能数据
5. **等待指定时间** - 监控运行指定时长（默认30秒）
6. **停止监控** - 自动停止数据收集
7. **关闭应用** - 自动关闭应用
8. **保存结果** - 保存本次测试数据

**适用场景：**
- 自动化性能测试
- CI/CD流水线集成
- 应用启动性能评估
- 批量应用性能测试

### 高级功能演示脚本

```bash
# 运行高级功能演示（需要先安装相关依赖）
python advanced_features_demo.py

# 演示内容包括：
# - 深度性能分析
# - 机器学习性能预测  
# - 实时性能告警系统
```

### 稳定性测试脚本

```bash
# 运行稳定性测试
python3 stability_test.py

# 测试内容包括：
# - 设备连接稳定性测试
# - 性能数据收集稳定性测试  
# - 命令执行稳定性测试
# - 错误处理和降级机制测试
```

### 命令行参数

```
-h, --help          显示帮助信息
-p, --package       应用包名（Android）或Bundle ID（iOS） (必填)
-d, --device        设备ID列表（可选，支持多设备并行测试，多个设备ID用空格分隔）
-i, --interval      数据采集间隔(秒)，默认为1秒
-t, --time          测试时长(秒)
-o, --output        结果输出目录，默认为./reports
--startup           仅测试启动时间
--auto-lifecycle    根据应用生命周期自动启动和关闭性能测试
--wait-time         应用启动后等待时间（秒），默认30秒
--platform          设备平台类型，可选值: android, ios (自动检测如果未指定)
--no-charts         不生成静态图表
--no-interactive    不生成交互式HTML报告
--max-workers       最大并行工作线程数，用于多设备并行测试，默认5
```

### 测试示例



#### Android设备测试
```bash
# 测试指定应用的性能，持续60秒
python lperf.py -p com.example.app -t 60

# 仅测试应用启动时间
python lperf.py -p com.example.app --startup

# 指定设备ID进行测试
python lperf.py -p com.example.app -d device_id -t 60

# 指定输出目录
python lperf.py -p com.example.app -o ./my_results

# 多应用并行测试
python lperf.py -p com.example.app1 com.example.app2 -t 60
```

#### iOS设备测试
```bash
# 测试指定应用的性能，持续60秒
python lperf.py -p com.example.bundleid --platform ios -t 60

# 仅测试应用启动时间
python lperf.py -p com.example.bundleid --platform ios --startup

# 指定设备ID进行测试
python lperf.py -p com.example.bundleid --platform ios -d device_id -t 60

# 指定输出目录
python lperf.py -p com.example.bundleid --platform ios -o ./my_results

# 多应用并行测试
python lperf.py -p com.example.bundleid1 com.example.bundleid2 --platform ios -t 60
```



### 功能详解

#### 多应用并行测试
- 支持同时对多个应用进行性能测试，大幅提高测试效率
- 每个应用的测试结果会保存在独立的子目录中
- 测试完成后会生成总体统计报告，显示各应用的测试状态
- 支持应用级别的性能对比分析

#### 网络流量监控
- 实时采集应用的网络流量数据（前台和后台流量）
- 数据以MB为单位进行统计和展示
- 在图表和交互式报告中直观展示网络流量变化趋势
- Android平台通过dumpsys traffic命令实现
- iOS平台通过idevicesyslog和ifconfig命令实现

#### FPS流畅度测试
- 采集应用的帧率数据，评估应用的流畅度
- Android平台通过dumpsys gfxinfo获取绘制性能数据
- iOS平台通过分析系统日志和设备性能特征估算FPS值
- 支持在图表和交互式报告中查看FPS变化情况
- 帮助开发人员识别应用中的卡顿问题

#### 启动时间测量
- 精确测量应用从启动到完全加载的时间
- Android平台通过am force-stop和am start -W命令实现
- iOS平台提供多种启动方法，包括自动和手动方式
- 支持启动过程监控和时间统计

#### 应用生命周期自动测试
- 支持根据应用启动和关闭来自动启动和关闭性能测试
- 自动化的应用启动、监控、关闭流程
- 可配置的等待时间（默认30秒）
- 支持多应用批量测试
- 自动保存每次测试的独立结果
- 适用于CI/CD流水线和自动化测试场景

#### 增强稳定性机制
- **设备连接稳定性**：自动检测设备响应性，优先使用响应正常的设备
- **命令执行重试**：ADB和iOS命令执行失败时自动重试，支持指数退避策略
- **数据收集降级**：性能数据获取失败时自动使用默认值，确保测试继续进行
- **异常处理增强**：完善的错误日志记录和异常恢复机制
- **超时保护**：所有命令执行都有超时保护，避免长时间等待

## 测试结果

测试完成后，工具会在指定的输出目录中生成以下文件：

1. **results.json**：包含所有性能指标的原始数据
2. **summary.json**：包含各性能指标的统计摘要（平均值、最大值、最小值等）
3. **charts/**：包含各性能指标的图表图片
   - cpu_chart_{timestamp}.png：CPU使用率图表
   - memory_chart_{timestamp}.png：内存使用图表
   - battery_chart_{timestamp}.png：电池电量图表
   - network_chart_{timestamp}.png：网络流量图表
   - fps_chart_{timestamp}.png：FPS帧率图表
   - summary_chart_{timestamp}.png：汇总所有指标的图表
4. **interactive_reports/**：包含交互式HTML报告
   - interactive_report_{timestamp}.html：可在浏览器中打开的交互式报告

### 多应用并行测试结果

进行多应用并行测试时，每个应用的测试结果会保存在输出目录下的独立子目录中：

```
output_dir/
├── app_app1/
│   ├── results.json
│   ├── summary.json
│   ├── charts/
│   └── interactive_reports/
├── app_app2/
│   ├── results.json
│   ├── summary.json
│   ├── charts/
│   └── interactive_reports/
└── global/
    ├── results.json
    ├── summary.json
    ├── charts/
    └── interactive_reports/
```

## 注意事项

1. 确保设备已通过USB连接并开启了USB调试模式（Android）或开发者模式（iOS）
2. iOS设备测试需要安装libimobiledevice工具包
3. 测试过程中尽量避免操作设备，以免影响测试结果的准确性
4. 如需测试特定场景，请在测试开始前准备好相应的测试环境
5. iOS平台的应用启动时间测量在某些情况下可能需要手动启动应用

## 扩展与定制

本工具采用模块化设计，便于扩展和定制新功能。您可以根据需求添加新的性能指标采集模块或优化现有功能。

### 最新功能

- [x] **iOS 10-18+ 全面支持**：支持iOS 10到最新版本的性能监控
- [x] **Android 8-16+ 全面支持**：支持Android 8到最新版本的性能监控
- [x] **智能平台检测**：自动检测设备平台类型和系统版本
- [x] **性能基准测试**：支持基准测试和压力测试
- [x] **系统兼容性检测**：自动检测工具可用性和系统兼容性

- [x] **应用级别测试**：所有性能指标基于具体应用收集
- [x] **多场景测试支持**：支持冷启动、正常使用、压力测试等场景

### 已实现功能

- [x] iOS平台全面支持
- [x] Android平台全面支持

- [x] 图形化测试报告生成
- [x] 多应用并行测试
- [x] 网络流量监控
- [x] FPS流畅度测试
- [x] 错误处理和重试机制
- [x] 结构化日志系统
- [x] 应用级别性能监控
- [x] 性能基准测试
- [x] 智能平台检测
- [x] 多场景测试支持

### 高级功能模块

#### 🔍 深度性能分析模块 (Deep Performance Analysis)

**技术架构：**
- **瓶颈分析引擎**：基于统计学和机器学习算法，支持多维度分析
- **趋势分析算法**：线性回归、移动平均、趋势预测、移动窗口分析
- **异常检测算法**：基于3-sigma规则、Z-score分析、机器学习模型
- **智能建议系统**：基于规则引擎和机器学习模型的优化建议生成

**核心功能：**
- **性能瓶颈分析**：
  - CPU使用率瓶颈检测（高使用率、波动性分析、趋势异常）
  - 内存使用瓶颈检测（内存泄漏、高使用率、增长趋势）
  - 网络流量瓶颈检测（流量异常、连接问题、波动性）
  - FPS性能瓶颈检测（低帧率、卡顿分析、渲染性能）
  - 系统级瓶颈检测（启动时间、电池消耗、系统负载）

**技术特点：**
- 支持多种统计分析方法（方差分析、趋势分析、异常检测、移动平均）
- 自动生成优化建议和性能改进方案
- 可配置的阈值和分析参数
- 支持历史数据对比和趋势预测
- 智能瓶颈识别和严重程度评估

**使用方法：**
```python
from deep_performance_analysis import DeepPerformanceAnalyzer

# 创建分析器实例
analyzer = DeepPerformanceAnalyzer(lperf_instance)

# 分析性能瓶颈
bottlenecks = analyzer.analyze_performance_bottlenecks()

# 分析性能趋势
trends = analyzer.analyze_performance_trends()

# 检测性能异常
anomalies = analyzer.detect_anomalies()

# 生成完整分析报告
report = analyzer.generate_analysis_report()

# 获取分析摘要
summary = analyzer.get_analysis_summary()
print(summary)
```

#### 🤖 机器学习性能预测模块 (Machine Learning Performance Prediction)

**技术架构：**
- **预测模型**：基于时间序列分析和机器学习算法，支持多种算法
- **特征工程**：多维度特征提取和选择，包括统计特征、趋势特征、波动性特征
- **模型训练**：支持增量学习和模型更新，自动优化模型参数
- **准确性评估**：交叉验证、预测误差分析、R²值计算

**核心功能：**
- **性能趋势预测**：基于历史数据预测未来性能趋势，支持短期和中期预测
- **异常预测**：基于历史异常模式预测未来异常，提供异常概率评估
- **容量规划**：基于预测结果进行资源需求预测，支持资源优化配置
- **风险评估**：基于预测结果评估系统风险，提供风险预警

**技术特点：**
- 支持多种机器学习算法（线性回归、移动平均、趋势外推、时间序列分析）
- 自动特征提取和模型训练，支持最优参数选择
- 支持模型准确性和预测置信度评估，提供预测可靠性分析
- 支持增量学习和模型更新，持续优化预测性能
- 智能特征工程，自动提取统计特征、趋势特征、波动性特征

**支持的预测算法：**
1. **移动平均模型**：适合处理时间序列数据，自动优化窗口大小
2. **线性回归模型**：适合分析趋势性数据，提供R²值评估
3. **趋势外推模型**：基于历史趋势进行外推，适合短期预测

**使用方法：**
```python
from ml_performance_predictor import MLPerformancePredictor

# 创建预测器实例
predictor = MLPerformancePredictor(lperf_instance)

# 准备训练数据
training_data = predictor.prepare_training_data()

# 训练预测模型
result = predictor.train_prediction_models('moving_average')

# 进行性能预测
prediction = predictor.predict_performance('cpu', horizon=10)

# 预测异常
anomaly_prediction = predictor.predict_anomalies('memory', horizon=5)

# 生成预测报告
report = predictor.generate_prediction_report()

# 获取预测摘要
summary = predictor.get_prediction_summary()
print(summary)

# 保存和加载模型
predictor.save_models('models.json')
predictor.load_models('models.json')
```

**预测准确性评估：**
- 支持多种准确性指标：均方根误差(RMSE)、R²值、预测置信度
- 自动模型选择：根据数据特征自动选择最优算法
- 预测置信度：基于模型准确性和预测步长计算置信度

#### 🚨 实时性能告警系统 (Real-time Performance Alert System)

**技术架构：**
- **告警规则引擎**：支持多种条件判断和阈值设置，包括复合条件
- **多渠道告警系统**：控制台、日志、文件、邮件、Webhook、自定义通道
- **告警管理**：告警历史、告警抑制、告警升级、告警模板管理
- **智能诊断**：基于规则引擎和机器学习的智能诊断和优化建议

**核心功能：**
- **实时监控**：持续监控系统性能指标，支持后台监控和实时告警
- **智能告警**：基于规则和机器学习触发告警，支持多种告警级别
- **多渠道通知**：支持多种告警通知方式，确保告警及时送达
- **告警规则管理**：支持自定义规则和模板，支持规则导入导出
- **告警历史记录**：记录所有告警事件和响应情况，支持告警分析
- **告警抑制机制**：避免告警风暴，支持告警升级和自动恢复

**技术特点：**
- 支持多种告警通道配置，可扩展自定义通道
- 支持告警规则模板和自定义规则，支持复杂条件组合
- 支持告警抑制和升级机制，提供智能告警管理
- 支持告警配置的持久化存储和恢复，支持配置热更新
- 支持告警风暴检测和智能抑制，提供告警质量评估

**支持的告警条件：**
- **比较操作符**：大于(gt)、小于(lt)、等于(eq)、不等于(ne)、范围(in)
- **复合条件**：支持AND、OR逻辑组合
- **时间窗口**：支持滑动窗口和固定窗口告警
- **告警级别**：info、warning、error、critical

**支持的告警通道：**
1. **控制台告警**：实时显示告警信息
2. **日志告警**：记录告警到日志文件
3. **文件告警**：保存告警到指定文件
4. **邮件告警**：发送告警邮件通知
5. **Webhook告警**：调用HTTP接口发送告警
6. **自定义通道**：支持扩展自定义告警方式

**使用方法：**
```python
from realtime_alert_system import RealTimeAlertSystem

# 创建告警系统实例
alert_system = RealTimeAlertSystem(lperf_instance)

# 添加告警规则
alert_system.add_alert_rule(
    metric='cpu',
    condition='gt',
    threshold=80,
    severity='warning',
    description='CPU使用率超过80%'
)

# 添加告警通道
alert_system.add_alert_channel('console', {})
alert_system.add_alert_channel('file', {'filepath': 'alerts.log'})

# 开始监控
alert_system.start_monitoring()

# 检查告警
current_data = {'cpu': 85, 'memory': 70}
alerts = alert_system.check_alerts(current_data)

# 获取告警历史
history = alert_system.get_alert_history()

# 保存告警配置
alert_system.save_alert_config('alert_config.json')

# 停止监控
alert_system.stop_monitoring()
```

**告警规则配置示例：**
```json
{
  "cpu_high_usage": {
    "metric": "cpu",
    "condition": "gt",
    "threshold": 80,
    "severity": "warning",
    "description": "CPU使用率超过80%",
    "recommendation": "检查后台进程和定时任务"
  },
  "memory_critical": {
    "metric": "memory",
    "condition": "gt",
    "threshold": 90,
    "severity": "critical",
    "description": "内存使用率超过90%",
    "recommendation": "立即检查内存泄漏问题"
  }
}
```

**智能告警特性：**
- **告警风暴检测**：自动识别告警风暴并实施抑制
- **告警升级机制**：根据告警严重程度和时间自动升级
- **智能诊断**：基于告警模式提供优化建议
- **告警质量评估**：评估告警的有效性和准确性

## 🚀 高级功能使用指南

### 完整工作流程示例

以下是一个完整的高级功能使用示例，展示如何集成深度分析、ML预测和实时告警（需要先安装相关依赖）：

```python
#!/usr/bin/env python3
"""
高级功能集成示例
展示如何使用lperf的高级功能模块进行全面的性能分析
"""

from lperf import LPerf
from deep_performance_analysis import DeepPerformanceAnalyzer
from ml_performance_predictor import MLPerformancePredictor
from realtime_alert_system import RealTimeAlertSystem
import time
import json

def main():
    # 1. 创建LPerf实例并收集性能数据
    print("🚀 开始性能数据收集...")
    lperf = LPerf(
        package_name='com.example.app',
        platform='android',
        interval=1.0,
        output_dir='./advanced_analysis'
    )
    
    # 收集60秒的性能数据
    lperf.start_monitoring(duration=60)
    
    # 2. 深度性能分析
    print("\\n🔍 开始深度性能分析...")
    analyzer = DeepPerformanceAnalyzer(lperf)
    
    # 分析性能瓶颈
    bottlenecks = analyzer.analyze_performance_bottlenecks()
    print(f"发现 {sum(len(b) for b in bottlenecks.values())} 个性能瓶颈")
    
    # 分析性能趋势
    trends = analyzer.analyze_performance_trends()
    print(f"分析了 {len(trends)} 个指标的趋势")
    
    # 检测性能异常
    anomalies = analyzer.detect_anomalies()
    print(f"检测到 {sum(len(a) for a in anomalies.values())} 个异常")
    
    # 生成分析报告
    analysis_report = analyzer.generate_analysis_report()
    print("\\n📊 深度分析报告摘要:")
    print(analyzer.get_analysis_summary())
    
    # 3. 机器学习性能预测
    print("\\n🤖 开始机器学习性能预测...")
    predictor = MLPerformancePredictor(lperf)
    
    # 准备训练数据
    training_data = predictor.prepare_training_data()
    print(f"准备了 {len(training_data)} 个指标的训练数据")
    
    # 训练预测模型
    training_result = predictor.train_prediction_models('moving_average')
    print(f"模型训练完成，整体准确性: {training_result['overall_accuracy']:.2f}")
    
    # 进行性能预测
    cpu_prediction = predictor.predict_performance('cpu', horizon=10)
    memory_prediction = predictor.predict_performance('memory', horizon=10)
    
    print(f"CPU未来10个时间点预测: {cpu_prediction['predictions']}")
    print(f"内存未来10个时间点预测: {memory_prediction['predictions']}")
    
    # 预测异常
    anomaly_prediction = predictor.predict_anomalies('cpu', horizon=5)
    print(f"CPU异常预测概率: {anomaly_prediction.get('anomaly_probabilities', [])}")
    
    # 4. 实时性能告警系统
    print("\\n🚨 配置实时性能告警系统...")
    alert_system = RealTimeAlertSystem(lperf)
    
    # 添加告警规则
    alert_system.add_alert_rule(
        metric='cpu',
        condition='gt',
        threshold=80,
        severity='warning',
        description='CPU使用率超过80%'
    )
    
    alert_system.add_alert_rule(
        metric='memory',
        condition='gt',
        threshold=200,
        severity='critical',
        description='内存使用超过200MB'
    )
    
    # 添加告警通道
    alert_system.add_alert_channel('console', {})
    alert_system.add_alert_channel('file', {'filepath': 'performance_alerts.log'})
    
    # 开始监控
    alert_system.start_monitoring()
    print("告警系统已启动，开始实时监控...")
    
    # 模拟实时数据检查
    for i in range(5):
        current_data = {
            'cpu': 75 + i * 5,  # 模拟CPU使用率上升
            'memory': 180 + i * 10  # 模拟内存使用上升
        }
        
        alerts = alert_system.check_alerts(current_data)
        if alerts:
            print(f"检测到告警: {alerts}")
        
        time.sleep(2)
    
    # 停止告警监控
    alert_system.stop_monitoring()
    
    # 5. 生成综合报告
    print("\\n📋 生成综合报告...")
    
    # 保存分析结果
    with open('./advanced_analysis/analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)
    
    # 保存预测结果
    prediction_report = predictor.generate_prediction_report()
    with open('./advanced_analysis/prediction_report.json', 'w', encoding='utf-8') as f:
        json.dump(prediction_report, f, ensure_ascii=False, indent=2)
    
    # 保存告警配置
    alert_system.save_alert_config('./advanced_analysis/alert_config.json')
    
    print("✅ 高级功能分析完成！")
    print("📁 结果保存在: ./advanced_analysis/")
    print("📊 分析报告: analysis_report.json")
    print("🔮 预测报告: prediction_report.json")
    print("🚨 告警配置: alert_config.json")

if __name__ == '__main__':
    main()
```

### 高级功能配置

#### 深度分析配置

```json
{
  "analysis_config": {
    "bottleneck_thresholds": {
      "cpu_high_usage": 80.0,
      "memory_high_usage": 85.0,
      "network_high_volatility": 1000.0,
      "fps_low_threshold": 30.0
    },
    "trend_analysis": {
      "min_data_points": 10,
      "trend_threshold": 0.1,
      "moving_average_window": 5
    },
    "anomaly_detection": {
      "sigma_threshold": 3.0,
      "min_data_points": 20
    }
  }
}
```

#### ML预测配置

```json
{
  "ml_config": {
    "feature_engineering": {
      "statistical_features": true,
      "trend_features": true,
      "volatility_features": true,
      "time_features": true
    },
    "model_selection": {
      "auto_select": true,
      "preferred_algorithms": ["moving_average", "linear_regression"]
    },
    "prediction": {
      "max_horizon": 20,
      "confidence_threshold": 0.7
    }
  }
}
```

#### 告警系统配置

```json
{
  "alert_config": {
    "global_settings": {
      "check_interval": 1.0,
      "alert_suppression": true,
      "suppression_window": 300,
      "escalation_enabled": true
    },
    "channels": {
      "console": {"enabled": true},
      "file": {"enabled": true, "filepath": "alerts.log"},
      "email": {"enabled": false, "smtp_server": "smtp.example.com"},
      "webhook": {"enabled": false, "url": "https://api.example.com/alerts"}
    }
  }
}
```

### 性能优化建议

1. **数据收集优化**：
   - 根据分析需求调整数据收集间隔
   - 使用多线程并行收集多应用数据
   - 定期清理历史数据以节省存储空间

2. **分析性能优化**：
   - 对于大量数据，使用批处理模式
   - 启用缓存机制减少重复计算
   - 使用异步处理提高响应速度

3. **预测模型优化**：
   - 定期重新训练模型以保持准确性
   - 使用交叉验证选择最优参数
   - 监控模型性能并自动调整

4. **告警系统优化**：
   - 合理设置告警阈值避免误报
   - 使用告警抑制机制避免告警风暴
   - 配置多级告警确保重要问题及时处理
  "cpu_high_usage": {
    "metric": "cpu",
    "condition": "gt",
    "threshold": 80,
    "severity": "high",
    "description": "CPU使用率超过80%",
    "recommendation": "检查后台进程和定时任务"
  },
  "memory_high_usage": {
    "metric": "memory",
    "condition": "gt",
    "threshold": 85,
    "severity": "high",
    "description": "内存使用率超过85%",
    "recommendation": "检查内存泄漏和后台进程"
  }
}
```

**告警通道配置：**
```json
{
  "console": {
    "type": "console",
    "config": {}
},
"log": {
  "type": "log",
  "config": {}
},
"file": {
  "type": "file",
  "config": {
    "file_path": "performance_alerts.log"
},
"email": {
  "type": "email",
  "config": {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "username": "alert@example.com",
    "password": "your_password"
},
"webhook": {
  "type": "webhook",
  "config": {
    "url": "https://api.example.com/webhook",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer token"
    }
  }
}
```

### 未来规划

## License

[MIT](LICENSE)