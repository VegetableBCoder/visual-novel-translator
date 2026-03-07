"""
截图线程

负责定时截图和区域裁剪，通过信号发送裁剪后的图像。
智能控制截图间隔，尽量保证间隔等于用户设置值，即使OCR耗时占用部分时间。
"""

import logging
import time
import uuid
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition, QMutexLocker

logger = logging.getLogger(__name__)


class CaptureThread(QThread):
    """截图线程 - 定时截图和区域裁剪"""

    # 信号定义
    image_captured = pyqtSignal(object, float)  # 裁剪后的图像, 时间戳
    error_signal = pyqtSignal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()

        # 配置快照（在启动时读取）
        self._config_snapshot = None

        # 状态标志
        self._running = False
        self._paused = False

        # 依赖注入
        self._window_capture = None
        self._image_processor = None

    def set_dependencies(self, window_capture, image_processor, ocr_service=None):
        """
        设置依赖的服务对象

        Args:
            window_capture: WindowCapture 实例
            image_processor: ImageProcessor 实例
            ocr_service: OCRService 实例（可选）
        """
        self._window_capture = window_capture
        self._image_processor = image_processor
        self._ocr_service = ocr_service
        logger.info("截图线程依赖已设置")

    def set_config_snapshot(self, config: dict):
        """
        设置配置快照（启动翻译时调用）

        Args:
            config: 配置快照
        """
        with QMutexLocker(self._mutex):
            self._config_snapshot = config
            logger.debug("配置快照已更新")

    def start_capture(self):
        """开始截图"""
        self._paused = False
        if not self.isRunning():
            self._running = True
            logger.info("启动截图线程")
            self.start()
        else:
            # 如果线程已经在运行，只是恢复
            self._paused = False
            logger.info("恢复截图线程")

    def pause(self):
        """暂停截图"""
        with QMutexLocker(self._mutex):
            self._paused = True
            logger.info("暂停截图线程")

    def resume(self):
        """恢复截图"""
        with QMutexLocker(self._mutex):
            self._paused = False
            self._wait_condition.wakeAll()
            logger.info("恢复截图线程")

    def stop(self):
        """停止线程"""
        with QMutexLocker(self._mutex):
            self._running = False
            self._paused = False
            self._wait_condition.wakeAll()
            logger.info("停止截图线程")

    def run(self):
        """线程主循环"""
        logger.info("截图线程开始运行")

        last_capture_time = 0  # 上一次截图开始时间

        while True:
            # 检查停止标志
            with QMutexLocker(self._mutex):
                if not self._running:
                    break

                # 检查暂停标志
                if self._paused:
                    logger.debug("截图线程暂停中...")
                    self._wait_condition.wait(self._mutex)
                    continue

            # 读取配置快照
            config = self._config_snapshot
            if not config:
                self.msleep(100)
                continue

            # 获取配置参数
            window_config = config.get("window", {})
            hwnd = window_config.get("hwnd")
            region = window_config.get("region", {})
            ocr_config = config.get("ocr", {})
            interval_ms = ocr_config.get("interval_ms", 1000)

            # 计算休眠时间：从上一次截图开始计算
            current_time = int(time.time()*1000)
            elapsed = current_time - last_capture_time
            sleep_time = max(0, interval_ms - elapsed)

            if sleep_time > 0:
                self.msleep(sleep_time)

            # 记录本次截图开始时间
            last_capture_time = current_time

            # 截图
            try:
                full_image = self._window_capture.capture_window(hwnd)
                if full_image is None:
                    logger.warning("截图失败，跳过本次循环")
                    continue
                else:
                    logger.info("截图成功, 开始对截图进行剪裁")

                # 裁剪区域
                window_size = (full_image.width, full_image.height)
                cropped_image = self._image_processor.crop_region(
                    full_image, region, window_size
                )
                if cropped_image is None:
                    logger.warning("裁剪失败，跳过本次循环")
                    continue
                else:
                    logger.info("图片剪裁成功, 准备开始进行OCR")
                    # cropped_image.save(f'I:\\screenshot\\{uuid.uuid4().hex}.jpg', format="JPEG")
                # 发送裁剪后的图像到 OCR 服务
                if self._ocr_service:
                    self._ocr_service.process_image(cropped_image)
                else:
                    # 如果没有 OCR 服务，直接发送信号
                    self.image_captured.emit(cropped_image, last_capture_time)
                logger.debug(f"截图成功: {cropped_image.width}x{cropped_image.height}")

            except Exception as e:
                error_msg = f"截图线程异常: {str(e)}"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)

        logger.info("截图线程结束")


# 独立运行测试
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    from src.core.window_capture import WindowCapture
    from src.service.image_processor import ImageProcessor

    app = QApplication(sys.argv)

    # 创建依赖对象
    window_capture = WindowCapture()
    image_processor = ImageProcessor()

    # 创建截图线程
    capture_thread = CaptureThread()
    capture_thread.set_dependencies(window_capture, image_processor)

    # 设置测试配置
    test_config = {
        "window": {
            "hwnd": 0,  # 需要有效的窗口句柄
            "region": {
                "left": 0.25,
                "top": 0.70,
                "right": 0.75,
                "bottom": 0.85
            }
        },
        "ocr": {
            "interval_ms": 1000
        }
    }
    capture_thread.set_config_snapshot(test_config)

    # 连接信号
    def on_image_captured(image, timestamp):
        logger.info(f"接收到截图信号: {image.width}x{image.height}, 时间戳: {timestamp}")

    def on_error(error_msg):
        logger.error(f"接收到错误信号: {error_msg}")

    capture_thread.image_captured.connect(on_image_captured)
    capture_thread.error_signal.connect(on_error)

    # 启动线程
    capture_thread.start_capture()

    # 运行10秒后停止
    import time
    time.sleep(10)
    capture_thread.stop()
    capture_thread.wait()

    sys.exit(app.exec_())
