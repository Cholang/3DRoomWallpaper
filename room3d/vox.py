"""MagicaVoxel .vox loader (and a tiny writer used for tests / the sample scene).

Coordinates: MagicaVoxel is x right, y forward, z up. We convert to this project's
x right, y up, z toward the viewer: (x, y, z)_vox -> (x, z, -y).
"""
import struct

import numpy as np

from .scene import _FACES


def _read_string(buf, off):
    n = struct.unpack_from("<i", buf, off)[0]
    off += 4
    return buf[off:off + n].decode("utf-8", "replace"), off + n


def _read_dict(buf, off):
    n = struct.unpack_from("<i", buf, off)[0]
    off += 4
    d = {}
    for _ in range(n):
        k, off = _read_string(buf, off)
        v, off = _read_string(buf, off)
        d[k] = v
    return d, off


def _rotation(r):
    """Decode MagicaVoxel's packed rotation byte into a 3x3 integer matrix."""
    i0, i1 = r & 3, (r >> 2) & 3
    i2 = 3 - i0 - i1
    m = np.zeros((3, 3), dtype=np.int64)
    m[0, i0] = -1 if (r >> 4) & 1 else 1
    m[1, i1] = -1 if (r >> 5) & 1 else 1
    m[2, i2] = -1 if (r >> 6) & 1 else 1
    return m


def _default_palette():
    # Only used for files without an RGBA chunk (rare): a simple hue ramp.
    idx = np.arange(256)
    hue = (idx % 32) / 32.0
    val = 0.4 + 0.6 * ((idx // 32) / 7.0)
    rgb = np.stack([np.abs(hue * 6 - 3) - 1, 2 - np.abs(hue * 6 - 2), 2 - np.abs(hue * 6 - 4)], 1)
    return np.clip(rgb, 0, 1) * val[:, None]


def load_vox(path):
    """Return (positions int[N,3] in project axes, colors float[N,3] in 0..1)."""
    with open(path, "rb") as f:
        buf = f.read()
    if buf[:4] != b"VOX ":
        raise ValueError(f"{path}: not a MagicaVoxel .vox file")

    sizes, models, palette = [], [], None
    nodes = {}
    off = 8
    while off + 12 <= len(buf):
        cid = buf[off:off + 4]
        n_content = struct.unpack_from("<i", buf, off + 4)[0]
        c = off + 12
        if cid == b"MAIN":
            off = c + n_content  # children follow; keep scanning them flat
            continue
        if cid == b"SIZE":
            sizes.append(struct.unpack_from("<3i", buf, c))
        elif cid == b"XYZI":
            n = struct.unpack_from("<i", buf, c)[0]
            models.append(np.frombuffer(buf, dtype=np.uint8, count=n * 4, offset=c + 4).reshape(n, 4))
        elif cid == b"RGBA":
            palette = np.frombuffer(buf, dtype=np.uint8, count=1024, offset=c).reshape(256, 4)[:, :3] / 255.0
        elif cid == b"nTRN":
            nid = struct.unpack_from("<i", buf, c)[0]
            _, p = _read_dict(buf, c + 4)
            child, _res, _layer, n_frames = struct.unpack_from("<4i", buf, p)
            p += 16
            frame = {}
            if n_frames > 0:
                frame, p = _read_dict(buf, p)
            t = np.array([int(v) for v in frame.get("_t", "0 0 0").split()], dtype=np.int64)
            r = _rotation(int(frame["_r"])) if "_r" in frame else np.eye(3, dtype=np.int64)
            nodes[nid] = ("T", child, t, r)
        elif cid == b"nGRP":
            nid = struct.unpack_from("<i", buf, c)[0]
            _, p = _read_dict(buf, c + 4)
            n = struct.unpack_from("<i", buf, p)[0]
            nodes[nid] = ("G", list(struct.unpack_from(f"<{n}i", buf, p + 4)))
        elif cid == b"nSHP":
            nid = struct.unpack_from("<i", buf, c)[0]
            _, p = _read_dict(buf, c + 4)
            n = struct.unpack_from("<i", buf, p)[0]
            p += 4
            ids = []
            for _ in range(n):
                ids.append(struct.unpack_from("<i", buf, p)[0])
                _, p = _read_dict(buf, p + 4)
            nodes[nid] = ("S", ids)
        off = c + n_content  # any children follow immediately; scanned flat
    if not models:
        raise ValueError(f"{path}: no voxel data")
    pal = _default_palette() if palette is None else palette

    placed = []  # (positions int[N,3] in vox axes, color index[N])

    def place(mid, t, r):
        v = models[mid][:, :3].astype(np.int64)
        pivot = np.array(sizes[mid], dtype=np.int64) // 2
        placed.append(((v - pivot) @ r.T + t, models[mid][:, 3]))

    def walk(nid, t, r):
        node = nodes.get(nid)
        if node is None:
            return
        if node[0] == "T":
            walk(node[1], t + r @ node[2], r @ node[3])
        elif node[0] == "G":
            for ch in node[1]:
                walk(ch, t, r)
        else:
            for mid in node[1]:
                place(mid, t, r)

    if nodes:
        walk(0, np.zeros(3, dtype=np.int64), np.eye(3, dtype=np.int64))
    if not placed:  # old files without a scene graph: models at their own origin
        for mid in range(len(models)):
            placed.append((models[mid][:, :3].astype(np.int64), models[mid][:, 3]))

    pos = np.concatenate([p for p, _ in placed])
    cidx = np.concatenate([c for _, c in placed]).astype(np.int64)
    pos = np.stack([pos[:, 0], pos[:, 2], -pos[:, 1]], 1)       # vox -> project axes
    pos, keep = np.unique(pos, axis=0, return_index=True)       # overlapping models
    colors = pal[(cidx[keep] - 1) % 256]
    return pos, colors.astype(np.float32)


def voxel_mesh(pos, colors, voxel_cm=1.0, offset=(0.0, 0.0, 0.0)):
    """Merge voxels into one triangle list, emitting only faces not hidden by a neighbour.

    pos: int[N,3] cell indices (cell i spans [i, i+1]). Returns float32[M, 9] (pos, normal, color).
    """
    pos = np.asarray(pos, dtype=np.int64)
    lo = pos.min(0) - 1
    occ = np.zeros(tuple(pos.max(0) - lo + 2), dtype=bool)
    idx = pos - lo
    occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    out = []
    for normal, signs in _FACES:
        n = np.array(normal, dtype=np.int64)
        nb = idx + n
        exposed = ~occ[nb[:, 0], nb[:, 1], nb[:, 2]]
        if not exposed.any():
            continue
        centers = pos[exposed] + 0.5
        corners = np.array(signs, dtype=np.float64) * 0.5                    # 4 x 3
        quad = centers[:, None, :] + corners[None, :, :]                       # k x 4 x 3
        tri = quad[:, [0, 1, 2, 0, 2, 3], :].reshape(-1, 3)
        col = np.repeat(colors[exposed], 6, axis=0)
        nrm = np.broadcast_to(np.array(normal, dtype=np.float64), tri.shape)
        out.append(np.concatenate([tri * voxel_cm + np.asarray(offset), nrm, col], 1))
    return np.concatenate(out).astype(np.float32)


def save_vox(path, size, voxels, palette):
    """Write a single-model .vox. voxels: iterable of (x, y, z, color_index 1..255) in vox axes."""
    vox = np.asarray(list(voxels), dtype=np.uint8)
    rgba = np.zeros((256, 4), dtype=np.uint8)
    rgba[:, 3] = 255
    for i, rgb in palette.items():  # palette: {color_index: (r, g, b)}
        rgba[i - 1, :3] = rgb

    def chunk(cid, content):
        return cid + struct.pack("<ii", len(content), 0) + content

    body = (chunk(b"SIZE", struct.pack("<3i", *size)) +
            chunk(b"XYZI", struct.pack("<i", len(vox)) + vox.tobytes()) +
            chunk(b"RGBA", rgba.tobytes()))
    with open(path, "wb") as f:
        f.write(b"VOX " + struct.pack("<i", 150) + b"MAIN" + struct.pack("<ii", 0, len(body)) + body)
