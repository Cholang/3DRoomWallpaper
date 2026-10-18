import numpy as np

from room3d.pixelcam import PALETTES, PixelArt


def test_output_uses_only_palette_colours():
    img = np.random.default_rng(0).uniform(0, 255, (45, 80, 3)).astype(np.float32)
    out = PixelArt("DB32")(img)
    pal = {tuple(c) for c in PALETTES["DB32"].astype(np.uint8)}
    assert {tuple(c) for c in out.reshape(-1, 3)} <= pal


def test_hysteresis_suppresses_noise_flicker():
    rng = np.random.default_rng(1)
    base = rng.uniform(0, 255, (45, 80, 3)).astype(np.float32)

    def changed_pixels(filt):
        prev, total = None, 0
        for _ in range(30):
            out = filt(base + rng.normal(0, 6, base.shape).astype(np.float32))  # webcam-like noise
            if prev is not None:
                total += (out != prev).any(-1).sum()
            prev = out
        return total

    raw = changed_pixels(PixelArt("DB32", smoothing=1.0, hysteresis=0.0))
    calm = changed_pixels(PixelArt("DB32"))
    assert calm < raw * 0.1
