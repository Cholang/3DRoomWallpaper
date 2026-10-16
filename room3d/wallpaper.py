"""Attach a window behind the desktop icons (Windows 10/11, incl. 24H2 layout)."""
import ctypes
import sys
from ctypes import wintypes

GWL_STYLE = -16
WS_CHILD, WS_POPUP, WS_CAPTION, WS_THICKFRAME = 0x40000000, 0x80000000, 0x00C00000, 0x00040000
SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0010, 0x0040


def _setup(user32):
    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowExW.restype = wintypes.HWND
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]


def attach_to_desktop(hwnd: int, zorder: str = "auto", parent_mode: str = "progman") -> str:
    """Returns a short status string describing what happened ('' on failure)."""
    if sys.platform != "win32":
        return ""
    user32 = ctypes.windll.user32
    _setup(user32)
    hwnd = wintypes.HWND(hwnd)
    progman = user32.FindWindowW("Progman", None)
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(ctypes.c_ulong()))

    # Classic layout: a top-level WorkerW sits right after the one holding SHELLDLL_DefView.
    found = []
    ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(top, _):
        if user32.FindWindowExW(top, None, "SHELLDLL_DefView", None):
            found.append(user32.FindWindowExW(None, top, "WorkerW", None))
        return True

    user32.EnumWindows(ENUM(cb), 0)
    workerw = found[0] if found and found[0] else None

    w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    if workerw:
        mode, parent, insert_after = "classic", workerw, None
    else:
        # Win11 24H2 layout: the wallpaper WorkerW is a child of Progman.
        if not progman:
            return ""
        # SetWindowPos places us *behind* hWndInsertAfter. Insert right behind the icon layer
        # (SHELLDLL_DefView): above the wallpaper WorkerW, below the icons.
        defview = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
        mode, parent, insert_after = "24H2", progman, defview or wintypes.HWND(0)  # 0 = HWND_TOP
        if parent_mode == "workerw":
            # Parent into the wallpaper WorkerW itself (the layer that draws the picture).
            wchild = user32.FindWindowExW(progman, None, "WorkerW", None)
            if wchild:
                mode, parent, insert_after = "24H2-workerw", wchild, wintypes.HWND(0)

    user32.SetParent(hwnd, parent)
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = (style & ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME)) | WS_CHILD
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    if zorder == "top":
        insert_after = wintypes.HWND(0)   # HWND_TOP: above everything inside the parent
    elif zorder == "bottom":
        insert_after = wintypes.HWND(1)   # HWND_BOTTOM
    user32.SetWindowPos(hwnd, insert_after, 0, 0, w, h, SWP_NOACTIVATE | SWP_SHOWWINDOW)
    user32.ShowWindow(hwnd, 5)  # SW_SHOW
    user32.UpdateWindow(hwnd)
    return mode


def dump_tree(hwnd: int):
    """Describe Progman's children (top of z-order first) for debugging."""
    user32 = ctypes.windll.user32
    _setup(user32)
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    me = wintypes.HWND(hwnd).value
    lines = []

    def info(h, indent):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, buf, 64)
        r = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        tag = "  <== OURS" if h == me else ""
        lines.append(f"{'  ' * indent}{buf.value or '?'} hwnd={h} visible={bool(user32.IsWindowVisible(h))} "
                     f"rect=({r.left},{r.top},{r.right},{r.bottom}){tag}")

    progman = user32.FindWindowW("Progman", None)
    lines.append("Progman children (top of z-order first):")
    info(progman, 0)
    c = user32.GetWindow(progman, 5)  # GW_CHILD
    while c:
        info(c, 1)
        c = user32.GetWindow(c, 2)    # GW_HWNDNEXT
    return lines


def cursor_pos():
    """Global cursor position (works even when the window gets no mouse input)."""
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y
