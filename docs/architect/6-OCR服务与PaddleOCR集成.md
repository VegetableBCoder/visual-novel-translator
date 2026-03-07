# OCR识别后台模块 - 详细技术设计文档

## 1. 模块概述
OCR识别后台模块负责在自动翻译运行期间，对截图线程获取的区域图像进行文字识别。该模块与截图线程协同工作：
- **截图线程**：定时截图、区域裁剪、调用OCR服务处理图像
- **OCR服务**：接收图像、通过图片差分算法判断是否需要识别、调用OCR引擎识别文字、将识别结果传递给翻译模块

## 2. 整体架构与分工

### 2.1 职责划分
| 模块 | 所在线程 | 核心职责 |
|--------|----------|----------|
| 截图线程 | 截图线程 | 定时截图、区域裁剪、调用OCR服务处理图像 |
| OCR服务 | 截图线程（同步调用） | 维护历史图片、图片差分判断、调用OCR引擎、触发翻译 |
| OCR引擎 | 截图线程（同步调用） | PaddleOCR封装、图像识别、结果解析 |
| 图像处理器 | 无状态工具类 | 提供图片差分计算的无状态方法 |

### 2.2 数据流
截图线程循环:
    截图 → 裁剪 → OCRService.process_image(cropped_image)

OCRService.process_image(image):
    加锁获取 last_image
    若 last_image 存在:
        diff = ImageProcessor.calculate_diff_percent(image, last_image)
        若 diff < threshold:
            return (跳过OCR)
    result = OCREngine.recognize(image)
    若 result.success:
        更新 last_image = image
        通过信号发送 OCR结果

## 3. 图片差分去重设计

### 3.1 选择差分算法而非pHash
- **pHash局限性**：对聊天框这种仅文本变动的场景不友好
  - pHash基于感知哈希，对细小文本变化不敏感
  - 视觉小说中，聊天框位置不变，仅文字内容变化时，pHash可能误判为相似

- **图片差分算法优势**：
  - 直接比较像素差异，对文本变化更敏感
  - 通过缩放统一尺寸平衡性能和准确度
  - 差异百分比阈值易于理解和配置

### 3.2 ImageProcessor扩展（无状态方法）

#### 方法签名
```python
@staticmethod
def calculate_diff_percent(
    image1: Optional[Image.Image],
    image2: Optional[Image.Image],
    target_size: Tuple[int, int] = (160, 120)
) -> float:
    """
    计算两张图片的像素差异百分比

    Args:
        image1: 图片1（可为None，表示首次）
        image2: 图片2（可为None，表示首次）
        target_size: 统一缩放的尺寸，默认160x120

    Returns:
        float: 差异百分比，0-1范围
               - None时返回1.0（视为完全不同）
    """
```

#### 算法实现
1. 任一为None，返回1.0（表示首次或完全不同）
2. 统一缩放到`target_size`（保持宽高比）
3. 转换为灰度图（单通道）
4. 转换为numpy数组
5. 计算像素差异：`diff = abs(img1 - img2).sum() / total_pixels`
6. 归一化到0-1范围（像素值0-255，除以255）

#### 性能考虑
- 缩放尺寸160x120：19,200像素，计算速度快
- 灰度处理：减少计算量
- 首次执行时快速返回1.0

## 4. OCR服务设计

### 4.1 类设计：OCRService

#### 状态维护
```python
class OCRService(QObject):
    # 信号定义
    ocr_result = pyqtSignal(str, float)  # 识别文本, 时间戳
    error_signal = pyqtSignal(str)       # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()

        # 依赖注入
        self._ocr_engine = None
        self._image_processor = None

        # 状态维护
        self._last_image = None          # 上一次触发OCR的图像
        self._consecutive_fail_count = 0  # 连续失败计数

        # 配置快照
        self._config_snapshot = None
```

#### 核心方法
```python
def set_dependencies(self, ocr_engine, image_processor=None):
    """设置依赖对象"""

def set_config_snapshot(self, config: dict):
    """设置配置快照"""

def process_image(self, image: Image.Image):
    """
    处理图像（图片差分去重 + OCR识别）

    Args:
        image: 裁剪后的图像
    """

def reset(self):
    """重置去重状态（清除last_image）"""
```

### 4.2 process_image工作流程
1. 检查依赖和配置，不满足则返回
2. 加锁获取`last_image`快照
3. 若`last_image`不为None：
   - 调用`ImageProcessor.calculate_diff_percent(image, last_image)`
   - 若差异 < `image_diff_threshold`，返回（跳过OCR）
4. 调用`OCREngine.recognize(image)`识别图像
5. 若识别成功：
   - 加锁更新`last_image = image`
   - 清除失败计数
   - 通过信号`ocr_result.emit(text, timestamp)`发送结果
6. 若识别失败：
   - 失败计数加1
   - 记录错误日志
   - 连续失败超过阈值，发送错误信号

### 4.3 线程安全
- 使用`QMutex`保护`_last_image`的读写
- 使用`QMutexLocker`确保锁的自动释放
- 在进程图像时获取快照，避免长时间持锁

### 4.4 边界处理
- **配置更新**：通过`set_config_snapshot()`实时生效
- **重置状态**：`reset()`方法清除历史图像（用于重新开始翻译）

## 5. OCR引擎设计

### 5.1 类设计：OCREngine

#### 初始化
```python
class OCREngine:
    def __init__(self, lang='japanese'):
        """
        初始化 PaddleOCR

        Args:
            lang: 语言代码，默认'japanese'
        """
        try:
            self._ocr = PaddleOCR(
                use_angle_cls=True,  # 启用方向分类（支持竖排文字）
                lang=lang,
                show_log=False
            )
            self._initialized = True
            logger.info(f"PaddleOCR初始化成功，语言: {lang}")
        except Exception as e:
            self._ocr = None
            self._initialized = False
            logger.error(f"PaddleOCR初始化失败: {str(e)}")
```

#### 核心方法
```python
def recognize(self, image: Image.Image) -> OCRResult:
    """
    识别图像中的文本

    Args:
        image: PIL Image 对象

    Returns:
        OCRResult: 识别结果
    """
```

### 5.2 OCRResult 数据结构
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class OCRResult:
    success: bool              # 识别是否成功
    text: str                  # 识别的文本（多个文本块拼接）
    confidence: float          # 平均置信度 (0-1)
    raw_data: Optional[list] = None  # 原始返回数据，用于调试
```

### 5.3 识别流程细节
1. 检查初始化状态，未初始化则返回失败结果
2. 调用`self._ocr.ocr(image, cls=True)`，直接传入PIL Image对象
3. PaddleOCR返回值格式：`[[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ('文本', confidence), ...]`
4. 解析结果：
   - 若返回None或空，返回`OCRResult(success=False, text='', confidence=0)`
   - 遍历每个文本块：
     - 提取文本（item[1][0]）
     - 提取置信度（item[1][1]）
     - 按出现顺序拼接文本
     - 计算平均置信度
5. 返回成功结果

### 5.4 异常处理
- PaddleOCR调用异常：捕获并记录日志，返回失败结果
- 初始化失败：构造函数捕获异常，设置`_initialized=False`
- 后续调用检查初始化状态，避免使用None对象

## 6. 与翻译模块的接口

### 6.1 文本传递
- OCR服务成功识别文本后，通过信号发送
- 翻译线程（或在同一线程）接收信号，调用翻译API
- 翻译完成后通过信号发送结果给主线程更新悬浮窗

### 6.2 文本去重
- 文本级去重由翻译模块负责
- 维护`last_translated_text`，使用Levenshtein编辑距离比较
- 相似度低于阈值才调用翻译API

## 7. 配置参数与动态更新

### 7.1 所需配置
```json
{
  "language": {
    "source": "ja"  // 源语言：ja(日语)或en(英语)
  },
  "ocr": {
    "image_diff_threshold": 0.05  // 图片差异阈值，0-1，默认5%
  }
}
```

### 7.2 配置说明
- `language.source`：OCR识别的语言
- `ocr.image_diff_threshold`：
  - 差异百分比超过此阈值才触发OCR
  - 建议范围：0.02-0.10（2%-10%）
  - 值越小越敏感，可能增加OCR调用次数
  - 值越大越宽松，可能漏掉细微变化

### 7.3 读取方式
- 通过`set_config_snapshot(config)`设置配置快照
- 在`process_image`中使用快照中的参数
- 配置热更新：主线程重新调用`set_config_snapshot`

## 8. 性能优化

### 8.1 图片差分性能
- 统一缩放到160x120（可调整）
- 灰度处理减少计算量
- numpy数组运算高效

### 8.2 OCR 模型加载
- 在`OCREngine`构造函数中一次性初始化
- 后续调用复用同一实例
- 初始化失败不影响程序运行，只是OCR功能不可用

### 8.3 线程同步开销
- 使用`QMutex`保护状态，临界区短（仅获取last_image）
- 避免长时间持锁，在锁外进行耗时操作

## 9. 异常与边界处理

### 9.1 PaddleOCR初始化失败
- 构造函数捕获异常，记录日志
- 设置`_initialized=False`
- 后续调用返回失败结果，不抛异常

### 9.2 OCR识别连续失败
- 维护连续失败计数
- 超过阈值（如5次）通过错误信号通知主线程
- 不停止线程，允许后续重试

### 9.3 窗口关闭或最小化
- 由截图线程处理，返回None
- OCR服务接收None直接返回

### 9.4 内存管理
- PIL Image对象使用完毕后引用消失，Python自动回收
- `last_image`引用会被新图像替换，旧图像自动释放

## 10. 流程图

```
截图线程循环:
  开始
  捕获窗口 → 裁剪区域
  OCRService.process_image(cropped_image)
    获取 last_image 快照
    若 last_image 存在:
      diff = ImageProcessor.calculate_diff_percent(image, last_image)
      若 diff < threshold:
   return (跳过)
    result = OCREngine.recognize(image)
    若 result.success:
      更新 last_image = image
      emit ocr_result(result.text, timestamp)
  休眠 interval

ImageProcessor.calculate_diff_percent(img1, img2):
  若任一为None: return 1.0
  统一缩放到 160x120
  转换为灰度图
  转换为numpy数组
  diff = abs(img1 - img2).sum() / total_pixels / 255
  return diff

OCREngine.recognize(image):
  若未初始化: return 失败结果
  result = self._ocr.ocr(image, cls=True)
  若 result 为空: return 失败结果
  解析文本块，拼接文本，计算平均置信度
  return 成功结果
```

## 11. 与已有模块的集成

### 11.1 依赖关系
- **被截图线程依赖**：`CaptureThread`调用`OCRService.process_image()`
- **依赖OCREngine**：`OCRService`调用`OCREngine.recognize()`
- **依赖ImageProcessor**：`OCRService`调用`ImageProcessor.calculate_diff_percent()`
- **信号输出**：通过`pyqtSignal`发送OCR结果给翻译模块

### 11.2 接口保持
- `OCRService.set_dependencies(ocr_engine, image_processor)`：依赖注入
- `OCRService.set_config_snapshot(config)`：配置更新
- `OCRService.process_image(image)`：处理图像（与placeholder接口一致）
- `OCRService.reset()`：重置状态
- `OCRService.ocr_result`：信号（与placeholder一致）
- `OCRService.error_signal`：错误信号（与placeholder一致）

### 11.3 兼容性
- 与`OCRServicePlaceholder`接口完全兼容
- 与`CaptureThread`的调用方式保持一致
- 无需修改调用方代码

## 12. 目录结构

```
src/
├── service/
│   ├── ocr_engine.py              # PaddleOCR封装（替换placeholder）
│   ├── ocr_service.py             # OCR服务（重写）
│   ├── ocr_result.py              # OCRResult数据类（新增）
│   └── image_processor.py         # 扩展：增加calculate_diff_percent方法
```
