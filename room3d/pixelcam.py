"""Live webcam rendered as pixel art.

Run:  python -m room3d.pixelcam [--windowed] [--camera N]
Keys: Space 3-2-1 photo | 1-4 palette | D dithering | [ ] pixel size | M mirror | H HUD | ESC quit
"""
import argparse
import sys
import time

import numpy as np


def _hex(colors):
    return np.array([[int(c[i:i + 2], 16) for i in (0, 2, 4)] for c in colors], dtype=np.float32)


PALETTES = {
    # DawnBringer 32: a classic 32-colour pixel-art palette
    "DB32": _hex("000000 222034 45283c 663931 8f563b df7126 d9a066 eec39a fbf236 99e550 6abe30 37946e "
                 "4b692f 524b24 323c39 3f3f74 306082 5b6ee1 639bff 5fcde4 cbdbfc ffffff 9badb7 847e87 "
                 "696a6a 595652 76428a ac3232 d95763 d77bba 8f974a 8a6f30".split()),
    "PICO-8": _hex("000000 1d2b53 7e2553 008751 ab5236 5f574f c2c3c7 fff1e8 ff004d ffa300 ffec27 00e436 "
                   "29adff 83769c ff77a8 ffccaa".split()),
    "GameBoy": _hex("0f380f 306230 8bac0f 9bbc0f".split()),
}
POSTERIZE = "Posterize"  # no fixed palette: 4 levels per channel (64 colours)
PALETTE_ORDER = ["DB32", "PICO-8", "GameBoy", POSTERIZE]

_BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) + 0.5) / 16 - 0.5


class PixelArt:
    """Stateful filter: temporal smoothing + palette mapping with hysteresis (anti-flicker)."""

    def __init__(self, palette="DB32", smoothing=0.35, hysteresis=12.0, dither=0.0):
        self.palette = palette
        self.smoothing = smoothing      # EMA weight of the newest frame (lower = calmer, laggier)
        self.hysteresis = hysteresis    # keep the previous colour unless a new one is this much closer
        self.dither = dither            # ordered-dither strength in RGB units (0 = off)
        self._avg = None
        self._prev_idx = None

    def reset(self):
        self._avg = self._prev_idx = None

    def __call__(self, small_rgb):
        """small_rgb: float32 [h, w, 3] in 0..255 (already downscaled). Returns uint8 [h, w, 3]."""
        if self._avg is None or self._avg.shape != small_rgb.shape:
            self._avg, self._prev_idx = small_rgb.copy(), None
        else:
            self._avg += self.smoothing * (small_rgb - self._avg)
        img = self._avg
        if self.dither > 0:
            h, w = img.shape[:2]
            img = img + np.tile(_BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w, None] * self.dither
        if self.palette == POSTERIZE:
            return (np.clip(np.round(img / 85.0), 0, 3) * 85).astype(np.uint8)
        pal = PALETTES[self.palette]
        d = ((img[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)    # h x w x P
        idx = d.argmin(-1)
        if self._prev_idx is not None and self._prev_idx.shape == idx.shape and self._prev_idx.max() < len(pal):
            best = np.take_along_axis(d, idx[..., None], -1)[..., 0]
            prev = np.take_along_axis(d, self._prev_idx[..., None], -1)[..., 0]
            keep = np.sqrt(prev) - np.sqrt(best) < self.hysteresis
            idx = np.where(keep, self._prev_idx, idx)
        self._prev_idx = idx
        return pal[idx].astype(np.uint8)


def _cover_crop(frame, aspect):
    """Crop the camera frame to the screen aspect ratio (fill, no letterbox)."""
    h, w = frame.shape[:2]
    if w / h > aspect:
        nw = int(h * aspect)
        x0 = (w - nw) // 2
        return frame[:, x0:x0 + nw]
    nh = int(w / aspect)
    y0 = (h - nh) // 2
    return frame[y0:y0 + nh]


PIXEL_STEPS = [160, 200, 250, 312, 390, 480]   # '[' / ']' walk through these


def render_still(frame_bgr, filt_template, pixels, aspect):
    """Process one photo with the current settings (fresh filter: no temporal state)."""
    import cv2
    ph = max(1, round(pixels / aspect))
    small = cv2.cvtColor(cv2.resize(frame_bgr, (pixels, ph), interpolation=cv2.INTER_AREA),
                         cv2.COLOR_BGR2RGB).astype(np.float32)
    f = PixelArt(filt_template.palette, dither=filt_template.dither)
    return f(small)


def main():
    ap = argparse.ArgumentParser(description="Live webcam as pixel art")
    ap.add_argument("--windowed", action="store_true", help="1280x720 window instead of a full-screen-size window")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--pixels", type=int, default=160, help="horizontal resolution of the pixel art (default 160)")
    ap.add_argument("--palette", choices=PALETTE_ORDER, default="DB32")
    ap.add_argument("--out", default="captures", help="folder for snapshots (default: captures)")
    a = ap.parse_args()

    import os

    import cv2
    import pygame

    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    cap = cv2.VideoCapture(a.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("웹캠을 열 수 없습니다. 카메라가 켜져 있는지(Fn 키, 개인정보 설정) 확인하세요.", file=sys.stderr)
        sys.exit(1)

    pygame.init()
    info = pygame.display.Info()
    size = (1280, 720) if a.windowed else (info.current_w, info.current_h)
    screen = pygame.display.set_mode(size, 0 if a.windowed else pygame.NOFRAME)
    pygame.display.set_caption("Pixel Cam")
    aspect = size[0] / size[1]
    font = pygame.font.SysFont("consolas,menlo,monospace", max(16, size[1] // 45))
    big_font = pygame.font.SysFont("arial,helvetica,sans", size[1] // 3, bold=True)

    filt = PixelArt(a.palette)
    pixels, mirror, show_hud = a.pixels, True, True
    countdown_end = None      # time when the 3-2-1 countdown fires
    still = None              # (raw_bgr) while showing a captured photo
    still_art = None
    flash_until = 0.0
    print("키: Space 3-2-1 촬영 (촬영 화면에서 Space = 실시간으로 복귀) | 1~4 팔레트 | D 디더링 | "
          "[ ] 픽셀 크기 | M 좌우반전 | H 정보 표시 | ESC 종료", flush=True)

    def step_pixels(direction):
        steps = sorted(set(PIXEL_STEPS + [pixels]))
        i = steps.index(pixels) + direction
        return steps[max(0, min(len(steps) - 1, i))]

    def text(surface, msg, pos, f, color=(255, 255, 255)):
        shadow = f.render(msg, True, (0, 0, 0))
        surface.blit(shadow, (pos[0] + 2, pos[1] + 2))
        surface.blit(f.render(msg, True, color), pos)

    clock = pygame.time.Clock()
    running = True
    frame = None
    while running:
        settings_changed = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    if still is not None:
                        still = still_art = None           # back to live
                        filt.reset()
                    elif countdown_end is None:
                        countdown_end = time.time() + 3.0
                elif pygame.K_1 <= e.key <= pygame.K_4:
                    filt.palette = PALETTE_ORDER[e.key - pygame.K_1]
                    settings_changed = True
                elif e.key == pygame.K_d:
                    filt.dither = 0.0 if filt.dither else 24.0
                    settings_changed = True
                elif e.key == pygame.K_LEFTBRACKET:        # more pixels = smaller blocks
                    pixels = step_pixels(+1)
                    settings_changed = True
                elif e.key == pygame.K_RIGHTBRACKET:       # fewer pixels = bigger blocks
                    pixels = step_pixels(-1)
                    settings_changed = True
                elif e.key == pygame.K_m:
                    mirror = not mirror
                elif e.key == pygame.K_h:
                    show_hud = not show_hud
        if settings_changed:
            filt.reset()
            if still is not None:
                still_art = render_still(still, filt, pixels, aspect)

        ok, cam = cap.read()
        if ok:
            cam = _cover_crop(cam, aspect)
            frame = np.ascontiguousarray(cam[:, ::-1]) if mirror else cam
        if frame is None:
            time.sleep(0.02)
            continue

        if countdown_end is not None and time.time() >= countdown_end:
            countdown_end = None
            still = frame.copy()
            still_art = render_still(still, filt, pixels, aspect)
            os.makedirs(a.out, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            raw_path = os.path.join(a.out, f"{stamp}_raw.png")
            art_path = os.path.join(a.out, f"{stamp}_pixel_{filt.palette}_{pixels}.png")
            cv2.imwrite(raw_path, still)
            big = cv2.resize(cv2.cvtColor(still_art, cv2.COLOR_RGB2BGR), size, interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(art_path, big)
            print(f"저장: {raw_path} / {art_path}", flush=True)
            flash_until = time.time() + 0.15

        if still is not None:
            art = still_art
        else:
            ph = max(1, round(pixels / aspect))
            small = cv2.resize(frame, (pixels, ph), interpolation=cv2.INTER_AREA)
            art = filt(cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32))
        surf = pygame.surfarray.make_surface(art.swapaxes(0, 1))
        screen.blit(pygame.transform.scale(surf, size), (0, 0))   # nearest-neighbour upscale

        if time.time() < flash_until:
            screen.fill((255, 255, 255))
        if countdown_end is not None:
            n = str(int(countdown_end - time.time()) + 1)
            w, h = big_font.size(n)
            text(screen, n, ((size[0] - w) // 2, (size[1] - h) // 2), big_font)
        if show_hud:
            ph = max(1, round(pixels / aspect))
            mode = "PHOTO (Space = live)" if still is not None else f"LIVE {clock.get_fps():.0f} fps"
            lines = [f"{mode}",
                     f"pixels {pixels} x {ph}   palette {filt.palette}   dither {'on' if filt.dither else 'off'}",
                     "Space 3-2-1 photo | 1-4 palette | D dither | [ ] pixel size | M mirror | H hide | ESC quit"]
            y = 10
            for ln in lines:
                text(screen, ln, (12, y), font)
                y += font.get_linesize()
        pygame.display.flip()
        clock.tick(30)
    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()
