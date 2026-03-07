"""
图像处理器

负责图像的区域裁剪和预处理（缩小、统一宽度等）。
"""

import logging
from typing import Optional, Tuple
from PIL import Image
import numpy as np
import cv2

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
        max_width: int = 640,
        max_height: int = 480
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

    @staticmethod
    def calculate_diff_percent(
        image1: Optional[Image.Image],
        image2: Optional[Image.Image],
        threshold: int = 30,
        max_width: int = 640,
        max_height: int = 480
    ) -> float:
        """
        计算两张图片的像素差异百分比（使用OpenCV精确差分）

        Args:
            image1: 图片1（可为None，表示首次）
            image2: 图片2（可为None，表示首次）
            threshold: 二值化阈值，过滤轻微噪声（默认30）
            max_width: 差分计算的最大宽度，超出则缩放（默认640）
            max_height: 差分计算的最大高度，超出则缩放（默认480）

        Returns:
            float: 差异百分比，0-1范围
                   - None时返回1.0（视为完全不同）
        """
        # 任一为None，返回1.0（表示首次或完全不同）
        if image1 is None or image2 is None:
            return 1.0

        try:
            # 确保图片尺寸相同（同一窗口截图应保持尺寸一致）
            if image1.size != image2.size:
                logger.warning(f"图片尺寸不一致: {image1.size} vs {image2.size}，可能影响差分准确性")

            # 可选：如果图片过大，进行缩放以提高性能
            orig_width, orig_height = image1.size
            if orig_width > max_width or orig_height > max_height:
                # 使用原有的 resize_for_diff 方法保持宽高比缩放
                image1 = ImageProcessor.resize_for_diff(image1, max_width, max_height)
                image2 = ImageProcessor.resize_for_diff(image2, max_width, max_height)

            # 转换为numpy数组
            img1_arr = np.array(image1)
            img2_arr = np.array(image2)

            # 转换为灰度图
            img1_gray = cv2.cvtColor(img1_arr, cv2.COLOR_RGB2GRAY)
            img2_gray = cv2.cvtColor(img2_arr, cv2.COLOR_RGB2GRAY)

            # 计算绝对差分
            diff = cv2.absdiff(img1_gray, img2_gray)

            # 二值化：大于阈值的像素视为变化
            _, binary = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

            # 统计非零像素（变化的像素数量）
            changed_pixels = cv2.countNonZero(binary)
            total_pixels = img1_gray.size

            # 计算变化百分比
            diff_percent = changed_pixels / total_pixels

            logger.debug(f"图片差异百分比: {diff_percent:.4f} (变化像素: {changed_pixels}/{total_pixels})")

            return diff_percent

        except Exception as e:
            logger.error(f"计算图片差异失败: {str(e)}")
            return 1.0  # 出错时视为完全不同


# 独立运行测试
if __name__ == "__main__":
    import sys

    # 创建测试图像
    test_image1 = Image.new("RGB", (800, 600), color=(255, 255, 255))
    test_image2 = Image.new("RGB", (800, 600), color=(250, 250, 250))  # 略有差异

    # 测试裁剪
    region_ratio = {
        "left": 0.25,
        "top": 0.70,
        "right": 0.75,
        "bottom": 0.85
    }

    cropped = ImageProcessor.crop_region(test_image1, region_ratio)
    if cropped:
        print(f"裁剪成功: {cropped.width}x{cropped.height}")
        cropped.save("test_crop.png")

    # 测试缩放
    resized = ImageProcessor.resize_for_diff(test_image1, 320, 240)
    if resized:
        print(f"缩放成功: {resized.width}x{resized.height}")
        resized.save("test_resize.png")

    # 测试差分
    diff = ImageProcessor.calculate_diff_percent(test_image1, test_image2)
    print(f"差分百分比: {diff:.4f}")
