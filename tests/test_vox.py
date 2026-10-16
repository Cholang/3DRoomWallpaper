import numpy as np

from room3d.vox import _rotation, load_vox, save_vox, voxel_mesh


def test_roundtrip_axes_and_palette(tmp_path):
    p = tmp_path / "t.vox"
    # one voxel at vox (x=1, y=2, z=3) with colour index 5
    save_vox(p, (4, 4, 4), [(1, 2, 3, 5)], {5: (255, 0, 0)})
    pos, col = load_vox(p)
    assert pos.tolist() == [[1, 3, -2]]          # (x, y, z)_vox -> (x, z, -y)
    assert np.allclose(col[0], [1, 0, 0])


def test_hidden_faces_are_culled():
    one = voxel_mesh(np.array([[0, 0, 0]]), np.ones((1, 3), np.float32))
    two = voxel_mesh(np.array([[0, 0, 0], [1, 0, 0]]), np.ones((2, 3), np.float32))
    assert len(one) == 6 * 6            # 6 faces x 2 triangles x 3 vertices
    assert len(two) == 10 * 6           # the shared face pair is dropped


def test_mesh_scale_and_offset():
    m = voxel_mesh(np.array([[0, 0, 0]]), np.ones((1, 3), np.float32), voxel_cm=5, offset=(10, 0, 0))
    assert m[:, 0].min() == 10 and m[:, 0].max() == 15


def test_rotation_identity_and_flip():
    assert (_rotation(4) == np.eye(3)).all()            # MagicaVoxel's identity byte
    assert (_rotation(4 | 16) == np.diag([-1, 1, 1])).all()


def test_sample_asset_loads():
    pos, col = load_vox("assets/sample_village.vox")
    assert len(pos) > 1000 and col.shape == (len(pos), 3)
