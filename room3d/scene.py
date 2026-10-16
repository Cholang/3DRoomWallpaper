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


WORLD_ROOM = (220.0, 140.0, 300.0)  # width, height, depth (cm)


def build_world_scene(width=WORLD_ROOM[0], height=WORLD_ROOM[1], depth=WORLD_ROOM[2], props=True):
    """Fixed, real-world-sized room (cm): x,y centred, z in [-depth, 0]."""
    floor = -height / 2
    parts = [box((0, 0, -depth / 2), (width, height, depth), (0.85, 0.82, 0.78), inside=True)]
    if not props:
        return parts[0]
    for x, z, s, hgt, col in [(-50, -130, 24, 90, (0.75, 0.35, 0.3)),
                              (60, -190, 30, 60, (0.3, 0.55, 0.75)),
                              (0, -270, 36, 100, (0.45, 0.7, 0.4))]:
        parts.append(box((x, floor + hgt / 2, z), (s, hgt, s), col))
    parts.append(box((15, -5, -80), (20, 20, 20), (0.95, 0.75, 0.25)))
    return np.concatenate(parts)


def place_vox_model(pos, colors, voxel_cm=0.0, room=WORLD_ROOM, fill=(0.8, 0.8, 0.6)):
    """Mesh a voxel model, scaled to fit the room (unless voxel_cm > 0), centred in x,
    standing on the floor, centred in depth."""
    from .vox import voxel_mesh
    ext = pos.max(0) - pos.min(0) + 1
    if voxel_cm <= 0:
        voxel_cm = float(min(fill[0] * room[0] / ext[0], fill[1] * room[1] / ext[1], fill[2] * room[2] / ext[2]))
    lo = pos.min(0)
    offset = (-(lo[0] + ext[0] / 2) * voxel_cm,
              -room[1] / 2 - lo[1] * voxel_cm,
              -room[2] / 2 - (lo[2] + ext[2] / 2) * voxel_cm)
    return voxel_mesh(pos, colors, voxel_cm, offset), voxel_cm
