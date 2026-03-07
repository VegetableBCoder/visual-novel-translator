"""
文本去重器（占位符）

临时占位符，用于测试翻译线程功能。
真实的文本去重器将在后续实现。
"""

import logging

logger = logging.getLogger(__name__)


class TextDeduplicator:
    """文本去重器占位符"""

    def __init__(self):
        """初始化文本去重器"""
        logger.info("文本去重器（占位符）已初始化")

    def is_similar(self, text1, text2):
        """
        判断两个文本是否相似

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            bool: True 表示相似，False 表示不相似
        """
        # 占位符：使用简单比较
        # 真实实现将使用 Levenshtein 编辑距离
        result = text1 == text2
        logger.debug(f"文本去重判断：'{text1}' vs '{text2}' -> {result}")
        return result


# 独立运行测试
if __name__ == "__main__":
    # 测试文本去重
    deduplicator = TextDeduplicator()

    result1 = deduplicator.is_similar("Hello", "Hello")
    print(f"相同文本去重：{result1}")

    result2 = deduplicator.is_similar("Hello", "World")
    print(f"不同文本去重：{result2}")
