"""
窗口选择界面

软件启动后的第二个界面，用于选择目标游戏窗口：
- 显示所有可见窗口的列表
- 支持刷新窗口列表
- 从列表中选择目标窗口
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QListWidget,
                           QListWidgetItem, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

from src.controller.config_interface import IConfigManager
from src.core.window_manager import WindowManager


class WindowSelectWidget(QWidget):
    """窗口选择界面"""

    # 定义信号，用于与主窗口通信
    back_signal = pyqtSignal()        # 用户点击上一步
    next_signal = pyqtSignal()        # 用户点击下一步
    cancel_signal = pyqtSignal()       # 用户点击取消

    def __init__(self, config_manager: IConfigManager, parent=None):
        """
        初始化窗口选择界面

        Args:
            config_manager: 配置管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.window_manager = WindowManager()
        self.selected_hwnd = None
        self.window_list = []  # 缓存窗口列表

        self._init_ui()
        self._connect_signals()
        self._refresh_window_list()
        self._load_selected_window()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("窗口选择")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 添加说明标签
        info_label = QLabel("请选择要翻译的游戏窗口：\n注意：已过滤最小化的窗口，请确保游戏窗口未被最小化。")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)

        # 窗口列表
        window_group = self._create_window_list_group()
        layout.addWidget(window_group)

        # 底部按钮
        button_layout = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.back_btn.setMinimumWidth(100)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(100)
        self.next_btn = QPushButton("下一步")
        self.next_btn.setMinimumWidth(100)
        self.next_btn.setEnabled(False)  # 初始禁用
        self.next_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")

        button_layout.addWidget(self.back_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.next_btn)
        layout.addLayout(button_layout)

    def _create_window_list_group(self) -> QGroupBox:
        """创建窗口列表组"""
        group = QGroupBox("窗口列表")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 刷新按钮
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setMinimumWidth(80)
        top_layout.addWidget(self.refresh_btn)
        layout.addLayout(top_layout)

        # 窗口列表控件
        self.window_list_widget = QListWidget()
        self.window_list_widget.setMinimumHeight(250)
        self.window_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EEEEEE;
            }
            QListWidget::item:selected {
                background-color: #E6F3FF;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
        """)
        layout.addWidget(self.window_list_widget)

        # 选中信息
        self.selected_info_label = QLabel("未选择窗口")
        self.selected_info_label.setStyleSheet("color: #808080;")
        layout.addWidget(self.selected_info_label)

        group.setLayout(layout)
        return group

    def _connect_signals(self):
        """连接信号"""
        self.refresh_btn.clicked.connect(self._refresh_window_list)
        self.window_list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.window_list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.back_btn.clicked.connect(self.back_signal.emit)
        self.cancel_btn.clicked.connect(self.cancel_signal.emit)
        self.next_btn.clicked.connect(self._on_next)

    def _refresh_window_list(self):
        """刷新窗口列表"""
        # 清空列表
        self.window_list_widget.clear()
        self.window_list = []

        # 枚举窗口（同步执行）
        try:
            windows = self.window_manager.enum_windows()
            self.window_list = windows

            # 填充列表
            for window in windows:
                item = QListWidgetItem()
                # 显示格式：窗口标题
                title = window['title'] if window['title'] else "(无标题)"
                # 如果标题为空，显示类名
                if not title or title.strip() == "":
                    title = f"[{window['class_name']}]"

                item.setText(title)
                # 存储窗口句柄作为数据
                item.setData(Qt.UserRole, window['hwnd'])
                # 设置提示信息显示详细内容
                tooltip = f"标题: {window['title']}\n类名: {window['class_name']}\n句柄: {window['hwnd']}"
                if window['rect']:
                    rect = window['rect']
                    tooltip += f"\n位置: ({rect[0]}, {rect[1]}) - ({rect[2]}, {rect[3]})"
                    tooltip += f"\n大小: {rect[2] - rect[0]} x {rect[3] - rect[1]}"
                item.setToolTip(tooltip)

                self.window_list_widget.addItem(item)

            # 更新状态
            if len(windows) == 0:
                self.selected_info_label.setText("未找到可见窗口")
            else:
                self.selected_info_label.setText(f"找到 {len(windows)} 个窗口")

            # 如果之前有选中，尝试恢复选中状态
            self._restore_selection()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"枚举窗口时出错：{str(e)}")
            self.selected_info_label.setText("枚举窗口失败")

    def _restore_selection(self):
        """恢复之前的选中状态"""
        if self.selected_hwnd is None:
            return

        # 遍历列表项，查找匹配的窗口
        for i in range(self.window_list_widget.count()):
            item = self.window_list_widget.item(i)
            if item is not None:
                hwnd = item.data(Qt.UserRole)
                if hwnd == self.selected_hwnd:
                    self.window_list_widget.setCurrentItem(item)
                    break

    def _on_selection_changed(self):
        """选中项变化处理"""
        current_item = self.window_list_widget.currentItem()

        if current_item is None:
            self.selected_hwnd = None
            self.selected_info_label.setText("未选择窗口")
            self.next_btn.setEnabled(False)
        else:
            hwnd = current_item.data(Qt.UserRole)
            self.selected_hwnd = hwnd

            # 查找窗口信息
            window_info = None
            for window in self.window_list:
                if window['hwnd'] == hwnd:
                    window_info = window
                    break

            if window_info:
                title = window_info['title'] if window_info['title'] else "(无标题)"
                if not title or title.strip() == "":
                    title = f"[{window_info['class_name']}]"
                self.selected_info_label.setText(f"已选择: {title}")
            else:
                self.selected_info_label.setText("已选择窗口")

            self.next_btn.setEnabled(True)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击列表项，直接进入下一步"""
        if item is not None:
            self._on_next()

    def _load_selected_window(self):
        """从配置加载已选择的窗口"""
        # 从配置中读取窗口句柄
        hwnd = self.config_manager.get("window.hwnd")
        if hwnd is not None:
            self.selected_hwnd = hwnd

    def _on_next(self):
        """下一步处理"""
        if self.selected_hwnd is None:
            QMessageBox.warning(self, "提示", "请先选择一个窗口")
            return

        # 查找窗口信息
        window_info = None
        for window in self.window_list:
            if window['hwnd'] == self.selected_hwnd:
                window_info = window
                break

        if window_info is None:
            QMessageBox.warning(self, "错误", "选中的窗口已不存在，请重新选择")
            self._refresh_window_list()
            return

        # 保存到配置
        self.config_manager.set("window.hwnd", window_info['hwnd'])
        self.config_manager.set("window.title", window_info['title'])

        # 如果有窗口区域配置，确保存在
        if self.config_manager.get("window.region") is None:
            self.config_manager.set("window.region", {
                "left": 0.25,
                "top": 0.70,
                "right": 0.75,
                "bottom": 0.85
            })

        # 持久化（TODO: 暂时只保存到内存）
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

    # 创建窗口选择界面
    widget = WindowSelectWidget(config_manager)

    # 显示界面
    widget.show()

    sys.exit(app.exec_())
