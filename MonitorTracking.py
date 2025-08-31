"""Head Mouse Tracker using MediaPipe face detection

Based on: https://github.com/JEOresearch/EyeTracker/tree/main/HeadTracker
"""
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
    """One Euro Filter for smooth mouse movement"""

    def __init__(self, min_cutoff=1.5, beta=0.03, d_cutoff=1.0, freq=60.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.freq = float(freq)
        self.prev_x = None
        self.prev_dx = None

    def _alpha(self, cutoff):
        """Calculate alpha for filtering"""
        tau = 1.0 / (2.0 * math.pi * cutoff)
        dt = 1.0 / self.freq
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x):
        """Apply One Euro Filter to input value"""
        # Calculate derivative
        if self.prev_x is None:
            dx = 0.0
        else:
            dx = (x - self.prev_x) * self.freq

        # Smooth derivative
        if self.prev_dx is None:
            smooth_dx = dx
        else:
            alpha_d = self._alpha(self.d_cutoff)
            smooth_dx = alpha_d * dx + (1 - alpha_d) * self.prev_dx

        # Dynamic cutoff frequency
        cutoff = self.min_cutoff + self.beta * abs(smooth_dx)
        alpha = self._alpha(cutoff)

        # Smooth the signal
        if self.prev_x is None:
            smooth_x = x
        else:
            smooth_x = alpha * x + (1 - alpha) * self.prev_x

        # Store for next iteration
        self.prev_x = smooth_x
        self.prev_dx = smooth_dx
        return smooth_x


class HeadMouseTracker:
    """Head-based mouse control using facial landmarks"""

    # Face outline landmark indices for MediaPipe
    FACE_OUTLINE = [
        10, 338, 297, 332, 284, 251, 389, 356,
        454, 323, 361, 288, 397, 365, 379, 378,
        400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21,
        54, 103, 67, 109
    ]

    # Key facial landmarks
    LANDMARKS = {
        "left": 234, "right": 454, "top": 10,
        "bottom": 152, "front": 1
    }

    def __init__(
        self,
        camera_index=0,
        filter_length=40,
        yaw_degrees=20.0,
        pitch_degrees=10.0,
        euro_min_cutoff=None,
        euro_beta=None,
        euro_freq=None,
        fast_mode=False,
        allow_runtime_override=True
    ):
        # Camera settings
        self.cap = None
        self.camera_index = camera_index
        self.filter_length = filter_length
        self.yaw_range = yaw_degrees
        self.pitch_range = pitch_degrees
        self.fast_mode = fast_mode

        # Runtime override permission
        user_params = any([euro_min_cutoff, euro_beta, euro_freq])
        self.allow_override = allow_runtime_override and not user_params

        # Performance settings
        if fast_mode:
            # Fast mode: 200Hz, responsive
            self.mouse_sleep = 0.005
            euro_freq = euro_freq or 120.0
            euro_min_cutoff = euro_min_cutoff or 0.8
            euro_beta = euro_beta or 0.015
        else:
            # Power saving: 60Hz, smooth
            self.mouse_sleep = 0.016
            euro_freq = euro_freq or 45.0
            euro_min_cutoff = euro_min_cutoff or 1.5
            euro_beta = euro_beta or 0.03

        # Screen dimensions
        self.screen_w, self.screen_h = pyautogui.size()
        self.center_x = self.screen_w // 2
        self.center_y = self.screen_h // 2

        # Control state
        self.mouse_enabled = True
        self.cal_yaw = 0.0
        self.cal_pitch = 0.0
        self.raw_yaw = 180.0
        self.raw_pitch = 180.0

        # Smoothing buffers
        self.origins = deque(maxlen=self.filter_length)
        self.directions = deque(maxlen=self.filter_length)

        # Store filter parameters
        self.euro_freq = euro_freq
        self.euro_cutoff = euro_min_cutoff
        self.euro_beta = euro_beta

        # Smoothing filters
        self.filter_x = OneEuroFilter(euro_min_cutoff, euro_beta, 1.0, euro_freq)
        self.filter_y = OneEuroFilter(euro_min_cutoff, euro_beta, 1.0, euro_freq)

        # Mouse target coordinates
        self.mouse_target = [self.center_x, self.center_y]
        self.mouse_lock = threading.Lock()

        # Threading
        self.stop_event = threading.Event()
        self.mouse_thread = None
        self.loop_thread = None

        # MediaPipe face mesh
        self.mp_face = mp.solutions.face_mesh
        self.face_mesh = None
    def start(self, block=True):
        """Start head tracking"""
        if self.face_mesh is None:
            self.face_mesh = self.mp_face.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

        # Initialize camera
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(f"Camera {self.camera_index} failed to open")
        self.stop_event.clear()

        # Start mouse control thread
        self.mouse_thread = threading.Thread(target=self.mouse_mover, daemon=True)
        self.mouse_thread.start()

        # Start processing
        if block:
            self.process_loop()
        else:
            self.loop_thread = threading.Thread(target=self.process_loop, daemon=True)
            self.loop_thread.start()

    def stop(self):
        """Stop tracking and cleanup"""
        self.stop_event.set()
        time.sleep(0.05)

        # Stop threads (avoid joining current thread)
        current_thread = threading.current_thread()

        if (self.loop_thread and self.loop_thread.is_alive() and
            self.loop_thread != current_thread):
            self.loop_thread.join(timeout=1.0)

        if (self.mouse_thread and self.mouse_thread.is_alive() and
            self.mouse_thread != current_thread):
            self.mouse_thread.join(timeout=1.0)

        # Cleanup camera
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        # Cleanup windows
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        # Cleanup MediaPipe
        if self.face_mesh:
            try:
                self.face_mesh.close()
            except Exception:
                pass
            self.face_mesh = None

    def toggle_mouse_control(self):
        """Toggle mouse control on/off"""
        self.mouse_enabled = not self.mouse_enabled
        state = 'Enabled' if self.mouse_enabled else 'Disabled'
        print(f"Mouse Control: {state}")

    def set_performance_mode(self, fast_mode):
        """Update performance settings"""
        self.fast_mode = fast_mode

        # Update mouse rate
        if fast_mode:
            self.mouse_sleep = 0.005  # 200Hz
            print("Fast mode: 200Hz tracking")
        else:
            self.mouse_sleep = 0.016  # 60Hz
            print("Power saving: 60Hz tracking")

        # Update filters if allowed
        if self.allow_override:
            if fast_mode:
                freq, cutoff, beta = 120.0, 0.8, 0.015
            else:
                freq, cutoff, beta = 45.0, 1.5, 0.03

            # Store new parameters
            self.euro_freq = freq
            self.euro_cutoff = cutoff
            self.euro_beta = beta

            # Recreate filters
            self.filter_x = OneEuroFilter(cutoff, beta, 1.0, freq)
            self.filter_y = OneEuroFilter(cutoff, beta, 1.0, freq)
            print(f"Filters updated: freq={freq}, cutoff={cutoff}, beta={beta}")
        else:
            print("Preserving custom filter parameters")

    def calibrate_center(self):
        """Calibrate center position"""
        self.cal_yaw = 180.0 - self.raw_yaw
        self.cal_pitch = 180.0 - self.raw_pitch
        print(f"Calibrated - Yaw: {self.cal_yaw:.2f}, Pitch: {self.cal_pitch:.2f}")

    def mouse_mover(self):
        """Mouse movement thread"""
        while not self.stop_event.is_set():
            with self.mouse_lock:
                x, y = self.mouse_target
            if self.mouse_enabled:
                pyautogui.moveTo(x, y)
            time.sleep(self.mouse_sleep)

    @staticmethod
    def landmark_to_3d(landmark, w, h):
        """Convert MediaPipe landmark to 3D coordinates"""
        return np.array([landmark.x * w, landmark.y * h, landmark.z * w])

    def process_loop(self):
        """Main processing loop"""
        while not self.stop_event.is_set() and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                debug_frame = np.zeros_like(frame)

                # Draw landmarks for debugging
                for i, landmark in enumerate(landmarks):
                    pt = self.landmark_to_3d(landmark, w, h)
                    x, y = int(pt[0]), int(pt[1])
                    if 0 <= x < w and 0 <= y < h:
                        color = (155, 155, 155) if i in self.FACE_OUTLINE else (255, 25, 10)
                        cv2.circle(debug_frame, (x, y), 3, color, -1)
                        frame[y, x] = (255, 255, 255)

                # Extract key facial points
                points = {}
                for name, idx in self.LANDMARKS.items():
                    pt = self.landmark_to_3d(landmarks[idx], w, h)
                    points[name] = pt
                    x, y = int(pt[0]), int(pt[1])
                    cv2.circle(frame, (x, y), 4, (0, 0, 0), -1)

                # Get face orientation points
                left = points["left"]
                right = points["right"]
                top = points["top"]
                bottom = points["bottom"]
                front = points["front"]

                # Calculate face coordinate system
                right_vec = (right - left)
                right_vec /= np.linalg.norm(right_vec)

                up_vec = (top - bottom)
                up_vec /= np.linalg.norm(up_vec)

                forward_vec = np.cross(right_vec, up_vec)
                forward_vec /= np.linalg.norm(forward_vec)
                forward_vec = -forward_vec  # Point outward

                # Face center
                center = (left + right + top + bottom + front) / 5.0

                # Draw 3D cube for visualization
                w_half = np.linalg.norm(right - left) / 2.0
                h_half = np.linalg.norm(top - bottom) / 2.0
                d_half = 80.0

                def corner(x, y, z):
                    return (center + x * w_half * right_vec +
                            y * h_half * up_vec + z * d_half * forward_vec)

                # Cube corners
                corners = [
                    corner(-1, 1, -1), corner(1, 1, -1),
                    corner(1, -1, -1), corner(-1, -1, -1),
                    corner(-1, 1, 1), corner(1, 1, 1),
                    corner(1, -1, 1), corner(-1, -1, 1),
                ]

                # Draw cube edges
                edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
                corners_2d = [(int(p[0]), int(p[1])) for p in corners]
                for i, j in edges:
                    cv2.line(frame, corners_2d[i], corners_2d[j], (255, 125, 35), 2)

                # Smooth head orientation
                self.origins.append(center)
                self.directions.append(forward_vec)
                smooth_origin = np.mean(self.origins, axis=0)
                smooth_direction = np.mean(self.directions, axis=0)
                smooth_direction /= np.linalg.norm(smooth_direction)

                # Calculate head angles
                ref_forward = np.array([0, 0, -1])

                # Yaw (left/right)
                xz_proj = np.array([smooth_direction[0], 0, smooth_direction[2]])
                xz_proj /= np.linalg.norm(xz_proj)
                yaw_rad = math.acos(np.clip(np.dot(ref_forward, xz_proj), -1.0, 1.0))
                if smooth_direction[0] < 0:
                    yaw_rad = -yaw_rad

                # Pitch (up/down)
                yz_proj = np.array([0, smooth_direction[1], smooth_direction[2]])
                yz_proj /= np.linalg.norm(yz_proj)
                pitch_rad = math.acos(np.clip(np.dot(ref_forward, yz_proj), -1.0, 1.0))
                if smooth_direction[1] > 0:
                    pitch_rad = -pitch_rad

                yaw_deg = np.degrees(yaw_rad)
                pitch_deg = np.degrees(pitch_rad)

                # Normalize angles
                if yaw_deg < 0:
                    yaw_deg = abs(yaw_deg)
                elif yaw_deg < 180:
                    yaw_deg = 360 - yaw_deg
                if pitch_deg < 0:
                    pitch_deg = 360 + pitch_deg

                # Store raw angles
                self.raw_yaw = yaw_deg
                self.raw_pitch = pitch_deg

                # Apply calibration
                yaw_deg += self.cal_yaw
                pitch_deg += self.cal_pitch

                # Map to screen coordinates
                screen_x = int(((yaw_deg - (180 - self.yaw_range)) / (2 * self.yaw_range)) * self.screen_w)
                screen_y = int(((180 + self.pitch_range - pitch_deg) / (2 * self.pitch_range)) * self.screen_h)

                # Keep cursor on screen
                screen_x = max(10, min(self.screen_w - 10, screen_x))
                screen_y = max(10, min(self.screen_h - 10, screen_y))

                # Apply smoothing filters
                smooth_x = int(round(self.filter_x.filter(screen_x)))
                smooth_y = int(round(self.filter_y.filter(screen_y)))

                # Update mouse target
                if self.mouse_enabled:
                    with self.mouse_lock:
                        self.mouse_target[0] = smooth_x
                        self.mouse_target[1] = smooth_y

                # Draw head direction ray
                ray_length = 2.5 * d_half
                ray_end = smooth_origin - smooth_direction * ray_length
                start_2d = (int(smooth_origin[0]), int(smooth_origin[1]))
                end_2d = (int(ray_end[0]), int(ray_end[1]))
                cv2.line(frame, start_2d, end_2d, (15, 255, 0), 3)
                cv2.line(debug_frame, start_2d, end_2d, (15, 255, 0), 3)

                # Show windows (already created and placed)
                cv2.imshow("Head Tracking", frame)
                cv2.imshow("Landmarks", debug_frame)

                # Hotkey for toggling mouse control
                if keyboard.is_pressed('f7'):
                    self.toggle_mouse_control()
                    time.sleep(0.3)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop()
                    return
                elif key == ord('c'):
                    self.calibrate_center()

            else:
                # No face detected - show frame anyway
                cv2.imshow("Head Tracking", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop()
                    return

        # Cleanup on exit
        self.stop()


def main():
    """Test the head tracker"""
    tracker = HeadMouseTracker(
        camera_index=0,
        filter_length=40,
        yaw_degrees=20.0,
        pitch_degrees=10.0,
        euro_min_cutoff=1.2,
        euro_beta=0.02,
        euro_freq=60.0
    )
    try:
        tracker.start(block=True)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        tracker.stop()


if __name__ == "__main__":
    main()
