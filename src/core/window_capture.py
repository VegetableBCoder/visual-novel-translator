"""
窗口截图服务

使用 Win32 API 的 PrintWindow 方法截取指定窗口的图像。
主要功能：

1. 根据窗口句柄（hwnd）捕获窗口内容
2. 支持硬件加速渲染的窗口（使用 PW_RENDERFULLCONTENT 标志）
3. 处理 DPI 缩放问题（修正整数截断导致的黑边）
4. 返回 PIL Image 对象供后续处理

所有操作均为同步执行，不使用多线程。
"""

from typing import Optional
import ctypes
from ctypes import wintypes
from PIL import Image
import math


class WindowCapture:
    """窗口截图服务（基于 Win32 API PrintWindow 实现）"""

    def __init__(self):
        """初始化窗口截图服务"""
        # ✅ 关键：设置进程 DPI 感知（避免系统虚拟缩放）
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PerMonitorV2
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self._user32 = ctypes.windll.user32
        self._gdi32 = ctypes.windll.gdi32
        self._init_win32_functions()

    def _init_win32_functions(self):
        """初始化 Win32 API 函数签名"""

        self._user32.IsWindow.argtypes = [wintypes.HWND]
        self._user32.IsWindow.restype = wintypes.BOOL

        self._user32.GetWindowRect.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.RECT)
        ]
        self._user32.GetWindowRect.restype = wintypes.BOOL

        self._user32.GetClientRect.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.RECT)
        ]
        self._user32.GetClientRect.restype = wintypes.BOOL

        self._user32.ClientToScreen.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.POINT)
        ]
        self._user32.ClientToScreen.restype = wintypes.BOOL

        self._user32.GetWindowDC.argtypes = [wintypes.HWND]
        self._user32.GetWindowDC.restype = wintypes.HDC

        self._gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        self._gdi32.CreateCompatibleDC.restype = wintypes.HDC

        self._gdi32.CreateCompatibleBitmap.argtypes = [
            wintypes.HDC,
            ctypes.c_int,
            ctypes.c_int
        ]
        self._gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP

        self._gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        self._gdi32.SelectObject.restype = wintypes.HGDIOBJ

        self._user32.PrintWindow.argtypes = [
            wintypes.HWND,
            wintypes.HDC,
            ctypes.c_uint
        ]
        self._user32.PrintWindow.restype = wintypes.BOOL

        # ✅ GetObjectW 正确注册
        self._gdi32.GetObjectW.argtypes = [
            wintypes.HGDIOBJ,
            ctypes.c_int,
            ctypes.c_void_p
        ]
        self._gdi32.GetObjectW.restype = ctypes.c_int

        self._gdi32.GetDIBits.argtypes = [
            wintypes.HDC,
            wintypes.HBITMAP,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint
        ]
        self._gdi32.GetDIBits.restype = ctypes.c_int

        self._user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        self._user32.ReleaseDC.restype = ctypes.c_int

        self._gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        self._gdi32.DeleteObject.restype = wintypes.BOOL

        self._gdi32.DeleteDC.argtypes = [wintypes.HDC]
        self._gdi32.DeleteDC.restype = wintypes.BOOL

    def _get_monitor_dpi(self, hwnd: wintypes.HWND) -> int:
        """获取当前窗口所在显示器 DPI"""
        MONITOR_DEFAULTTONEAREST = 2
        monitor = self._user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

        try:
            shcore = ctypes.windll.shcore
            dpi_x = ctypes.c_uint()
            dpi_y = ctypes.c_uint()

            MDT_EFFECTIVE_DPI = 0
            res = shcore.GetDpiForMonitor(
                monitor,
                MDT_EFFECTIVE_DPI,
                ctypes.byref(dpi_x),
                ctypes.byref(dpi_y)
            )
            if res == 0:
                return int(dpi_x.value)
        except Exception:
            pass

        hdc_screen = self._user32.GetDC(0)
        if hdc_screen:
            LOGPIXELSX = 88
            dpi = self._gdi32.GetDeviceCaps(hdc_screen, LOGPIXELSX)
            self._user32.ReleaseDC(0, hdc_screen)
            if dpi:
                return int(dpi)

        return 96

    def capture_window(self, hwnd: int) -> Optional[Image.Image]:
        """截取指定窗口的图像"""

        if not self._user32.IsWindow(hwnd):
            return None

        window_rect = wintypes.RECT()
        if not self._user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
            return None

        win_width = window_rect.right - window_rect.left
        win_height = window_rect.bottom - window_rect.top

        if win_width <= 0 or win_height <= 0:
            return None

        client_rect = wintypes.RECT()
        if not self._user32.GetClientRect(hwnd, ctypes.byref(client_rect)):
            return None

        client_width = client_rect.right
        client_height = client_rect.bottom
        window_dpi = self._user32.GetDpiForWindow(hwnd)
        dpi = self._get_monitor_dpi(hwnd)
        scale_factor = 1.0 if window_dpi == dpi else dpi / 96.0

        # ✅ 修正：使用 ceil 避免像素丢失
        phys_win_width = math.ceil(win_width / scale_factor)
        phys_win_height = math.ceil(win_height / scale_factor)

        phys_client_width = math.ceil(client_width / scale_factor)
        phys_client_height = math.ceil(client_height / scale_factor)

        pt = wintypes.POINT(0, 0)
        if self._user32.ClientToScreen(hwnd, ctypes.byref(pt)):
            offset_x = pt.x - window_rect.left
            offset_y = pt.y - window_rect.top
        else:
            offset_x = 0
            offset_y = 0

        hdc_window = self._user32.GetWindowDC(hwnd)
        if not hdc_window:
            return None

        try:
            hdc_mem = self._gdi32.CreateCompatibleDC(hdc_window)
            if not hdc_mem:
                return None

            try:
                hbitmap = self._gdi32.CreateCompatibleBitmap(
                    hdc_window,
                    phys_win_width,
                    phys_win_height
                )
                if not hbitmap:
                    return None

                try:
                    old_obj = self._gdi32.SelectObject(hdc_mem, hbitmap)
                    if not old_obj:
                        return None

                    PW_RENDERFULLCONTENT = 2
                    if not self._user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT):
                        return None

                    full_image = self._bitmap_to_image(
                        hdc_mem,
                        hbitmap,
                        phys_win_width,
                        phys_win_height
                    )
                    if full_image is None:
                        return None

                    # ✅ 修正：物理像素偏移 = 逻辑偏移 / scale
                    phys_offset_x = math.floor(offset_x / scale_factor)
                    phys_offset_y = math.floor(offset_y / scale_factor)

                    phys_offset_x = max(0, phys_offset_x)
                    phys_offset_y = max(0, phys_offset_y)

                    phys_right = min(
                        phys_offset_x + phys_client_width,
                        phys_win_width
                    )
                    phys_bottom = min(
                        phys_offset_y + phys_client_height,
                        phys_win_height
                    )

                    if phys_offset_x >= phys_right or phys_offset_y >= phys_bottom:
                        return full_image

                    client_image = full_image.crop(
                        (
                            phys_offset_x,
                            phys_offset_y,
                            phys_right,
                            phys_bottom
                        )
                    )

                    # ✅ 不再使用 int() 截断
                    if scale_factor != 1.0:
                        client_image = client_image.resize(
                            (client_width, client_height),
                            Image.LANCZOS
                        )

                    return client_image

                finally:
                    self._gdi32.SelectObject(hdc_mem, old_obj)
                    self._gdi32.DeleteObject(hbitmap)

            finally:
                self._gdi32.DeleteDC(hdc_mem)

        finally:
            self._user32.ReleaseDC(hwnd, hdc_window)

    def _bitmap_to_image(
            self,
            hdc: wintypes.HDC,
            hbitmap: wintypes.HBITMAP,
            width: int,
            height: int
    ) -> Optional[Image.Image]:

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", ctypes.c_uint32 * 1),
            ]

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)

        result = self._gdi32.GetDIBits(
            hdc,
            hbitmap,
            0,
            height,
            buffer,
            ctypes.byref(bmi),
            0
        )

        if result == 0:
            return None

        try:
            image = Image.frombuffer(
                "RGBA",
                (width, height),
                buffer,
                "raw",
                "BGRA",
                0,
                1
            ).convert("RGB")
        except Exception:
            return None

        return image


_capture_instance = None


def capture_window(hwnd: int) -> Optional[Image.Image]:
    global _capture_instance

    if _capture_instance is None:
        _capture_instance = WindowCapture()

    return _capture_instance.capture_window(hwnd)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python window_capture.py <hwnd>")
        sys.exit(1)

    hwnd = int(sys.argv[1], 0)

    image = capture_window(hwnd)

    if image is None:
        print("截图失败")
        sys.exit(1)

    print(f"截图成功: {image.width} x {image.height}")
    image.save("test_capture.png")
