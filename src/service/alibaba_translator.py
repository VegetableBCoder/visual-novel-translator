"""
阿里云翻译 - HTTP API 调用
"""

import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Optional

import requests

from src.service.translation_result import TranslationResult

logger = logging.getLogger(__name__)

# 阿里云翻译 API 配置
ALIBABA_API_ENDPOINT = "https://mt.cn-hangzhou.aliyuncs.com"
API_VERSION = "2018-10-12"


class AlibabaTranslator:
    """阿里云翻译器"""

    def __init__(self, access_key_id: str, access_key_secret: str):
        """
        初始化阿里云翻译器

        Args:
            access_key_id: 阿里云 AccessKey ID
            access_key_secret: 阿里云 AccessKey Secret
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        logger.info("阿里云翻译器初始化完成")

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
        if not text:
            return TranslationResult(success=False, translated_text="", error="待翻译文本为空")

        try:
            # 构建请求参数
            params = {
                "Action": "TranslateGeneral",
                "Format": "JSON",
                "Version": API_VERSION,
                "AccessKeyId": self.access_key_id,
                "SignatureMethod": "HMAC-SHA1",
                "SignatureVersion": "1.0",
                "SignatureNonce": str(int(time.time() * 1000)),  # 使用时间戳作为随机数
                "Timestamp": self._get_utc_timestamp(),
                "SourceLanguage": source_lang,
                "TargetLanguage": target_lang,
                "SourceText": text
            }

            # 计算签名
            signature = self._calculate_signature(params)
            params["Signature"] = signature

            # 发送请求
            response = requests.post(
                ALIBABA_API_ENDPOINT,
                data=params,
                timeout=timeout,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # 解析响应
            result = self._parse_response(response)

            logger.debug(f"阿里云翻译成功: '{text[:30]}...' -> '{result.translated_text[:30]}...'")
            return result

        except requests.exceptions.Timeout:
            error_msg = f"阿里云翻译超时（{timeout}秒）"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"阿里云翻译网络错误: {str(e)}"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)

        except Exception as e:
            error_msg = f"阿里云翻译异常: {str(e)}"
            logger.error(error_msg)
            return TranslationResult(success=False, translated_text="", error=error_msg)

    def _get_utc_timestamp(self) -> str:
        """
        获取 UTC 时间戳（ISO8601 格式）

        Returns:
            时间戳字符串
        """
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _calculate_signature(self, params: dict) -> str:
        """
        计算阿里云 API 签名

        Args:
            params: 请求参数字典

            Returns:
                Base64 编码的签名
        """
        # 1. 按参数名排序
        sorted_params = sorted(params.items())

        # 2. URL 编码
        encoded_params = []
        for key, value in sorted_params:
            encoded_key = urllib.parse.quote(key, safe='')
            encoded_value = urllib.parse.quote(str(value), safe='')
            encoded_params.append(f"{encoded_key}={encoded_value}")

        # 3. 拼接查询字符串
        query_string = "&".join(encoded_params)

        # 4. 构造待签名字符串
        string_to_sign = f"POST&{urllib.parse.quote(ALIBABA_API_ENDPOINT, safe='')}&{urllib.parse.quote(query_string, safe='')}"

        # 5. 计算签名
        key = (self.access_key_secret + "&").encode('utf-8')
        msg = string_to_sign.encode('utf-8')
        signature = hmac.new(key, msg, hashlib.sha1).digest()

        # 6. Base64 编码
        signature_base64 = signature.decode('utf-8')

        logger.debug(f"待签名字符串: {string_to_sign}")
        return signature_base64

    def _parse_response(self, response: requests.Response) -> TranslationResult:
        """
        解析阿里云 API 响应

        Args:
            response: requests 响应对象

        Returns:
            TranslationResult: 翻译结果
        """
        try:
            response.raise_for_status()
            data = response.json()

            # 检查响应结构
            if "TranslatedText" in data:
                translated_text = data["TranslatedText"]
                return TranslationResult(
                    success=True,
                    translated_text=translated_text,
                    raw_data=data
                )

            # 检查是否有错误
            if "Code" in data:
                error_msg = f"阿里云翻译错误: {data.get('Message', '未知错误')} (Code: {data['Code']})"
                logger.error(error_msg)
                return TranslationResult(success=False, translated_text="", error=error_msg)

            # 未知的响应格式
            logger.error(f"阿里云翻译响应格式异常: {data}")
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

    # 从环境变量或硬编码获取密钥（仅用于测试）
    # 实际使用时应从配置文件读取
    ACCESS_KEY_ID = ""  # 请填入你的 AccessKey ID
    ACCESS_KEY_SECRET = ""  # 请填入你的 AccessKey Secret

    if not ACCESS_KEY_ID or not ACCESS_KEY_SECRET:
        print("请设置 ACCESS_KEY_ID 和 ACCESS_KEY_SECRET")
        sys.exit(1)

    # 测试翻译
    translator = AlibabaTranslator(ACCESS_KEY_ID, ACCESS_KEY_SECRET)

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
