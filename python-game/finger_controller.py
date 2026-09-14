"""
FINGER CONTROLLER - Webcam Index-Finger Control
================================================
A reusable module that watches the webcam, detects your hand with
MediaPipe, tracks your index fingertip, and turns its *movement*
into UP / DOWN / LEFT / RIGHT directions for the Snake game.

The direction is based on the MOTION of the finger (its movement
vector), NOT on where the finger happens to be on the screen:

    finger moves up    ->  "up"
    finger moves down  ->  "down"
    finger moves left  ->  "left"
    finger moves right ->  "right"

While the finger is still, or only jitters a few pixels, the Snake
keeps its current direction.

The controller runs on its own background thread so the game stays
smooth. It exposes a tiny interface:

    controller.start()
    direction = controller.get_direction()   # "up"/"down"/"left"/"right" or None
    controller.stop()

The Snake game does NOT need to know anything about MediaPipe.
"""

import contextlib
import os
import threading
import time
import urllib.request

import cv2
import numpy as np

from mediapipe import Image, ImageFormat
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

# ============================================================
# CONFIGURABLE SETTINGS (tune to the room / your webcam)
# ============================================================
FINGER_MOVE_THRESHOLD = 30       # min pixels of finger motion needed to change direction
DIRECTION_COOLDOWN = 0.15        # seconds between accepted direction changes (debounce)
SMOOTHING_FACTOR = 0.5           # 0..1 finger smoothing (1 = use raw position, 0 = freeze)
CAMERA_ID = 0                    # which webcam to use (0 = default)
CAMERA_WIDTH = 640               # capture width in pixels
CAMERA_HEIGHT = 480              # capture height in pixels
SHOW_CAMERA = True               # show a small camera preview window
DEBUG_MODE = False               # print extra info to the console
HAND_CONFIDENCE = 0.5            # min confidence to accept a hand / keep tracking it

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
MODEL_FILE = "hand_landmarker.task"

INDEX_FINGER_TIP = 8             # MediaPipe hand landmark index for the index finger tip

# Hand skeleton lines used for the camera preview only
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),              # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),              # index finger
    (5, 9), (9, 10), (10, 11), (11, 12),         # middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),       # ring finger
    (13, 17), (17, 18), (18, 19), (19, 20),      # pinky
    (0, 17),
]

# Screen arrow offsets used on the camera preview
ARROWS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

OPPOSITE = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}


@contextlib.contextmanager
def _quiet_stderr():
    """Temporarily point the C++ error stream (fd 2) at the null device.

    MediaPipe + TensorFlow Lite print a few INFO / WARNING lines to stderr
    when a hand model is created. They are harmless, but they look scary in
    a kids' console, so we hide them during that one moment."""
    try:
        null_fd = os.open(os.devnull, os.O_WRONLY)
        saved_fd = os.dup(2)
        os.dup2(null_fd, 2)
        os.close(null_fd)
        yield
    finally:
        try:
            os.dup2(saved_fd, 2)
            os.close(saved_fd)
        except Exception:
            pass


class FingerController:
    """Track the index finger tip with the webcam and expose its motion
    as a Snake direction. Runs in its own background thread."""

    def __init__(self, camera_id=None, show_camera=None, debug=None, threshold=None,
                 cooldown=None, smoothing=None):
        self.camera_id = camera_id if camera_id is not None else CAMERA_ID
        self.show_camera = show_camera if show_camera is not None else SHOW_CAMERA
        self.debug = debug if debug is not None else DEBUG_MODE
        self.threshold = threshold if threshold is not None else FINGER_MOVE_THRESHOLD
        self.cooldown = cooldown if cooldown is not None else DIRECTION_COOLDOWN
        self.smoothing = smoothing if smoothing is not None else SMOOTHING_FACTOR

        self._running = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

        self._cap = None
        self._landmarker = None

        # ---- Tracking state (guarded by self._lock) ----
        self._direction = None          # last direction we told the game (for display)
        self._pending = False           # a NEW direction is ready to be handed out
        self._last_emit = 0.0           # time of the last accepted direction change
        self._anchor = None             # reference point used to measure finger motion
        self._smoothed = None           # EMA-filtered fingertip position
        self._prev_pos = None           # raw fingertip position of the previous frame
        self._hand_seen = False
        self._webcam_ok = False
        self._model_ok = False
        self._error = None
        self._read_failures = 0

        self._model_path = self._resolve_model_path()
        self._window_name = "Finger Control Camera"

        self._debug_info = {
            "hand": False,
            "finger": False,
            "direction": None,
            "dx": 0.0,                  # raw finger motion since last frame
            "dy": 0.0,
            "move_dx": 0.0,             # smoothed motion since the last direction change
            "move_dy": 0.0,
            "threshold": self.threshold,
            "cooldown": self.cooldown,
        }

    # ============================================================
    # PUBLIC API
    # ============================================================
    def start(self):
        """Start the webcam + hand tracking. Returns True if OK.

        If the webcam or the hand model cannot be used, the controller
        stores an error message and returns False, so the game can keep
        running with the keyboard instead of crashing."""
        if self._running.is_set():
            return True
        if not self._ensure_model():
            return False
        if not self._open_webcam():
            return False
        if not self._init_landmarker():
            return False
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if self.debug:
            print("[FingerController] started (camera {}, threshold {}px)".format(
                self.camera_id, self.threshold))
        return True

    def stop(self):
        """Stop the webcam thread and release all resources."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._release_resources()

    def get_direction(self):
        """Return the Snake direction for a NEW finger gesture, or None.

        A direction is handed out only once (like a key press). While the
        finger is still, or repeats the same direction, the game just keeps
        doing what it already did, and the keyboard keeps working normally."""
        with self._lock:
            if self._pending:
                self._pending = False
                return self._direction
            return None

    def get_last_direction(self):
        """The most recent direction, for display only (never cleared)."""
        with self._lock:
            return self._direction

    def is_hand_detected(self):
        """True if a hand is currently visible to the camera."""
        with self._lock:
            return self._hand_seen

    def is_available(self):
        """True if the webcam and the hand model are working."""
        with self._lock:
            return self._webcam_ok and self._model_ok

    def is_running(self):
        """True if the controller thread is running."""
        return self._running.is_set()

    def get_error(self):
        """Human readable error if the controller could not start."""
        with self._lock:
            return self._error

    def get_debug_info(self):
        """A copy of the internal status (hand, dx, dy, direction...)."""
        with self._lock:
            return dict(self._debug_info)

    # ============================================================
    # SETUP HELPERS
    # ============================================================
    def _resolve_model_path(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(folder, MODEL_FILE)

    def _ensure_model(self):
        """Make sure hand_landmarker.task exists next to this file.
        Downloads it once if needed (free official Google model)."""
        if os.path.exists(self._model_path):
            return True
        try:
            if self.debug:
                print("[FingerController] downloading hand landmarker model ...")
            urllib.request.urlretrieve(MODEL_URL, self._model_path)
            return os.path.exists(self._model_path)
        except Exception as exc:
            with self._lock:
                self._error = "Hand model download failed: {}".format(exc)
            return False

    def _open_webcam(self):
        try:
            cap = cv2.VideoCapture(self.camera_id)
            if not cap.isOpened():
                cap.release()
                with self._lock:
                    self._webcam_ok = False
                    self._error = ("Webcam unavailable (camera not found or in use). "
                                   "The game will use the keyboard only.")
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self._cap = cap
            with self._lock:
                self._webcam_ok = True
            return True
        except Exception as exc:
            with self._lock:
                self._webcam_ok = False
                self._error = "Webcam error: {}".format(exc)
            return False

    def _init_landmarker(self):
        try:
            base_options = mp_tasks.BaseOptions(model_asset_path=self._model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=HAND_CONFIDENCE,
                min_tracking_confidence=HAND_CONFIDENCE,
            )
            with _quiet_stderr():
                self._landmarker = vision.HandLandmarker.create_from_options(options)
                # Warm the model up now (hidden) so the very first camera
                # frame is not slowed down by model loading.
                black = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
                warm = Image(image_format=ImageFormat.SRGB, data=black)
                self._landmarker.detect_for_video(warm, 1)
            with self._lock:
                self._model_ok = True
            return True
        except Exception as exc:
            with self._lock:
                self._model_ok = False
                self._error = "MediaPipe hand tracking failed to start: {}".format(exc)
            return False

    # ============================================================
    # MAIN LOOP (runs on the background thread)
    # ============================================================
    def _run(self):
        cap = self._cap
        landmarker = self._landmarker
        ts = 1000
        try:
            while self._running.is_set():
                ok = False
                frame = None
                if cap is not None:
                    ok, frame = cap.read()

                if not ok:
                    # Camera hiccup or disconnect: do NOT mess with the direction,
                    # just mark the hand as gone and try to recover quietly.
                    self._mark_hand_lost()
                    self._read_failures += 1
                    if self._read_failures > 60:
                        cap = self._reopen_webcam() or self._cap
                    time.sleep(0.05)
                    continue

                self._read_failures = 0

                # Mirror the view so it feels natural (like a mirror, not a friend).
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                ts += 33  # strictly increasing timestamp for the video landmarker
                mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(mp_image, ts)

                self._process_hand(result, frame.shape[0], frame.shape[1])

                if self.show_camera:
                    self._show_frame(self._annotate(frame, result))

                time.sleep(0.003)  # keep CPU usage polite
        except Exception as exc:
            with self._lock:
                self._error = "Camera loop error: {}".format(exc)
            self._mark_hand_lost()
        finally:
            self._running.clear()
            self._release_resources()

    def _reopen_webcam(self):
        """Try to reconnect to the camera after it disappeared."""
        old = self._cap
        try:
            new = cv2.VideoCapture(self.camera_id)
            if new.isOpened():
                new.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                new.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                self._cap = new
                if old is not None:
                    old.release()
                with self._lock:
                    self._webcam_ok = True
                self._read_failures = 0
                if self.debug:
                    print("[FingerController] camera reconnected")
                return new
            new.release()
        except Exception:
            pass
        with self._lock:
            self._webcam_ok = False
        if self.debug:
            print("[FingerController] camera still unavailable, retrying ...")
        return None

    # ============================================================
    # HAND / FINGER TRACKING
    # ============================================================
    def _process_hand(self, result, frame_h, frame_w):
        with self._lock:
            if result is not None and result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                tip = landmarks[INDEX_FINGER_TIP]
                x = tip.x * frame_w
                y = tip.y * frame_h
                self._debug_info["hand"] = True
                self._hand_seen = True
                self._update_tracking(x, y)
            else:
                self._mark_hand_lost()

    def _update_tracking(self, x, y):
        """Live tracking: measure the fingertip motion and decide a direction."""
        # Raw finger motion since the previous frame (diagnostic / debug only).
        if self._prev_pos is not None:
            self._debug_info["dx"] = x - self._prev_pos[0]
            self._debug_info["dy"] = y - self._prev_pos[1]
        self._prev_pos = (x, y)

        # First frame with a hand: just remember the starting spot.
        if self._smoothed is None:
            self._smoothed = (x, y)
            self._anchor = (x, y)
            self._debug_info["finger"] = True
            self._debug_info["move_dx"] = 0.0
            self._debug_info["move_dy"] = 0.0
            return

        # Smooth the fingertip position so tiny camera noise is ignored.
        sx = self.smoothing * x + (1 - self.smoothing) * self._smoothed[0]
        sy = self.smoothing * y + (1 - self.smoothing) * self._smoothed[1]
        self._smoothed = (sx, sy)

        # Cumulative motion since the last accepted direction change.
        # ("dx = current_position - reference_position")
        dx = sx - self._anchor[0]
        dy = sy - self._anchor[1]
        self._debug_info["move_dx"] = dx
        self._debug_info["move_dy"] = dy
        self._debug_info["finger"] = True

        # Dominant axis decides the direction; the threshold ignores small motions.
        if abs(dx) >= abs(dy):
            if abs(dx) >= self.threshold:
                self._emit("right" if dx > 0 else "left")
        else:
            if abs(dy) >= self.threshold:
                self._emit("down" if dy > 0 else "up")

    def _emit(self, new_dir):
        """Accept a new direction if the cooldown has passed and it is not
        the exact opposite of the previous one (classic Snake rule)."""
        now = time.time()
        if now - self._last_emit < self.cooldown:
            return  # debounce: wait for the finger movement to settle

        if new_dir == OPPOSITE.get(self._direction):
            # Instant reversal is not allowed; restart the motion meter from here.
            self._anchor = self._smoothed
            return

        self._direction = new_dir
        self._pending = True            # hand this direction to the game once
        self._last_emit = now
        self._anchor = self._smoothed  # fresh reference point for the next gesture
        self._debug_info["direction"] = new_dir
        if self.debug:
            print("[FingerController] direction: {}".format(new_dir.upper()))

    def _mark_hand_lost(self):
        """The hand is gone (temporarily). Keep the last direction, reset the
        motion meter so the hand does not 'teleport' into a wrong command."""
        was_lost = not self._hand_seen and self._smoothed is None
        self._hand_seen = False
        self._debug_info["hand"] = False
        if was_lost:
            return
        self._smoothed = None
        self._anchor = None
        self._prev_pos = None
        self._debug_info["finger"] = False
        self._debug_info["dx"] = 0.0
        self._debug_info["dy"] = 0.0
        self._debug_info["move_dx"] = 0.0
        self._debug_info["move_dy"] = 0.0
        if self.debug:
            print("[FingerController] hand lost - keeping direction")

    # ============================================================
    # CAMERA PREVIEW (optional)
    # ============================================================
    def _annotate(self, frame, result):
        """Draw the hand skeleton, the fingertip, and a direction arrow."""
        h, w = frame.shape[:2]

        with self._lock:
            direction = self._direction
            hand_seen = self._hand_seen
            dx = self._debug_info["dx"]
            dy = self._debug_info["dy"]

        if result is not None and result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            points = [(int(landmark.x * w), int(landmark.y * h))
                      for landmark in landmarks]
            for a, b in CONNECTIONS:
                cv2.line(frame, points[a], points[b], (255, 200, 80), 2)
            for i, p in enumerate(points):
                if i == INDEX_FINGER_TIP:
                    cv2.circle(frame, p, 9, (0, 255, 0), -1)
                    cv2.circle(frame, p, 13, (50, 255, 50), 2)
                else:
                    cv2.circle(frame, p, 2, (255, 255, 255), -1)

            # Direction arrow coming out of the fingertip
            arrow = ARROWS.get(direction)
            if arrow is not None:
                tip = points[INDEX_FINGER_TIP]
                end = (tip[0] + arrow[0] * 45, tip[1] + arrow[1] * 45)
                cv2.arrowedLine(frame, tip, end, (0, 200, 255), 4,
                                tipLength=0.4)

        # Status text in the top-left corner
        hand_text = "HAND: DETECTED" if hand_seen else "HAND: NOT FOUND"
        dir_text = direction.upper() if direction else "NONE (finger still)"
        lines = [hand_text, "DIRECTION: " + dir_text]
        if DEBUG_MODE:
            lines += ["dx: {:.1f}".format(dx), "dy: {:.1f}".format(dy)]
        for i, line in enumerate(lines):
            color = (0, 255, 0) if hand_seen else (255, 80, 80)
            cv2.putText(frame, line, (10, 24 + i * 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                        cv2.LINE_AA)
        return frame

    def _show_frame(self, frame):
        """Show the camera preview. If the preview ever fails (for example the
        window was closed), quietly stop showing it and keep tracking."""
        try:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            cv2.imshow(self._window_name, frame)
            cv2.waitKey(1)
        except Exception:
            self.show_camera = False

    # ============================================================
    # CLEANUP
    # ============================================================
    def _release_resources(self):
        cap = self._cap
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
            self._cap = None
        landmarker = self._landmarker
        if landmarker is not None:
            try:
                landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        if self.show_camera:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
        with self._lock:
            self._webcam_ok = False
            self._model_ok = False
            self._hand_seen = False


# ============================================================
# STANDALONE TEST (run this file directly to debug the controller)
# ============================================================
if __name__ == "__main__":
    controller = FingerController(show_camera=True, debug=True)
    print("Starting finger controller. Press Ctrl+C to stop.")
    print("Move your index finger up / down / left / right.")
    print("  Up        -> make the finger go up")
    print("  Down      -> make the finger go down")
    print("  Left      -> make the finger go left")
    print("  Right     -> make the finger go right")
    if not controller.start():
        print("ERROR:", controller.get_error())
        raise SystemExit(1)
    try:
        last = None
        while True:
            info = controller.get_debug_info()
            if info["direction"] is not None and info["direction"] != last:
                print(">>> DIRECTION:", info["direction"].upper())
                last = info["direction"]
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        controller.stop()
        print("Stopped.")