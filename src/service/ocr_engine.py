"""
OCR 引擎 - PaddleOCR 封装
"""

import logging
from typing import Optional

import numpy as np
from PIL import Image
from paddleocr import PaddleOCR

from src.service.ocr_result import OCRResult

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR 引擎 - PaddleOCR 封装"""

    def __init__(self, lang='japan'):
        """
        初始化 PaddleOCR

        Args:
            lang: 语言代码，默认'japanese'
        """
        try:
            self._ocr = PaddleOCR(
                use_angle_cls=False,  # 启用方向分类（支持竖排文字）
                lang=lang
            )
            self._initialized = True
            self._lang = lang
            logger.info(f"PaddleOCR 初始化成功，语言: {lang}")
        except Exception as e:
            self._ocr = None
            self._initialized = False
            self._lang = lang
            logger.error(f"PaddleOCR 初始化失败: {str(e)}")

    def recognize(self, image: Image.Image) -> OCRResult:
        """
        识别图像中的文本

        Args:
            image: PIL Image 对象

        Returns:
            OCRResult: 识别结果
        """
        # 检查初始化状态
        if not self._initialized or self._ocr is None:
            logger.warning("PaddleOCR 未初始化，返回失败结果")
            return OCRResult(success=False, text='', confidence=0.0)

        try:
            # 调用 PaddleOCR 识别
            # PaddleOCR 返回值格式: [[box], (text, confidence), ...]
            img_np = np.array(image)
            result = self._ocr.predict(img_np)

            # 检查返回结果
            if result is None or len(result) == 0:
                logger.debug("OCR 识别结果为空")
                return OCRResult(success=False, text='', confidence=0.0)

            # 解析结果
            texts = []
            confidences = []

            for item in result:
                if item is None:
                    continue

                # 检查是否为字典格式（新版 PaddleOCR 返回格式）
                if isinstance(item, dict):
                    # 从 rec_texts 和 rec_scores 字段获取结果
                    rec_texts = item.get('rec_texts', [])
                    rec_rec_scores = item.get('rec_scores', [])

                    for i, text in enumerate(rec_texts):
                        if text and text.strip():
                            texts.append(text)
                            if i < len(rec_rec_scores):
                                confidences.append(rec_rec_scores[i])
                elif len(item) >= 2:
                    # 兼容旧格式: [[box], (text, confidence), ...]
                    text_info = item[1]
                    if text_info is None or (isinstance(text_info, (list, tuple)) and len(text_info) < 2):
                        continue

                    text = text_info[0]
                    conf = text_info[1]

                    if text and text.strip():
                        texts.append(text)
                        confidences.append(conf)

            # 如果没有识别到文本
            if not texts:
                logger.debug("OCR 未识别到有效文本")
                return OCRResult(success=False, text='', confidence=0.0)

            # 拼接所有文本（按出现顺序）
            full_text = ''.join(texts)

            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            logger.debug(f"OCR 识别成功: 文本长度={len(full_text)}, 置信度={avg_confidence:.2f}")

            return OCRResult(
                success=True,
                text=full_text,
                confidence=avg_confidence,
                raw_data=result
            )

        except Exception as e:
            error_msg = f"OCR 识别异常: {str(e)}"
            logger.error(error_msg)
            return OCRResult(success=False, text='', confidence=0.0)


# 独立运行测试
if __name__ == "__main__":
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建测试图像
    test_image = Image.open(fp='I:\\screenshot\\5efb8999176e4c3d83b53e2c0bd198b5.jpg')

    # 测试 OCR 引擎
    ocr_engine = OCREngine()

    if ocr_engine._initialized:
        result = ocr_engine.recognize(test_image)
        print(f"OCR 识别结果: {result}")
    else:
        print("OCR 引擎初始化失败，请检查依赖")
