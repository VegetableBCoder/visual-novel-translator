"""
视觉小说翻译器 - 程序入口

主程序入口，初始化配置并启动主窗口。
"""

import sys
from PyQt5.QtWidgets import QApplication

from src.controller.config_helper import ConfigHelper
from src.ui.main_window import MainWindow


def main():
    """主函数"""
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setApplicationName("Visual Novel Translator")
    app.setOrganizationName("VNT")

    # 创建配置管理器
    config_manager = ConfigHelper()

    # 创建并显示主窗口
    window = MainWindow(config_manager)
    window.show()

    # 运行事件循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
