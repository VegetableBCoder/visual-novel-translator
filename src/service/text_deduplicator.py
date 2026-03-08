"""
文本去重器 - 基于Levenshtein编辑距离
"""

import logging
import re

logger = logging.getLogger(__name__)

# 尝试导入 python-Levenshtein，如果失败则使用 difflib 作为备选
try:
    import Levenshtein
    USE_C_LEVENSHTEIN = True
except ImportError:
    from difflib import SequenceMatcher
    USE_C_LEVENSHTEIN = False
    logger.warning("python-Levenshtein 未安装，使用 difflib.SequenceMatcher 作为备选（性能较低）")


# 标点符号集合（日文+英文+中文）
PUNCTUATION_PATTERN = re.compile(r'^[！？。、，．：；」』」】）}\]\[\]\(\)\*\+\-\=\_\~\`\'\"\,\.\!\?\;\:\<\>\@\#\$\%\^\&\|\\\s]+$')


class TextDeduplicator:
    """文本去重器 - 基于Levenshtein编辑距离"""

    def __init__(self, threshold: int = 75):
        """
        初始化文本去重器

        Args:
            threshold: 相似度阈值（0-100），默认75
                      当文本相似度 >= threshold 时视为相似文本，不翻译
                      当文本相似度 < threshold 时视为新文本，需要翻译
        """
        self.threshold = max(0, min(100, threshold))  # 限制在 0-100 范围内
        self.last_text = ""  # 上一次翻译的文本
        logger.info(f"文本去重器初始化完成，阈值: {self.threshold}%")

    def should_translate(self, new_text: str) -> bool:
        """
        判断是否需要翻译新文本

        Args:
            new_text: 新文本

        Returns:
            True 表示需要翻译，False 表示不需要翻译
        """
        # 1. 空文本过滤
        if not new_text or not new_text.strip():
            logger.debug("文本为空，跳过翻译")
            return False

        # 2. 纯标点符号过滤
        if self._is_punctuation_only(new_text):
            logger.debug(f"文本仅包含标点符号，跳过翻译: '{new_text}'")
            return False

        # 3. 首次翻译
        if not self.last_text:
            self.last_text = new_text
            logger.debug(f"首次翻译，文本: '{new_text}'")
            return True

        # 4. 计算相似度
        similarity = self._calculate_similarity(self.last_text, new_text)
        logger.debug(f"文本相似度: {similarity:.2f}% (阈值: {self.threshold}%)")

        # 5. 判断是否超过阈值（相似度低表示变化大，需要翻译）
        if similarity >= self.threshold:
            logger.debug(f"文本相似（{similarity:.2f}% >= {self.threshold}%），跳过翻译")
            return False
        else:
            self.last_text = new_text
            logger.debug(f"文本不相似（{similarity:.2f}% < {self.threshold}%），需要翻译")
            return True

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度（0-100），100表示完全相同
        """
        if not text1 and not text2:
            return 100.0
        if not text1 or not text2:
            return 0.0

        if USE_C_LEVENSHTEIN:
            # 使用 C 实现的 Levenshtein（性能更好）
            ratio = Levenshtein.ratio(text1, text2)
        else:
            # 使用 Python 内置的 SequenceMatcher
            ratio = SequenceMatcher(None, text1, text2).ratio()

        return ratio * 100.0

    def _is_punctuation_only(self, text: str) -> bool:
        """
        检查文本是否只包含标点符号或空白字符

        Args:
            text: 待检查文本

        Returns:
            True 表示仅包含标点/空白，False 否则
        """
        if not text:
            return True
        return bool(PUNCTUATION_PATTERN.match(text.strip()))

    def reset(self):
        """重置去重器状态"""
        self.last_text = ""
        logger.debug("文本去重器状态已重置")

    def update_threshold(self, threshold: int):
        """
        更新相似度阈值

        Args:
            threshold: 新的阈值（0-100）
        """
        old_threshold = self.threshold
        self.threshold = max(0, min(100, threshold))
        logger.info(f"文本去重阈值更新: {old_threshold}% -> {self.threshold}%")


# 独立运行测试
if __name__ == "__main__":
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试文本去重
    deduplicator = TextDeduplicator(threshold=75)

    print("\n=== 测试1：首次翻译 ===")
    result = deduplicator.should_translate("こんにちは世界")
    print(f"应该翻译: {result}")

    print("\n=== 测试2：相同文本（相似度100%） ===")
    result = deduplicator.should_translate("こんにちは世界")
    print(f"应该翻译: {result}")

    print("\n=== 测试3：略微不同文本（相似度高）约95% ===")
    result = deduplicator.should_translate("こんにちは世界！")
    print(f"应该翻译: {result}")

    print("\n=== 测试4：不同文本（相似度低）约20% ===")
    result = deduplicator.should_translate("さようなら世界")
    print(f"应该翻译: {result}")

    print("\n=== 测试5：空文本 ===")
    result = deduplicator.should_translate("")
    print(f"应该翻译: {result}")

    print("\n=== 测试6：纯标点符号 ===")
    result = deduplicator.should_translate("！？。")
    print(f"应该翻译: {result}")

    print("\n=== 测试7：重置后首次翻译 ===")
    deduplicator.reset()
    result = deduplicator.should_translate("こんにちは世界")
    print(f"应该翻译: {result}")

    print("\n=== 测试完成 ===")
