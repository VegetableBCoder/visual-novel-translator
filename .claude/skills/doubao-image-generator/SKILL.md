---
name: doubao-image-generator
description: 使用豆包 (Doubao) Seedream API 生成 AI 图片。当用户需要生成图片、创建插图、根据文字描述生成图像、或提到"豆包生成图片"/"AI 画图"/"seedream"/"生成配图"时触发。支持传入 prompt 和文件保存路径，内置 5 秒限流。
---

# Doubao Image Generator

使用火山引擎豆包 Seedream API 生成 AI 图片，基于 `volcengine-python-sdk[ark]`。

## 前置依赖

首次使用前安装 SDK（只需一次）：

```bash
pip install 'volcengine-python-sdk[ark]'
```

## API Key 配置

**使用前必须设置占位符为你的真实 API Key。**

获取地址：https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement

三种设置方式（优先级从高到低）：

```bash
# 方式 1：环境变量（推荐）
export DOUBAO_API_KEY="your-api-key-here"

# 方式 2：兼容旧版命名
export AGENT_API_KEY="your-api-key-here"

# 方式 3：命令行参数（不推荐，容易泄露到历史记录）
python scripts/generate.py --api-key "your-api-key-here" ...
```

**密钥使用占位符**：SKILL.md 和脚本中不含真实密钥，使用时由你自己填写。

## 快速开始

```bash
# 基本用法
python <skill-dir>/scripts/generate.py \
  --prompt "一只可爱的橘猫坐在窗台上，阳光洒在毛发上" \
  --output cat.png

# 指定尺寸和格式
python <skill-dir>/scripts/generate.py \
  --prompt "赛博朋克风格的城市夜景，霓虹灯招牌" \
  --output cyberpunk.jpg \
  --size 1K \
  --format jpg

# 从文件读取 prompt
python <skill-dir>/scripts/generate.py \
  --prompt-file prompt.txt \
  --output result.png
```

## 命令行选项

```
python scripts/generate.py [options]

必需参数：
  --output, -o <path>      图片保存路径（必需）
  --prompt, -p <text>      图片生成提示词（与 --prompt-file 二选一）
  --prompt-file <path>     从文件读取提示词（与 --prompt 二选一）

可选参数：
  --model <name>           模型名称（默认: doubao-seedream-5.0-lite）
  --size <1K|2K>           图片尺寸（默认: 2K）
  --format <png|jpg|webp>  输出格式（默认: png）
  --watermark              添加水印（默认不添加）
  --api-key <key>          API Key（优先级高于环境变量，但不推荐）
```

## 支持的模型与参数

| 参数 | 可选值 | 说明 |
|------|--------|------|
| model | `doubao-seedream-5.0-lite` | 轻量模型，速度快 |
| size | `1K`, `2K` | 分辨率：1K ≈ 1024px, 2K ≈ 2048px |
| format | `png`, `jpg`, `webp` | 输出图片格式 |
| watermark | true / false | 是否添加水印（默认 false） |

## 限流机制

**API 有频率限制，脚本内置 5 秒间隔**，批量生成时自动等待：

```
[生成] 模型: doubao-seedream-5.0-lite | 尺寸: 2K
[限流] 等待 3.2s ...          # 距离上次调用不足 5 秒时自动等待
[响应] 图片 URL: https://...
[下载] 保存到: output.png
[完成] output.png (2,458,112 bytes)
```

连续调用多张图片时无需手动控制间隔，脚本会自动处理。

## 工作原理

```
用户提供 Prompt
    │
    ▼
rate_limit_wait() ──→ 检查距上次调用是否 >= 5 秒
    │
    ▼
Ark SDK ──→ POST ark.cn-beijing.volces.com/api/plan/v3
    │            model="doubao-seedream-5.0-lite"
    │            prompt, size, format, watermark
    ▼
返回图片 URL ──→ urlretrieve() 下载图片
    │
    ▼
保存到指定路径（自动创建父目录，自动补扩展名）
```

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| `ModuleNotFoundError: volcenginesdkarkruntime` | 运行 `pip install 'volcengine-python-sdk[ark]'` |
| `未提供 API Key` | 设置 `DOUBAO_API_KEY` 环境变量，或用 `--api-key` 参数 |
| API 返回 429 (Too Many Requests) | 限流被触发是正常的，脚本会自动等待 5 秒后重试 |
| 下载的图片打不开 | 检查 URL 是否有效，尝试用浏览器直接打开 URL 验证 |
| 中文 prompt 乱码 | 使用 `python -X utf8` 执行，或确保终端编码为 UTF-8 |
| 生成的图片质量不满意 | 尝试更详细的 prompt、更大的 `--size`、或更换模型 |

## Prompt 编写建议

豆包 Seedream 支持中英文 prompt，建议遵循以下原则：

- **主体 + 风格 + 细节**：`"一只猫"` → `"一只毛发蓬松的橘猫，油画风格，柔和自然光，浅景深"`
- **具体 > 抽象**：避免 `"美丽的风景"`，使用 `"富士山脚下的樱花树，清晨薄雾，浮世绘风格"`
- **长度适中**：50-200 字效果最佳，过长可能被截断
- **负面提示**：可通过描述"不要/避免"来排除不需要的元素

## 示例

### 示例 1：生成插图

```bash
python scripts/generate.py \
  --prompt "日式视觉小说风格的教室场景，午后阳光透过窗户，柔和色调，背景有书架和黑板，2D动画风格" \
  --output classroom.png \
  --size 2K
```

### 示例 2：批量生成角色立绘

```bash
# 批量生成会因限流自动间隔，无需手动 sleep
for char in "傲娇少女" "温柔学长" "神秘转校生"; do
  python scripts/generate.py \
    --prompt "视觉小说角色立绘：${char}，上半身，白色背景，干净线条，日式动画风格" \
    --output "char_${char}.png" \
    --size 1K
done
```

### 示例 3：生成背景素材

```bash
python scripts/generate.py \
  --prompt "夜晚的城市天际线，霓虹灯倒映在河面上，赛博朋克风格，宽屏构图" \
  --output bg_city_night.png \
  --size 2K
```
