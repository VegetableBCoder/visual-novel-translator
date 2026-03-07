"""
主窗口 - 视觉小说翻译器

管理所有界面的切换和导航，使用堆叠窗口（QStackedWidget）实现界面切换。
"""

from PyQt5.QtWidgets import (QMainWindow, QStackedWidget, QWidget,
                           QVBoxLayout, QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer
from typing import Optional

from src.controller.config_interface import IConfigManager
from src.ui.settings_window import TranslationSettingsWidget
from src.ui.window_select import WindowSelectWidget
from src.ui.region_select import RegionSelectWidgetWrapper
from src.ui.run_config import RunConfigWidget
from src.core.window_capture import WindowCapture
from src.service.image_processor import ImageProcessor
from src.service.scheduler import Scheduler
from src.service.ocr_engine_placeholder import OCREngine
from src.service.translator_placeholder import Translator
from src.service.text_deduplicator_placeholder import TextDeduplicator

# 界面索引常量
PAGE_SETTINGS = 0  # 翻译设置界面
PAGE_WINDOW_SELECT = 1  # 窗口选择界面
PAGE_REGION_SELECT = 2  # 区域选择界面
PAGE_RUN_CONFIG = 3  # 运行参数界面（未实现）


class MainWindow(QMainWindow):
    """主窗口，管理界面导航"""

    def __init__(self, config_manager: IConfigManager):
        """
        初始化主窗口

        Args:
            config_manager: 配置管理器实例
        """
        super().__init__()
        self.config_manager = config_manager

        # 调度器和悬浮窗实例
        self.scheduler = None
        self.floating_window = None

        self._init_ui()
        self._init_pages()
        self._connect_signals()

    def _init_ui(self):
        """初始化主窗口"""
        self.setWindowTitle("视觉小说翻译器")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 800)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建堆叠窗口用于界面切换
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

    def _init_pages(self):
        """初始化所有页面"""
        # 创建翻译设置界面
        self.settings_page = TranslationSettingsWidget(self.config_manager)
        self.stacked_widget.addWidget(self.settings_page)

        # 创建窗口选择界面
        self.window_select_page = WindowSelectWidget(self.config_manager)
        self.stacked_widget.addWidget(self.window_select_page)

        # 创建区域选择界面
        self.region_select_page = RegionSelectWidgetWrapper(self.config_manager)
        self.stacked_widget.addWidget(self.region_select_page)

        # 创建运行参数配置界面
        self.run_config_page = RunConfigWidget(
            self.config_manager,
            scheduler=self.scheduler,
            floating_window=self.floating_window
        )
        self.stacked_widget.addWidget(self.run_config_page)

        # 预留：占位页面（后续可实现悬浮窗等其他界面）
        # self.run_config_placeholder = QWidget()
        # layout = QVBoxLayout(self.run_config_placeholder)
        # layout.addWidget(QWidget())
        # self.stacked_widget.addWidget(self.run_config_placeholder)

        # 默认显示翻译设置界面
        self.stacked_widget.setCurrentIndex(PAGE_SETTINGS)

    def _connect_signals(self):
        """连接信号"""
        # 翻译设置界面信号
        self.settings_page.next_signal.connect(self._on_settings_next)
        self.settings_page.cancel_signal.connect(self.close)

        # 窗口选择界面信号
        self.window_select_page.back_signal.connect(self._on_window_select_back)
        self.window_select_page.next_signal.connect(self._on_window_select_next)
        self.window_select_page.cancel_signal.connect(self.close)

        # 区域选择界面信号
        self.region_select_page.back_signal.connect(self._on_region_select_back)
        self.region_select_page.next_signal.connect(self._on_region_select_next)
        self.region_select_page.cancel_signal.connect(self.close)

        # 运行参数界面信号
        self.run_config_page.back_signal.connect(self._on_run_config_back)
        self.run_config_page.start_signal.connect(self._on_run_config_start)
        self.run_config_page.pause_signal.connect(self._on_run_config_pause)
        self.run_config_page.resume_signal.connect(self._on_run_config_resume)
        self.run_config_page.cancel_signal.connect(self.close)

    def _on_settings_next(self):
        """翻译设置界面 - 下一步处理"""
        # 验证 API Key 是否已输入
        if not self._validate_api_keys():
            return

        # 切换到窗口选择界面
        self.stacked_widget.setCurrentIndex(PAGE_WINDOW_SELECT)

        # 刷新窗口列表
        self.window_select_page._refresh_window_list()

    def _on_window_select_back(self):
        """窗口选择界面 - 上一步处理"""
        # 返回翻译设置界面
        self.stacked_widget.setCurrentIndex(PAGE_SETTINGS)

    def _on_window_select_next(self):
        """窗口选择界面 - 下一步处理"""
        # 切换到区域选择界面
        self.stacked_widget.setCurrentIndex(PAGE_REGION_SELECT)
        # 切换后调用截图
        self.region_select_page._capture_and_load()

    def _on_region_select_back(self):
        """区域选择界面 - 上一步处理"""
        # 返回窗口选择界面
        self.stacked_widget.setCurrentIndex(PAGE_WINDOW_SELECT)

    def _on_region_select_next(self):
        """区域选择界面 - 下一步处理"""
        # 切换到运行参数配置界面
        self.stacked_widget.setCurrentIndex(PAGE_RUN_CONFIG)

    def _on_run_config_back(self):
        """运行参数界面 - 上一步处理"""
        # 返回区域选择界面
        self.stacked_widget.setCurrentIndex(PAGE_REGION_SELECT)

    def _on_run_config_start(self):
        """运行参数界面 - 开始翻译处理"""
        print("[主窗口] 收到开始翻译信号")

        # 首次调用：创建调度器和依赖
        if self.scheduler is None:
            self._create_scheduler()

        # 传递配置快照给调度器
        config = self.config_manager.load_config()
        self.scheduler.set_config_snapshot(config)

        # 启动调度器
        self.scheduler.start()

    def _on_run_config_pause(self):
        """运行参数界面 - 暂停翻译处理"""
        print("[主窗口] 收到暂停翻译信号")
        if self.scheduler:
            self.scheduler.pause()

    def _on_run_config_resume(self):
        """运行参数界面 - 恢复翻译处理"""
        print("[主窗口] 收到恢复翻译信号")

        # 传递新的配置快照给调度器
        config = self.config_manager.load_config()
        self.scheduler.set_config_snapshot(config)

        # 恢复调度器
        if self.scheduler:
            self.scheduler.resume()

    def _create_scheduler(self):
        """创建调度器和所有依赖"""
        print("[主窗口] 创建调度器...")

        # 创建依赖服务实例
        window_capture = WindowCapture()
        image_processor = ImageProcessor()
        ocr_engine = OCREngine()
        translator = Translator()
        text_deduplicator = TextDeduplicator()

        # 创建调度器
        self.scheduler = Scheduler()

        # 设置依赖
        self.scheduler.set_dependencies(
            window_capture, image_processor, ocr_engine,
            translator, text_deduplicator
        )

        # 连接调度器信号
        self.scheduler.translation_result.connect(self._on_translation_result)
        self.scheduler.error_signal.connect(self._on_error)

        # 将调度器传递给运行参数界面
        self.run_config_page.set_scheduler(self.scheduler)

        print("[主窗口] 调度器创建完成")

    def _on_translation_result(self, original, translated, timestamp):
        """接收翻译结果"""
        print(f"[主窗口] 收到翻译结果: {original} -> {translated}")
        # TODO: 后续实现悬浮窗更新
        if self.floating_window:
            self.floating_window.set_translation(original, translated)

    def _on_error(self, error_msg):
        """接收错误信息"""
        print(f"[主窗口] 收到错误: {error_msg}")
        # TODO: 后续实现错误提示

    def _validate_api_keys(self) -> bool:
        """
        验证 API Key 是否已输入

        Returns:
            bool: 验证是否通过
        """
        # 获取当前选中的引擎
        engine = self.config_manager.get("translation.engine", "alibaba")

        if engine == "alibaba":
            # 检查阿里云密钥
            key_id = self.settings_page.alibaba_id_edit.text().strip()
            key_secret = self.settings_page.alibaba_secret_edit.text().strip()

            if not key_id or not key_secret:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请输入阿里云的 AccessKey ID 和 AccessKey Secret。\n\n"
                    "您可以在阿里云控制台的「访问管理」页面获取这些信息。"
                )
                return False

        elif engine == "google":
            # 检查 Google API Key
            api_key = self.settings_page.google_key_edit.text().strip()

            if not api_key:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请输入 Google 翻译的 API Key。\n\n"
                    "您可以在 Google Cloud 控制台的「凭据」页面获取 API Key。\n"
                    "注意：国内使用 Google API 需要自行解决网络问题。"
                )
                return False

        return True

    def closeEvent(self, event):
        """
        窗口关闭事件

        Args:
            event: 关闭事件
        """
        # 停止调度器
        if self.scheduler:
            self.scheduler.stop()

        # 保存配置
        config = self.config_manager.load_config()
        self.config_manager.save_config(config)

        # 确认退出（可选）
        # reply = QMessageBox.question(
        #     self,
        #     "确认退出",
        #     "确定要退出吗？",
        #     QMessageBox.Yes | QMessageBox.No,
        #     QMessageBox.No
        # )
        # if reply == QMessageBox.Yes:
        #     event.accept()
        # else:
        #     event.ignore()
        event.accept()


# 独立运行测试
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    # 创建配置管理器
    from src.controller.config_helper import ConfigHelper
    config_manager = ConfigHelper()

    # 创建主窗口
    window = MainWindow(config_manager)
    window.show()

    sys.exit(app.exec_())
