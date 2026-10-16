from dataclasses import dataclass


@dataclass
class Config:
    # --- Physical setup (cm). Measure these once for best realism. ---
    screen_width_cm: float = 34.5      # 16" 16:10 laptop panel (use --screen-width-cm to override)
    cam_offset_cm: float = 1.5         # webcam height above the top edge of the screen
    room_depth_cm: float = 120.0       # how far the room extends behind the screen

    # --- Webcam ---
    camera_index: int = 0
    cam_width: int = 1280
    cam_height: int = 720
    hfov_deg: float = 70.0             # Logi C920/C922 ~70 deg horizontal at 16:9
    ipd_cm: float = 6.3                # average interpupillary distance

    # --- Behaviour ---
    default_eye_cm: tuple = (0.0, 0.0, 60.0)  # used when no face is visible
    smoothing_min_cutoff: float = 1.2  # One-Euro filter: lower = smoother
    smoothing_beta: float = 0.05       # higher = less lag on fast moves
    parallax_gain: float = 1.0         # >1 exaggerates the effect
    lost_face_return_s: float = 1.5    # time to ease back to default pose
    approach_zoom: float = 0.0         # experimental hack; 0 = pure window physics (default)
    mode: str = "frame"                # "frame": screen = camera frame glued to your face; "window": fixed glass window
    move_scale: float = 2.0            # frame mode: world cm moved per real cm of head movement
    frame_fov_deg: float = 0.0         # frame mode: horizontal FOV; 0 = derive from screen size at default distance
    start_cam_cm: tuple = (0.0, -25.0, 100.0)  # frame mode: camera at the default pose (1m in front of the room opening, 25cm below centre)
