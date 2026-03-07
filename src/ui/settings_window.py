"""
翻译设置界面

软件启动后的第一个界面，用于配置翻译参数：
- 源语言选择（日语/英语）
- 翻译引擎选择（阿里云/Google）
- API 密钥配置
- 密钥验证功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                           QLabel, QComboBox, QRadioButton,
                           QPushButton, QLineEdit, QStackedWidget,
                           QMessageBox, QFrame, QButtonGroup)
from PyQt5.QtCore import Qt, pyqtSignal

from src.controller.config_interface import IConfigManager


class TranslationSettingsWidget(QWidget):
    """翻译设置界面"""

    # 定义信号，用于与主窗口通信
    next_signal = pyqtSignal()        # 用户点击下一步
    cancel_signal = pyqtSignal()       # 用户点击取消

    def __init__(self, config_manager: IConfigManager, parent=None):
        """
        初始化翻译设置界面

        Args:
            config_manager: 配置管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.config_manager = config_manager

        self._init_ui()
        self._load_config()
        self._connect_signals()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("翻译设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 添加各组件
        layout.addWidget(self._create_language_group())
        layout.addWidget(self._create_engine_group())
        layout.addStretch()

        # 底部按钮
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(100)
        self.next_btn = QPushButton("下一步")
        self.next_btn.setMinimumWidth(100)
        self.next_btn.setStyleSheet("background-color: #4A90E2; color: white; font-weight: bold;")

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.next_btn)
        layout.addLayout(button_layout)

    def _create_language_group(self) -> QGroupBox:
        """创建语言设置组"""
        group = QGroupBox("语言设置")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # 源语言
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("源语言："))
        source_layout.addSpacing(10)
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["日语", "英语"])
        self.source_lang_combo.setMinimumWidth(150)
        source_layout.addWidget(self.source_lang_combo)
        source_layout.addStretch()
        layout.addLayout(source_layout)

        # 目标语言
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("目标语言："))
        target_layout.addSpacing(10)
        target_label = QLabel("简体中文")
        target_label.setStyleSheet("color: #808080;")
        target_layout.addWidget(target_label)
        target_layout.addStretch()
        layout.addLayout(target_layout)

        group.setLayout(layout)
        return group

    def _create_engine_group(self) -> QGroupBox:
        """创建翻译引擎配置组"""
        group = QGroupBox("翻译引擎")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # 引擎选择
        self.engine_group = QButtonGroup(self)
        self.alibaba_radio = QRadioButton("阿里云翻译")
        self.google_radio = QRadioButton("Google翻译")
        self.engine_group.addButton(self.alibaba_radio, 0)
        self.engine_group.addButton(self.google_radio, 1)
        self.alibaba_radio.setChecked(True)  # 默认选中阿里云

        engine_layout = QHBoxLayout()
        engine_layout.addWidget(self.alibaba_radio)
        engine_layout.addSpacing(30)
        engine_layout.addWidget(self.google_radio)
        engine_layout.addStretch()
        layout.addLayout(engine_layout)

        # 配置面板堆叠
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self._create_alibaba_panel())
        self.stacked_widget.addWidget(self._create_google_panel())
        layout.addWidget(self.stacked_widget)

        group.setLayout(layout)
        return group

    def _create_alibaba_panel(self) -> QWidget:
        """创建阿里云配置面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # AccessKey ID
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("AccessKey ID："))
        id_layout.addSpacing(10)
        self.alibaba_id_edit = QLineEdit()
        self.alibaba_id_edit.setPlaceholderText("请输入 AccessKey ID")
        id_layout.addWidget(self.alibaba_id_edit)
        layout.addLayout(id_layout)

        # AccessKey Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(QLabel("AccessKey Secret："))
        secret_layout.addSpacing(10)
        self.alibaba_secret_edit = QLineEdit()
        self.alibaba_secret_edit.setPlaceholderText("请输入 AccessKey Secret")
        self.alibaba_secret_edit.setEchoMode(QLineEdit.Password)
        secret_layout.addWidget(self.alibaba_secret_edit)
        layout.addLayout(secret_layout)

        # 验证按钮和帮助
        btn_layout = QHBoxLayout()
        self.alibaba_verify_btn = QPushButton("验证")
        self.alibaba_verify_btn.setMinimumWidth(80)
        help_label = QLabel("ⓘ")
        help_label.setToolTip("AccessKey可在阿里云控制台-访问管理页面获取")
        help_label.setStyleSheet("color: #4A90E2; cursor: help;")
        help_label.setFixedWidth(20)
        btn_layout.addWidget(self.alibaba_verify_btn)
        btn_layout.addSpacing(5)
        btn_layout.addWidget(help_label)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def _create_google_panel(self) -> QWidget:
        """创建 Google 配置面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # API Key
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key："))
        key_layout.addSpacing(10)
        self.google_key_edit = QLineEdit()
        self.google_key_edit.setPlaceholderText("请输入 API Key")
        self.google_key_edit.setEchoMode(QLineEdit.Password)
        key_layout.addWidget(self.google_key_edit)
        layout.addLayout(key_layout)

        # 验证按钮和帮助
        btn_layout = QHBoxLayout()
        self.google_verify_btn = QPushButton("验证")
        self.google_verify_btn.setMinimumWidth(80)
        help_label = QLabel("ⓘ")
        help_label.setToolTip("API Key可在Google Cloud控制台-凭据页面获取\n国内使用需自行解决网络问题")
        help_label.setStyleSheet("color: #4A90E2; cursor: help;")
        help_label.setFixedWidth(20)
        btn_layout.addWidget(self.google_verify_btn)
        btn_layout.addSpacing(5)
        btn_layout.addWidget(help_label)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def _connect_signals(self):
        """连接信号"""
        self.engine_group.buttonClicked.connect(self._on_engine_changed)
        self.alibaba_verify_btn.clicked.connect(self._on_verify_alibaba)
        self.google_verify_btn.clicked.connect(self._on_verify_google)
        self.cancel_btn.clicked.connect(self.cancel_signal.emit)
        self.next_btn.clicked.connect(self._on_next)

    def _load_config(self):
        """加载配置到界面"""
        config = self.config_manager.load_config()

        # 加载源语言
        source = config.get("language.source", "ja")
        self.source_lang_combo.setCurrentIndex(0 if source == "ja" else 1)

        # 加载引擎选择
        engine = config.get("translation.engine", "alibaba")
        if engine == "google":
            self.google_radio.setChecked(True)
        else:
            self.alibaba_radio.setChecked(True)

        # 加载密钥
        self.alibaba_id_edit.setText(config.get("translation.alibaba.access_key_id", ""))
        self.alibaba_secret_edit.setText(config.get("translation.alibaba.access_key_secret", ""))
        self.google_key_edit.setText(config.get("translation.google.api_key", ""))

    def _save_config(self):
        """保存界面配置"""
        # 保存源语言
        source_code = "ja" if self.source_lang_combo.currentIndex() == 0 else "en"
        self.config_manager.set("language.source", source_code)

        # 保存引擎选择
        engine = "google" if self.google_radio.isChecked() else "alibaba"
        self.config_manager.set("translation.engine", engine)

        # 保存密钥
        self.config_manager.set("translation.alibaba.access_key_id",
                            self.alibaba_id_edit.text())
        self.config_manager.set("translation.alibaba.access_key_secret",
                            self.alibaba_secret_edit.text())
        self.config_manager.set("translation.google.api_key",
                            self.google_key_edit.text())

        # 持久化（TODO: 暂时只保存到内存）
        self.config_manager.save_config(self.config_manager.load_config())

    def _on_engine_changed(self, button):
        """引擎切换处理"""
        if button == self.alibaba_radio:
            self.stacked_widget.setCurrentIndex(0)
        elif button == self.google_radio:
            self.stacked_widget.setCurrentIndex(1)

    def _on_verify_alibaba(self):
        """验证阿里云密钥"""
        self.alibaba_verify_btn.setEnabled(False)
        self.alibaba_verify_btn.setText("验证中...")

        if self._validate_alibaba_key_sync(
            self.alibaba_id_edit.text().strip(),
            self.alibaba_secret_edit.text().strip()
        ):
            QMessageBox.information(self, "验证成功", "阿里云密钥验证成功！")
        else:
            QMessageBox.warning(self, "验证失败", "验证失败，请检查密钥或网络连接。")

        self.alibaba_verify_btn.setEnabled(True)
        self.alibaba_verify_btn.setText("验证")

    def _on_verify_google(self):
        """验证 Google 密钥"""
        self.google_verify_btn.setEnabled(False)
        self.google_verify_btn.setText("验证中...")

        if self._validate_google_key_sync(
            self.google_key_edit.text().strip()
        ):
            QMessageBox.information(self, "验证成功", "Google API Key 验证成功！")
        else:
            QMessageBox.warning(self, "验证失败", "验证失败，请检查密钥或网络连接。")

        self.google_verify_btn.setEnabled(True)
        self.google_verify_btn.setText("验证")

    def _validate_alibaba_key_sync(self, key_id: str, key_secret: str) -> bool:
        """
        同步验证阿里云密钥

        TODO: 实现真实的阿里云 API 验证

        Args:
            key_id: AccessKey ID
            key_secret: AccessKey Secret

        Returns:
            bool: 验证是否成功
        """
        if not key_id or not key_secret:
            return False

        try:
            import time
            # TODO: 实现真实的阿里云 API 验证
            time.sleep(1)  # 模拟网络延迟
            return True  # 暂时返回 True 用于测试流程
        except Exception:
            return False

    def _validate_google_key_sync(self, api_key: str) -> bool:
        """
        同步验证 Google 密钥

        TODO: 实现真实的 Google API 验证

        Args:
            api_key: Google API Key

        Returns:
            bool: 验证是否成功
        """
        if not api_key:
            return False

        try:
            import time
            # TODO: 实现真实的 Google API 验证
            time.sleep(1)  # 模拟网络延迟
            return True  # 暂时返回 True 用于测试流程
        except Exception:
            return False

    def _on_next(self):
        """下一步处理"""
        self._save_config()
        self.next_signal.emit()


# 独立运行测试
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from src.controller.config_helper import ConfigHelper

    app = QApplication(sys.argv)

    # 创建配置管理器
    config_manager = ConfigHelper()

    # 创建翻译设置界面
    widget = TranslationSettingsWidget(config_manager)

    # 显示界面
    widget.show()

    sys.exit(app.exec_())
