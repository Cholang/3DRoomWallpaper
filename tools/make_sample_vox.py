"""Generate assets/sample_village.vox: a small house, trees and a pond (MagicaVoxel axes: z up)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from room3d.vox import save_vox  # noqa: E402

GRASS, SAND, WALL, WOOD, GLASS, ROOF, LEAF, YELLOW, PINK, WATER = range(1, 11)
PALETTE = {GRASS: (96, 160, 72), SAND: (214, 190, 140), WALL: (236, 226, 204), WOOD: (120, 80, 50),
           GLASS: (150, 200, 230), ROOF: (178, 64, 52), LEAF: (58, 120, 60), YELLOW: (240, 210, 60),
           PINK: (230, 120, 170), WATER: (70, 130, 200)}
SX, SY, SZ = 48, 40, 30
v = {}

for x in range(SX):                                   # ground (front of scene is y = 0)
    for y in range(SY):
        v[(x, y, 0)] = GRASS
for y in range(0, 24):                                # path to the door
    for x in (12, 13):
        v[(x, y, 0)] = SAND
for x in range(24, 31):                               # pond
    for y in range(4, 10):
        if (x - 27) ** 2 / 9 + (y - 6.5) ** 2 / 9 <= 1.0:
            v[(x, y, 0)] = WATER

x0, x1, y0, y1 = 6, 19, 24, 35                        # house walls
for z in range(1, 10):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if x in (x0, x1) or y in (y0, y1):
                v[(x, y, z)] = WALL
for z in range(1, 5):                                 # door
    for x in (12, 13):
        v[(x, y0, z)] = WOOD
for x in (8, 9, 16, 17):                              # windows
    for z in (5, 6):
        v[(x, y0, z)] = GLASS
for i, z in enumerate(range(10, 16)):                 # stepped roof
    for x in range(x0 - 1 + i, x1 + 2 - i):
        for y in range(y0 - 1, y1 + 2):
            v[(x, y, z)] = ROOF


def tree(cx, cy, h, r):
    for z in range(1, h + 1):
        for x in (cx, cx + 1):
            for y in (cy, cy + 1):
                v[(x, y, z)] = WOOD
    cz = h + r - 1
    for x in range(cx - r, cx + r + 2):
        for y in range(cy - r, cy + r + 2):
            for z in range(cz - r, cz + r + 1):
                if (x - cx - 0.5) ** 2 + (y - cy - 0.5) ** 2 + (z - cz) ** 2 <= r * r:
                    v[(x, y, z)] = LEAF


tree(34, 14, 7, 5)
tree(41, 31, 5, 4)
tree(3, 8, 4, 3)
for i, (x, y) in enumerate([(5, 2), (8, 5), (17, 3), (20, 9), (37, 4), (44, 12), (22, 18), (30, 15)]):
    v[(x, y, 1)] = YELLOW if i % 2 else PINK

out = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_village.vox")
save_vox(out, (SX, SY, SZ), [(x, y, z, c) for (x, y, z), c in v.items()], PALETTE)
print(f"wrote {os.path.normpath(out)} ({len(v)} voxels)")
