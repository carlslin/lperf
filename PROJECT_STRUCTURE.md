# lperf 项目结构说明

## 📁 项目文件结构

```
lperf/
├── README.md                           # 项目主要说明文档
├── ARCHITECTURE_DIAGRAM.md            # 系统架构图和技术说明
├── LICENSE                            # MIT开源许可证
├── requirements.txt                   # Python依赖包列表
├── .gitignore                        # Git忽略文件配置
├── PROJECT_STRUCTURE.md              # 本文件：项目结构说明
│
├── 核心模块/
│   ├── lperf.py                      # 主程序文件
│   ├── deep_performance_analysis.py  # 深度性能分析模块
│   ├── ml_performance_predictor.py   # 机器学习性能预测模块
│   └── realtime_alert_system.py      # 实时性能告警系统模块
│
└── 配置文件/
    ├── app_test_config.json          # 应用测试配置
    └── system_compatibility.json     # 系统兼容性配置
```

## 🔧 核心模块说明

### 1. lperf.py (主程序)
- **功能**：主要的性能测试工具
- **大小**：174KB，4005行代码
- **作用**：提供命令行界面，协调各模块工作

### 2. deep_performance_analysis.py
- **功能**：深度性能分析引擎
- **大小**：17KB，453行代码
- **作用**：性能瓶颈分析、趋势分析、异常检测

### 3. ml_performance_predictor.py
- **功能**：机器学习性能预测
- **大小**：14KB，417行代码
- **作用**：基于历史数据的性能趋势预测和异常预测

### 4. realtime_alert_system.py
- **功能**：实时性能告警系统
- **大小**：17KB，467行代码
- **作用**：实时监控、智能告警、多渠道通知

## 📋 配置文件说明



### 2. app_test_config.json
- **用途**：应用测试的配置参数
- **内容**：测试时长、采样间隔、应用包名等

### 3. system_compatibility.json
- **用途**：系统兼容性检测配置
- **内容**：各平台版本支持、命令可用性检测

## 🚀 使用方法

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行主程序
```bash
python lperf.py --help
```

### 测试Android应用
```bash
python lperf.py -p com.example.app --platform android -t 60
```

### 测试iOS应用
```bash
python lperf.py -p com.example.bundleid --platform ios -t 60
```



## 📊 输出文件

运行测试后会在指定目录生成：
- `results.json`：原始性能数据
- `summary.json`：性能统计摘要
- `charts/`：性能图表
- `interactive_reports/`：交互式HTML报告

## 🔍 高级功能

### 深度性能分析
```python
from deep_performance_analysis import DeepPerformanceAnalyzer
analyzer = DeepPerformanceAnalyzer(lperf_instance)
report = analyzer.generate_analysis_report()
```

### 机器学习预测
```python
from ml_performance_predictor import MLPerformancePredictor
predictor = MLPerformancePredictor(lperf_instance)
prediction = predictor.predict_performance('cpu', horizon=5)
```

### 实时告警系统
```python
from realtime_alert_system import RealTimeAlertSystem
alert_system = RealTimeAlertSystem(lperf_instance)
alert_system.start_monitoring()
```

## 📝 开发说明

- 项目采用模块化设计，各功能模块独立
- 支持插件式扩展，可轻松添加新功能
- 完善的错误处理和日志系统
- 支持多平台和多设备并行测试
- 提供丰富的配置选项和自定义能力

## 📄 许可证

本项目采用MIT开源许可证，详见LICENSE文件。
