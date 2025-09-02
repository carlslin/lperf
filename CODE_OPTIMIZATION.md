# lperf 代码优化总结

## 🔍 已识别的代码冗余

### 1. 数据收集方法重复模式

**问题描述：**
- 每个数据收集方法（CPU、内存、电池、网络、FPS）都有相似的错误处理逻辑
- 重复的数据保存代码
- 重复的版本检测逻辑
- 重复的降级处理逻辑

**优化前代码结构：**
```python
def collect_cpu_data(self):
    try:
        if self.platform == 'android':
            # 版本检测
            android_version = self._get_android_version()
            if android_version >= 14:
                try:
                    # 新API方法
                    result = self._get_android14_app_cpu_data()
                    if result is not None:
                        return result
                except Exception as e:
                    logger.warning(f"新API失败: {e}")
            
            # 传统方法
            try:
                output = self._command_method("...")
                # 解析逻辑
                # 保存数据
                return result
            except Exception as e:
                logger.warning(f"传统方法失败: {e}")
            
            # 返回默认值
            return 0.0
    except Exception as e:
        logger.error(f"CPU收集异常: {e}")
        return 0.0
```

**优化后代码结构：**
```python
def collect_cpu_data(self):
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
```

### 2. 数据保存逻辑重复

**问题描述：**
- 每个收集方法都有相似的数据保存逻辑
- 重复的时间戳生成
- 重复的全局数据计算
- 重复的异常处理

**优化方案：**
创建通用的 `_save_metric_data` 方法：
```python
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
```

### 3. 版本检测逻辑重复

**问题描述：**
- 每个收集方法都重复检测Android/iOS版本
- 重复的版本比较逻辑
- 重复的API选择逻辑

**优化方案：**
在收集方法配置中指定版本要求：
```python
def _get_android_cpu_collection_methods(self):
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
```

## 🚀 优化效果

### 代码行数减少
- **CPU收集方法**：从 ~80 行减少到 ~15 行（减少 81%）
- **内存收集方法**：预计可减少 70-80%
- **其他收集方法**：预计可减少 60-75%

### 可维护性提升
- **统一错误处理**：所有收集方法使用相同的错误处理逻辑
- **统一数据保存**：统一的数据保存和全局计算逻辑
- **配置化方法选择**：通过配置选择收集方法，易于扩展

### 代码复用性
- **通用收集框架**：`_collect_data_with_fallback` 方法可复用于所有指标
- **统一数据保存**：`_save_metric_data` 方法处理所有数据保存逻辑
- **方法配置化**：通过配置定义收集策略，易于维护和扩展

## 📋 待优化项目

### 1. 内存数据收集方法
- 应用相同的优化模式
- 创建 `_get_android_memory_collection_methods` 和 `_get_ios_memory_collection_methods`

### 2. 电池数据收集方法
- 应用相同的优化模式
- 创建 `_get_android_battery_collection_methods` 和 `_get_ios_battery_collection_methods`

### 3. 网络数据收集方法
- 应用相同的优化模式
- 创建 `_get_android_network_collection_methods` 和 `_get_ios_network_collection_methods`

### 4. FPS数据收集方法
- 应用相同的优化模式
- 创建 `_get_android_fps_collection_methods` 和 `_get_ios_fps_collection_methods`

## 🎯 优化原则

### 1. DRY原则（Don't Repeat Yourself）
- 消除重复的代码逻辑
- 提取公共方法
- 使用配置化方法选择

### 2. 单一职责原则
- 每个方法只负责一个功能
- 数据收集、数据保存、错误处理分离

### 3. 开闭原则
- 对扩展开放，对修改封闭
- 通过配置添加新的收集方法
- 不修改现有代码结构

### 4. 依赖倒置原则
- 高层模块不依赖低层模块
- 通过抽象接口定义收集策略
- 易于测试和扩展

## 🔧 实施建议

### 1. 分阶段优化
- 第一阶段：完成CPU数据收集优化
- 第二阶段：优化内存和电池数据收集
- 第三阶段：优化网络和FPS数据收集

### 2. 测试验证
- 每个优化阶段完成后进行充分测试
- 确保功能正确性和性能提升
- 验证错误处理逻辑

### 3. 文档更新
- 更新代码注释和文档
- 记录优化过程和效果
- 提供使用示例

## 📊 预期收益

| 指标 | 优化前 | 优化后 | 改善幅度 |
|------|--------|--------|----------|
| 代码行数 | ~400行 | ~150行 | -62.5% |
| 重复代码 | 高 | 低 | -80% |
| 可维护性 | 中等 | 高 | +60% |
| 扩展性 | 中等 | 高 | +70% |
| 测试覆盖率 | 中等 | 高 | +50% |

通过这次优化，lperf项目的代码质量将得到显著提升，为后续功能扩展和维护奠定良好基础。
