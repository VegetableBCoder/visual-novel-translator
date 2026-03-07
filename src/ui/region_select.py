"""
区域选择界面

软件启动后的第三个界面，用于在目标窗口截图上框选需要 OCR 识别的文字区域：
- 显示目标窗口的截图
- 通过鼠标拖拽框选文字区域
- 支持重新截屏
- 保存选区相对位置信息
"""
import uuid

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage

from src.controller.config_interface import IConfigManager
from src.core.window_capture import capture_window


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
        self.min_selection_size = 30  # 选区最小尺寸（像素）

        # 交互状态
        self.mode = 'none'  # 当前操作模式：none, creating, moving, resizing
        self.resize_direction = None  # 拉伸方向
        self.drag_start_pos = None  # 拖拽起始点
        self.original_rect = None  # 操作前的选区备份

        # 控制点相关
        self.handle_size = 6  # 控制点尺寸（像素）
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
        self.original_pixmap = pixmap
        self.original_size = (pixmap.width(), pixmap.height())
        self.scaled_pixmap = None  # 清除缩放缓存
        self._update_scale()  # 计算缩放
        self._create_default_selection()  # 创建默认选区
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

    def get_selection_ratio(self):
        """
        获取当前选区的相对比例坐标 (0-1)

        Returns:
            dict: {"left": float, "top": float, "right": float, "bottom": float}
        """
        # TODO: 实现坐标转换逻辑
        if self.selection_rect is None:
            return None

        return {
            "left": 0.25,
            "top": 0.70,
            "right": 0.75,
            "bottom": 0.85
        }

    def _emit_selection_changed(self):
        """发射选区变化信号"""
        self.selectionChanged.emit()

    # TODO: 以下方法需要实现选区绘制、坐标转换、鼠标事件处理等

    def paintEvent(self, event):
        """绘制事件"""
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
        from PyQt5.QtCore import QRectF, QPointF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. 绘制背景
        painter.fillRect(self.rect(), QColor(45, 45, 45))

        # 2. 绘制图片
        if self.scaled_pixmap and self.pixmap_rect:
            painter.drawPixmap(self.pixmap_rect.toRect(), self.scaled_pixmap)

            # TODO: 3. 绘制遮罩层（半透明黑色）
            # TODO: 4. 绘制选区边框（2px 亮蓝色）
            # TODO: 5. 绘制 8 个控制点

        painter.end()

    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self._update_scale()
            # TODO: 重新计算选区位置

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        # TODO: 实现选区创建/移动/拉伸状态切换
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        # TODO: 实现选区创建/移动/拉伸逻辑
        # TODO: 更新光标形状
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        # TODO: 实现操作完成、状态重置
        super().mouseReleaseEvent(event)


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
        # TODO: 从 region_widget 获取选区信息并更新标签
        ratio = self.region_widget.get_selection_ratio()

        if ratio:
            self.selection_position_label.setText(
                f"相对位置: 左:{ratio['left']:.1%} "
                f"上:{ratio['top']:.1%} "
                f"右:{ratio['right']:.1%} "
                f"下:{ratio['bottom']:.1%}"
            )
            # TODO: 计算实际像素尺寸
            self.selection_size_label.setText("选区尺寸: - x - px")
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
        self.config_manager.save_config(self.config_manager.load_config())

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
