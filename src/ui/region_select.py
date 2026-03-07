"""
区域选择界面

软件启动后的第三个界面，用于在目标窗口截图上框选需要 OCR 识别的文字区域：
- 显示目标窗口的截图
- 通过鼠标拖拽框选文字区域
- 支持重新截屏
- 保存选区相对位置信息
"""
import logging
import uuid

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage

from src.controller.config_interface import IConfigManager
from src.core.window_capture import capture_window

logger = logging.getLogger(__name__)


class RegionSelectWidget(QWidget):
    """区域选择自定义控件，用于显示截图并处理选区交互"""

    # 定义信号，用于与主界面通信
    selectionChanged = pyqtSignal()  # 选区变化时发射

    def __init__(self, parent=None):
        """
        初始化区域选择控件

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        # 图像相关
        self.original_pixmap = None  # 原始 QPixmap（未缩放）
        self.original_size = None  # 原始图片尺寸 (width, height)
        self.scaled_pixmap = None  # 缩放后的 QPixmap
        self.current_scale = 1.0  # 当前缩放因子
        self.pixmap_rect = None  # 图片在控件中的显示区域

        # 选区相关
        self.selection_rect = None  # 选区在图片显示区域中的坐标
        self.selection_ratio = None  # 选区的相对比例坐标（0-1），用于暂存
        self.min_selection_size = 30  # 选区最小尺寸（像素）

        # 交互状态
        self.mode = 'none'  # 当前操作模式：none, moving, resizing
        self.resize_direction = None  # 拉伸方向
        self.drag_start_pos = None  # 拖拽起始点
        self.original_rect = None  # 操作前的选区备份

        # 控制点相关
        self.handle_size = 15  # 控制点尺寸（像素）
        self.hovered_handle = None  # 当前悬停的控制点

        # 信号节流
        self._signal_timer = QTimer()
        self._signal_timer.setSingleShot(True)
        self._signal_timer.timeout.connect(self._emit_selection_changed)

        # 初始化样式
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #2D2D2D;")

    def set_pixmap(self, pixmap: QPixmap):
        """
        设置显示的图片

        Args:
            pixmap: QPixmap 对象
        """
        # 保存当前选区的相对比例（如果存在）
        if self.selection_rect:
            self.selection_ratio = self.get_selection_ratio()

        self.original_pixmap = pixmap
        self.original_size = (pixmap.width(), pixmap.height())
        self.scaled_pixmap = None  # 清除缩放缓存
        self._update_scale()  # 计算缩放

        # 如果有保存的选区比例，则恢复选区；否则创建默认选区
        if self.selection_ratio:
            self._restore_selection_from_ratio()
        else:
            self._create_default_selection()

        self.update()  # 触发重绘

    def _update_scale(self):
        """更新缩放因子和图片显示区域"""
        if self.original_pixmap is None:
            return

        orig_w, orig_h = self.original_size
        widget_w = self.width()
        widget_h = self.height()

        # 计算保持宽高比的缩放因子
        scale_x = widget_w / orig_w
        scale_y = widget_h / orig_h
        self.current_scale = min(scale_x, scale_y)

        # 计算缩放后的图片尺寸
        scaled_w = int(orig_w * self.current_scale)
        scaled_h = int(orig_h * self.current_scale)

        # 缩放图片
        from PyQt5.QtCore import QRectF
        self.scaled_pixmap = self.original_pixmap.scaled(
            scaled_w, scaled_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # 计算图片在控件中的显示区域（居中）
        from PyQt5.QtCore import QPointF
        x = (widget_w - scaled_w) / 2
        y = (widget_h - scaled_h) / 2
        self.pixmap_rect = QRectF(x, y, scaled_w, scaled_h)

    def _create_default_selection(self):
        """创建默认选区（图片中心 60% 宽度、30% 高度）"""
        if self.pixmap_rect is None:
            return

        from PyQt5.QtCore import QRectF, QPointF
        rect_w = self.pixmap_rect.width() * 0.6
        rect_h = self.pixmap_rect.height() * 0.3
        rect_x = (self.pixmap_rect.width() - rect_w) / 2
        rect_y = (self.pixmap_rect.height() - rect_h) / 2

        self.selection_rect = QRectF(rect_x, rect_y, rect_w, rect_h)

    def _restore_selection_from_ratio(self):
        """从保存的相对比例恢复选区位置"""
        if self.selection_ratio is None or self.pixmap_rect is None:
            return

        ratio = self.selection_ratio
        orig_w, orig_h = self.original_size

        # 计算缩放后的选区位置和尺寸
        left = ratio['left'] * orig_w * self.current_scale
        top = ratio['top'] * orig_h * self.current_scale
        right = ratio['right'] * orig_w * self.current_scale
        bottom = ratio['bottom'] * orig_h * self.current_scale

        from PyQt5.QtCore import QRectF
        self.selection_rect = QRectF(left, top, right - left, bottom - top)

    def widget_to_display(self, widget_pos):
        """
        将控件坐标转换为图片显示区域坐标

        Args:
            widget_pos: QPointF 控件坐标

        Returns:
            QPointF: 图片显示区域坐标
        """
        from PyQt5.QtCore import QPointF
        return widget_pos - self.pixmap_rect.topLeft()

    def display_to_original(self, display_pos):
        """
        将图片显示区域坐标转换为原始图片坐标

        Args:
            display_pos: QPointF 图片显示区域坐标

        Returns:
            QPointF: 原始图片坐标
        """
        from PyQt5.QtCore import QPointF
        return QPointF(display_pos.x() / self.current_scale, display_pos.y() / self.current_scale)

    def original_to_relative(self, original_rect):
        """
        将原始图片坐标矩形转换为相对比例坐标（0-1）

        Args:
            original_rect: QRectF 原始图片坐标矩形

        Returns:
            dict: {"left": float, "top": float, "right": float, "bottom": float}
        """
        orig_w, orig_h = self.original_size
        return {
            "left": original_rect.left() / orig_w,
            "top": original_rect.top() / orig_h,
            "right": original_rect.right() / orig_w,
            "bottom": original_rect.bottom() / orig_h
        }

    def constrain_rect(self, rect):
        """
        约束矩形在图片区域内且不小于最小尺寸

        Args:
            rect: QRectF 待约束的矩形

        Returns:
            QRectF: 约束后的矩形
        """
        from PyQt5.QtCore import QRectF

        # 约束边界
        from PyQt5.QtCore import QPointF
        rect.setLeft(max(rect.left(), 0))
        rect.setTop(max(rect.top(), 0))
        rect.setRight(min(rect.right(), self.pixmap_rect.width()))
        rect.setBottom(min(rect.bottom(), self.pixmap_rect.height()))

        # 约束最小尺寸（在边界约束后的基础上）
        min_size = self.min_selection_size
        if rect.width() < min_size:
            if rect.left() == 0:
                rect.setRight(min_size)
            else:
                rect.setLeft(rect.right() - min_size)

        if rect.height() < min_size:
            if rect.top() == 0:
                rect.setBottom(min_size)
            else:
                rect.setTop(rect.bottom() - min_size)

        return rect

    def get_selection_ratio(self):
        """
        获取当前选区的相对比例坐标 (0-1)

        Returns:
            dict: {"left": float, "top": float, "right": float, "bottom": float}
        """
        if self.selection_rect is None:
            return None

        # 将图片显示坐标转换为原始图片坐标
        from PyQt5.QtCore import QRectF
        orig_rect = QRectF(
            self.selection_rect.left() / self.current_scale,
            self.selection_rect.top() / self.current_scale,
            self.selection_rect.width() / self.current_scale,
            self.selection_rect.height() / self.current_scale
        )

        # 转换为相对比例坐标
        return self.original_to_relative(orig_rect)

    def get_selection_pixel_size(self):
        """
        获取当前选区的实际像素尺寸（原始图片坐标）

        Returns:
            dict: {"width": int, "height": int} 或 None
        """
        if self.selection_rect is None:
            return None

        return {
            "width": int(self.selection_rect.width() / self.current_scale),
            "height": int(self.selection_rect.height() / self.current_scale)
        }

    def _emit_selection_changed(self):
        """发射选区变化信号"""
        self.selectionChanged.emit()

    # 控制点相关方法

    def get_handle_rects(self):
        """
        计算所有控制点的矩形区域（图片显示坐标）

        Returns:
            dict: 键为控制点名称，值为 QRectF
        """
        r = self.selection_rect
        hs = self.handle_size
        from PyQt5.QtCore import QRectF
        return {
            'topleft': QRectF(r.left() - hs/2, r.top() - hs/2, hs, hs),
            'top': QRectF(r.center().x() - hs/2, r.top() - hs/2, hs, hs),
            'topright': QRectF(r.right() - hs/2, r.top() - hs/2, hs, hs),
            'left': QRectF(r.left() - hs/2, r.center().y() - hs/2, hs, hs),
            'right': QRectF(r.right() - hs/2, r.center().y() - hs/2, hs, hs),
            'bottomleft': QRectF(r.left() - hs/2, r.bottom() - hs/2, hs, hs),
            'bottom': QRectF(r.center().x() - hs/2, r.bottom() - hs/2, hs, hs),
            'bottomright': QRectF(r.right() - hs/2, r.bottom() - hs/2, hs, hs)
        }

    def _get_edge_at_pos(self, display_pos):
        """
        根据鼠标位置判断命中的边框

        Args:
            display_pos: QPointF 图片显示区域坐标

        Returns:
            str: 边框名称（'left', 'right', 'top', 'bottom', 'topleft', 'topright', 'bottomleft', 'bottomright'），未命中返回 None
        """
        if self.selection_rect is None:
            return None

        r = self.selection_rect
        edge_threshold = 6  # 边框检测阈值（像素）

        x = display_pos.x()
        y = display_pos.y()
        left_dist = abs(x - r.left())
        right_dist = abs(x - r.right())
        top_dist = abs(y - r.top())
        bottom_dist = abs(y - r.bottom())

        # 检查角落（两个方向同时拉伸）
        if left_dist < edge_threshold and top_dist < edge_threshold:
            return 'topleft'
        if right_dist < edge_threshold and top_dist < edge_threshold:
            return 'topright'
        if left_dist < edge_threshold and bottom_dist < edge_threshold:
            return 'bottomleft'
        if right_dist < edge_threshold and bottom_dist < edge_threshold:
            return 'bottomright'

        # 检查四条边（单方向拉伸）
        if left_dist < edge_threshold:
            return 'left'
        if right_dist < edge_threshold:
            return 'right'
        if top_dist < edge_threshold:
            return 'top'
        if bottom_dist < edge_threshold:
            return 'bottom'

        return None

    def _get_handle_at_pos(self, display_pos):
        """
        根据鼠标位置判断命中的控制点

        Args:
            display_pos: QPointF 图片显示区域坐标

        Returns:
            str: 控制点名称，未命中返回 None
        """
        if self.selection_rect is None:
            return None

        handles = self.get_handle_rects()
        for name, rect in handles.items():
            # 稍微扩大检测范围，使得更容易点中
            if rect.contains(display_pos):
                return name
        return None

    def _get_cursor_for_handle(self, handle):
        """
        根据控制点获取对应对应的光标形状

        Args:
            handle: str 控制点名称

        Returns:
            Qt.CursorShape: 光标形状
        """
        if handle in ('topleft', 'bottomright'):
            return Qt.SizeFDiagCursor
        elif handle in ('topright', 'bottomleft'):
            return Qt.SizeBDiagCursor
        elif handle in ('left', 'right'):
            return Qt.SizeHorCursor
        elif handle in ('top', 'bottom'):
            return Qt.SizeVerCursor
        else:
            return Qt.ArrowCursor

    # 绘制相关方法

    def _draw_mask(self, painter):
        """
        绘制半透明遮罩层（选区外部区域）

        Args:
            painter: QPainter 绘制对象
        """
        from PyQt5.QtGui import QColor, QBrush
        from PyQt5.QtCore import QRectF

        # 遮罩颜色：半透明黑色（60%透明度）
        mask_color = QColor(0, 0, 0, 153)
        mask_brush = QBrush(mask_color)

        # 获取图片显示区域和选区
        pixmap_rect = self.pixmap_rect
        sel_rect = self.selection_rect

        # 绘制四个外围区域的遮罩
        # 上方
        top_rect = QRectF(
            pixmap_rect.left(),
            pixmap_rect.top(),
            pixmap_rect.width(),
            sel_rect.top()
        )
        painter.fillRect(top_rect, mask_brush)

        # 下方
        bottom_rect = QRectF(
            pixmap_rect.left(),
            sel_rect.bottom(),
            pixmap_rect.width(),
            pixmap_rect.bottom() - sel_rect.bottom()
        )
        painter.fillRect(bottom_rect, mask_brush)

        # 左方
        left_rect = QRectF(
            pixmap_rect.left(),
            sel_rect.top(),
            sel_rect.left(),
            sel_rect.height()
        )
        painter.fillRect(left_rect, mask_brush)

        # 右方
        right_rect = QRectF(
            sel_rect.right(),
            sel_rect.top(),
            pixmap_rect.right() - sel_rect.right(),
            sel_rect.height()
        )
        painter.fillRect(right_rect, mask_brush)

    def _draw_selection_border(self, painter):
        """
        绘制选区边框（2px 亮蓝色）

        Args:
            painter: QPainter 绘制对象
        """
        from PyQt5.QtGui import QPen, QColor

        # 选区边框颜色：亮蓝色
        border_color = QColor(0, 120, 215)
        border_pen = QPen(border_color, 2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.selection_rect)

    def _draw_handles(self, painter):
        """
        绘制8个控制点

        Args:
            painter: QPainter 绘制对象
        """
        from PyQt5.QtGui import QPen, QColor, QBrush

        # 控制点样式
        handle_brush = QBrush(QColor(255, 255, 255))  # 白色填充
        border_color = QColor(0, 120, 215)  # 蓝色边框

        handles = self.get_handle_rects()
        for name, rect in handles.items():
            # 悬停时高亮
            if name == self.hovered_handle:
                border_pen = QPen(border_color, 3)
            else:
                border_pen = QPen(border_color, 1)

            painter.setPen(border_pen)
            painter.setBrush(handle_brush)
            painter.drawRect(rect)

    # 鼠标事件处理方法

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        # 检查是否在图片显示区域内
        if self.pixmap_rect is None:
            super().mousePressEvent(event)
            return

        from PyQt5.QtCore import QPointF
        pos = QPointF(event.pos())

        if not self.pixmap_rect.contains(pos):
            super().mousePressEvent(event)
            return

        # 转换为图片显示坐标
        display_pos = self.widget_to_display(pos)

        # 按优先级判断操作类型
        # 1. 检查是否命中控制点
        handle = self._get_handle_at_pos(display_pos)
        if handle:
            self.mode = 'resizing'
            self.resize_direction = handle
            self.drag_start_pos = display_pos
            self.original_rect = self.selection_rect.normalized()
            event.accept()
            return

        # 2. 检查是否命中边框
        edge = self._get_edge_at_pos(display_pos)
        if edge:
            self.mode = 'resizing'
            self.resize_direction = edge
            self.drag_start_pos = display_pos
            self.original_rect = self.selection_rect.normalized()
            event.accept()
            return

        # 3. 检查是否在选区内部
        if self.selection_rect and self.selection_rect.contains(display_pos):
            self.mode = 'moving'
            self.drag_start_pos = display_pos
            self.original_rect = self.selection_rect.normalized()
            event.accept()
            return

        # 3. 点击在图片区域内但选区外，不执行任何操作
        # 只支持移动和拉伸现有选区，不支持创建新选区
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        from PyQt5.QtCore import QPointF
        pos = QPointF(event.pos())

        # 始终检查并更新光标形状（无论当前模式）
        self._update_cursor_widget_pos(pos)

        # 只在图片区域内处理操作
        if self.pixmap_rect is None or not self.pixmap_rect.contains(pos):
            return

        display_pos = self.widget_to_display(pos)

        # 处理不同的操作模式
        if self.mode == 'moving':
            self._update_moving_selection(display_pos)
        elif self.mode == 'resizing':
            self._update_resizing_selection(display_pos)

    def _update_moving_selection(self, display_pos):
        """更新移动中的选区"""
        # 计算偏移量
        delta = display_pos - self.drag_start_pos

        # 计算新位置
        new_left = self.original_rect.left() + delta.x()
        new_top = self.original_rect.top() + delta.y()
        new_right = self.original_rect.right() + delta.x()
        new_bottom = self.original_rect.bottom() + delta.y()

        from PyQt5.QtCore import QRectF
        new_rect = QRectF(new_left, new_top, new_right - new_left, new_bottom - new_top)

        # 约束边界
        new_rect = self._constrain_to_pixmap(new_rect)

        self.selection_rect = new_rect

        # 触发重绘和信号
        self.update()
        self._signal_timer.start(50)

    def _update_resizing_selection(self, display_pos):
        """更新拉伸中的选区"""
        from PyQt5.QtCore import QRectF

        # 复制原始矩形
        new_rect = QRectF(self.original_rect)
        direction = self.resize_direction

        # 根据拉伸方向调整对应边界
        if 'left' in direction:
            new_rect.setLeft(display_pos.x())
        if 'right' in direction:
            new_rect.setRight(display_pos.x())
        if 'top' in direction:
            new_rect.setTop(display_pos.y())
        if 'bottom' in direction:
            new_rect.setBottom(display_pos.y())

        # 约束边界和最小尺寸
        new_rect = self.constrain_rect(new_rect)

        self.selection_rect = new_rect

        # 触发重绘和信号
        self.update()
        self._signal_timer.start(50)

    def _constrain_to_pixmap(self, rect):
        """约束矩形在图片区域内"""
        from PyQt5.QtCore import QRectF

        # 约束到图片显示区域内
        left = max(rect.left(), 0)
        top = max(rect.top(), 0)
        right = min(rect.right(), self.pixmap_rect.width())
        bottom = min(rect.bottom(), self.pixmap_rect.height())

        return QRectF(left, top, right - left, bottom - top)

    def _update_cursor_widget_pos(self, widget_pos):
        """
        根据控件坐标位置更新光标形状

        Args:
            widget_pos: QPointF 控件坐标
        """
        # 如果没有图片，显示默认光标
        if self.pixmap_rect is None:
            self.setCursor(Qt.ArrowCursor)
            return

        # 检查是否在图片显示区域内
        if not self.pixmap_rect.contains(widget_pos):
            self.setCursor(Qt.ArrowCursor)
            self.hovered_handle = None
            return

        # 转换为图片显示坐标
        display_pos = self.widget_to_display(widget_pos)

        # 如果正在拖拽（移动或拉伸），保持当前光标不变
        if self.mode in ('moving', 'resizing'):
            return

        # 检查控制点
        handle = self._get_handle_at_pos(display_pos)
        if handle:
            self.setCursor(self._get_cursor_for_handle(handle))
            self.hovered_handle = handle
            return

        # 检查边框
        edge = self._get_edge_at_pos(display_pos)
        if edge:
            self.setCursor(self._get_cursor_for_handle(edge))
            self.hovered_handle = None
            return

        # 检查选区内部
        if self.selection_rect and self.selection_rect.contains(display_pos):
            self.setCursor(Qt.SizeAllCursor)
            self.hovered_handle = None
            return

        # 图片其他区域（选区外）：显示默认箭头
        self.setCursor(Qt.ArrowCursor)
        self.hovered_handle = None

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            # 重置模式
            self.mode = 'none'
            self.resize_direction = None
            self.drag_start_pos = None
            self.original_rect = None

            # 触发最终信号
            self._signal_timer.stop()
            self._emit_selection_changed()

        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """绘制事件"""
        from PyQt5.QtGui import QPainter, QColor

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. 绘制背景
        painter.fillRect(self.rect(), QColor(45, 45, 45))

        # 2. 绘制图片
        if self.scaled_pixmap and self.pixmap_rect:
            painter.drawPixmap(self.pixmap_rect.toRect(), self.scaled_pixmap)

            # 3. 绘制遮罩层（半透明黑色）
            if self.selection_rect:
                self._draw_mask(painter)

            # 4. 绘制选区边框（2px 亮蓝色）
            self._draw_selection_border(painter)

            # 5. 绘制 8 个控制点
            self._draw_handles(painter)

        painter.end()

    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        if self.original_pixmap and self.selection_rect:
            # 保存选区的相对比例
            ratio_before = self.get_selection_ratio()

            # 更新缩放
            self._update_scale()

            # 根据比例恢复选区位置
            if ratio_before:
                orig_w, orig_h = self.original_size
                new_left = ratio_before['left'] * orig_w * self.current_scale
                new_top = ratio_before['top'] * orig_h * self.current_scale
                new_right = ratio_before['right'] * orig_w * self.current_scale
                new_bottom = ratio_before['bottom'] * orig_h * self.current_scale

                from PyQt5.QtCore import QRectF
                self.selection_rect = QRectF(
                    new_left, new_top,
                    new_right - new_left,
                    new_bottom - new_top
                )

            self.update()


class RegionSelectWidgetWrapper(QWidget):
    """区域选择界面包装器"""

    # 定义信号，用于与主窗口通信
    back_signal = pyqtSignal()  # 用户点击上一步
    next_signal = pyqtSignal()  # 用户点击下一步
    cancel_signal = pyqtSignal()  # 用户点击取消

    def __init__(self, config_manager: IConfigManager, parent=None):
        """
        初始化区域选择界面

        Args:
            config_manager: 配置管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.current_hwnd = None

        self._init_ui()
        self._connect_signals()
        # 不在初始化时调用截图，而是在界面显示时调用

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("选择识别区域")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 添加说明标签
        info_label = QLabel("请在下方截图上框选需要OCR识别的文字区域")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333333;")
        layout.addWidget(info_label)

        # 创建区域选择控件
        self.region_widget = RegionSelectWidget()
        layout.addWidget(self.region_widget, stretch=1)

        # 截图信息栏
        info_layout = QHBoxLayout()
        self.image_size_label = QLabel("原始截图: - x -")
        self.image_size_label.setStyleSheet("color: #666666;")
        info_layout.addWidget(self.image_size_label)
        info_layout.addStretch()

        # 重新截屏按钮
        self.refresh_btn = QPushButton("🔄 重新截屏")
        self.refresh_btn.setMinimumWidth(100)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                padding: 5px 15px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
            QPushButton:pressed {
                background-color: #D8D8D8;
            }
        """)
        info_layout.addWidget(self.refresh_btn)
        layout.addLayout(info_layout)

        # 选区信息标签
        selection_info_layout = QHBoxLayout()
        self.selection_size_label = QLabel("选区尺寸: - x - px")
        self.selection_size_label.setStyleSheet("color: #666666; font-size: 12px;")
        self.selection_position_label = QLabel("相对位置: -")
        self.selection_position_label.setStyleSheet("color: #666666; font-size: 12px;")
        selection_info_layout.addWidget(self.selection_size_label)
        selection_info_layout.addSpacing(20)
        selection_info_layout.addWidget(self.selection_position_label)
        selection_info_layout.addStretch()
        layout.addLayout(selection_info_layout)

        # 底部按钮
        button_layout = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.back_btn.setMinimumWidth(100)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                padding: 8px 20px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
            QPushButton:pressed {
                background-color: #D8D8D8;
            }
        """)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                padding: 8px 20px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
            QPushButton:pressed {
                background-color: #D8D8D8;
            }
        """)
        self.next_btn = QPushButton("下一步")
        self.next_btn.setMinimumWidth(100)
        self.next_btn.setEnabled(True)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3A80D2;
            }
            QPushButton:pressed {
                background-color: #2A70C2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)

        button_layout.addWidget(self.back_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.next_btn)
        layout.addLayout(button_layout)

    def _connect_signals(self):
        """连接信号"""
        self.refresh_btn.clicked.connect(self._capture_and_load)
        self.region_widget.selectionChanged.connect(self._update_selection_info)
        self.back_btn.clicked.connect(self.back_signal.emit)
        self.cancel_btn.clicked.connect(self.cancel_signal.emit)
        self.next_btn.clicked.connect(self._on_next)

    def _capture_and_load(self):
        """截取窗口并加载到界面"""
        # 从配置中获取窗口句柄
        hwnd = self.config_manager.get("window.hwnd")

        if hwnd is None:
            QMessageBox.warning(self, "错误", "未找到窗口句柄，请先选择窗口")
            self.back_signal.emit()
            return

        self.current_hwnd = hwnd

        # 截图
        try:
            pil_image = capture_window(hwnd)
            pil_image.save(f"I:\\screenshot\\{uuid.uuid4().hex}.jpg", "JPEG")
            if pil_image is None:
                QMessageBox.warning(
                    self,
                    "截图失败",
                    f"无法截取窗口（句柄: 0x{hwnd:X}），可能窗口已关闭或最小化"
                )
                self.image_size_label.setText("原始截图: 截图失败")
                self.next_btn.setEnabled(False)
                return

            # 转换为 QPixmap
            width, height = pil_image.size
            bytes_per_line = width * 3  # RGB
            qimage = QImage(
                pil_image.tobytes(),
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888
            )
            qpixmap = QPixmap.fromImage(qimage)

            # 设置到区域选择控件
            self.region_widget.set_pixmap(qpixmap)

            # 更新信息
            self.image_size_label.setText(f"原始截图: {width} x {height}")
            self.next_btn.setEnabled(True)

            # 更新选区信息
            self._update_selection_info()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"截图时发生异常：{str(e)}")
            self.image_size_label.setText("原始截图: 出错")
            self.next_btn.setEnabled(False)

    def _update_selection_info(self):
        """更新选区信息显示"""
        # 获取选区相对比例
        ratio = self.region_widget.get_selection_ratio()
        # 获取选区像素尺寸
        pixel_size = self.region_widget.get_selection_pixel_size()

        if ratio and pixel_size:
            self.selection_position_label.setText(
                f"相对位置: 左:{ratio['left']:.1%} "
                f"上:{ratio['top']:.1%} "
                f"右:{ratio['right']:.1%} "
                f"下:{ratio['bottom']:.1%}"
            )
            self.selection_size_label.setText(
                f"选区尺寸: {pixel_size['width']} x {pixel_size['height']} px"
            )
        else:
            self.selection_size_label.setText("选区尺寸: - x - px")
            self.selection_position_label.setText("相对位置: -")

    def _on_next(self):
        """下一步处理"""
        if self.current_hwnd is None:
            QMessageBox.warning(self, "提示", "请先截取窗口截图")
            return

        # 获取选区比例
        ratio = self.region_widget.get_selection_ratio()

        if ratio is None:
            QMessageBox.warning(self, "提示", "请先选择识别区域")
            return

        # 保存到配置
        self.config_manager.set("window.region", ratio)

        # 持久化
        config_data = self.config_manager.load_config()
        self.config_manager.save_config(config_data)

        # 输出完整配置到日志（JSON 格式）
        logger.info("=" * 60)
        logger.info("区域选择配置已保存")
        logger.info("=" * 60)
        import json
        logger.info(json.dumps(config_data, ensure_ascii=False, indent=2))
        logger.info("=" * 60)

        # 发送下一步信号
        self.next_signal.emit()


# 独立运行测试
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from src.controller.config_helper import ConfigHelper

    app = QApplication(sys.argv)

    # 创建配置管理器
    config_manager = ConfigHelper()

    # 确保有窗口句柄（如果没有，先运行窗口选择）
    hwnd = config_manager.get("window.hwnd")
    if hwnd is None:
        print("错误：请先运行窗口选择界面选择一个窗口")
        sys.exit(1)

    # 创建区域选择界面
    widget = RegionSelectWidgetWrapper(config_manager)

    # 显示界面
    widget.show()

    sys.exit(app.exec_())
