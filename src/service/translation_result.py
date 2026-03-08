"""
翻译结果数据类
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationResult:
    """翻译结果"""

    success: bool                  # 翻译是否成功
    translated_text: str          # 翻译后的文本
    error: str = ""               # 错误信息（失败时）
    raw_data: Optional[dict] = None  # 原始返回数据，用于调试
