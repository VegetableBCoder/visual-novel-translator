# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

**重要：与用户的所有交互必须使用中文。**

## 项目概述

视觉小说翻译器 - 一款针对视觉小说游戏的实时翻译工具。通过 OCR 技术从游戏中捕获日文/英文文本，使用翻译 API 转换为中文，并通过悬浮窗口显示结果。

**当前状态：** 规划/文档阶段。源代码尚未实现。

## 自定义技能

本项目在 `.claude/skills/` 中使用三个自定义 Claude 技能：

1. **requirement-driving** - 文档驱动开发工作流
   - 基于 `docs/requirements/` 中的需求文档
   - 在 `docs/requirements/TRACKER.md` 中跟踪需求状态
   - 状态流转：Todo → In Progress → Done
   - 用法：`/requirement-driving <文档>` 或查看状态

2. **architect-driving** - 设计优先，代码在后工作流
   - 提出 2-3 种实现方案
   - 编写任何代码前必须获得用户批准
   - 用法：`/architect-driving <任务描述>`

3. **architect-review** - 审核已有技术设计方案
   - 对照需求审核 `docs/architect/` 中的架构文档
   - 发现问题时提出替代方案
   - 用法：`/architect-review <需求>`

## 架构

### 技术栈
- **编程语言：** Python 3.14
- **GUI 框架：** PyQt5
- **Windows API：** pywin32（窗口捕获、屏幕截图）
- **OCR 引擎：** PaddleOCR（日语识别，支持竖排文字）
- **翻译服务：** 阿里云 API / Google API
- **图像处理：** Pillow + imagehash（用于基于 pHash 的去重）
- **文本去重：** Levenshtein 编辑距离

### 规划的目录结构
```
visual-novel-translator/
├── main.py                 # �入口程序
├── requirements.txt        # 依赖清单
├── ui/                     # 用户界面层 (PyQt5)
│   ├── main_window.py      # 主窗口
│   ├── settings_window.py  # 翻译设置
│   ├── window_select.py    # 窗口选择
│   ├── region_select.py    # 区域选择
│   ├── run_config.py       # 运行参数
│   └── floating_window.py  # 翻译结果悬浮窗
├── controller/             # 控制调度层
│   ├── config_manager.py   # 配置管理
│   ├── state_manager.py    # 状态管理
│   └── scheduler.py        # 任务调度
├── core/                   # 核心服务层
│   ├── window_manager.py   # 窗口管理 (pywin32)
│   ├── capture.py          # 截图服务
│   ├── image_processor.py  # 图像处理 (裁剪/hash)
│   ├── ocr_engine.py       # OCR 服务 (PaddleOCR)
│   ├── text_deduplicator.py # 文本去重
│   └── translator.py       # 翻译服务
└── data/                   # 数据目录
    ├── config.json         # 配置文件
    └── logs/               # 日志文件
```

### 线程模型
- **主线程 (UI)：** PyQt5 事件循环、用户界面、悬浮窗更新
- **工作线程 1 (截图)：** 定时屏幕截图、区域裁剪、pHash 计算、图像去重
- **工作线程 2 (OCR/翻译)：** OCR 识别、文本去重、API 翻译

### 数据流向
1. 截图线程捕获窗口区域 → 计算 计算 pHash
2. 如果图像变化 → 发送到 OCR 线程
3. OCR 识别文本 → 文本去重检查
4. 如果文本变化 → 调用翻译 API
5. 格式化结果 → 通过 Qt 信号发送到主线程
6. 主线程更新悬浮窗口

### 关键设计原则
- **相对定位：** OCR 区域使用比例坐标 (0-1)，适配窗口大小调整
- **两级去重：** 图像级 (pHash) + 文本级 (Levenshtein) 以最小化 API 调用
- **异步处理：** OCR 和翻译在独立线程运行，避免阻塞截图循环
- **状态分离：** 配置界面与运行界面分离

### 配置结构
```json
{
  "version": "1.0",
  "language": {"source": "ja", "target": "zh"},
  "translation": {
    "engine": "alibaba",
    "alibaba": {"access_key_id": "", "access_key_secret": ""},
    "google": {"api_key": ""}
  },
  "window": {
    "hwnd": 123456,
    "title": "",
    "region": {"left": 0.25, "top": 0.70, "right": 0.75, "bottom": 0.85}
  },
  "ocr": {
    "interval_ms": 1000,
    "image_threshold": 10,
    "text_threshold": 75
  },
  "display": {
    "font_family": "微软雅黑",
    "font_size": 16,
    "font_color": "#FFFFFF",
    "bg_opacity": 40,
    "show_original": true
  }
}
```

## 文档

- **需求文档：** `docs/requirements/` - 详细需求文档（中文）
- **架构文档：** `docs/architect/` - 架构设计文档（中文）
- **跟踪器：** `docs/requirements/TRACKER.md` - 需求状态跟踪

### 核心文档
- `docs/requirements/0-整体需求.md` - 整体功能需求
- `docs/architect/0-总体实现方案.md` - 总体技术架构
