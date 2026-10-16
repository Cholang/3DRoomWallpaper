import argparse
import sys
import time

import pygame

from .config import Config


def main():
    ap = argparse.ArgumentParser(description="Head-tracked 3D room wallpaper")
    ap.add_argument("--wallpaper", action="store_true", help="attach behind desktop icons (Windows)")
    ap.add_argument("--windowed", action="store_true", help="1280x720 window for testing")
    ap.add_argument("--mouse", action="store_true", help="use the mouse instead of the webcam")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--approach-zoom", type=float, help="0 = pure window physics, 1 = grow when closer (default)")
    ap.add_argument("--debug", action="store_true", help="print estimated eye position (cm) twice a second")
    ap.add_argument("--background", action="store_true",
                    help="fallback: full-screen window kept behind all other windows (hides icons)")
    ap.add_argument("--parent", choices=["progman", "workerw"], default="progman",
                    help="wallpaper debugging: which window to parent into (Win11 24H2)")
    ap.add_argument("--zorder", choices=["auto", "top", "bottom"], default="auto",
                    help="wallpaper debugging: where to put our window among Progman children")
    ap.add_argument("--screen-width-cm", type=float)
    ap.add_argument("--hfov", type=float)
    ap.add_argument("--cam-offset-cm", type=float)
    a = ap.parse_args()

    cfg = Config(camera_index=a.camera)
    if a.screen_width_cm: cfg.screen_width_cm = a.screen_width_cm
    if a.hfov: cfg.hfov_deg = a.hfov
    if a.approach_zoom is not None: cfg.approach_zoom = a.approach_zoom
    if a.cam_offset_cm is not None: cfg.cam_offset_cm = a.cam_offset_cm

    if sys.platform == "win32":  # report real pixels on scaled (e.g. 125%) displays
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    pygame.init()
    info = pygame.display.Info()
    size = (1280, 720) if a.windowed else (info.current_w, info.current_h)
    flags = pygame.OPENGL | pygame.DOUBLEBUF | (0 if a.windowed else pygame.NOFRAME)
    pygame.display.set_mode(size, flags, vsync=1)
    pygame.display.set_caption("3D Room Wallpaper")

    if a.background:
        from .wallpaper import make_background
        print("[background] ok" if make_background(pygame.display.get_wm_info()["window"])
              else "[background] FAILED", flush=True)
    if a.wallpaper:
        from .wallpaper import attach_to_desktop, dump_tree
        hwnd = pygame.display.get_wm_info()["window"]
        mode = attach_to_desktop(hwnd, a.zorder, a.parent)
        print("\n".join(dump_tree(hwnd)))
        print(f"[wallpaper] attach: {mode or 'FAILED'}")
        if not mode:
            print("Could not attach to desktop (Windows only).", file=sys.stderr)

    from .renderer import Renderer
    r = Renderer(size[0], size[1], cfg.screen_width_cm, cfg.room_depth_cm)

    tracker = None
    if not a.mouse:
        from .tracker import HeadTracker
        tracker = HeadTracker(cfg, r.half_h)
        tracker.start()

    clock = pygame.time.Clock()
    last_dbg = 0.0
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
        if tracker:
            eye = tracker.latest()
        else:
            if a.wallpaper or a.background:
                from .wallpaper import cursor_pos
                mx, my = cursor_pos()
            else:
                mx, my = pygame.mouse.get_pos()
            eye = ((mx / size[0] - 0.5) * 2 * r.half_w, (0.5 - my / size[1]) * 2 * r.half_h,
                   cfg.default_eye_cm[2])
        if a.debug and time.time() - last_dbg > 0.5:
            last_dbg = time.time()
            print(f"eye x={eye[0]:6.1f} y={eye[1]:6.1f} z(distance)={eye[2]:6.1f} cm | "
                  f"screen={r.half_w * 2:.1f}x{r.half_h * 2:.1f} cm", flush=True)
        g = cfg.parallax_gain
        ref = cfg.default_eye_cm[2]
        zoom = min(1.0, eye[2] / ref) ** cfg.approach_zoom   # only magnify when closer than the default distance
        r.draw((eye[0] * g, eye[1] * g, eye[2]), zoom)
        pygame.display.flip()
        clock.tick(60)
    if tracker:
        tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
