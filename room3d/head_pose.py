"""Convert eye pixel positions into a 3D eye position in screen space."""
import math


def focal_px(img_w, hfov_deg):
    return (img_w / 2) / math.tan(math.radians(hfov_deg) / 2)


def eye_position_cm(left_px, right_px, img_w, img_h, hfov_deg, ipd_cm, cam_offset_cm,
                    screen_half_h_cm):
    """Estimate the midpoint between the eyes in screen space (cm).

    left_px/right_px: (x, y) pixel coords of the two pupils in the *raw* (un-mirrored)
    camera image. Pinhole model: distance = f * real_ipd / pixel_ipd.
    The webcam sits `cam_offset_cm` above the top edge of the screen.
    """
    f = focal_px(img_w, hfov_deg)
    ipd_px = math.hypot(right_px[0] - left_px[0], right_px[1] - left_px[1])
    if ipd_px < 1e-3:
        return None
    z = f * ipd_cm / ipd_px
    mx = (left_px[0] + right_px[0]) / 2
    my = (left_px[1] + right_px[1]) / 2
    # Raw image is mirrored relative to the viewer: image-right is the viewer's left.
    x = -(mx - img_w / 2) * z / f
    y_cam = -(my - img_h / 2) * z / f           # +y up, relative to camera axis
    y = y_cam + screen_half_h_cm + cam_offset_cm  # camera is above screen centre
    return (x, y, z)
