"""
运行参数配置界面

软件启动后的第四个界面，也是最后一个配置界面。用于配置：
- OCR识别参数（截图间隔、图片相似度阈值）
- 文本处理参数（文本去重阈值）
- 翻译结果展示参数（字体、大小、颜色、透明度）

点击"开始翻译"后，所有配置被保存，后台线程启动，界面进入运行中状态（参数锁定）。
点击"暂停翻译"可暂停后台任务并解锁界面。
"""

import logging
from enum import Enum
from typing import Optional

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QSpinBox, QSlider, QComboBox,
                             QPushButton, QMessageBox, QColorDialog,
                             QButtonGroup, QRadioButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtGui import QFontDatabase

logger = logging.getLogger(__name__)

from src.controller.config_interface import IConfigManager


class RunState(Enum):
    """运行状态枚举"""
    IDLE = "idle"       # 空闲状态
    RUNNING = "running" # 运行中
    PAUSED = "paused"   # 暂停状态


class RunConfigWidget(QWidget):
    """运行参数配置界面"""

    # 定义信号，用于与主窗口通信
    back_signal = pyqtSignal()        # 用户点击上一步
    cancel_signal = pyqtSignal()       # 用户点击取消
    start_signal = pyqtSignal()        # 用户点击开始翻译（通知主窗口启动调度器）
    pause_signal = pyqtSignal()       # 用户点击暂停翻译（通知主窗口暂停调度器）
    resume_signal = pyqtSignal()       # 用户点击恢复翻译（通知主窗口恢复调度器）

    def __init__(self,
                 config_manager: IConfigManager,
                 scheduler: Optional[object] = None,
                 floating_window: Optional[object] = None,
                 parent=None):
        """
        初始化运行参数配置界面

        Args:
            config_manager: 配置管理器实例
            scheduler: 任务调度器实例（可选，用于后续集成）
            floating_window: 悬浮窗实例（可选，用于后续集成）
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.scheduler = scheduler  # 预留：任务调度器
        self.floating_window = floating_window  # 预留：悬浮窗

        # 运行状态
        self._current_state = RunState.IDLE

        # 预留：调度控制相关属性（为后续实现做兼容）
        self._capture_interval_ms = 1000  # 当前截图间隔
        self._is_capture_running = False   # 截图线程运行标志

        self._init_ui()
        self._load_config()
        self._connect_signals()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("运行参数配置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 添加引导文案
        guide_label = QLabel("请配置OCR识别和翻译结果的显示参数")
        guide_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(guide_label)

        # 添加各配置组
        layout.addWidget(self._create_ocr_group())
        layout.addWidget(self._create_text_processing_group())
        layout.addWidget(self._create_display_group())

        layout.addStretch()

        # 状态标签
        self.status_label = QLabel("状态: 等待启动")
        self.status_label.setStyleSheet("color: #808080; margin: 5px;")
        layout.addWidget(self.status_label)

        # 底部按钮
        button_layout = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.back_btn.setMinimumWidth(100)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(100)
        self.action_btn = QPushButton("开始翻译")
        self.action_btn.setMinimumWidth(100)
        self.action_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")

        button_layout.addWidget(self.back_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.action_btn)
        layout.addLayout(button_layout)

    def _create_ocr_group(self) -> QGroupBox:
        """创建OCR参数配置组"""
        group = QGroupBox("OCR参数设置")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # OCR截图间隔
        interval_layout = self._create_slider_spinbox_pair(
            label="OCR截图间隔",
            min_val=1000,
            max_val=10000,
            default_val=1000,
            step=100,
            suffix=" ms",
            tooltip="数值越小识别越频繁，性能占用越高"
        )
        self.interval_spinbox, self.interval_slider = interval_layout['controls']
        interval_container = interval_layout['container']
        layout.addWidget(interval_container)

        # 图片相似度阈值
        image_threshold_layout = self._create_slider_spinbox_pair(
            label="图片相似度阈值",
            min_val=0,
            max_val=100,
            default_val=10,
            step=1,
            suffix="",
            tooltip="0表示每次都识别，100表示只有完全不同的图片才识别。数值越高，图片变化越小越容易触发OCR",
            has_description=True,
            description_text="数值越高，图片变化越小越容易触发OCR"
        )
        self.image_threshold_spinbox, self.image_threshold_slider = image_threshold_layout['controls']
        image_threshold_container = image_threshold_layout['container']
        layout.addWidget(image_threshold_container)

        group.setLayout(layout)
        return group

    def _create_text_processing_group(self) -> QGroupBox:
        """创建文本处理参数配置组"""
        group = QGroupBox("文本处理设置")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # 文本去重阈值
        text_threshold_layout = self._create_slider_spinbox_pair(
            label="文本去重阈值",
            min_val=0,
            max_val=100,
            default_val=75,
            step=1,
            suffix="",
            tooltip="0表示每次都翻译，100表示只有完全不同的文本才翻译。数值越高，文本变化越小越容易触发翻译",
            has_description=True,
            description_text="数值越高，文本变化越小越容易触发翻译"
        )
        self.text_threshold_spinbox, self.text_threshold_slider = text_threshold_layout['controls']
        text_threshold_container = text_threshold_layout['container']
        layout.addWidget(text_threshold_container)

        group.setLayout(layout)
        return group

    def _create_display_group(self) -> QGroupBox:
        """创建翻译结果显示设置组"""
        group = QGroupBox("翻译结果显示设置")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # 字体选择
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("译文字体："))
        font_layout.addSpacing(10)

        # 获取所有可用的字体
        font_db = QFontDatabase()
        all_fonts = font_db.families()

        self.font_combo = QComboBox()
        self.font_combo.setMinimumWidth(200)
        self.font_combo.addItems(all_fonts)

        # 尝试选中默认字体
        default_font = "微软雅黑"
        if default_font in all_fonts:
            self.font_combo.setCurrentText(default_font)
        elif "SimHei" in all_fonts:
            self.font_combo.setCurrentText("SimHei")  # 黑体

        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        layout.addLayout(font_layout)

        # 字体大小
        font_size_layout = self._create_slider_spinbox_pair(
            label="字体大小",
            min_val=8,
            max_val=72,
            default_val=16,
            step=1,
            suffix=" pt"
        )
        self.font_size_spinbox, self.font_size_slider = font_size_layout['controls']
        font_size_container = font_size_layout['container']
        layout.addWidget(font_size_container)

        # 字体颜色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("字体颜色："))
        color_layout.addSpacing(10)

        self.color_btn = QPushButton()
        self.color_btn.setMinimumWidth(150)
        self.color_btn.setMaximumHeight(30)
        self.current_color = QColor(255, 255, 255)  # 默认白色
        self._update_color_button()

        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        # 背景透明度
        opacity_layout = self._create_slider_spinbox_pair(
            label="窗口透明度",
            min_val=0,
            max_val=100,
            default_val=40,
            step=1,
            suffix=" %",
            has_description=True,
            description_text="数值越高，悬浮窗背景越不透明"
        )
        self.opacity_spinbox, self.opacity_slider = opacity_layout['controls']
        opacity_container = opacity_layout['container']
        layout.addWidget(opacity_container)

        group.setLayout(layout)
        return group

    def _create_slider_spinbox_pair(self,
                                    label: str,
                                    min_val: int,
                                    max_val: int,
                                    default_val: int,
                                    step: int,
                                    suffix: str = "",
                                    tooltip: str = "",
                                    has_description: bool = False,
                                    description_text: str = "") -> dict:
        """
        创建滑块和SpinBox的组合控件

        Args:
            label: 标签文字
            min_val: 最小值
            max_val: 最大值
            default_val: 默认值
            step: 步进值
            suffix: 单位后缀
            tooltip: 工具提示
            has_description: 是否有描述文字
            description_text: 描述文字

        Returns:
            dict: 包含 container 和 controls 的字典
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 第一行：标签 + SpinBox + Slider
        row_layout = QHBoxLayout()

        row_layout.addWidget(QLabel(f"{label}："))
        row_layout.addSpacing(10)

        spinbox = QSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default_val)
        spinbox.setSingleStep(step)
        spinbox.setSuffix(suffix)
        spinbox.setMinimumWidth(80)
        row_layout.addWidget(spinbox)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setSingleStep(step)
        slider.setPageStep(step)  # 确保点击进度条时也按 step 的整数倍变动
        row_layout.addWidget(slider)

        row_layout.addStretch()
        layout.addLayout(row_layout)

        # 工具提示
        if tooltip:
            widget_for_tooltip = row_layout.itemAt(0).widget()  # 标签
            widget_for_tooltip.setToolTip(tooltip)

        # 第二行：描述文字（可选）
        if has_description:
            desc_label = QLabel(description_text)
            desc_label.setStyleSheet("color: #808080; font-size: 11px;")
            layout.addWidget(desc_label)

        return {
            'container': container,
            'controls': (spinbox, slider)
        }

    def _connect_signals(self):
        """连接信号"""
        # OCR参数滑块与SpinBox联动
        self._connect_slider_spinbox(self.interval_spinbox, self.interval_slider)
        self._connect_slider_spinbox(self.image_threshold_spinbox, self.image_threshold_slider)

        # 文本处理参数滑块与SpinBox联动
        self._connect_slider_spinbox(self.text_threshold_spinbox, self.text_threshold_slider)

        # 显示参数滑块与SpinBox联动
        self._connect_slider_spinbox(self.font_size_spinbox, self.font_size_slider)
        self._connect_slider_spinbox(self.opacity_spinbox, self.opacity_slider)

        # 颜色按钮
        self.color_btn.clicked.connect(self._on_color_button_clicked)

        # 底部按钮
        self.back_btn.clicked.connect(self.back_signal.emit)
        self.cancel_btn.clicked.connect(self.cancel_signal.emit)
        self.action_btn.clicked.connect(self._on_action_button_clicked)

    def _connect_slider_spinbox(self, spinbox: QSpinBox, slider: QSlider):
        """
        连接滑块和SpinBox，实现双向绑定

        Args:
            spinbox: QSpinBox 控件
            slider: QSlider 控件
        """
        # 获取步进值（spinbox 和 slider 应该使用相同的步进值）
        step = spinbox.singleStep()

        # SpinBox值变化时更新滑块（确保按步进值整数倍）
        spinbox.valueChanged.connect(
            lambda val: slider.setValue(val if val % step == 0 else (val // step) * step)
        )

        # 滑块值变化时更新SpinBox（确保按步进值整数倍）
        slider.valueChanged.connect(
            lambda val: spinbox.setValue(val if val % step == 0 else (val // step) * step)
        )

    def _load_config(self):
        """从配置管理器加载配置到界面"""
        config = self.config_manager.load_config()

        # 加载OCR参数
        self.interval_spinbox.setValue(config.get("ocr.interval_ms", 1000))
        self.image_threshold_spinbox.setValue(config.get("ocr.image_threshold", 10))

        # 加载文本处理参数
        self.text_threshold_spinbox.setValue(config.get("ocr.text_threshold", 75))

        # 加载显示参数
        font_family = config.get("display.font_family", "微软雅黑")
        if self.font_combo.findText(font_family) >= 0:
            self.font_combo.setCurrentText(font_family)

        self.font_size_spinbox.setValue(config.get("display.font_size", 16))

        color_hex = config.get("display.font_color", "#FFFFFF")
        self.current_color = QColor(color_hex)
        self._update_color_button()

        self.opacity_spinbox.setValue(config.get("display.bg_opacity", 40))

    def _save_config(self):
        """从界面保存配置到配置管理器"""
        # OCR参数
        interval_ms = self.interval_spinbox.value()
        image_threshold = self.image_threshold_spinbox.value()
        self.config_manager.set("ocr.interval_ms", interval_ms)
        self.config_manager.set("ocr.image_threshold", image_threshold)

        # 文本处理参数
        text_threshold = self.text_threshold_spinbox.value()
        self.config_manager.set("ocr.text_threshold", text_threshold)

        # 显示参数
        font_family = self.font_combo.currentText()
        font_size = self.font_size_spinbox.value()
        font_color = self.current_color.name()
        bg_opacity = self.opacity_spinbox.value()

        self.config_manager.set("display.font_family", font_family)
        self.config_manager.set("display.font_size", font_size)
        self.config_manager.set("display.font_color", font_color)
        self.config_manager.set("display.bg_opacity", bg_opacity)

        # 持久化到文件
        config_data = self.config_manager.load_config()
        self.config_manager.save_config(config_data)

        # 预留：更新截图间隔（为后续调度器做兼容）
        self._capture_interval_ms = interval_ms

        # 输出完整配置到日志（JSON 格式）
        logger.info("=" * 60)
        logger.info("配置已保存")
        logger.info("=" * 60)
        import json
        logger.info(json.dumps(config_data, ensure_ascii=False, indent=2))
        logger.info("=" * 60)

    def _on_color_button_clicked(self):
        """颜色按钮点击处理"""
        color = QColorDialog.getColor(
            self.current_color,
            self,
            "选择字体颜色"
        )

        if color.isValid():
            self.current_color = color
            self._update_color_button()

    def _update_color_button(self):
        """更新颜色按钮的显示"""
        color_name = self.current_color.name().upper()
        self.color_btn.setText(f"■ {color_name}")
        self.color_btn.setStyleSheet(f"background-color: {color_name}; color: {'white' if self.current_color.lightness() < 128 else 'black'};")

    def _on_action_button_clicked(self):
        """开始翻译/暂停翻译按钮点击处理"""
        if self._current_state == RunState.IDLE:
            # 从空闲状态开始翻译
            self._start_translation()
        elif self._current_state == RunState.RUNNING:
            # 从运行状态暂停翻译
            self._pause_translation()
        elif self._current_state == RunState.PAUSED:
            # 从暂停状态恢复翻译
            self._resume_translation()

    def _start_translation(self):
        """开始翻译"""
        logger.info("开始翻译...")

        # 先保存配置
        self._save_config()

        # 预留：启动调度器
        if self.scheduler is not None:
            try:
                # 这里假设调度器有 start() 方法
                # 后续实现时，调度器需要实现启动截图线程和OCR/翻译线程
                if hasattr(self.scheduler, 'start'):
                    self.scheduler.start()
                    logger.info("调度器已启动")
            except Exception as e:
                logger.error(f"启动翻译服务失败：{str(e)}")
                QMessageBox.warning(self, "启动失败", f"启动翻译服务失败：{str(e)}")
                return
        else:
            # 调度器尚未实现，打印日志作为占位
            logger.info(f"调度器尚未实现，截图间隔: {self._capture_interval_ms}ms")

        # 预留：创建/显示悬浮窗
        if self.floating_window is not None:
            try:
                self.floating_window.show()
                logger.info("悬浮窗已显示")
            except Exception as e:
                logger.error(f"显示悬浮窗失败：{e}")
        else:
            logger.info("悬浮窗尚未实现")

        # 发送信号通知主窗口（主窗口可能需要执行其他操作）
        self.start_signal.emit()

        # 更新状态为运行中
        self._update_state(RunState.RUNNING)

    def _pause_translation(self):
        """暂停翻译"""
        logger.info("暂停翻译...")

        # 预留：暂停调度器
        if self.scheduler is not None:
            try:
                # 这里假设调度器有 pause() 方法
                # 后续实现时，调度器需要实现暂停截图循环和OCR/翻译处理
                if hasattr(self.scheduler, 'pause'):
                    self.scheduler.pause()
                    logger.info("调度器已暂停")
            except Exception as e:
                logger.error(f"暂停翻译服务失败：{str(e)}")
                QMessageBox.warning(self, "暂停失败", f"暂停翻译服务失败：{str(e)}")
                return
        else:
            # 调度器尚未实现
            logger.info("调度器尚未实现，暂停翻译")

        # 发送信号通知主窗口
        self.pause_signal.emit()

        # 更新状态为暂停
        self._update_state(RunState.PAUSED)

    def _resume_translation(self):
        """恢复翻译"""
        logger.info("恢复翻译...")

        # 预留：恢复调度器
        if self.scheduler is not None:
            try:
                # 这里假设调度器有 resume() 方法
                # 后续实现时，调度器需要实现恢复截图循环和OCR/翻译处理
                if hasattr(self.scheduler, 'resume'):
                    self.scheduler.resume()
                    logger.info("调度器已恢复")
            except Exception as e:
                logger.error(f"恢复翻译服务失败：{str(e)}")
                QMessageBox.warning(self, "恢复失败", f"恢复翻译服务失败：{str(e)}")
                return
        else:
            # 调度器尚未实现
            logger.info("调度器尚未实现，恢复翻译")

        # 发送信号通知主窗口
        self.resume_signal.emit()

        # 更新状态为运行中
        self._update_state(RunState.RUNNING)

    def _update_state(self, state: RunState):
        """
        更新界面状态

        Args:
            state: 新的状态
        """
        self._current_state = state

        if state == RunState.IDLE:
            # 空闲状态：所有控件启用，按钮为"开始翻译"，上一步可点击
            self._set_controls_enabled(True)
            self.action_btn.setText("开始翻译")
            self.action_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")
            self.back_btn.setEnabled(True)
            self.status_label.setText("状态: 等待启动")
            self.status_label.setStyleSheet("color: #808080;")

            # 预留：更新截图运行标志
            self._is_capture_running = False

        elif state == RunState.RUNNING:
            # 运行中状态：所有控件禁用，按钮为"暂停翻译"，上一步禁用
            self._set_controls_enabled(False)
            self.action_btn.setText("暂停翻译")
            self.action_btn.setStyleSheet("background-color: #E6A23C; color: white; font-weight: bold;")
            self.back_btn.setEnabled(False)
            self.status_label.setText('状态: <font color="green">●</font> 翻译运行中，参数已锁定')
            self.status_label.setStyleSheet("")

            # 预留：更新截图运行标志
            self._is_capture_running = True

        elif state == RunState.PAUSED:
            # 暂停状态：所有控件启用，按钮为"开始翻译"，上一步可点击
            self._set_controls_enabled(True)
            self.action_btn.setText("开始翻译")
            self.action_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")
            self.back_btn.setEnabled(True)
            self.status_label.setText("状态: 翻译已暂停")
            self.status_label.setStyleSheet("color: #E6A23C;")

            # 预留：更新截图运行标志
            self._is_capture_running = False

    def _set_controls_enabled(self, enabled: bool):
        """
        设置所有配置控件的启用/禁用状态

        Args:
            enabled: 是否启用
        """
        # OCR参数
        self.interval_spinbox.setEnabled(enabled)
        self.interval_slider.setEnabled(enabled)
        self.image_threshold_spinbox.setEnabled(enabled)
        self.image_threshold_slider.setEnabled(enabled)

        # 文本处理参数
        self.text_threshold_spinbox.setEnabled(enabled)
        self.text_threshold_slider.setEnabled(enabled)

        # 显示参数
        self.font_combo.setEnabled(enabled)
        self.font_size_spinbox.setEnabled(enabled)
        self.font_size_slider.setEnabled(enabled)
        self.color_btn.setEnabled(enabled)
        self.opacity_spinbox.setEnabled(enabled)
        self.opacity_slider.setEnabled(enabled)

    # 预留：为后续调度器提供的公共方法

    def get_capture_interval(self) -> int:
        """
        获取当前配置的截图间隔（毫秒）

        Returns:
            int: 截图间隔，单位毫秒
        """
        return self.interval_spinbox.value()

    def is_capture_running(self) -> bool:
        """
        检查截图是否正在运行

        Returns:
            bool: 是否正在运行
        """
        return self._is_capture_running

    def set_scheduler(self, scheduler):
        """
        设置调度器实例（用于后续集成）

        Args:
            scheduler: 任务调度器实例
        """
        self.scheduler = scheduler
        logger.info(f"调度器已设置: {type(scheduler).__name__}")

    def set_floating_window(self, floating_window):
        """
        设置悬浮窗实例（（用于后续集成）

        Args:
            floating_window: 悬浮窗实例
        """
        self.floating_window = floating_window
        logger.info(f"悬浮窗已设置: {type(floating_window).__name__}")

    def force_pause(self):
        """
        强制暂停翻译（由外部调用，如窗口关闭时）

        这个方法用于从外部强制暂停翻译，而不是通过UI按钮触发
        """
        if self._current_state == RunState.RUNNING:
            self._pause_translation()

    def force_stop(self):
        """
        强制停止翻译（由外部调用，如程序退出时）

        这个方法用于从外部强制停止翻译，并重置状态为空闲
        """
        logger.info("强制停止翻译...")

        if self._current_state == RunState.RUNNING or self._current_state == RunState.PAUSED:
            # 预留：停止调度器
            if self.scheduler is not None:
                try:
                    if hasattr(self.scheduler, 'stop'):
                        self.scheduler.stop()
                        logger.info("调度器已停止")
                except Exception as e:
                    logger.error(f"停止调度器失败：{e}")

            # 隐藏悬浮窗
            if self.floating_window is not None:
                try:
                    self.floating_window.hide()
                except Exception:
                    pass

            # 重置状态
            self._update_state(RunState.IDLE)


# 独立运行测试
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from src.controller.config_helper import ConfigHelper

    app = QApplication(sys.argv)

    # 创建配置管理器
    config_manager = ConfigHelper()

    # 创建运行参数配置界面
    widget = RunConfigWidget(config_manager)

    # 显示界面
    widget.show()

    sys.exit(app.exec_())
