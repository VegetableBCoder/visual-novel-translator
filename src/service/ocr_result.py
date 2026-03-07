"""
OCR识别结果数据类
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OCRResult:
    """OCR识别结果"""

    success: bool              # 识别是否成功
    text: str                  # 识别的文本（多个文本块拼接）
    confidence: float          # 平均置信度 (0-1)
    raw_data: Optional[list] = None  # 原始返回数据，用于调试
