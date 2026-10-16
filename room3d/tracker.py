"""Background webcam face tracker producing a smoothed eye position."""
import threading
import time

from .config import Config
from .head_pose import eye_position_cm
from .smoothing import OneEuro


class HeadTracker:
    def __init__(self, cfg: Config, screen_half_h_cm: float):
        self.cfg = cfg
        self.half_h = screen_half_h_cm
        self._eye = tuple(cfg.default_eye_cm)
        self._seen_t = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._filters = [OneEuro(cfg.smoothing_min_cutoff, cfg.smoothing_beta) for _ in range(3)]
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def latest(self):
        """Eye position (cm). Eases back to the default pose if the face is lost."""
        with self._lock:
            eye, seen = self._eye, self._seen_t
        lost = time.time() - seen
        if lost > 0.3:
            k = min(1.0, (lost - 0.3) / self.cfg.lost_face_return_s)
            d = self.cfg.default_eye_cm
            eye = tuple(e + (t - e) * k for e, t in zip(eye, d))
        return eye

    def _run(self):
        import cv2
        import mediapipe as mp

        cfg = self.cfg
        cap = cv2.VideoCapture(cfg.camera_index, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") and
                               __import__("sys").platform == "win32" else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.cam_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.cam_height)
        mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5)
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                h, w = frame.shape[:2]
                res = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if not res.multi_face_landmarks:
                    continue
                lm = res.multi_face_landmarks[0].landmark
                # 468 / 473 = iris centres (needs refine_landmarks=True).
                # In the raw image, 473 (subject's left eye) has the larger x.
                a, b = lm[468], lm[473]
                pos = eye_position_cm((a.x * w, a.y * h), (b.x * w, b.y * h), w, h,
                                      cfg.hfov_deg, cfg.ipd_cm, cfg.cam_offset_cm, self.half_h)
                if pos is None:
                    continue
                t = time.time()
                smooth = tuple(f(v, t) for f, v in zip(self._filters, pos))
                with self._lock:
                    self._eye, self._seen_t = smooth, t
        finally:
            cap.release()
            mesh.close()
