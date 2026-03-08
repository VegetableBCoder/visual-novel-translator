"""
翻译服务 - 统一接口
"""

import logging
from typing import Optional

from src.controller.config_helper import ConfigHelper
from src.service.alibaba_translator import AlibabaTranslator
from src.service.google_translator import GoogleTranslator
from src.service.translation_result import TranslationResult

logger = logging.getLogger(__name__)


class Translator:
    """翻译服务 - 统一接口"""

    def __init__(self, config_helper: ConfigHelper):
        """
        初始化翻译服务

        Args:
            config_helper: 配置管理器
        """
        self.config = config_helper
        self._engine_type: Optional[str] = None
        self._alibaba_translator: Optional[AlibabaTranslator] = None
        self._google_translator: Optional[GoogleTranslator] = None

        self._init_engine()

    def _init_engine(self):
        """从配置读取并初始化翻译引擎"""
        try:
            engine_type = self.config.get("translation", {}).get("engine")
            self._engine_type = engine_type

            if engine_type == "alibaba":
                # 初始化阿里云翻译器
                alibaba_config = self.config.get("translation", {}).get("alibaba", {})
                access_key_id = alibaba_config.get("access_key_id", "")
                access_key_secret = alibaba_config.get("access_key_secret", "")

                if access_key_id and access_key_secret:
                    self._alibaba_translator = AlibabaTranslator(access_key_id, access_key_secret)
                    logger.info("阿里云翻译引擎初始化成功")
                else:
                    logger.warning("阿里云翻译引擎初始化失败：缺少 AccessKey ID 或 Secret")
                    self._engine_type = None

            elif engine_type == "google":
                # 初始化 Google 翻译器
                google_config = self.config.get("translation", {}).get("google", {})
                api_key = google_config.get("api_key", "")

                self._google_translator = GoogleTranslator(api_key)
                logger.info("Google 翻译引擎初始化成功")

            else:
                logger.warning(f"未知的翻译引擎类型: {engine_type}")

        except Exception as e:
            logger.error(f"翻译引擎初始化异常: {str(e)}")
            self._engine_type = None

    def translate(
        self,
        text: str,
        source_lang: str = "ja",
        target_lang: str = "zh",
        timeout: float = 3.0
    ) -> TranslationResult:
        """
        翻译文本

        Args:
            text: 待翻译文本
            source_lang: 源语言（ja=日语, en=英语）
            target_lang: 目标语言（zh=中文）
            timeout: 超时时间（秒）

        Returns:
            TranslationResult: 翻译结果
        """
        if not self._engine_type:
            return TranslationResult(success=False, translated_text="", error="翻译引擎未配置")

        try:
            if self._engine_type == "alibaba":
                if self._alibaba_translator:
                    return self._alibaba_translator.translate(text, source_lang, target_lang, timeout)
                else:
                    return TranslationResult(success=False, translated_text="", error="阿里云翻译引擎未初始化")

            elif self._engine_type == "google":
                if self._google_translator:
                    return self._google_translator.translate(text, source_lang, target_lang, timeout)
                else:
                    return TranslationResult(success=False, translated_text="", error="Google 翻ser引擎未初始化")

            else:
                return TranslationResult(success=False, translated_text="", error=f"未知翻译引擎: {self._engine_type}")

        except Exception as e:
            logger.error(f"翻译异常: {str(e)}")
            return TranslationResult(success=False, translated_text="", error=str(e))

    def reinitialize(self):
        """重新初始化翻译引擎（用于配置更新后）"""
        logger.info("重新初始化翻译引擎")
        self._alibaba_translator = None
        self._google_translator = None
        self._init_engine()


# 独立运行测试
if __name__ == "__main__":
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 模拟配置
    mock_config = {
        "translation": {
            "engine": "google",  # 可改为 "alibaba" 测试阿里云
            "alibaba": {
                "access_key_id": "",
                "access_key_secret": ""
            },
            "google": {
                "api_key": ""
            }
        }
    }

    # 创建配置管理器
    from src.controller.config_helper import ConfigHelper
    config_helper = ConfigHelper()
    config_helper._config = mock_config

    # 测试翻译
    translator = Translator(config_helper)

    print("\n=== 测试1：日语翻译 ===")
    result = translator.translate("こんにちは世界", source_lang="ja", target_lang="zh")
    if result.success:
        print(f"翻译成功: {result.translated_text}")
    else:
        print(f"翻译失败: {result.error}")

    print("\n=== 测试2：英语翻译 ===")
    result = translator.translate("Hello World", source_lang="en",)
    if result.success:
        print(f"翻译成功: {result.translated_text}")
    else:
        print(f"翻译失败: {result.error}")
