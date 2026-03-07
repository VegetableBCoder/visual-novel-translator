"""
OCR 引擎（占位符）

临时占位符，用于测试截图线程功能。
真实的 OCR 引擎集成将在后续实现。
"""

import logging

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR 引擎占位符"""

    def __init__(self):
        """初始化 OCR 引擎"""
        logger.info("OCR 引擎（占位符）已初始化")

    def recognize(self, image):
        """
        识别图像中的文本

        Args:
            image: PIL Image 对象

        Returns:
            dict: 包含 "text" 和 "confidence" 的字典
        """
        # 占位符：返回测试文本
        result = {
            "text": "测试文本 - OCR服务待实现",
            "confidence": 0.9
        }
        logger.debug(f"OCR 识别结果：{result['text']}")
        return result


# 独立运行测试
if __name__ == "__main__":
    from PIL import Image

    # 创建测试图像
    test_image = Image.new("RGB", (800, 600), color=(255, 255, 255))

    # 测试 OCR 识别
    ocr_engine = OCREngine()
    result = ocr_engine.recognize(test_image)
    print(f"OCR 识别结果：{result}")
