"""
翻译线程 - 文本去重和翻译
"""

import logging
import time
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from src.service.text_deduplicator import TextDeduplicator
from src.service.translator import Translator

logger = logging.getLogger(__name__)


class TranslationThread(QObject):
    """翻译线程 - 文本去重和翻译"""

    # 信号定义
    translation_result = pyqtSignal(str, str, float)  # 原文, 译文, 时间戳
    error_signal = pyqtSignal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)

        # 配置快照
        self._config_snapshot = None

        # 翻译状态
        self._is_translating = False  # 是否正在翻译

        # 依赖注入
        self._translator: Optional[Translator] = None
        self._text_deduplicator: Optional[TextDeduplicator] = None

    def set_dependencies(self, translator: Translator, text_deduplicator: TextDeduplicator):
        """
        设置依赖的服务对象

        Args:
            translator: 翻译服务
            text_deduplicator: 文本去重器
        """
        self._translator = translator
        self._text_deduplicator = text_deduplicator
        logger.info("翻译线程依赖已设置")

    def set_config_snapshot(self, config: dict):
        """
        设置配置快照

        Args:
            config: 配置字典
        """
        self._config_snapshot = config
        logger.debug("翻译线程配置快照已更新")

    def on_ocr_result(self, text: str, timestamp: float):
        """
        槽函数 - 接收OCR识别结果

        Args:
            text: OCR识别的文本
            timestamp: 时间戳
        """
        if not text or not text.strip():
            logger.debug("OCR文本为空，跳过翻译")
            return

        # 如果正在翻译，丢弃新的识别结果
        if self._is_translating:
            logger.debug("翻译任务进行中，丢弃新的识别结果")
            return

        # 读取配置
        config = self._config_snapshot
        if not config:
            logger.warning("配置快照为空，跳过翻译")
            return

        # 文本级去重
        if self._text_deduplicator:
            should_translate = self._text_deduplicator.should_translate(text)
            if not should_translate:
                return
        else:
            logger.warning("文本去重器未设置，跳过去重判断")

        # 标记正在翻译
        self._is_translating = True

        # 调用翻译API
        try:
            language_config = config.get("language", {})
            source_lang = language_config.get("source", "ja")
            target_lang = language_config.get("target", "zh")

            # 读取超时配置
            ocr_config = config.get("ocr", {})
            timeout = ocr_config.get("translation_timeout", 3.0)

            result = self._translator.translate(text, source_lang, target_lang, timeout)

            if result.success:
                logger.debug(f"翻译成功: '{text[:20]}...' -> '{result.translated_text[:20]}...'")
                self.translation_result.emit(text, result.translated_text, timestamp)
            else:
                logger.error(f"翻译失败: {result.error}")
                self.error_signal.emit(result.error)

        except Exception as e:
            error_msg = f"翻译异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_signal.emit(error_msg)
        finally:
            # 翻译完成，标记状态
            self._is_translating = False
