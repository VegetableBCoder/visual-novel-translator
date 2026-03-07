"""
OCR 服务（占位符）

临时占位符，用于测试调度器功能。
真实的 OCR 服务集成将在后续实现。
"""

import logging
import time
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PIL import Image

logger = logging.getLogger(__name__)


class OCRService(QObject):
    """OCR服务 - 图像差分去重和OCR识别（占位符）"""

    # 信号定义
    ocr_result = pyqtSignal(str, float)  # 识别结果文本, 时间戳
    error_signal = pyqtSignal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)

        # OCR引擎（依赖注入）
        self._ocr_engine = None

        # 配置快照
        self._config_snapshot = None

    def set_dependencies(self, ocr_engine, image_processor=None):
        """
        设置依赖对象

        Args:
            ocr_engine: OCR引擎实例
            image_processor: ImageProcessor实例（可选，用于图像预处理）
        """
        self._ocr_engine = ocr_engine
        self._image_processor = image_processor
        logger.info("OCR服务依赖已设置")

    def set_config_snapshot(self, config: dict):
        """设置配置快照"""
        self._config_snapshot = config
        logger.debug("OCR服务配置快照已更新")

    def process_image(self, image: Image.Image):
        """
        处理图像（占位符：直接调用OCR引擎，不做差分去重）

        Args:
            image: 裁剪后的图像
        """
        if not self._config_snapshot or not self._ocr_engine:
            return

        try:
            # 占位符：直接调用 OCR 引擎识别
            # TODO: 后续实现图像差分去重逻辑
            result = self._ocr_engine.recognize(image)

            if result and "text" in result:
                text = result["text"]
                if text.strip():
                    self.ocr_result.emit(text, time.time())

        except Exception as e:
            error_msg = f"OCR处理异常: {str(e)}"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)

    def reset(self):
        """重置去重状态（占位符）"""
        logger.debug("OCR服务去重状态已重置")
