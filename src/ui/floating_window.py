"""
悬浮窗 - 显示翻译结果

可拖拽、可调整大小、透明背景、支持复制和关闭功能。
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QHBoxLayout, QApplication, QToolButton)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QBrush, QIcon, QFont
from typing import Optional

from src.controller.config_interface import IConfigManager


# 默认尺寸（增大）
_DEFAULT_WIDTH = 500
_DEFAULT_HEIGHT = 300

# 边缘检测阈值（像素）
_EDGE_THRESHOLD = 8

# 按钮尺寸
_BUTTON_SIZE = 24


class FloatingTranslateWindow(QWidget):
    """翻译结果悬浮窗"""

    # 关闭请求信号
    closeRequested = pyqtSignal()

    def __init__(self, config_manager: IConfigManager):
        """
        初始化悬浮窗

        Args:
            config_manager: 配置管理器实例
        """
        super().__init__()

        self.config_manager = config_manager

        # 拖拽状态
        self._dragging = False
        self._drag_start_position = QPoint()
        self._drag_start_window_pos = QPoint()

        # 调整大小状态
        self._resizing = False
        self._resize_edge = None
        self._resize_start_geometry = None

        # 文本内容
        self._original_text = ""
        self._translated_text = ""

        # 初始化样式配置
        self._init_style_config()

        # 初始化UI
        self._init_ui()

        # 恢复窗口位置和大小
        self._restore_window_geometry()

        # 隐藏窗口（等待显示）
        self.hide()

    def _init_style_config(self):
        """初始化样式配置"""
        config = self.config_manager.load_config()
        display_config = config.get("display", {})

        # 字体设置
        self._font_family = display_config.get("font_family", "微软雅黑")
        self._font_size = display_config.get("font_size", 16)
        self._font_color = QColor(display_config.get("font_color", "#FFFFFF"))
        self._original_text_color = QColor("#AAAAAA")  # 原文使用灰色

        # 背景设置
        self._bg_opacity = display_config.get("bg_opacity", 40)
        self._bg_color = QColor(0, 0, 0, self._bg_opacity if self._bg_opacity > 0 else 0)

        # 显示设置
        self._show_original = display_config.get("show_original", True)

    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 始终置顶
            Qt.Tool  # 工具窗口（不显示在任务栏）
        )

        # 设置窗口透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 设置默认大小
        self.resize(_DEFAULT_WIDTH, _DEFAULT_HEIGHT)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建按钮容器（位于右上角）
        self._button_container = QWidget(self)
        self._button_container.setStyleSheet("background: transparent;")
        self._button_container.setGeometry(
            _DEFAULT_WIDTH - _BUTTON_SIZE * 2 - 10,  # x
            0,  # y
            _BUTTON_SIZE * 2 + 10,  # width
            _BUTTON_SIZE + 10  # height
        )

        # 复制按钮
        self._copy_button = QToolButton(self._button_container)
        self._copy_button.setGeometry(0, 0, _BUTTON_SIZE, _BUTTON_SIZE)
        self._copy_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: white;
                padding: 0px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 30);
                border-radius: 4px;
            }
        """)
        self._copy_button.setText("⧉")  # 复制图标
        self._copy_button.setToolTip("复制翻译结果")
        self._copy_button.clicked.connect(self._copy_translation)

        # 关闭按钮
        self._close_button = QToolButton(self._button_container)
        self._close_button.setGeometry(_BUTTON_SIZE + 10, 0, _BUTTON_SIZE, _BUTTON_SIZE)
        self._close_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: white;
                padding: 0px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 30);
                border-radius: 4px;
            }
        """)
        self._close_button.setText("×")  # 关闭图标
        self._close_button.setToolTip("关闭悬浮窗")
        self._close_button.clicked.connect(self._on_close_clicked)

        # 创建内容容器
        self._content_widget = QWidget(self)
        self._content_widget.setStyleSheet("background: transparent;")

        # 创建内容布局
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(5)

        # 原文标签
        self._original_label = QLabel(self._content_widget)
        self._original_label.setWordWrap(True)
        self._original_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        font = QFont(self._font_family, self._font_size)
        font.setPointSize(int(self._font_size * 0.75))  # 原文字体较小
        self._original_label.setFont(font)
        self._original_label.setStyleSheet(f"color: {self._original_text_color.name()}; background: transparent;")
        self._original_label.setVisible(self._show_original)

        # 翻译标签
        self._translated_label = QLabel(self._content_widget)
        self._translated_label.setWordWrap(True)
        self._translated_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        font = QFont(self._font_family, self._font_size)
        self._translated_label.setFont(font)
        self._translated_label.setStyleSheet(f"color: {self._font_color.name()}; background: transparent;")

        # 添加标签到布局
        if self._show_original:
            content_layout.addWidget(self._original_label)
        content_layout.addWidget(self._translated_label)

        # 将内容widget添加到主布局
        main_layout.addWidget(self._content_widget)

    def on_translation_completed(self, original: str, translated: str):
        """
        更新翻译结果

        Args:
            original: 原文
            translated: 翻译结果
        """
        self._original_text = original
        self._translated_text = translated

        # 更新UI
        if self._show_original:
            self._original_label.setText(original)
        self._translated_label.setText(translated)

        # 根据内容调整大小
        self._adjust_size_to_content()

    def _adjust_size_to_content(self):
        """根据内容调整窗口大小"""
        # 计算所需高度
        content_height = 0

        if self._show_original:
            self._original_label.adjustSize()
            content_height += self._original_label.height() + 5

        self._translated_label.adjustSize()
        content_height += self._translated_label.height() + 5

        # 加上边距
        content_height += 20  # 上下边距

        # 获取当前宽度
        current_width = self.width()

        # 限制最小高度
        min_height = max(content_height, 100)

        # 如果内容超出当前宽度，调整宽度
        max_content_width = max(self._translated_label.width(), 0)
        if self._show_original:
            max_content_width = max(max_content_width, self._original_label.width())

        max_content_width += 20  # 左右边距

        new_width = max(current_width, min(max_content_width, _DEFAULT_WIDTH))
        new_height = min_height

        # 调整大小（保留当前窗口位置）
        current_pos = self.pos()
        self.resize(new_width, new_height)
        self.move(current_pos)

        # 更新按钮容器位置
        self._update_button_container_position()

    def _update_button_container_position(self):
        """更新按钮容器位置到右上角"""
        self._button_container.setGeometry(
            self.width() - _BUTTON_SIZE * 2 - 10,
            0,
            _BUTTON_SIZE * 2 + 10,
            _BUTTON_SIZE + 10
        )

    def _copy_translation(self):
        """复制翻译结果到剪贴板"""
        clipboard = QApplication.clipboard()
        text_to_copy = self._translated_text
        clipboard.setText(text_to_copy)

    def _on_close_clicked(self):
        """关闭按钮点击处理"""
        self.closeRequested.emit()

    def mousePressEvent(self, event):
        """
        鼠标按下事件

        Args:
            event: 鼠标事件
        """
        if event.button() == Qt.LeftButton:
            # 检查是否在边缘（调整大小）
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_geometry = self.geometry()
            else:
                # 拖拽
                self._dragging = True
                self._drag_start_position = event.globalPos()
                self._drag_start_window_pos = self.pos()

    def mouseMoveEvent(self, event):
        """
        鼠标移动事件

        Args:
            event: 鼠标事件
        """
        if self._resizing and self._resize_edge:
            # 调整大小
            self._perform_resize(event.globalPos())
        elif self._dragging:
            # 拖拽
            delta = event.globalPos() - self._drag_start_position
            new_pos = self._drag_start_window_pos + delta
            self.move(new_pos)

        # 更新鼠标光标
        edge = self._get_resize_edge(event.pos())
        if edge:
            cursor_shape = self._get_cursor_shape(edge)
            self.setCursor(cursor_shape)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """
        鼠标释放事件

        Args:
            event: 鼠标事件
        """
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._resizing = False
            self._resize_edge = None

            # 保存窗口位置和大小
            self._save_window_geometry()

    def _get_resize_edge(self, pos: QPoint) -> Optional[str]:
        """
        检测鼠标是否在窗口边缘

        Args:
            pos: 鼠标位置

        Returns:
            Optional[str]: 边缘类型（'left', 'right', 'top', 'bottom', 'topleft', 'topright', 'bottomleft', 'bottomright'）
        """
        w = self.width()
        h = self.height()

        left = pos.x() < _EDGE_THRESHOLD
        right = pos.x() > w - _EDGE_THRESHOLD
        top = pos.y() < _EDGE_THRESHOLD
        bottom = pos.y() > h - _EDGE_THRESHOLD

        if top and left:
            return "topleft"
        elif top and right:
            return "topright"
        elif bottom and left:
            return "bottomleft"
        elif bottom and right:
            return "bottomright"
        elif left:
            return "left"
        elif right:
            return "right"
        elif top:
            return "top"
        elif bottom:
            return "bottom"

        return None

    def _get_cursor_shape(self, edge: str) -> Qt.CursorShape:
        """
        获取边缘对应的鼠标光标

        Args:
            edge: 边缘类型

        Returns:
            Qt.CursorShape: 鼠标光标形状
        """
        cursor_map = {
            "left": Qt.SizeHorCursor,
            "right": Qt.SizeHorCursor,
            "top": Qt.SizeVerCursor,
            "bottom": Qt.SizeVerCursor,
            "topleft": Qt.SizeFDiagCursor,
            "topright": Qt.SizeBDiagCursor,
            "bottomleft": Qt.SizeBDiagCursor,
            "bottomright": Qt.SizeFDiagCursor
        }
        return cursor_map.get(edge, Qt.ArrowCursor)

    def _perform_resize(self, global_pos: QPoint):
        """
        执行调整大小操作

        Args:
            global_pos: 鼠标全局位置
        """
        if not self._resize_start_geometry:
            return

        start_geo = self._resize_start_geometry
        start_mouse = self._drag_start_position
        delta = global_pos - start_mouse

        new_x = start_geo.x()
        new_y = start_geo.y()
        new_w = start_geo.width()
        new_h = start_geo.height()

        # 根据边缘调整
        if "left" in self._resize_edge:
            new_x = start_geo.x() + delta.x()
            new_w = start_geo.width() - delta.x()

        if "right" in self._resize_edge:
            new_w = start_geo.width() + delta.x()

        if "top" in self._resize_edge:
            new_y = start_geo.y() + delta.y()
            new_h = start_geo.height() - delta.y()

        if "bottom" in self._resize_edge:
            new_h = start_geo.height() + delta.y()

        # 限制最小尺寸
        min_w = 200
        min_h = 100

        if new_w < min_w:
            new_w = min_w
            if "left" in self._resize_edge:
                new_x = start_geo.right() - min_w

        if new_h < min_h:
            new_h = min_h
            if "top" in self._resize_edge:
                new_y = start_geo.bottom() - min_h

        # 设置新几何属性
        self.setGeometry(new_x, new_y, new_w, new_h)

        # 更新按钮容器位置
        self._update_button_container_position()

    def paintEvent(self, event):
        """
        绘制事件

        Args:
            event: 绘制事件
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 只有当背景不透明度大于0时才绘制背景
        if self._bg_opacity > 0:
            # 绘制半透明背景
            brush = QBrush(self._bg_color)
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

    def _save_window_geometry(self):
        """保存窗口位置和大小到配置"""
        config = self.config_manager.load_config()

        if "display" not in config:
            config["display"] = {}

        config["display"]["window_pos_x"] = self.x()
        config["display"]["window_pos_y"] = self.y()
        config["display"]["window_width"] = self.width()
        config["display"]["window_height"] = self.height()

        self.config_manager.save_config(config)

    def _restore_window_geometry(self):
        """从配置恢复窗口位置和大小"""
        config = self.config_manager.load_config()
        display_config = config.get("display", {})

        x = display_config.get("window_pos_x")
        y = display_config.get("window_pos_y")
        w = display_config.get("window_width", _DEFAULT_WIDTH)
        h = display_config.get("window_height", _DEFAULT_HEIGHT)

        # 设置大小
        self.resize(w, h)

        # 如果有保存的位置，设置位置
        if x is not None and y is not None:
            self.move(x, y)

        # 更新按钮容器位置
        self._update_button_container_position()

    def closeEvent(self, event):
        """
        关闭事件

        Args:
            event: 关闭事件
        """
        # 保存窗口位置和大小
        self._save_window_geometry()
        super().closeEvent(event)
