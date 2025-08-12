# https://github.com/JEOresearch/EyeTracker/tree/main/HeadTracker
import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import pyautogui
import math
import threading
import time
import keyboard

class OneEuroFilter:
    def __init__(self, min_cutoff=1.5, beta=0.03, d_cutoff=1.0, freq=60.0):
        self.min_cutoff = float(min_cutoff)  # Hz
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.freq = float(freq)
        self.x_prev = None
        self.dx_prev = None

    def _alpha(self, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x):
        # derivative
        if self.x_prev is None:
            dx = 0.0
        else:
            dx = (x - self.x_prev) * self.freq

        # smooth derivative
        if self.dx_prev is None:
            dx_hat = dx
        else:
            a_d = self._alpha(self.d_cutoff)
            dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        # dynamic cutoff
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff)

        # smooth signal
        if self.x_prev is None:
            x_hat = x
        else:
            x_hat = a * x + (1 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat


class HeadMouseTracker:
    FACE_OUTLINE_INDICES = [
        10, 338, 297, 332, 284, 251, 389, 356,
        454, 323, 361, 288, 397, 365, 379, 378,
        400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21,
        54, 103, 67, 109
    ]
    LANDMARKS = { "left": 234, "right": 454, "top": 10, "bottom": 152, "front": 1 }

    def __init__(
        self,
        camera_index: int = 0,
        filter_length: int = 40,
        yawDegrees: float = 20.0,
        pitchDegrees: float = 10.0,
        euro_min_cutoff: float = 1.2,
        euro_beta: float = 0.02,
        euro_freq: float = 60.0
    ):
        self.cap = None
        self.camera_index = camera_index
        self.filter_length = filter_length
        self.yawDegrees = yawDegrees
        self.pitchDegrees = pitchDegrees

        # Screen info
        self.MONITOR_WIDTH, self.MONITOR_HEIGHT = pyautogui.size()
        self.CENTER_X = self.MONITOR_WIDTH // 2
        self.CENTER_Y = self.MONITOR_HEIGHT // 2

        # State
        self.mouse_control_enabled = True
        self.calibration_offset_yaw = 0.0
        self.calibration_offset_pitch = 0.0
        self.raw_yaw_deg = 180.0
        self.raw_pitch_deg = 180.0

        # Buffers
        self.ray_origins = deque(maxlen=self.filter_length)
        self.ray_directions = deque(maxlen=self.filter_length)

        # Smoothing filters (screen coords)
        self.filt_x = OneEuroFilter(min_cutoff=euro_min_cutoff, beta=euro_beta, d_cutoff=1.0, freq=euro_freq)
        self.filt_y = OneEuroFilter(min_cutoff=euro_min_cutoff, beta=euro_beta, d_cutoff=1.0, freq=euro_freq)

        # Shared cursor target
        self.mouse_target = [self.CENTER_X, self.CENTER_Y]
        self.mouse_lock = threading.Lock()

        # Threads / control
        self._stop_event = threading.Event()
        self._mouse_thread = None
        self._loop_thread = None

        # MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = None

    # ---------- Public API ----------
    def start(self, block: bool = True):
        """Start tracking. If block=True, runs in the current thread until stopped."""
        if self.face_mesh is None:
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open camera index {self.camera_index}")

        self._stop_event.clear()

        # Mouse mover thread
        self._mouse_thread = threading.Thread(target=self._mouse_mover, daemon=True)
        self._mouse_thread.start()

        if block:
            # Run processing loop here
            self._process_loop()
        else:
            # Spawn processing in background
            self._loop_thread = threading.Thread(target=self._process_loop, daemon=True)
            self._loop_thread.start()

    def stop(self):
        """Signal threads to stop and clean up resources."""
        self._stop_event.set()
        time.sleep(0.05)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=1.0)
        if self._mouse_thread and self._mouse_thread.is_alive():
            self._mouse_thread.join(timeout=1.0)

        # Release camera and windows
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        # Release MediaPipe
        if self.face_mesh is not None:
            try:
                self.face_mesh.close()
            except Exception:
                pass
            self.face_mesh = None

    def toggle_mouse_control(self):
        self.mouse_control_enabled = not self.mouse_control_enabled
        print(f"[Mouse Control] {'Enabled' if self.mouse_control_enabled else 'Disabled'}")

    def calibrate_center(self):
        """Call when user is looking at screen center."""
        self.calibration_offset_yaw = 180.0 - self.raw_yaw_deg
        self.calibration_offset_pitch = 180.0 - self.raw_pitch_deg
        print(f"[Calibrated] Offset Yaw: {self.calibration_offset_yaw:.2f}, Offset Pitch: {self.calibration_offset_pitch:.2f}")

    # ---------- Internal ----------
    def _mouse_mover(self):
        # You can tune the rate and interpolation here if needed
        while not self._stop_event.is_set():
            with self.mouse_lock:
                x, y = self.mouse_target
            if self.mouse_control_enabled:
                pyautogui.moveTo(x, y)
            time.sleep(0.01)

    @staticmethod
    def _landmark_to_np(landmark, w, h):
        return np.array([landmark.x * w, landmark.y * h, landmark.z * w])

    def _process_loop(self):
        while not self._stop_event.is_set() and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0].landmark
                landmarks_frame = np.zeros_like(frame)  # Black canvas

                # Draw landmarks (optional)
                for i, landmark in enumerate(face_landmarks):
                    pt = self._landmark_to_np(landmark, w, h)
                    x, y = int(pt[0]), int(pt[1])
                    if 0 <= x < w and 0 <= y < h:
                        color = (155,155,155) if i in self.FACE_OUTLINE_INDICES else (255,25,10)
                        cv2.circle(landmarks_frame, (x, y), 3, color, -1)
                        frame[y, x] = (255,255,255)

                # Key landmarks
                key_points = {}
                for name, idx in self.LANDMARKS.items():
                    pt = self._landmark_to_np(face_landmarks[idx], w, h)
                    key_points[name] = pt
                    x, y = int(pt[0]), int(pt[1])
                    cv2.circle(frame, (x, y), 4, (0,0,0), -1)

                left   = key_points["left"]
                right  = key_points["right"]
                top    = key_points["top"]
                bottom = key_points["bottom"]
                front  = key_points["front"]

                # Face axes
                right_axis = (right - left);   right_axis /= np.linalg.norm(right_axis)
                up_axis    = (top - bottom);   up_axis /= np.linalg.norm(up_axis)
                forward_axis = np.cross(right_axis, up_axis); forward_axis /= np.linalg.norm(forward_axis)
                forward_axis = -forward_axis  # ensure outward

                center = (left + right + top + bottom + front) / 5.0

                # Head-aligned cube (for viz)
                half_width  = np.linalg.norm(right - left) / 2.0
                half_height = np.linalg.norm(top - bottom) / 2.0
                half_depth  = 80.0

                def corner(x_sign, y_sign, z_sign):
                    return (center
                        + x_sign * half_width  * right_axis
                        + y_sign * half_height * up_axis
                        + z_sign * half_depth  * forward_axis)

                cube_corners = [
                    corner(-1,  1, -1), corner( 1,  1, -1),
                    corner( 1, -1, -1), corner(-1, -1, -1),
                    corner(-1,  1,  1), corner( 1,  1,  1),
                    corner( 1, -1,  1), corner(-1, -1,  1),
                ]

                def project(pt3d): return int(pt3d[0]), int(pt3d[1])

                edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
                cc2d = [project(p) for p in cube_corners]
                for i,j in edges:
                    cv2.line(frame, cc2d[i], cc2d[j], (255,125,35), 2)

                # Smooth forward ray inputs
                self.ray_origins.append(center)
                self.ray_directions.append(forward_axis)
                avg_origin    = np.mean(self.ray_origins, axis=0)
                avg_direction = np.mean(self.ray_directions, axis=0)
                avg_direction /= np.linalg.norm(avg_direction)

                # Angles (your original math)
                reference_forward = np.array([0, 0, -1])
                xz_proj = np.array([avg_direction[0], 0, avg_direction[2]])
                xz_proj /= np.linalg.norm(xz_proj)
                yaw_rad = math.acos(np.clip(np.dot(reference_forward, xz_proj), -1.0, 1.0))
                if avg_direction[0] < 0:
                    yaw_rad = -yaw_rad

                yz_proj = np.array([0, avg_direction[1], avg_direction[2]])
                yz_proj /= np.linalg.norm(yz_proj)
                pitch_rad = math.acos(np.clip(np.dot(reference_forward, yz_proj), -1.0, 1.0))
                if avg_direction[1] > 0:
                    pitch_rad = -pitch_rad

                yaw_deg   = np.degrees(yaw_rad)
                pitch_deg = np.degrees(pitch_rad)

                # Convert (original logic)
                if yaw_deg < 0:
                    yaw_deg = abs(yaw_deg)
                elif yaw_deg < 180:
                    yaw_deg = 360 - yaw_deg
                if pitch_deg < 0:
                    pitch_deg = 360 + pitch_deg

                self.raw_yaw_deg = yaw_deg
                self.raw_pitch_deg = pitch_deg

                # Apply calibration
                yaw_deg   += self.calibration_offset_yaw
                pitch_deg += self.calibration_offset_pitch

                # Map to screen
                screen_x = int(((yaw_deg - (180 - self.yawDegrees)) / (2 * self.yawDegrees)) * self.MONITOR_WIDTH)
                screen_y = int(((180 + self.pitchDegrees - pitch_deg) / (2 * self.pitchDegrees)) * self.MONITOR_HEIGHT)

                # Clamp
                screen_x = max(10, min(self.MONITOR_WIDTH  - 10, screen_x))
                screen_y = max(10, min(self.MONITOR_HEIGHT - 10, screen_y))

                # One Euro smoothing (only change vs original)
                smooth_x = int(round(self.filt_x.filter(screen_x)))
                smooth_y = int(round(self.filt_y.filter(screen_y)))

                # Update target for mouse mover thread
                if self.mouse_control_enabled:
                    with self.mouse_lock:
                        self.mouse_target[0] = smooth_x
                        self.mouse_target[1] = smooth_y

                # Draw forward ray (viz)
                ray_length = 2.5 * half_depth
                ray_end = avg_origin - avg_direction * ray_length
                cv2.line(frame, project(avg_origin), project(ray_end), (15,255,0), 3)
                cv2.line(landmarks_frame, project(avg_origin), project(ray_end), (15,255,0), 3)

                # Debug print (optional)
                # print(f"Screen (raw): ({screen_x}, {screen_y}) | smooth: ({smooth_x}, {smooth_y})")

                cv2.imshow("Head-Aligned Cube", frame)
                cv2.imshow("Facial Landmarks", landmarks_frame)

                # Hotkeys (same as your original behavior)
                if keyboard.is_pressed('f7'):
                    self.toggle_mouse_control()
                    time.sleep(0.3)  # debounce

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop()
                    return
                elif key == ord('c'):
                    self.calibrate_center()

            else:
                # No face — still show frames (optional)
                cv2.imshow("Head-Aligned Cube", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop()
                    return

        # graceful stop
        self.stop()


def main():
    tracker = HeadMouseTracker(
        camera_index=0,
        filter_length=40,
        yawDegrees=20.0,
        pitchDegrees=10.0,
        euro_min_cutoff=1.2,
        euro_beta=0.02,
        euro_freq=60.0
    )
    try:
        tracker.start(block=True)  # runs until 'q' pressed or tracker.stop() called
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop()


if __name__ == "__main__":
    main()
