"""Procedural room geometry. Vertex layout: pos(3) normal(3) color(3)."""
import numpy as np

_FACES = [  # (normal, 4 corner signs) for a unit cube centred at origin, CCW from outside
    ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
    ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
    ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
    ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
    ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
]


def _quad(corners, normal, color, flip=False):
    c = [np.array(p, dtype=np.float32) for p in corners]
    idx = [0, 2, 1, 0, 3, 2] if flip else [0, 1, 2, 0, 2, 3]
    return [np.concatenate([c[i], np.array(normal, np.float32), np.array(color, np.float32)])
            for i in idx]


def box(center, size, color, inside=False):
    """Axis-aligned box. inside=True faces point inward (a room)."""
    cx, cy, cz = center
    hx, hy, hz = (s / 2 for s in size)
    verts = []
    for n, signs in _FACES:
        corners = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx, sy, sz in signs]
        normal = tuple(-v for v in n) if inside else n
        verts += _quad(corners, normal, color, flip=inside)
    return np.array(verts, dtype=np.float32)


def build_scene(width, height, depth):
    """Room occupying x∈[-w/2,w/2], y∈[-h/2,h/2], z∈[-depth,0] plus props."""
    parts = [box((0, 0, -depth / 2), (width, height, depth), (0.85, 0.82, 0.78), inside=True)]
    # Props: pillars standing on the floor, a floating cube that pops out of the screen.
    floor = -height / 2
    for x, z, s, hgt, col in [(-width * 0.28, -depth * 0.35, 8, height * 0.55, (0.75, 0.35, 0.3)),
                               (width * 0.30, -depth * 0.6, 10, height * 0.4, (0.3, 0.55, 0.75)),
                               (0.0, -depth * 0.85, 14, height * 0.7, (0.45, 0.7, 0.4))]:
        parts.append(box((x, floor + hgt / 2, z), (s, hgt, s), col))
    parts.append(box((width * 0.08, height * 0.05, 12), (9, 9, 9), (0.95, 0.75, 0.25)))
    return np.concatenate(parts)
