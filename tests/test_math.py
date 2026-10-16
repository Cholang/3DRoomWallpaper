import math

import numpy as np

from room3d.head_pose import eye_position_cm, focal_px
from room3d.projection import project
from room3d.smoothing import OneEuro

HW, HH = 30.0, 17.0


def test_screen_corner_maps_to_ndc_corner_for_any_eye():
    for eye in [(0, 0, 60), (15, -5, 40), (-20, 8, 90)]:
        x, y, _ = project((HW, HH, 0), eye, HW, HH)
        assert math.isclose(x, 1, abs_tol=1e-9) and math.isclose(y, 1, abs_tol=1e-9)


def test_deep_point_shifts_with_head_motion_and_near_point_against():
    # Window parallax: moving right, far objects slide right relative to the frame, near ones left.
    p = (0, 0, -50)
    x0, _, _ = project(p, (0, 0, 60), HW, HH)
    x1, _, _ = project(p, (15, 0, 60), HW, HH)
    assert x1 > x0
    n0 = project((0, 0, 20), (0, 0, 60), HW, HH)[0]
    n1 = project((0, 0, 20), (15, 0, 60), HW, HH)[0]
    assert n1 < n0


def test_point_on_screen_plane_does_not_move_when_head_moves():
    p = (10, 5, 0)
    a = project(p, (0, 0, 60), HW, HH)[:2]
    b = project(p, (20, -10, 45), HW, HH)[:2]
    # on-plane point stays at the same physical spot -> same NDC
    assert np.allclose(a, b, atol=1e-9)


def test_distance_from_ipd():
    f = focal_px(1280, 70)
    z_true = 60.0
    ipd_px = f * 6.3 / z_true
    cx, cy = 640, 360
    pos = eye_position_cm((cx - ipd_px / 2, cy), (cx + ipd_px / 2, cy), 1280, 720, 70, 6.3, 1.5, HH)
    assert math.isclose(pos[2], z_true, rel_tol=1e-6)
    assert math.isclose(pos[0], 0, abs_tol=1e-6)
    assert math.isclose(pos[1], HH + 1.5, abs_tol=1e-6)  # camera is above the screen


def test_head_right_gives_positive_x():
    # Viewer moves to their right -> appears on image-left (smaller pixel x).
    pos = eye_position_cm((300, 360), (340, 360), 1280, 720, 70, 6.3, 0, HH)
    assert pos[0] > 0


def test_one_euro_converges():
    f = OneEuro(1.0, 0.0)
    v = 0
    for i in range(200):
        v = f(10.0, i * 0.016)
    assert math.isclose(v, 10.0, abs_tol=1e-3)


def test_frame_mode_far_object_grows_when_head_moves_closer_and_fov_is_fixed():
    from room3d.projection import frame_camera
    rest = (0.0, 0.0, 60.0)
    start = (0.0, 0.0, 60.0)

    def width_pct(eye_z):
        mvp, _ = frame_camera((0, 0, eye_z), rest, 17.25, 1.6, 2.0, start)
        pts = []
        for x in (-18, 18):  # a 36 cm wide object at z = -270
            p = mvp @ np.array([x, 0, -270, 1.0])
            pts.append(p[0] / p[3])
        return abs(pts[1] - pts[0]) / 2 * 100

    assert width_pct(30) > width_pct(60) * 1.2     # approaching makes it clearly bigger
    assert width_pct(90) < width_pct(60)            # leaning back makes it smaller
    mvp, cam = frame_camera((0, 0, 60), rest, 17.25, 1.6, 2.0, start)
    assert np.allclose(cam, start)                  # rest pose = start camera
