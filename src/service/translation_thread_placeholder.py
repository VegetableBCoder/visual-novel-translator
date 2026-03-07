"""
翻译线程（占位符）

临时占位符，用于测试调度器功能。
真实的翻译线程集成将在后续实现。
"""

import logging
import time
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TranslationThread(QObject):
    """翻译线程 - 文本去重和翻译（占位符）"""

    # 信号定义
    translation_result = pyqtSignal(str, str, float)  # 原文, 译文, 时间戳
    error_signal = pyqtSignal(str)  # 错误信息

    def __init__(self, parent=None):
        super().__init__(parent)

        # 配置快照
        self._config_snapshot = None

        # 去重状态
        self._last_translated_text = ""

        # 翻译状态
        self._is_translating = False  # 是否正在翻译

        # 依赖注入
        self._translator = None
        self._text_deduplicator = None

    def set_dependencies(self, translator, text_deduplicator):
        """设置依赖的服务对象"""
        self._translator = translator
        self._text_deduplicator = text_deduplicator
        logger.info("翻译线程依赖已设置")

    def set_config_snapshot(self, config: dict):
        """设置配置快照"""
        self._config_snapshot = config
        logger.debug("翻译线程配置快照已更新")

    def on_ocr_result(self, text: str, timestamp: float):
        """槽函数 - 接收OCR识别结果"""
        if not text.strip():
            return

        # 如果正在翻译，丢弃新的识别结果
        if self._is_translating:
            logger.debug("翻译任务进行中，丢弃新的识别结果")
            return

        # 读取配置
        config = self._config_snapshot
        if not config:
            return

        # 文本级去重
        if self._text_deduplicator and self._text_deduplicator.is_similar(text, self._last_translated_text):
            logger.debug("文本相似，跳过翻译")
            return

        # 更新上一次文本
        self._last_translated_text = text

        # 标记正在翻译
        self._is_translating = True

        # 调用翻译API
        try:
            language_config = config.get("language", {})
            source_lang = language_config.get("source", "ja")
            target_lang = language_config.get("target", "zh")

            translated = self._translator.translate(text, source_lang, target_lang)

            if translated:
                self.translation_result.emit(text, translated, timestamp)

        except Exception as e:
            error_msg = f"翻译失败: {str(e)}"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)
        finally:
            # 翻译完成，标记状态
            self._is_translating = False
