# 需求跟踪器

最新ID: 27

---

## 一、需求文档跟踪

| ID | 文档 | 状态 | 完成日期 | 备注 |
|----|----------|--------|-----------|-------|
| REQ-001 | 0-整体需求.md | Done | 2026-03-06 | 整体功能设计概述 |
| REQ-002 | 1-翻译基础设置.md | In Progress | 2026-03-06 | 翻译设置界面需求（开发中） |
| REQ-003 | 2-翻译窗口选择.md | Done | 2026-03-07 | 窗口选择界面需求 |
| REQ-004 | 3-截屏区域定位.md | Done | 2026-03-07 | 区域选择界面需求 |
| REQ-005 | 4-运行参数配置.md | Done | 2026-03-07 | 运行参数配置需求 |
| REQ-006 | 5-OCR文本识别.md | Todo | - | OCR识别后台功能需求 |
| REQ-007 | 6-文本翻译.md | Todo | - | 文本翻译与结果展示需求 |

---

## 二、架构设计文档跟踪

| 文档名称 | 状态 | 备注 |
|---------|------|------|
| 总体技术架构设计 (0-总体实现方案.md) | Done | 技术栈、线程模型、分层架构 |
| 翻译设置界面详细设计 (1-翻译设置-详细设计.md) | Done | ui/settings_window.py 设计 |
| 窗口选择界面详细设计 (2-窗口选择-详细设计.md) | Done | ui/window_select.py 设计 |
| 截图区域选择界面详细设计 (3-区域选择-详细设计.md) | Done | ui/region_select.py 设计 |
| 运行参数配置界面详细设计 (4-运行参数-详细设计.md) | Done | ui/run_config.py 设计与实现 |
| 截图服务与多线程调度 (5-截图服务与多线程调度.md) | Done | controller/scheduler.py + core/capture.py 设计 |
| OCR服务与PaddleOCR集成 (6-OCR服务与PaddleOCR集成.md) | Done | core/ocr_engine.py 设计 |
| 文本去重与翻译服务 (7-文本去重与翻译服务.md) | Done | core/text/eduplicator.py + core/translator.py 设计 |
| 悬浮窗实现与样式控制 (8-悬浮窗实现与样式控制.md) | Done | ui/floating_window.py 设计 |

---

## 三、开发任务跟踪

| ID | 任务描述 | 状态 | 优先级 | 关联需求 | 备注 |
|----|----------|--------|--------|----------|-------|
| DEV-001 | 项目目录结构创建 | Done | High | ALL | 创建 ui/, controller/, data/ 目录 |
| DEV-002 | requirements.txt 依赖配置 | Done | High | ALL | PyQt5, pywin32, PaddleOCR, Pillow, imagehash, python-Levenshtein |
| DEV-003 | main.py 程序入口 | Done | High | REQ-001 | |
| DEV-004 | utils/logger.py 日志系统 | Todo | Medium | ALL | |
| DEV-005 | controller/config_interface.py | Done | High | REQ-002, REQ-005 | 配置管理器接口定义 |
| DEV-006 | controller/config_helper.py | Done | High | REQ-002, REQ-005 | 配置管理器临时实现（内存） |
| DEV-007 | controller/state_manager.py | Todo | Medium | REQ-005 | 状态管理器 |
| DEV-008 | controller/scheduler.py | Todo | High | REQ-4 | 任务调度器（多线程） |
| DEV-009 | core/window_manager.py | Done | High | REQ-003 | 窗口管理器 |
| DEV-010 | core/capture.py | Todo | High | REQ-4 | 截图服务 |
| DEV-011 | core/image_processor.py | Todo | High | REQ-4 | 图像处理（裁剪/hash） |
| DEV-012 | core/ocr_engine.py | Todo | High | REQ-5 | OCR服务（PaddleOCR） |
| DEV-013 | core/text_deduplicator.py | Todo | High | | 文本去重 |
| DEV-014 | core/translator.py | Todo | High | REQ-6 | 翻译服务 |
| DEV-015 | ui/main_window.py | Done | High | REQ-001 | 主窗口（含界面导航） |
| DEV-016 | ui/settings_window.py | Done | High | REQ-002 | 翻译设置界面 |
| DEV-017 | ui/window_select.py | Done | High | REQ-003 | 窗口选择界面 |
| DEV-018 | ui/region_select.py | Done | High | REQ-4 | 区域选择界面 |
| DEV-019 | ui/run_config.py | Done | High | REQ-005 | 运行参数界面 |
| DEV-020 | ui/floating_window.py | Todo | High | REQ-6 | 悬浮窗 |

### 区域选择功能细化任务

| ID | 任务描述 | 状态 | 优先级 | 关联需求 | 备注 |
|----|----------|--------|--------|----------|-------|
| DEV-021 | core/window_capture.py 窗口截图服务 | Done | High | REQ-4 | 使用 hwnd 获取窗口截图的公共工具，支持定时截图 |
| DEV-022 | ui/region_select.py 主界面框架 | Done | High | REQ-4 | 区域选择界面布局、按钮、标签 |
| DEV-023 | ui/region_select_widget.py 基础结构 | Done | High | REQ-4 | RegionSelectWidget 初始化、数据结构 |
| DEV-024 | ui/region_select_widget.py 图片展示与缩放 | Done | High | REQ-4 | 加载图片、缩放适配、居中显示 |
| DEV-025 | ui/region_select_widget.py 坐标转换系统 | Done | High | REQ-4 | 控件/显示/原始/比例坐标转换 |
| DEV-026 | ui/region_select_widget.py 边界约束函数 | Done | High | REQ-4 | constrain_rect 边界与最小尺寸约束 |
| DEV-027 | ui/region_select_widget.py 遮罩层绘制 | Done | High | REQ-4 | 半透明遮罩、亮色选区绘制 |
| DEV-028 | ui/region_select_widget.py 选区边框绘制 | Done | High | REQ-4 | 2px 蓝色边框绘制 |
| DEV-029 | ui/region_select_widget.py 控制点绘制 | Done | High | REQ-4 | 8个控制点计算与绘制 |
| DEV-030 | ui/region_select_widget.py 控制点检测 | Done | High | REQ-4 | 鼠标命中控制点检测 |
| DEV-031 | ui/region_select_widget.py 光标形状更新 | Done | High | REQ-4 | 根据位置更新光标形状 |
| DEV-032 | ui/region_select_widget.py 鼠标按下事件 | Done | High | REQ-4 | 移动/拉伸状态切换 |
| DEV-033 | ui/region_select_widget.py 鼠标移动事件 | Done | High | REQ-4 | 选区移动/拉伸逻辑 |
| DEV-034 | ui/region_select_widget.py 鼠标释放事件 | Done | High | REQ-4 | 操作完成、状态重置 |
| DEV-035 | ui/region_select_widget.py 窗口大小变化事件 | Done | High | REQ-4 | 重新计算缩放因子、调整选区 |
| DEV-036 | ui/region_select_widget.py 信号定义与节流 | Done | High | REQ-4 | selectionChanged 信号、50ms 节流 |
| DEV-037 | ui/region_select.py 主界面逻辑集成 | Done | High | REQ-4 | 截图调用、信息更新、配置保存 |

---

## 四、统计摘要

| 类别 | Total | Todo | In Progress | Done |
|------|-------|------|-------------|------|
| 需求文档 | 7 | 3 | 3 | 1 |
| 架构设计文档 | 9 | 0 | 0 | 9 |
| 开发任务 | 37 | 13 | 2 | 22 |

---

## 五、运行参数界面开发任务

| ID | 任务描述 | 状态 |
|----|----------|------|
| DEV-038 | 创建运行参数界面主框架和布局 | Done |
| DEV-039 | 实现配置加载和保存功能 | Done |
| DEV-040 | 实现状态管理和界面更新逻辑 | Done |
| DEV-041 | 实现滑块与SpinBox联动机制 | Done |
| DEV-042 | 实现字体选择和颜色选择功能 | Done |
| DEV-043 | 实现开始/暂停翻译逻辑 | Done |
| DEV-044 | 修改main_window.py集成运行参数界面 | Done |

## 六、待补充内容

(无待补充内容)

---

## 七、开发建议

### 阶段1：基础设施
- ✅ DEV-001 项目目录结构创建
- ✅ DEV-002 requirements.txt 依赖配置
- ✅ DEV-003 main.py 程序入口
- DEV-004 日志系统

### 阶段2：核心服务层
- ✅ DEV-009 窗口管理器
- ✅ DEV-021 窗口截图服务（区域选择先依赖）
- DEV-010 完整截图服务（含定时）
- DEV-011 图像处理器
- DEV-012 OCR引擎
- DEV-013 文本去重器
- DEV-014 翻译服务

### 阶段3：用户界面层
- ✅ DEV-015 主窗口
- ✅ DEV-016 翻译设置界面
- ✅ DEV-017 窗口选择界面
- ✅ DEV-018 区域选择界面（含 DEV-021~037）
- ✅ DEV-019 运行参数界面（含 DEV-038~044）
- DEV-020 悬浮窗

### 阶段4：控制调度与集成
- DEV-007 状态管理器
- DEV-008 任务调度器
- 集成测试

---

## 七、区域选择功能任务依赖关系

```
DEV-021 窗口截图服务
    ↓
DEV-022 主界面框架
    ↓
DEV-023 基础结构
    ├─→ DEV-024 图片展示与缩放
    ├─→ DEV-025 坐标转换系统
    └─→ DEV-026 边界约束函数
    ↓
DEV-027 遮罩层绘制
DEV-028 选区边框绘制
DEV-029 控制点绘制
    ↓
DEV-030 控制点检测
DEV-031 光标形状更新
    ↓
DEV-032 鼠标按下事件
    ↓
DEV-033 鼠标移动事件
    ↓
DEV-034 鼠标释放事件
    ↓
DEV-035 窗口大小变化事件
    ↓
DEV-036 信号定义与节流
    ↓
DEV-037 主界面逻辑集成
```
