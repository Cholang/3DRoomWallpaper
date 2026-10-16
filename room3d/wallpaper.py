"""Attach a window behind the desktop icons (Windows 10/11)."""
import ctypes
import sys


def attach_to_desktop(hwnd: int) -> bool:
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    progman = user32.FindWindowW("Progman", None)
    # Ask Progman to spawn a WorkerW behind the icons.
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(ctypes.c_ulong()))

    found = []
    ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(top, _):
        if user32.FindWindowExW(top, None, "SHELLDLL_DefView", None):
            found.append(user32.FindWindowExW(None, top, "WorkerW", None))
        return True

    user32.EnumWindows(ENUM(cb), 0)
    workerw = found[0] if found else None
    if not workerw:
        return False
    user32.SetParent(hwnd, workerw)
    w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    user32.SetWindowPos(hwnd, None, 0, 0, w, h, 0x0040)  # SWP_SHOWWINDOW
    return True
