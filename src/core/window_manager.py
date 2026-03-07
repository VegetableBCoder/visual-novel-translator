"""
窗口管理器

使用 Win32 API 枚举和管理 Windows 窗口。
主要功能：

1. 枚举所有可见顶层窗口
2. 获取窗口标题、类名、位置
3. 根据标题查找窗口

所有操作均为同步执行，不使用多线程。
"""

from typing import List, Dict, Optional, Tuple, Any
import ctypes
from ctypes import wintypes


class WindowManager:
    """窗口管理器（基于 Win32 API 实现）"""

    # 过滤掉不感兴趣的窗口类名
    FILTERED_CLASSES = {
        "IME",
        "MSCTFIME Composition",
        "GDI+ Window",
        "Tooltip",
        "Shell_TrayWnd",
        "TrayNotifyWnd",
        "Progman",
        "WorkerW",
        "Desktop User Class",
    }

    def __init__(self):
        """初始化窗口管理器"""
        self._user32 = ctypes.windll.user32
        self._init_win32_functions()

    def _init_win32_functions(self):
        """初始化 Win32 API 函数签名"""

        # EnumWindows 回调类型
        self._EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM
        )

        # 枚举窗口
        self._user32.EnumWindows.argtypes = [
            self._EnumWindowsProc,
            wintypes.LPARAM,
        ]
        self._user32.EnumWindows.restype = wintypes.BOOL

        # 获取窗口标题长度
        self._user32.GetWindowTextLengthW.argtypes = [
            wintypes.HWND
        ]
        self._user32.GetWindowTextLengthW.restype = ctypes.c_int

        # 获取窗口标题
        self._user32.GetWindowTextW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int
        ]
        self._user32.GetWindowTextW.restype = ctypes.c_int

        # 获取窗口类名
        self._user32.GetClassNameW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int
        ]
        self._user32.GetClassNameW.restype = ctypes.c_int

        # 判断窗口是否可见
        self._user32.IsWindowVisible.argtypes = [
            wintypes.HWND
        ]
        self._user32.IsWindowVisible.restype = wintypes.BOOL

        # 判断窗口是否存在
        self._user32.IsWindow.argtypes = [
            wintypes.HWND
        ]
        self._user32.IsWindow.restype = wintypes.BOOL

        # 获取窗口矩形
        self._user32.GetWindowRect.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.RECT)
        ]
        self._user32.GetWindowRect.restype = wintypes.BOOL

        # 获取窗口扩展样式
        self._user32.GetWindowLongPtrW.argtypes = [
            wintypes.HWND,
            ctypes.c_int
        ]

        # 兼容 32 / 64 位
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            self._user32.GetWindowLongPtrW.restype = ctypes.c_longlong
        else:
            self._user32.GetWindowLongPtrW.restype = ctypes.c_long

        # 判断窗口是否最小化
        self._user32.IsIconic.argtypes = [
            wintypes.HWND
        ]
        self._user32.IsIconic.restype = wintypes.BOOL

    def enum_windows(self) -> List[Dict[str, Any]]:
        """
        枚举所有可见的顶层窗口

        Returns
        -------
        List[Dict[str, Any]]
            窗口列表，每个元素包含：

            hwnd : int
                窗口句柄

            title : str
                窗口标题

            class_name : str
                窗口类名

            rect : Tuple[int, int, int, int]
                窗口矩形 (left, top, right, bottom)
        """

        windows: List[Dict[str, Any]] = []

        def callback(hwnd: wintypes.HWND, lparam: wintypes.LPARAM) -> bool:
            """EnumWindows 回调函数"""

            if self._should_include_window(hwnd):
                info = self._get_window_info(hwnd)
                if info:
                    windows.append(info)

            return True  # 继续枚举

        # 防止 callback 被 GC
        self._enum_callback = self._EnumWindowsProc(callback)

        self._user32.EnumWindows(self._enum_callback, 0)

        return windows

    def _should_include_window(self, hwnd: wintypes.HWND) -> bool:
        """
        判断窗口是否应该被包含在枚举结果中

        Parameters
        ----------
        hwnd : HWND
            窗口句柄

        Returns
        -------
        bool
            是否包含
        """

        # 必须是可见窗口
        if not self._user32.IsWindowVisible(hwnd):
            return False

        # 过滤最小化的窗口
        if self._user32.IsIconic(hwnd):
            return False

        class_name = self._get_window_class(hwnd)

        if not class_name:
            return False

        # 过滤不需要的窗口类型
        if class_name in self.FILTERED_CLASSES:
            return False

        # 输入法窗口
        if class_name.startswith("MSCTF"):
            return False

        # 检查扩展样式
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000

        ex_style = self._user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)

        if not (ex_style & WS_EX_APPWINDOW):
            # 如果没有 APPWINDOW 样式，则要求窗口必须有标题
            title = self._get_window_title(hwnd)

            if not title.strip():
                return False

        return True

    def _get_window_info(self, hwnd: wintypes.HWND) -> Optional[Dict[str, Any]]:
        """
        获取窗口信息

        Parameters
        ----------
        hwnd : HWND
            窗口句柄

        Returns
        -------
        Dict[str, Any] | None
            窗口信息
        """

        title = self._get_window_title(hwnd)
        class_name = self._get_window_class(hwnd)
        rect = self.get_window_rect(hwnd)

        return {
            "hwnd": hwnd,
            "title": title,
            "class_name": class_name,
            "rect": rect,
        }

    def _get_window_title(self, hwnd: wintypes.HWND) -> str:
        """
        获取窗口标题

        Parameters
        ----------
        hwnd : HWND
            窗口句柄

        Returns
        -------
        str
            窗口标题
        """

        length = self._user32.GetWindowTextLengthW(hwnd)

        if length == 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)

        self._user32.GetWindowTextW(hwnd, buffer, length + 1)

        return buffer.value

    def _get_window_class(self, hwnd: wintypes.HWND) -> str:
        """
        获取窗口类名

        Parameters
        ----------
        hwnd : HWND
            窗口句柄

        Returns
        -------
        str
            窗口类名
        """

        buffer = ctypes.create_unicode_buffer(256)

        length = self._user32.GetClassNameW(hwnd, buffer, 256)

        if length == 0:
            return ""

        return buffer.value

    def get_window_rect(
        self, hwnd: wintypes.HWND
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        获取窗口矩形区域

        Parameters
        ----------
        hwnd : HWND
            窗口句柄

        Returns
        -------
        tuple | None
            (left, top, right, bottom)
        """

        rect = wintypes.RECT()

        if self._user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)

        return None

    def is_window_valid(self, hwnd: wintypes.HWND) -> bool:
        """
        判断窗口句柄是否有效

        Parameters
        ----------
        hwnd : HWND

        Returns
        -------
        bool
        """

        return bool(self._user32.IsWindow(hwnd))

    def find_window_by_title(
        self,
        title: str,
        exact: bool = True,
    ) -> Optional[int]:
        """
        根据窗口标题查找窗口

        Parameters
        ----------
        title : str
            窗口标题

        exact : bool
            是否精确匹配

        Returns
        -------
        int | None
            窗口句柄
        """

        windows = self.enum_windows()

        for window in windows:

            window_title = window["title"]

            if exact:
                if window_title == title:
                    return window["hwnd"]
            else:
                if title in window_title:
                    return window["hwnd"]

        return None