"""Live webcam rendered as pixel art.

Run:  python -m room3d.pixelcam [--windowed] [--camera N]
Keys: 1-4 palette | D dithering | [ ] pixel size | M mirror | ESC quit
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


def main():
    ap = argparse.ArgumentParser(description="Live webcam as pixel art")
    ap.add_argument("--windowed", action="store_true", help="1280x720 window instead of a full-screen-size window")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--pixels", type=int, default=160, help="horizontal resolution of the pixel art (default 160)")
    ap.add_argument("--palette", choices=PALETTE_ORDER, default="DB32")
    a = ap.parse_args()

    import cv2
    import pygame

    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    cap = cv2.VideoCapture(a.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        print("웹캠을 열 수 없습니다. 카메라가 켜져 있는지(Fn 키, 개인정보 설정) 확인하세요.", file=sys.stderr)
        sys.exit(1)

    pygame.init()
    info = pygame.display.Info()
    size = (1280, 720) if a.windowed else (info.current_w, info.current_h)
    screen = pygame.display.set_mode(size, 0 if a.windowed else pygame.NOFRAME)
    pygame.display.set_caption("Pixel Cam")
    aspect = size[0] / size[1]

    filt = PixelArt(a.palette)
    pixels, mirror = a.pixels, True
    print("키: 1~4 팔레트(DB32 / PICO-8 / GameBoy / Posterize) | D 디더링 | [ ] 픽셀 크기 | M 좌우반전 | ESC 종료",
          flush=True)
    clock = pygame.time.Clock()
    last_title = 0.0
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= e.key <= pygame.K_4:
                    filt.palette = PALETTE_ORDER[e.key - pygame.K_1]
                    filt.reset()
                elif e.key == pygame.K_d:
                    filt.dither = 0.0 if filt.dither else 24.0
                elif e.key == pygame.K_LEFTBRACKET:
                    pixels = min(480, int(pixels * 1.25))   # more pixels = smaller blocks
                    filt.reset()
                elif e.key == pygame.K_RIGHTBRACKET:
                    pixels = max(40, int(pixels / 1.25))    # fewer pixels = bigger blocks
                    filt.reset()
                elif e.key == pygame.K_m:
                    mirror = not mirror
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.02)
            continue
        frame = _cover_crop(frame, aspect)
        if mirror:
            frame = frame[:, ::-1]
        ph = max(1, round(pixels / aspect))
        small = cv2.resize(frame, (pixels, ph), interpolation=cv2.INTER_AREA)
        small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32)
        art = filt(small)
        surf = pygame.surfarray.make_surface(art.swapaxes(0, 1))
        screen.blit(pygame.transform.scale(surf, size), (0, 0))   # nearest-neighbour upscale
        pygame.display.flip()
        if time.time() - last_title > 1.0:
            last_title = time.time()
            pygame.display.set_caption(f"Pixel Cam | {filt.palette} | {pixels}x{ph} | "
                                       f"dither {'on' if filt.dither else 'off'} | {clock.get_fps():.0f} fps")
        clock.tick(30)
    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()
