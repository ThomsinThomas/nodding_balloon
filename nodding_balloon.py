import cv2
import mediapipe as mp
import numpy as np
import time
import math
import random

# ====================================================
# CONSTANTS & THEME
# ====================================================
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
CALIBRATION_FRAMES = 90
DEFAULT_SESSION_TIME = 60
BALLOON_SIZE = 140

# Modern Color Palette (BGR)
BG_COLOR = (15, 15, 20)
TEXT_COLOR = (240, 240, 245)
TEXT_MUTED = (180, 180, 190)
ACCENT = (100, 200, 255)  # Orange accent
SUCCESS = (100, 220, 120)  # Green
WARNING = (80, 180, 255)   # Orange
DANGER = (60, 60, 220)     # Red

# Button Colors - More realistic and vibrant
BTN_PRIMARY = (200, 130, 50)      # Blue
BTN_PRIMARY_HOVER = (255, 170, 80) # Lighter Blue
BTN_SECONDARY = (80, 80, 100)     # Gray
BTN_SECONDARY_HOVER = (110, 110, 130)  # Lighter Gray
BTN_SUCCESS = (80, 180, 100)      # Green
BTN_SUCCESS_HOVER = (100, 200, 130)
BTN_DANGER = (50, 60, 200)        # Red
BTN_DANGER_HOVER = (70, 80, 230)
BTN_TEXT = (255, 255, 255)

FONT = cv2.FONT_HERSHEY_SIMPLEX


# ====================================================
# DRAW HELPERS
# ====================================================
def draw_rounded_rect(img, x, y, w, h, color, radius=12, thickness=-1):
    """Rounded rectangle with antialiasing."""
    if radius > min(w, h) // 2:
        radius = min(w, h) // 2

    if thickness < 0:
        cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, -1)
        cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, -1)
    else:
        cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, thickness)
        cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, thickness)

    cv2.ellipse(img, (x + radius, y + radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x + w - radius, y + radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x + w - radius, y + h - radius), (radius, radius), 0, 0, 90, color, thickness)
    cv2.ellipse(img, (x + radius, y + h - radius), (radius, radius), 90, 0, 90, color, thickness)


def draw_button_shadow(img, x, y, w, h, radius=12, offset=4):
    shadow_color = (5, 5, 10, 80)
    overlay = img.copy()
    draw_rounded_rect(overlay, x + offset, y + offset, w, h, shadow_color[:3], radius, -1)
    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)


def draw_text_center(img, text, center, scale, color, thickness=2):
    size = cv2.getTextSize(text, FONT, scale, thickness)[0]
    x = int(center[0] - size[0] / 2)
    y = int(center[1] + size[1] / 2)
    cv2.putText(img, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


def load_background(image_path, width, height):
    """Load and resize background image, return None if not found"""
    try:
        img = cv2.imread(image_path)
        if img is not None:
            return cv2.resize(img, (width, height))
    except:
        pass
    return None


def apply_background(frame, bg_image):
    """Apply background image with dark overlay"""
    if bg_image is not None:
        frame[:] = bg_image
        overlay = np.zeros_like(frame)
        overlay[:] = (0, 0, 0)
        frame[:] = cv2.addWeighted(frame, 0.5, overlay, 0.5, 0)
    else:
        frame[:] = BG_COLOR
    return frame


def draw_top_bar(frame, time_remaining, nods, best, avg):
    # Semi-transparent top bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (WINDOW_WIDTH, 80), (20, 20, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, f"NODS", (20, 30), FONT, 0.6, TEXT_MUTED, 1, cv2.LINE_AA)
    cv2.putText(frame, f"{nods}", (20, 60), FONT, 0.9, TEXT_COLOR, 2, cv2.LINE_AA)

    if best < float('inf'):
        cv2.putText(frame, f"BEST", (150, 30), FONT, 0.6, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{best:.1f}s", (150, 60), FONT, 0.9, SUCCESS, 2, cv2.LINE_AA)

    if avg > 0:
        cv2.putText(frame, f"AVG", (300, 30), FONT, 0.6, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{avg:.1f}s", (300, 60), FONT, 0.9, TEXT_COLOR, 2, cv2.LINE_AA)

    pill_w, pill_h = 200, 40
    px = WINDOW_WIDTH // 2 - pill_w // 2
    py = 20

    if time_remaining > 10:
        pill_color = BTN_PRIMARY
    elif time_remaining > 0:
        pill_color = WARNING
    else:
        pill_color = DANGER

    draw_rounded_rect(frame, px, py, pill_w, pill_h, pill_color, radius=20, thickness=-1)
    cv2.putText(frame, "TIME", (px + 12, py + 27), FONT, 0.6, (230, 230, 240), 1, cv2.LINE_AA)

    time_text = f"{int(time_remaining)}s"
    size = cv2.getTextSize(time_text, FONT, 0.9, 2)[0]
    cv2.putText(frame, time_text,
                (px + pill_w - size[0] - 15, py + 28),
                FONT, 0.9, BTN_TEXT, 2, cv2.LINE_AA)


# ====================================================
# Pose Tracker
# ====================================================
class PoseTracker:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )

    def process(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self.pose.process(rgb)

        landmarks = {}
        if result.pose_landmarks:
            lm = result.pose_landmarks.landmark
            landmarks = {
                'nose': (int(lm[0].x * w), int(lm[0].y * h), lm[0].visibility),
                'left_hip': (int(lm[23].x * w), int(lm[23].y * h), lm[23].visibility),
                'right_hip': (int(lm[24].x * w), int(lm[24].y * h), lm[24].visibility),
            }
        return landmarks


# ====================================================
# Button
# ====================================================
class Button:
    def __init__(self, x, y, width, height, text, button_type="primary"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.hovered = False
        self.button_type = button_type

    def contains_point(self, px, py):
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def draw(self, frame):
        # Select color based on type and hover state
        if self.button_type == "primary":
            color = BTN_PRIMARY_HOVER if self.hovered else BTN_PRIMARY
        elif self.button_type == "success":
            color = BTN_SUCCESS_HOVER if self.hovered else BTN_SUCCESS
        elif self.button_type == "danger":
            color = BTN_DANGER_HOVER if self.hovered else BTN_DANGER
        else:  # secondary
            color = BTN_SECONDARY_HOVER if self.hovered else BTN_SECONDARY

        # Shadow
        draw_button_shadow(frame, self.x, self.y, self.width, self.height, radius=18)

        # Button body
        draw_rounded_rect(frame, self.x, self.y, self.width, self.height, color, radius=18, thickness=-1)

       

        # Text
        center = (self.x + self.width // 2, self.y + self.height // 2 + 3)
        draw_text_center(frame, self.text, center, 0.7, BTN_TEXT, thickness=2)


# ====================================================
# Start Menu
# ====================================================
class StartMenu:
    def __init__(self):
        self.window_name = "Nodding Balloons"
        self.session_time = DEFAULT_SESSION_TIME

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, WINDOW_WIDTH, WINDOW_HEIGHT)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        btn_w, btn_h = 200, 60
        self.start_btn = Button(WINDOW_WIDTH//2 - btn_w - 20, 550, btn_w, btn_h, "START", "success")
        self.quit_btn  = Button(WINDOW_WIDTH//2 + 20, 550, btn_w, btn_h, "QUIT", "danger")
        
        self.time_minus_btn = Button(WINDOW_WIDTH//2 - 190, 450, 60, 50, "-", "secondary")
        self.time_plus_btn  = Button(WINDOW_WIDTH//2 + 130, 450, 60, 50, "+", "secondary")

        self.action = None
        self.bg_image = load_background("start_background.jpg", WINDOW_WIDTH, WINDOW_HEIGHT)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self.start_btn.hovered = self.start_btn.contains_point(x, y)
            self.quit_btn.hovered = self.quit_btn.contains_point(x, y)
            self.time_minus_btn.hovered = self.time_minus_btn.contains_point(x, y)
            self.time_plus_btn.hovered = self.time_plus_btn.contains_point(x, y)

        elif event == cv2.EVENT_LBUTTONDOWN:
            if self.start_btn.contains_point(x, y):
                self.action = "start"
            elif self.quit_btn.contains_point(x, y):
                self.action = "quit"
            elif self.time_minus_btn.contains_point(x, y):
                self.session_time = max(30, self.session_time - 10)
            elif self.time_plus_btn.contains_point(x, y):
                self.session_time = min(300, self.session_time + 10)

    def draw(self):
        frame = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        apply_background(frame, self.bg_image)

        
        draw_text_center(frame, "NODDING BALLONS", (WINDOW_WIDTH//2, 100),
                         1.8, ACCENT, thickness=3)

        # Instructions
        instructions = [
            "HOW TO PLAY",
            "1. Sit on a chair for calibration",
            "2. Stand up when instructed",
            "3. Nod your head to touch the balloon",
            "4. Sit down after each balloon"
        ]
        y = 180
        for i, inst in enumerate(instructions):
            scale = 0.9 if i == 0 else 0.7
            color = TEXT_COLOR if i == 0 else TEXT_MUTED
            draw_text_center(frame, inst, (WINDOW_WIDTH//2, y), scale, color, thickness=2 if i == 0 else 1)
            y += 40

        # Session time section
        draw_text_center(frame, "SESSION TIME", (WINDOW_WIDTH//2, 400), 0.8, TEXT_COLOR, 2)

        # Time display
        time_text = f"{self.session_time}s"
        draw_text_center(frame, time_text, (WINDOW_WIDTH//2, 470), 1.4, ACCENT, 3)

        # +/- buttons
        self.time_minus_btn.draw(frame)
        self.time_plus_btn.draw(frame)

        # Bottom buttons
        self.start_btn.draw(frame)
        self.quit_btn.draw(frame)

        return frame

    def run(self):
        while True:
            frame = self.draw()
            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                cv2.destroyWindow(self.window_name)
                return None

            if self.action == "quit":
                cv2.destroyWindow(self.window_name)
                return None

            if self.action == "start":
                return self.session_time


# ====================================================
# Overlay PNG helper
# ====================================================
def overlay_png(background, overlay, x, y):
    h, w = overlay.shape[:2]

    if x < 0 or y < 0 or x + w > background.shape[1] or y + h > background.shape[0]:
        return background

    if overlay.shape[2] == 4:
        alpha = overlay[:, :, 3] / 255.0
        for c in range(3):
            background[y:y+h, x:x+w, c] = (
                alpha * overlay[:, :, c] +
                (1 - alpha) * background[y:y+h, x:x+w, c]
            )
    else:
        background[y:y+h, x:x+w] = overlay

    return background


# ====================================================
# Balloon
# ====================================================
class Balloon:
    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        self.image = image
        self.visible = True
        self.size = image.shape[0]
        self.radius = self.size // 2

    def draw(self, frame):
        if not self.visible:
            return

        top_left_x = self.x - self.radius
        top_left_y = self.y - self.radius
        overlay_png(frame, self.image, top_left_x, top_left_y)

        cv2.circle(frame, (self.x, self.y), 15, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.circle(frame, (self.x, self.y), 4, (255, 255, 255), -1, cv2.LINE_AA)

    def check_collision(self, point):
        if not self.visible:
            return False
        px, py = point
        dist = math.sqrt((px - self.x) ** 2 + (py - self.y) ** 2)
        return dist < 20


# ====================================================
# Game Controller
# ====================================================
class BalloonGame:
    def __init__(self, session_time):
        self.balloon_image = cv2.imread("balloon.png", cv2.IMREAD_UNCHANGED)
        if self.balloon_image is None:
            raise FileNotFoundError("balloon.png not found")
        self.balloon_image = cv2.resize(self.balloon_image, (BALLOON_SIZE, BALLOON_SIZE))

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.window_name = "Nodding Balloons"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, WINDOW_WIDTH, WINDOW_HEIGHT)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        self.pose_tracker = PoseTracker()
        self.session_time = session_time

        self.state = "CALIBRATING"
        self.calibration_step = 1
        self.calibration_count = 0

        self.sitting_hip_height = None
        self.standing_hip_height = None
        self.standing_head_y = None
        self.standing_head_x = None

        self.balloon_min_x = 200
        self.balloon_max_x = 1080
        self.balloon_y_center = 150
        self.balloon_y_range = 50

        self.balloon = None
        self.is_standing = False
        self.is_sitting = True
        self.nods = 0
        self.nod_times = []
        self.last_nod_time = None

        self.fastest_nod = float('inf')
        self.average_speed = 0

        self.session_start_time = None
        self.session_elapsed = 0
        self.session_time_remaining = self.session_time

        self.pause_btn = Button(WINDOW_WIDTH - 230, 15, 110, 45, "PAUSE", "secondary")
        self.quit_btn = Button(WINDOW_WIDTH - 115, 15, 95, 45, "QUIT", "danger")

        self.action = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            if self.state in ["PLAYING", "PAUSED"]:
                self.pause_btn.hovered = self.pause_btn.contains_point(x, y)
                self.quit_btn.hovered = self.quit_btn.contains_point(x, y)

        elif event == cv2.EVENT_LBUTTONDOWN:
            if self.state == "PLAYING":
                if self.pause_btn.contains_point(x, y):
                    self.state = "PAUSED"
                elif self.quit_btn.contains_point(x, y):
                    self.state = "END"

            elif self.state == "PAUSED":
                if self.pause_btn.contains_point(x, y):
                    self.state = "PLAYING"
                elif self.quit_btn.contains_point(x, y):
                    self.state = "END"

            elif self.state == "END":
                self.action = "click"

    def calibrate(self, landmarks):
        if not landmarks:
            return False

        left_hip = landmarks['left_hip']
        right_hip = landmarks['right_hip']
        nose = landmarks['nose']

        if left_hip[2] < 0.5 or right_hip[2] < 0.5 or nose[2] < 0.5:
            return False

        hip_center_y = (left_hip[1] + right_hip[1]) // 2

        if self.calibration_step == 1:
            self.calibration_count += 1
            if self.calibration_count >= CALIBRATION_FRAMES:
                self.sitting_hip_height = hip_center_y
                self.calibration_step = 2
                self.calibration_count = 0
            return False

        elif self.calibration_step == 2:
            self.calibration_count += 1
            if self.calibration_count >= CALIBRATION_FRAMES:
                self.standing_hip_height = hip_center_y
                self.standing_head_y = nose[1]
                self.standing_head_x = nose[0]

                self.balloon_y_center = self.standing_head_y
                self.balloon_y_range = 60

                head_width_range = 250
                self.balloon_min_x = max(150, self.standing_head_x - head_width_range // 2)
                self.balloon_max_x = min(WINDOW_WIDTH - 150, self.standing_head_x + head_width_range // 2)

                self.state = "PLAYING"
                self.spawn_balloon()
                self.session_start_time = time.time()
                return True
            return False

        return False

    def spawn_balloon(self):
        balloon_x = random.randint(self.balloon_min_x, self.balloon_max_x)
        balloon_y = self.balloon_y_center + random.randint(-self.balloon_y_range, self.balloon_y_range)
        balloon_y = max(BALLOON_SIZE // 2 + 10, min(WINDOW_HEIGHT - BALLOON_SIZE // 2 - 80, balloon_y))

        self.balloon = Balloon(balloon_x, balloon_y, self.balloon_image)
        self.last_nod_time = time.time()

    def check_posture(self, landmarks):
        if not landmarks or self.sitting_hip_height is None or self.standing_hip_height is None:
            return False, False

        left_hip = landmarks['left_hip']
        right_hip = landmarks['right_hip']

        if left_hip[2] < 0.5 or right_hip[2] < 0.5:
            return False, False

        hip_center_y = (left_hip[1] + right_hip[1]) // 2

        mid_point = (self.sitting_hip_height + self.standing_hip_height) / 2
        threshold = abs(self.sitting_hip_height - self.standing_hip_height) * 0.25

        is_standing = hip_center_y < (mid_point - threshold)
        is_sitting = hip_center_y > (mid_point + threshold)

        return is_standing, is_sitting

    def check_balloon_nod(self, landmarks):
        if not self.balloon or not self.balloon.visible or not landmarks:
            return False

        nose = landmarks['nose']

        if nose[2] < 0.5:
            return False

        if self.balloon.check_collision((nose[0], nose[1])):
            nod_time = time.time() - self.last_nod_time
            self.nod_times.append(nod_time)

            self.fastest_nod = min(self.fastest_nod, nod_time)
            self.average_speed = sum(self.nod_times) / len(self.nod_times)

            self.balloon.visible = False
            self.nods += 1

            return True

        return False

    def draw_calibration_ui(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0), -1)
        frame[:] = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        if self.calibration_step == 1:
            instruction = "SIT ON A CHAIR"
            subtext = "Hold still for 3 seconds"
        else:
            instruction = "STAND UP STRAIGHT"
            subtext = "Hold still for 3 seconds"

        cy = WINDOW_HEIGHT // 2
        draw_text_center(frame, instruction, (WINDOW_WIDTH//2, cy - 40), 1.2, TEXT_COLOR, 3)
        draw_text_center(frame, subtext, (WINDOW_WIDTH//2, cy + 10), 0.8, TEXT_MUTED, 2)

        # Progress bar
        bar_w = 400
        bar_h = 30
        bar_x = WINDOW_WIDTH//2 - bar_w//2
        bar_y = cy + 60

        draw_rounded_rect(frame, bar_x, bar_y, bar_w, bar_h, (40, 40, 50), radius=15, thickness=-1)

        progress = int((self.calibration_count / CALIBRATION_FRAMES) * 100)
        fill_w = int((progress / 100) * (bar_w - 6))
        if fill_w > 0:
            draw_rounded_rect(frame, bar_x + 3, bar_y + 3, fill_w, bar_h - 6, SUCCESS, radius=12, thickness=-1)

        draw_text_center(frame, f"{progress}%", (WINDOW_WIDTH//2, bar_y + 22), 0.7, TEXT_COLOR, 2)

    def draw_game_ui(self, frame):
        draw_top_bar(frame, self.session_time_remaining, self.nods, self.fastest_nod, self.average_speed)

        self.pause_btn.text = "RESUME" if self.state == "PAUSED" else "PAUSE"
        self.pause_btn.draw(frame)
        self.quit_btn.draw(frame)

    def draw_paused_overlay(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0), -1)
        frame[:] = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        draw_text_center(frame, "PAUSED", (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 20),
                         2.0, TEXT_COLOR, 3)
        draw_text_center(frame, "Click RESUME to continue", (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 40),
                         0.8, TEXT_MUTED, 2)

    def draw_end_screen(self, frame):
        bg_image = load_background("end_background.jpg", WINDOW_WIDTH, WINDOW_HEIGHT)
        apply_background(frame, bg_image)

        draw_text_center(frame, "SESSION COMPLETE", (WINDOW_WIDTH//2, 120),
                         1.8, ACCENT, 3)

        y = 220
        draw_text_center(frame, f"Total Nods: {self.nods}", (WINDOW_WIDTH//2, y),
                         1.2, TEXT_COLOR, 2)
        y += 70

        if self.nod_times:
            draw_text_center(frame, f"Fastest: {self.fastest_nod:.2f}s", (WINDOW_WIDTH//2, y),
                             1.0, SUCCESS, 2)
            y += 50
            draw_text_center(frame, f"Average: {self.average_speed:.2f}s", (WINDOW_WIDTH//2, y),
                             1.0, TEXT_MUTED, 2)
            y += 50

        draw_text_center(frame, f"Duration: {int(self.session_elapsed)}s", (WINDOW_WIDTH//2, y),
                         1.0, TEXT_MUTED, 2)

        btn_w, btn_h = 200, 60
        home_btn = Button(WINDOW_WIDTH//2 - btn_w - 20, 520, btn_w, btn_h, "HOME", "primary")
        quit_btn = Button(WINDOW_WIDTH//2 + 20, 520, btn_w, btn_h, "QUIT", "danger")

        home_btn.draw(frame)
        quit_btn.draw(frame)

        return home_btn, quit_btn

    def run(self):
        home_btn = None
        quit_btn = None

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))

            landmarks = self.pose_tracker.process(frame)

            if landmarks:
                temp = landmarks['left_hip']
                landmarks['left_hip'] = landmarks['right_hip']
                landmarks['right_hip'] = temp

            if self.state == "CALIBRATING":
                self.draw_calibration_ui(frame)
                self.calibrate(landmarks)

            elif self.state == "PLAYING":
                if self.session_start_time:
                    self.session_elapsed = time.time() - self.session_start_time
                    self.session_time_remaining = max(0, self.session_time - self.session_elapsed)

                    if self.session_time_remaining <= 0:
                        self.state = "END"

                if self.balloon:
                    self.balloon.draw(frame)

                is_standing, is_sitting = self.check_posture(landmarks)
                self.is_standing = is_standing
                self.is_sitting = is_sitting

                if is_standing and self.balloon and self.balloon.visible:
                    self.check_balloon_nod(landmarks)

                if is_sitting and self.balloon and not self.balloon.visible:
                    self.spawn_balloon()

                self.draw_game_ui(frame)

            elif self.state == "PAUSED":
                if self.balloon:
                    self.balloon.draw(frame)
                self.draw_game_ui(frame)
                self.draw_paused_overlay(frame)

            elif self.state == "END":
                home_btn, quit_btn = self.draw_end_screen(frame)

                if self.action == "click":
                    self.cap.release()
                    cv2.destroyWindow(self.window_name)
                    return "menu"

            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

        self.cap.release()
        cv2.destroyWindow(self.window_name)
        return None


# ====================================================
# End Screen
# ====================================================
class EndScreen:
    def __init__(self, nods, fastest, average, duration):
        self.window_name = "Nodding Balloons"
        self.nods = nods
        self.fastest = fastest
        self.average = average
        self.duration = duration

        cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        self.home_btn = Button(WINDOW_WIDTH//2 - 220, 500, 180, 50, "HOME")
        self.quit_btn = Button(WINDOW_WIDTH//2 + 40, 500, 180, 50, "QUIT")

        self.action = None
        self.bg_image = load_background("end_background.jpg", WINDOW_WIDTH, WINDOW_HEIGHT)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self.home_btn.hovered = self.home_btn.contains_point(x, y)
            self.quit_btn.hovered = self.quit_btn.contains_point(x, y)

        elif event == cv2.EVENT_LBUTTONDOWN:
            if self.home_btn.contains_point(x, y):
                self.action = "home"
            elif self.quit_btn.contains_point(x, y):
                self.action = "quit"

    def draw(self):
        frame = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        apply_background(frame, self.bg_image)

        draw_text_center(frame, "SESSION COMPLETE", (WINDOW_WIDTH//2, 150),
                         1.5, ACCENT, 3)

        y = 260
        draw_text_center(frame, f"Total Nods: {self.nods}", (WINDOW_WIDTH//2, y),
                         1.0, TEXT_COLOR, 2)
        y += 60

        if self.nods > 0:
            draw_text_center(frame, f"Fastest: {self.fastest:.2f}s", (WINDOW_WIDTH//2, y),
                             0.9, SUCCESS, 2)
            y += 50
            draw_text_center(frame, f"Average: {self.average:.2f}s", (WINDOW_WIDTH//2, y),
                             0.9, TEXT_MUTED, 2)
            y += 50

        draw_text_center(frame, f"Duration: {int(self.duration)}s", (WINDOW_WIDTH//2, y),
                         0.9, TEXT_MUTED, 2)

        self.home_btn.draw(frame)
        self.quit_btn.draw(frame)

        return frame

    def run(self):
        while True:
            frame = self.draw()
            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                cv2.destroyWindow(self.window_name)
                return None

            if self.action == "quit":
                cv2.destroyWindow(self.window_name)
                return None

            if self.action == "home":
                cv2.destroyWindow(self.window_name)
                return "home"


# ====================================================
# Main
# ====================================================
def main():
    print("=" * 60)
    print("BALLOON NOD EXERCISE")
    print("=" * 60)

    while True:
        menu = StartMenu()
        session_time = menu.run()

        if session_time is None:
            break

        game = BalloonGame(session_time)
        result = game.run()

        if result != "menu":
            break

        if game.nods > 0:
            end = EndScreen(game.nods, game.fastest_nod, game.average_speed, game.session_elapsed)
            result = end.run()
            if result != "home":
                break
        else:
            continue

    cv2.destroyAllWindows()
    print("\nGoodbye!")


if __name__ == "__main__":
    main()