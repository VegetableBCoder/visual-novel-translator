"""
任务调度器（占位符）

管理截图+OCR线程和翻译线程，实现完整的翻译流程。
"""

import logging

from PyQt5.QtCore import QObject, pyqtSignal

from src.service.capture_thread import CaptureThread
from src.service.ocr_service_placeholder import OCRService
from src.service.translation_thread_placeholder import TranslationThread

logger = logging.getLogger(__name__)


class Scheduler(QObject):
    """任务调度器 - 管理截图+OCR线程和翻译线程线程"""

    # 信号定义（转发给主线程）
    translation_result = pyqtSignal(str, str, float)  # 原文, 译文, 时间戳
    error_signal = pyqtSignal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建工作线程
        self._capture_thread = CaptureThread()
        self._ocr_service = OCRService()
        self._translation_thread = TranslationThread()

        # 连接信号
        self._connect_signals()

        # 状态
        self._config_snapshot = None

        logger.info("调度器已初始化")

    def _connect_signals(self):
        """连接内部线程信号"""
        # OCR服务 → 翻译线程
        self._ocr_service.ocr_result.connect(
            self._translation_thread.on_ocr_result
        )

        # 错误信号转发
        self._capture_thread.error_signal.connect(self.error_signal)
        self._ocr_service.error_signal.connect(self.error_signal)
        self._translation_thread.error_signal.connect(self.error_signal)

        # 翻译线程 → 主线程
        self._translation_thread.translation_result.connect(
            self.translation_result
        )

        logger.debug("调度器信号已连接")

    def set_dependencies(self, window_capture, image_processor, ocr_engine,
                      translator, text_deduplicator):
        """设置所有依赖的服务对象"""
        self._capture_thread.set_dependencies(
            window_capture, image_processor, self._ocr_service
        )
        self._ocr_service.set_dependencies(ocr_engine, image_processor)
        self._translation_thread.set_dependencies(
            translator, text_deduplicator
        )

        logger.info("调度器依赖已设置")

    def set_config_snapshot(self, config: dict):
        """设置配置快照"""
        self._config_snapshot = config.copy()
        self._capture_thread.set_config_snapshot(self._config_snapshot)
        self._ocr_service.set_config_snapshot(self._config_snapshot)
        self._translation_thread.set_config_snapshot(self._config_snapshot)

        logger.debug("配置快照已传递到所有组件")

    def start(self):
        """启动翻译"""
        logger.info("启动调度器...")
        self._capture_thread.start_capture()

    def pause(self):
        """暂停翻译"""
        logger.info("暂停调度器...")
        self._capture_thread.pause()

    def resume(self):
        """恢复翻译"""
        logger.info("恢复调度器...")
        self._capture_thread.resume()

    def stop(self):
        """停止翻译"""
        logger.info("停止调度器...")
        self._capture_thread.stop()
        self._capture_thread.wait()
        logger.info("调度器已停止")
