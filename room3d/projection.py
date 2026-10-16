"""Off-axis ("fish tank") projection math. Pure numpy, no GL needed.

Coordinate system (cm): origin at the screen centre, +x right, +y up,
+z toward the viewer. The screen is the plane z = 0; the room lies at z < 0.
"""
import numpy as np


def frustum(left, right, bottom, top, near, far):
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = 2 * near / (right - left)
    m[1, 1] = 2 * near / (top - bottom)
    m[0, 2] = (right + left) / (right - left)
    m[1, 2] = (top + bottom) / (top - bottom)
    m[2, 2] = -(far + near) / (far - near)
    m[2, 3] = -2 * far * near / (far - near)
    m[3, 2] = -1.0
    return m


def off_axis_projection(eye, half_w, half_h, near=1.0, far=1000.0):
    """Frustum whose near-plane window is the physical screen seen from `eye`."""
    ex, ey, ez = eye
    ez = max(float(ez), near * 1.01)
    s = near / ez
    return frustum((-half_w - ex) * s, (half_w - ex) * s,
                   (-half_h - ey) * s, (half_h - ey) * s, near, far)


def view_matrix(eye):
    m = np.eye(4)
    m[:3, 3] = -np.asarray(eye, dtype=np.float64)
    return m


def project(point, eye, half_w, half_h, near=1.0, far=1000.0):
    """Return NDC (x, y, z) of a world point. Handy for tests."""
    mvp = off_axis_projection(eye, half_w, half_h, near, far) @ view_matrix(eye)
    p = mvp @ np.append(np.asarray(point, dtype=np.float64), 1.0)
    return p[:3] / p[3]
