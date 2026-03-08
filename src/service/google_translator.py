"""
Google 翻译 - HTTP API 调用

注意：使用非官方 API，可能存在稳定性问题
"""

import logging
from typing import Optional

import requests

from src.service.translation_result import TranslationResult

logger = logging.getLogger(__name__)

# Google 翻译 API 配置
GOOGLE_API_ENDPOINT = "https://translate.googleapis.com/translate_a/single"


class GoogleTranslator:
    """Google 翻译器（非官方 API）"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Google 翻译器

        Args:
            api_key: API Key（非官方 API 暂不需要，预留字段）
        """
        self.api_key = api_key
        logger.info("Google 翻译器初始化完成")

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
            target_lang: 目标语言（zh=中文，实际应使用 zh-CN）
            timeout: 超时时间（秒）

        Returns:
            TranslationResult: 翻译结果
        """
        if not text:
            return TranslationResult(success=False, translated_text="", error="待翻译文本为空")

        # Google API 使用 zh-CN 表示简体中文
        if target_lang == "zh":
            target_lang = "zh-CN"

        try:
            # 构建请求参数
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",  # 只返回翻译文本
                "q": text
            }

            # 发送请求
            response = requests.get(
                GOOGLE_API_ENDPOINT,
                params=params,
                timeout=timeout
            )

            # 解析响应
            result = self._parse_response(response)

            logger.debug(f"Google 翻译成功: '{text[:30]}...' -> '{result.translated_text[:30]}...'")
            return result

        except requests.exceptions.Timeout:
            error_msg = f"Google 翻译超时（{timeout}秒）"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Google 翻译网络错误: {str(e)}"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)

        except Exception as e:
            error_msg = f"Google 翻译异常: {str(e)}"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)

    def _parse_response(self, response: requests.Response) -> TranslationResult:
        """
        解析 Google API 响应

        Google API 返回格式示例：
        [
            [
                ["翻译文本", "原始文本", ...],
                ...
            ],
            源语言,
            ...
        ]

        Args:
            response: requests 响应对象

        Returns:
            TranslationResult: 翻译结果
        """
        try:
            response.raise_for_status()
            data = response.json()

            # Google API 返回的格式：[[[translation, original, ...], ...], source, ...]
            # 第一个元素是翻译结果列表
            if isinstance(data, list) and len(data) > 0:
                translations = data[0]

                if isinstance(translations, list):
                    # 提取所有翻译文本并拼接
                    translated_texts = []
                    for item in translations:
                        if isinstance(item, list) and len(item) > 0:
                            translated_texts.append(item[0])

                    translated_text = "".join(translated_texts)

                    return TranslationResult(
                        success=True,
                        translated_text=translated_text,
                        raw_data=data
                    )

            # 未知的响应格式
            logger.error(f"Google 翻译响应格式异常: {data}")
            return TranslationResult(success=False, translated_text="", error="响应格式异常")

        except ValueError as e:
            error_msg = f"解析响应失败（非JSON格式）: {str(e)}"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)


# 独立运行测试
if __name__ == "__main__":
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试翻译
    translator = GoogleTranslator()

    print("\n=== 测试1：日语翻译 ===")
    result = translator.translate("こんにちは世界", source_lang="ja", target_lang="zh")
    if result.success:
        print(f"翻译成功: {result.translated_text}")
    else:
        print(f"翻译失败: {result.error}")

    print("\n=== 测试2：英语翻译 ===")
    result = translator.translate("Hello World", source_lang="en", target_lang="zh")
    if result.success:
        print(f"翻译成功: {result.translated_text}")
    else:
        print(f"翻译失败: {result.error}")

    print("\n=== 测试3：长文本翻译 ===")
    result = translator.translate(
        "これはテストです。Google翻訳APIを使用してテキストを翻訳しています。",
        source_lang="ja",
        target_lang="zh"
    )
    if result.success:
        print(f"翻译成功: {result.translated_text}")
    else:
        print(f"翻译失败: {result.error}")
