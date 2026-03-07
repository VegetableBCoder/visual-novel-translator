"""
OCR 服务 - 图片差分去重和OCR识别
"""

import logging
import time
import uuid
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
from PIL import Image

logger = logging.getLogger(__name__)


class OCRService(QObject):
    """OCR服务 - 图片差分去重和OCR识别"""

    # 信号定义
    ocr_result = pyqtSignal(str, float)  # 识别结果文本, 时间戳
    error_signal = pyqtSignal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()

        # OCR引擎（依赖注入）
        self._ocr_engine = None

        # 图像处理器（依赖注入）
        self._image_processor = None

        # 配置快照
        self._config_snapshot = None

        # 状态维护
        self._last_image = None  # 上一次触发OCR的图像
        self._consecutive_fail_count = 0  # 连续失败计数
        self._max_consecutive_fails = 5  # 最大连续失败次数

    def set_dependencies(self, ocr_engine, image_processor=None):
        """
        设置依赖对象

        Args:
            ocr_engine: OCR引擎实例
            image_processor: ImageProcessor实例（可选，用于图像差分计算）
        """
        self._ocr_engine = ocr_engine
        self._image_processor = image_processor
        logger.info("OCR服务依赖已设置")

    def set_config_snapshot(self, config: dict):
        """设置配置快照"""
        with QMutexLocker(self._mutex):
            self._config_snapshot = config
            logger.debug("OCR服务配置快照已更新")

    def process_image(self, image: Image.Image):
        """
        处理图像（图片差分去重 + OCR识别）

        Args:
            image: 裁剪后的图像
        """
        if not self._config_snapshot or not self._ocr_engine:
            return

        try:
            # 获取配置参数
            ocr_config = self._config_snapshot.get("ocr", {})
            image_diff_threshold = ocr_config.get("image_diff_threshold", 0.05)

            # 加锁获取last_image快照
            with QMutexLocker(self._mutex):
                last_image = self._last_image

            # 图片差分去重判断
            if last_image is not None and self._image_processor is not None:
                try:
                    diff_percent = self._image_processor.calculate_diff_percent(
                        image, last_image
                    )
                    logger.debug(f"图片差异百分比: {diff_percent:.4f}, 阈值: {image_diff_threshold:.4f}")

                    # 差异小于阈值，跳过OCR
                    if diff_percent < image_diff_threshold:
                        logger.debug("图片变化不大，跳过OCR")
                        return
                except Exception as e:
                    logger.warning(f"图片差分计算失败: {str(e)}，继续执行OCR")

            # 调用OCR引擎识别
            result = self._ocr_engine.recognize(image)

            if result.success and result.text.strip():
                # OCR成功
                logger.info(f"OCR识别成功: 文本='{result.text[:50]}...', 置信度={result.confidence:.2f}")

                # 加锁更新last_image
                with QMutexLocker(self._mutex):
                    self._last_image = image
                    self._consecutive_fail_count = 0

                # 发送OCR结果
                timestamp = time.time()
                self.ocr_result.emit(result.text, timestamp)
            else:
                # image.save(fp=f'I:\\screenshot\\{uuid.uuid4().hex}.jpg', format="JPEG")
                # OCR失败或无结果
                logger.debug("OCR识别失败或无结果")
                self._handle_ocr_failure()

        except Exception as e:
            # image.save(fp=f'I:\\screenshot\\{uuid.uuid4().hex}.jpg', format="JPEG")
            error_msg = f"OCR处理异常: {str(e)}"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)
            self._handle_ocr_failure()

    def _handle_ocr_failure(self):
        """处理OCR失败"""
        with QMutexLocker(self._mutex):
            self._consecutive_fail_count += 1
            fail_count = self._consecutive_fail_count

        logger.warning(f"OCR失败计数: {fail_count}/{self._max_consecutive_fails}")

        # 连续失败超过阈值，发送错误信号
        if fail_count >= self._max_consecutive_fails:
            error_msg = f"OCR连续失败{fail_count}次，请检查配置"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)

    def reset(self):
        """重置去重状态（清除last_image）"""
        with QMutexLocker(self._mutex):
            self._last_image = None
            self._consecutive_fail_count = 0
            logger.debug("OCR服务去重状态已重置")

