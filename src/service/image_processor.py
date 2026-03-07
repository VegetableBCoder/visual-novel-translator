"""
图像处理器

负责图像的区域裁剪和预处理（缩小、统一宽度等）。
"""

import logging
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class ImageProcessor:
    """图像处理器 - 负责裁剪和预处理"""

    @staticmethod
    def crop_region(
        image: Image.Image,
        region_ratio: dict,
        window_size: Optional[Tuple[int, int]] = None
    ) -> Optional[Image.Image]:
        """
        根据相对比例裁剪图像区域

        Args:
            image: 原始图像（整个窗口）
            region_ratio: 区域比例坐标 {"left": 0.0-1.0, "top": 0.0-1.0, ...}
            window_size: 窗口尺寸 (width, height)，可选。如果为None则使用image.size

        Returns:
            裁剪后的图像，失败返回 None
        """
        if not region_ratio:
            logger.warning("区域比例为空，无法裁剪")
            return None

        try:
            # 获取窗口尺寸
            if window_size is None:
                window_size = image.size

            win_width, win_height = window_size

            # 获取区域比例
            left_ratio = region_ratio.get("left", 0.0)
            top_ratio = region_ratio.get("top", 0.0)
            right_ratio = region_ratio.get("right", 1.0)
            bottom_ratio = region_ratio.get("bottom", 1.0)

            # 验证比例范围
            if not all(0.0 <= x <= 1.0 for x in [left_ratio, top_ratio, right_ratio, bottom_ratio]):
                logger.warning(f"区域比例无效: left={left_ratio}, top={top_ratio}, right={right_ratio}, bottom={bottom_ratio}")
                return None

            # 验证区域有效性
            if left_ratio >= right_ratio or top_ratio >= bottom_ratio:
                logger.warning(f"区域无效: left({left_ratio}) >= right({right_ratio}) 或 top({top_ratio}) >= bottom({bottom_ratio})")
                return None

            # 转换为绝对像素坐标
            left = int(left_ratio * win_width)
            top = int(top_ratio *win_height)
            right = int(right_ratio * win_width)
            bottom = int(bottom_ratio * win_height)

            # 确保坐标在图像范围内
            left = max(0, min(left, win_width))
            top = max(0, min(top, win_height))
            right = max(0, min(right, win_width))
            bottom = max(0, min(bottom, win_height))

            # 验证裁剪区域大小
            if right <= left or bottom <= top:
                logger.warning(f"裁剪区域大小为零: ({left}, {top}, {right}, {bottom})")
                return None

            # 裁剪图像
            cropped = image.crop((left, top, right, bottom))

            logger.debug(f"裁剪图像: 原始{win_width}x{win_height} -> 裁剪后{cropped.width}x{cropped.height}")

            return cropped

        except Exception as e:
            logger.error(f"裁剪图像失败: {str(e)}")
            return None

    @staticmethod
    def resize_for_diff(
        image: Image.Image,
        max_width: int = 320,
        max_height: int = 240
    ) -> Image.Image:
        """
        为图像差分调整图像大小（缩小以提高性能）

        Args:
            image: 输入图像
            max_width: 最大宽度（默认320）
            max_height: 最大高度（默认240）

        Returns:
            调整后的图像
        """
        try:
            # 获取原始尺寸
            orig_width, orig_height = image.size

            # 如果已经小于目标尺寸，直接返回
            if orig_width <= max_width and orig_height <= max_height:
                return image

            # 计算缩放比例（保持宽高比）
            width_ratio = max_width / orig_width
            height_ratio = max_height / orig_height
            scale_ratio = min(width_ratio, height_ratio)

            new_width = int(orig_width * scale_ratio)
            new_height = int(orig_height * scale_ratio)

            # 使用 LANCZOS 插值进行高质量缩小
            resized = image.resize((new_width, new_height), Image.LANCZOS)

            logger.debug(f"调整图像大小: {orig_width}x{orig_height} -> {new_width}x{new_height}")

            return resized

        except Exception as e:
            logger.error(f"调整图像大小失败: {str(e)}")
            return image

    @staticmethod
    def normalize_width(
        image: Image.Image,
        target_width: Optional[int] = None
    ) -> Image.Image:
        """
        统一图像宽度（可选，用于差分比较）

        Args:
            image: 输入图像
            target_width: 目标宽度，None表示不调整

        Returns:
            调整后的图像
        """
        if target_width is None:
            return image

        try:
            orig_width, orig_height = image.size

            # 如果宽度已经是目标宽度，直接返回
            if orig_width == target_width:
                return image

            # 计算缩放比例
            scale_ratio = target_width / orig_width
            new_height = int(orig_height * scale_ratio)

            # 使用 LANCZOS 插值
            resized = image.resize((target_width, new_height), Image.LANCZOS)

            logger.debug(f"统一图像宽度: {orig_width}x{orig_height} -> {target_width}x{new_height}")

            return resized

        except Exception as e:
            logger.error(f"统一图像宽度失败: {str(e)}")
            return image


# 独立运行测试
if __name__ == "__main__":
    import sys

    # 创建测试图像
    test_image = Image.new("RGB", (800, 600), color=(255, 255, 255))

    # 测试裁剪
    region_ratio = {
        "left": 0.25,
        "top": 0.70,
        "right": 0.75,
        "bottom": 0.85
    }

    cropped = ImageProcessor.crop_region(test_image, region_ratio)
    if cropped:
        print(f"裁剪成功: {cropped.width}x{cropped.height}")
        cropped.save("test_crop.png")

    # 测试缩放
    resized = ImageProcessor.resize_for_diff(test_image, 320, 240)
    if resized:
        print(f"缩放成功: {resized.width}x{resized.height}")
        resized.save("test_resize.png")
