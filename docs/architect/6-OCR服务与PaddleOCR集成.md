# OCR识别后台模块 - 详细技术设计文档

## 1. 模块概述
OCR识别后台模块负责在自动翻译运行期间，持续监控目标窗口指定区域的图像变化，并对变化的图像进行文字识别。该模块实际由两个子模块协同工作：
- **图像采集与去重子模块**（运行于截图线程）：定时截图、计算图像哈希、判断内容变化，将有变化的图像放入任务队列。
- **OCR识别子模块**（运行于OCR/翻译线程）：从队列获取图像，调用OCR引擎识别文字，并将识别结果传递给翻译模块。

## 2. 整体架构与分工

### 2.1 职责划分
| 子模块 | 所在线程 | 核心职责 |
|--------|----------|----------|
| 图像采集与去重 | 截图线程 | 定时截图、区域裁剪、pHash计算、与上一次OCR图像比较、入队 |
| OCR识别 | OCR/翻译线程 | 从队列取图、调用PaddleOCR、解析结果、触发翻译 |

### 2.2 数据流
截图线程循环:
    截图 → 裁剪 → pHash → 与 last_ocr_hash 比较
    若变化 → 封装 OCRTask(image, timestamp) → 放入 task_queue
    (更新 last_ocr_hash 为当前哈希)

OCR/翻译线程循环:
    task = task_queue.get()
    text = ocr_engine.recognize(task.image)
    若 text 有效 → 触发翻译

## 3. 图像采集与去重子模块设计

### 3.1 类设计：ImageCollector
- 运行在截图线程内部，作为线程的主要逻辑。
- 维护状态：
  - `last_ocr_hash`：最后一次触发OCR的图像的pHash值（初始为 None）。
  - `consecutive_fail_count`：连续截图失败次数。
  - `stop_flag` / `pause_flag`：线程控制标志。
- 核心方法 `run()` 实现循环。

### 3.2 工作流程
1. 从配置管理器读取最新配置快照：窗口句柄、区域比例、截图间隔、图像阈值。
2. 调用 `CaptureService.capture_region(hwnd, region_ratio)` 获取区域图像。
3. 若截图失败（返回 None）：
   - `consecutive_fail_count` 加1。
   - 若连续失败超过阈值（如5次），通过信号通知主线程显示提示。
   - 休眠后继续下一次循环。
4. 若截图成功，`consecutive_fail_count` 清零。
5. 计算图像 pHash：`current_hash = imagehash.phash(image)`。
6. 判断是否需要触发OCR：
   - 若 `last_ocr_hash` 为 None，则判定为变化。
   - 否则计算汉明距离 `diff = last_ocr_hash - current_hash`。
   - 若 `diff > config.image_threshold`，则判定为变化。
7. 若判定为变化：
   - 将图像和当前时间戳封装为 `OCRTask`，放入任务队列。
   - 更新 `last_ocr_hash = current_hash`。
8. 根据配置的截图间隔休眠。

### 3.3 边界处理
- **窗口无效或最小化**：`capture_region` 返回 None，连续失败计数增加。
- **队列满**：若任务队列有界且已满，丢弃当前任务（记录日志），但不更新 `last_ocr_hash`。
- **配置热更新**：每次循环重新读取配置，保证间隔、阈值等实时生效。

## 4. OCR识别子模块设计

### 4.1 类设计：OCREngine
- 封装 PaddleOCR 实例，提供识别接口。
- 初始化参数：语言（从配置读取），启用方向分类（固定为 True）。
- 方法 `recognize(image: PIL.Image) -> OCRResult`。

### 4.2 OCRResult 数据结构
```
class OCRResult:
def init(self, success, text, confidence, raw_data=None):
    self.success = success # bool
    self.text = text # str
    self.confidence = float # 平均置信度
    self.raw_data = raw_data # 原始返回，用于调试
```


### 4.3 识别流程细节
1. PaddleOCR 初始化应在 OCR/翻译线程启动时完成，避免重复加载模型。
2. 调用 `ocr.ocr(image, cls=True)`，`image` 直接使用 PIL Image 对象。
3. 返回值格式：[[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ('文本', confidence)]
4. 解析：
   - 遍历每个检测到的文本块，提取文本和置信度。
   - 将所有文本按出现顺序拼接。
   - 计算平均置信度。
5. 若识别结果为空，返回 `OCRResult(success=False, text='')`。

### 4.4 异常处理
- PaddleOCR 抛出异常时，捕获并记录日志，返回失败结果。
- 连续失败计数，但不影响线程运行。

## 5. 任务队列设计

### 5.1 队列选择
- 使用 `queue.Queue`，设置最大长度如 `maxsize=10`。

### 5.2 任务对象

```
class OCRTask:
def init(self, image, timestamp):
self.image = image # PIL Image
self.timestamp = timestamp # datetime
```


### 5.3 队列操作
- 截图线程：`task_queue.put(task, block=False)`，队列满时捕获 `queue.Full` 异常，丢弃任务。
- OCR/翻译线程：`task_queue.get(block=True)` 阻塞等待。

## 6. 与翻译模块的接口

### 6.1 文本传递
- OCR/翻译线程成功识别文本后，直接在同一线程中调用翻译模块的 `translate()` 方法。
- 翻译完成后通过信号将结果发送给主线程更新悬浮窗。

### 6.2 文本去重
- 在调用翻译前，应进行文本级去重：维护 `last_translated_text`，与当前识别文本进行 Levenshtein 相似度比较，若相似度低于阈值才调用翻译API。

## 7. 配置参数与动态更新

### 7.1 所需配置
- 窗口句柄（`hwnd`）
- 区域比例（`region_ratio`）
- 截图间隔（`ocr_interval_ms`）
- 图像相似度阈值（`image_threshold`）
- OCR语言（`source_language`）

### 7.2 读取方式
- 截图线程每次循环开始时，通过配置管理器获取所有所需配置的快照。
- 配置管理器应提供线程安全的读取方法（使用 `threading.Lock`）。

## 8. 性能优化

### 8.1 图像哈希计算
- `imagehash.phash` 内部已缩放到 32x32，速度足够。

### 8.2 OCR 模型加载
- PaddleOCR 初始化耗时较长，在 OCR/翻译线程启动时一次性初始化，后续复用。

### 8.3 队列大小监控
- 可记录队列长度，若经常满，提示用户降低截图频率。

## 9. 异常与边界处理

### 9.1 窗口关闭
- 截图线程连续失败超过3次，通过信号通知主线程弹出提示，自动暂停。

### 9.2 OCR 连续失败
- 记录错误日志，不停止线程。

### 9.3 内存管理
- 图像对象用完后引用消失，Python 垃圾回收自动处理。

## 10. 流程图

截图线程:
开始
初始化 last_hash = None
循环:
    读取配置
    img = capture_region(hwnd, region)
    if img is None:
        失败计数++
        若失败过多 → 发信号
        休眠 interval
        continue
    current_hash = phash(img)
    if last_hash is None or (last_hash - current_hash) > threshold:
        task_queue.put( OCRTask(img, now) )
        last_hash = current_hash
    休眠 interval

OCR/翻译线程:
初始化 ocr_engine = PaddleOCR(lang)
循环:
    task = task_queue.get()
    result = ocr_engine.recognize(task.image)
    if not result.success:
        记录日志
        continue
    if text_deduplicator.should_translate(result.text):
        translation = translator.translate(result.text)
        emit translation_result(result.text, translation)

## 11. 与已有模块的集成
- 依赖 `CaptureService` 提供截图功能。
- 依赖 `ConfigManager` 获取配置。
- 依赖 `TranslationService` 和 `TextDeduplicator` 完成后续处理。
- 通过 `pyqtSignal` 将翻译结果传递给主线程更新悬浮窗。
