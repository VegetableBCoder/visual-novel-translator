import ctypes
from ctypes import wintypes

def _get_monitor_dpi(self, hwnd: wintypes.HWND) -> int:
    """
    返回与窗口所在监视器对应的 DPI（整数，通常 96, 120, 144...）。
    优先使用 shcore.GetDpiForMonitor（Windows 8.1+），不可用则退回 GetDeviceCaps(LOGPIXELSX)。
    """
    # MonitorFromWindow
    MONITOR_DEFAULTTONEAREST = 2
    monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    # try shcore.GetDpiForMonitor
    try:
        shcore = ctypes.windll.shcore
    except Exception:
        shcore = None

    if shcore:
        MDT_EFFECTIVE_DPI = 0
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        # BOOL GetDpiForMonitor(HMONITOR, MONITOR_DPI_TYPE, UINT*, UINT*);
        try:
            res = shcore.GetDpiForMonitor(
                monitor,
                MDT_EFFECTIVE_DPI,
                ctypes.byref(dpi_x),
                ctypes.byref(dpi_y)
            )
            if res == 0:
                return int(dpi_x.value)
        except AttributeError:
            # older shcore without function
            pass

    # fallback: use primary screen DC GetDeviceCaps
    hdc_screen = ctypes.windll.user32.GetDC(0)
    if hdc_screen:
        LOGPIXELSX = 88
        gdi32 = ctypes.windll.gdi32
        dpi = gdi32.GetDeviceCaps(hdc_screen, LOGPIXELSX)
        ctypes.windll.user32.ReleaseDC(0, hdc_screen)
        if dpi:
            return int(dpi)

    # 最后兜底
    return 96


def _get_dpi_for_window_safe(self, hwnd: wintypes.HWND) -> int:
    """
    返回 GetDpiForWindow 的值（如果 API 不存在或返回异常，则返回 96）。
    """
    try:
        func = getattr(self._user32, "GetDpiForWindow", None)
        if func:
            func.argtypes = [wintypes.HWND]
            func.restype = ctypes.c_uint
            return int(func(hwnd))
    except Exception:
        pass
    return 96
