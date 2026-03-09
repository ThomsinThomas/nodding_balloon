import sys
import cv2
import mediapipe as mp
import numpy as np
import time
import math
import random
import os
import platform
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QPushButton,
    QStackedWidget,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
    QSize,
    QUrl,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
)
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication, QColor


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- THEME COLORS ---
COLOR_ACCENT = "#ffb300"
COLOR_SELECTED = "#64DC78"
COLOR_DANGER = "#ff4d4d"
COLOR_NAVY_BLUE = "#003366"
COLOR_NEON_CYAN = "#00f2ff"
GLASS_BG = "rgba(255, 255, 255, 0.12)"
GLASS_BORDER = "rgba(255, 255, 255, 0.35)"

# Calibration Box Width
CAL_BOX_W = 500


# ====================================================
# UNIFORM QUIT BUTTON
# ====================================================
class RealisticQuitButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("QUIT", parent)
        self.setFixedSize(120, 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_DANGER};
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
                border: 2px solid #b33636;
            }}
            QPushButton:hover {{
                background-color: #ff3333;
            }}
        """
        )


# ====================================================
# CHANGE 4: BACK BUTTON — styled to match existing theme
# ====================================================
class BackButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("← BACK", parent)
        self.setFixedSize(120, 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_NAVY_BLUE};
                color: {COLOR_ACCENT};
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                border: 2px solid {COLOR_ACCENT};
            }}
            QPushButton:hover {{
                background-color: #004488;
            }}
        """
        )


# ====================================================
# SOUND HELPERS
# ====================================================
def play_pop_sound():
    try:
        if platform.system() == "Darwin":
            os.system("afplay /System/Library/Sounds/Tink.aiff &")
        elif platform.system() == "Windows":
            import winsound

            winsound.Beep(1000, 150)
    except:
        pass


def play_success_beep():
    try:
        if platform.system() == "Darwin":
            os.system("afplay /System/Library/Sounds/Glass.aiff &")
        elif platform.system() == "Windows":
            import winsound

            winsound.Beep(1200, 300)
    except:
        pass


# ====================================================
# PAGE 1: SPLASH
# ====================================================
class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self, screen_size):
        super().__init__()
        self.setFixedSize(screen_size)
        self.bg_label = QLabel(self)
        self.bg_label.setFixedSize(screen_size)
        img = cv2.imread(resource_path("flash_screen.jpg"))
        if img is not None:
            img = cv2.cvtColor(
                cv2.resize(img, (screen_size.width(), screen_size.height())),
                cv2.COLOR_BGR2RGB,
            )
            self.bg_label.setPixmap(
                QPixmap.fromImage(
                    QImage(
                        img.data,
                        screen_size.width(),
                        screen_size.height(),
                        QImage.Format.Format_RGB888,
                    )
                )
            )

        layout = QVBoxLayout(self)
        layout.addStretch()
        self.pbar = QProgressBar()
        self.pbar.setFixedSize(600, 12)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(
            f"QProgressBar {{ background-color: rgba(30, 30, 40, 180); border-radius: 6px; }} QProgressBar::chunk {{ background-color: {COLOR_SELECTED}; border-radius: 5px; }}"
        )
        layout.addWidget(self.pbar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(100)

        self.val = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_p)
        # CHANGE 1: Timer interval reduced from 35ms to 10ms — ~3.5x faster loading bar
        self.timer.start(10)

    def update_p(self):
        self.val += 1
        self.pbar.setValue(self.val)
        if self.val >= 100:
            self.timer.stop()
            self.finished.emit()


# ====================================================
# PAGE 2: SETUP
# ====================================================
class UnifiedSetupPage(QWidget):
    start_signal = pyqtSignal(int, int)
    quit_app = pyqtSignal()

    def __init__(self, screen_size):
        super().__init__()
        self.setFixedSize(screen_size)
        self.duration = 2
        self.bg = QLabel(self)
        self.bg.setFixedSize(screen_size)
        img = cv2.imread(resource_path("background.jpg"))
        if img is not None:
            img = cv2.cvtColor(
                cv2.resize(img, (screen_size.width(), screen_size.height())),
                cv2.COLOR_BGR2RGB,
            )
            self.bg.setPixmap(
                QPixmap.fromImage(
                    QImage(
                        img.data,
                        screen_size.width(),
                        screen_size.height(),
                        QImage.Format.Format_RGB888,
                    )
                )
            )

        self.quit_btn = RealisticQuitButton(self)
        self.quit_btn.move(screen_size.width() - 150, 30)
        self.quit_btn.clicked.connect(lambda: self.quit_app.emit())

        main_layout = QVBoxLayout(self)
        main_layout.addStretch(1)
        content_vbox = QVBoxLayout()
        content_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_vbox.setSpacing(45)

        self.glass_panel = QFrame()
        self.glass_panel.setFixedSize(750, 420)
        self.glass_panel.setStyleSheet(
            f"background: {GLASS_BG}; border: 2px solid {GLASS_BORDER}; border-radius: 40px;"
        )
        gl = QVBoxLayout(self.glass_panel)
        gl.setContentsMargins(40, 30, 40, 30)
        gl.setSpacing(15)

        hdr = QLabel("HOW TO PLAY")
        hdr.setFixedSize(280, 55)
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet(
            f"background-color: {COLOR_NAVY_BLUE}; color: {COLOR_ACCENT}; font-size: 28px; font-weight: 900; font-family: 'Trebuchet MS'; border-radius: 12px; border: none;"
        )
        gl.addWidget(hdr, alignment=Qt.AlignmentFlag.AlignCenter)
        gl.addSpacing(15)

        points = [
            "Sit on a chair facing the camera",
            "Stay within the highlighted Play Area",
            "Stand and stretch to pop balloons",
            "Follow the Side-Bound Arrows",
            "Sit down to spawn the next balloon",
        ]
        for p in points:
            txt = QLabel(p)
            txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt.setStyleSheet(
                "font-size: 23px; color: white; background: transparent; border: none; font-family: 'Helvetica Neue'; font-weight: 600;"
            )
            gl.addWidget(txt)

        content_vbox.addWidget(self.glass_panel, alignment=Qt.AlignmentFlag.AlignCenter)

        dur_section = QVBoxLayout()
        dur_section.setSpacing(15)
        d_hdr = QLabel("DURATION")
        d_hdr.setFixedSize(220, 50)
        d_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_hdr.setStyleSheet(
            f"background-color: {COLOR_NAVY_BLUE}; color: {COLOR_ACCENT}; font-size: 24px; font-weight: 900; font-family: 'Trebuchet MS'; border-radius: 12px;"
        )
        dur_section.addWidget(d_hdr, alignment=Qt.AlignmentFlag.AlignCenter)

        db = QHBoxLayout()
        self.m_btn = QPushButton("-")
        self.p_btn = QPushButton("+")
        self.d_lbl = QLabel("2 Min")
        self.d_lbl.setMinimumWidth(220)
        self.d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.d_lbl.setStyleSheet(
            f"background: #F5F5DC; color: {COLOR_NAVY_BLUE}; font-size: 34px; font-weight: 900; padding: 5px 35px; border-radius: 15px; font-family: 'Trebuchet MS';"
        )

        for b in [self.m_btn, self.p_btn]:
            b.setFixedSize(60, 60)
            b.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.15); color: white; border-radius: 30px; font-size: 34px; font-weight: bold; border: 1px solid white; }"
            )

        self.m_btn.clicked.connect(lambda: self.upd_d(-1))
        self.p_btn.clicked.connect(lambda: self.upd_d(1))

        db.addStretch()
        db.addWidget(self.m_btn)
        db.addSpacing(25)
        db.addWidget(self.d_lbl)
        db.addSpacing(25)
        db.addWidget(self.p_btn)
        db.addStretch()

        dur_section.addLayout(db)
        content_vbox.addLayout(dur_section)

        self.play_btn = QPushButton("PLAY")
        self.play_btn.setFixedSize(300, 85)
        self.play_btn.setStyleSheet(
            f"QPushButton {{ background: {COLOR_ACCENT}; color: {COLOR_NAVY_BLUE}; font-size: 38px; font-weight: 900; border-radius: 42px; font-family: 'Trebuchet MS'; }} QPushButton:hover {{ background: {COLOR_SELECTED}; color: white; }}"
        )
        self.play_btn.clicked.connect(lambda: self.start_signal.emit(self.duration, 1))
        content_vbox.addWidget(self.play_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addLayout(content_vbox)
        main_layout.addStretch(1)

    def upd_d(self, v):
        # CHANGE 2: Max duration reduced from 30 to 20 minutes
        self.duration = max(2, min(20, self.duration + v))
        self.d_lbl.setText(f"{self.duration} Min")
        self.m_btn.setEnabled(self.duration > 2)
        self.p_btn.setEnabled(self.duration < 20)


# ====================================================
# PAGE 3: CALIBRATION
# ====================================================
class CalibrationPage(QWidget):
    calibration_finished = pyqtSignal(dict)
    exit_signal = pyqtSignal()
    # CHANGE 4: New signal to go back to the setup/menu page
    back_signal = pyqtSignal()

    def __init__(self, screen_size):
        super().__init__()
        self.setFixedSize(screen_size)
        self.ssize = screen_size
        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=0.7, min_tracking_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

        self.up_arrow = cv2.imread(resource_path("arrow_up.png"), cv2.IMREAD_UNCHANGED)
        self.down_arrow = cv2.imread(
            resource_path("arrow_down.png"), cv2.IMREAD_UNCHANGED
        )

        self.reset_calibration_state()

        self.video_lbl = QLabel(self)
        self.video_lbl.setFixedSize(screen_size)

        self.overlay = QFrame(self)
        self.overlay.setGeometry(0, 0, screen_size.width(), screen_size.height())
        layout = QVBoxLayout(self.overlay)
        layout.setContentsMargins(0, 40, 0, 80)

        self.t_lbl = QLabel("STEP 1: SITTING CALIBRATION")
        self.t_lbl.setFixedSize(500, 65)
        self.t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t_lbl.setStyleSheet(
            f"background-color: {COLOR_NAVY_BLUE}; color: {COLOR_ACCENT}; font-size: 26px; font-weight: 900; border-radius: 15px;"
        )
        layout.addWidget(self.t_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.instr_lbl = QLabel("Position yourself inside the box.")
        self.instr_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: 600;")
        layout.addWidget(self.instr_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # CHANGE 3: Depth label for forward/backward guidance
        self.depth_lbl = QLabel("")
        self.depth_lbl.setFixedHeight(36)
        self.depth_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.depth_lbl.setStyleSheet(
            f"color: {COLOR_NEON_CYAN}; font-size: 20px; font-weight: 700; background: transparent; border: none;"
        )
        layout.addWidget(self.depth_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(
            f"font-size: 160px; color: {COLOR_NEON_CYAN}; font-weight: 900;"
        )
        layout.addWidget(self.count_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        self.pbar = QProgressBar()
        self.pbar.setFixedSize(600, 20)
        self.pbar.setTextVisible(False)
        self.pbar.hide()
        self.pbar.setStyleSheet(
            f"QProgressBar {{ background: rgba(255,255,255,0.1); border-radius: 10px; }} QProgressBar::chunk {{ background: {COLOR_NEON_CYAN}; }}"
        )
        layout.addWidget(self.pbar, alignment=Qt.AlignmentFlag.AlignCenter)

        # CHANGE 4: Back button top-left, Quit button top-right
        self.back_btn = BackButton(self)
        self.back_btn.move(30, 30)
        self.back_btn.clicked.connect(self._on_back_clicked)

        self.exit_btn = RealisticQuitButton(self)
        self.exit_btn.move(screen_size.width() - 150, 30)
        self.exit_btn.clicked.connect(lambda: self.exit_signal.emit())

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_feed)
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.decrement_countdown)

    def _on_back_clicked(self):
        """Stop all timers cleanly then emit back signal."""
        self.timer.stop()
        self.countdown_timer.stop()
        self.back_signal.emit()

    def reset_calibration_state(self):
        self.phase = "SIT"
        self.heights = {
            "SIT": 0.0,
            "STAND": 0.0,
            "SHOULDER_WIDTH": 0.0,
            "HEAD_Y": 0.0,
            "TRUNK": 0.0,
        }
        self.temp_list = []
        self.frames = 0
        self.is_recording = False
        self.countdown_started = False
        self.countdown_val = 5

    def start_camera(self, cap_obj):
        self.reset_calibration_state()
        self.t_lbl.setText("STEP 1: SITTING CALIBRATION")
        self.instr_lbl.setText("Place your feet on the RED LINE and SIT in the box.")
        self.depth_lbl.setText("")
        self.cap = cap_obj
        self.timer.start(30)

    def decrement_countdown(self):
        self.countdown_val -= 1
        if self.countdown_val > 0:
            self.count_lbl.setText(str(self.countdown_val))
        else:
            self.countdown_timer.stop()
            self.count_lbl.setText("")
            self.is_recording = True
            self.pbar.show()

    def update_feed(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        sw, sh = self.ssize.width(), self.ssize.height()
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (sw, sh))
        res = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Draw Center Rectangle (Full Height)
        rx = (sw - CAL_BOX_W) // 2
        box_color = (100, 255, 100) if self.countdown_started else (255, 255, 255)
        cv2.rectangle(frame, (rx, 0), (rx + CAL_BOX_W, sh), box_color, 2)
        
        # Draw Red Foot Line
        foot_line_y = int(sh * 0.9)
        cv2.line(frame, (rx, foot_line_y), (rx + CAL_BOX_W, foot_line_y), (0, 0, 255), 4)

        if res.pose_landmarks:
            # Draw Key Points / Skeleton for user feedback
            self.mp_drawing.draw_landmarks(
                frame,
                res.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(
                    color=(255, 242, 0), thickness=2, circle_radius=2
                ),
                self.mp_drawing.DrawingSpec(color=(0, 242, 255), thickness=2),
            )

            lm = res.pose_landmarks.landmark
            head_x = lm[0].x * sw
            head_y = lm[0].y * sh
            hip_y = (lm[23].y + lm[24].y) / 2
            ankle_y = (lm[27].y + lm[28].y) / 2
            # Valication Logic
            in_box = rx < head_x < rx + CAL_BOX_W
            feet_on_line = 0.82 < ankle_y < 0.98
            
            is_correct_pose = False
            if self.phase == "SIT":
                visible_full = 0 < head_y < sh and feet_on_line
                is_correct_pose = hip_y > 0.60
                arrow_img = self.down_arrow
            else:
                visible_full = 0 < head_y < sh and feet_on_line
                is_correct_pose = hip_y < 0.60
                arrow_img = self.up_arrow

            if (
                in_box
                and visible_full
                and is_correct_pose
                and not self.countdown_started
            ):
                self.countdown_started = True
                self.count_lbl.setText(str(self.countdown_val))
                self.countdown_timer.start(1000)
                self.instr_lbl.setText("STAY STILL...")

            if (
                (not in_box or not visible_full or not is_correct_pose)
                and self.countdown_started
                and not self.is_recording
            ):
                self.countdown_started = False
                self.countdown_timer.stop()
                self.countdown_val = 5
                self.count_lbl.setText("")
                msg = "Position yourself and " + (
                    "SIT" if self.phase == "SIT" else "STAND"
                )
                if not feet_on_line:
                    msg = "STEP BACK: Place feet on the RED LINE!"
                elif not visible_full:
                    msg = "Move until your head is visible!"
                self.instr_lbl.setText(msg)

            if self.is_recording:
                scan_y = int((self.frames / 90) * sh)
                cv2.line(
                    frame, (rx, scan_y), (rx + CAL_BOX_W, scan_y), (0, 242, 255), 4
                )

                self.temp_list.append((hip_y, lm[0].y, abs(lm[11].x - lm[12].x)))
                self.frames += 1
                self.pbar.setValue(int((self.frames / 90) * 100))

                if self.frames >= 90:
                    play_success_beep()
                    avg_data = np.mean(self.temp_list, axis=0)
                    self.heights[self.phase] = avg_data[0]
                    if self.phase == "STAND":
                        self.heights["HEAD_Y"], self.heights["SHOULDER_WIDTH"] = (
                            avg_data[1],
                            avg_data[2],
                        )
                        self.heights["TRUNK"] = abs(avg_data[1] - avg_data[0])
                        self.timer.stop()
                        self.calibration_finished.emit(self.heights)
                    else:
                        self.next_phase()

            if not self.countdown_started:
                pulse = int(math.sin(time.time() * 5) * 15)
                if arrow_img is not None:
                    self.overlay_png(
                        frame,
                        cv2.resize(arrow_img, (120, 120)),
                        sw // 2 - 60,
                        sh // 2 - 200 + pulse,
                    )

        self.video_lbl.setPixmap(
            QPixmap.fromImage(
                QImage(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).data,
                    sw,
                    sh,
                    QImage.Format.Format_RGB888,
                )
            )
        )

    def next_phase(self):
        self.phase = "STAND"
        self.is_recording = False
        self.countdown_started = False
        self.countdown_val = 5
        self.frames = 0
        self.temp_list = []
        self.pbar.hide()
        self.depth_lbl.setText("")
        self.t_lbl.setText("STEP 2: STANDING CALIBRATION")
        self.instr_lbl.setText("Keep feet on the RED LINE and STAND UP.")

    def overlay_png(self, bg, ov, x, y):
        h, w = ov.shape[:2]
        sh_bg, sw_bg = bg.shape[:2]
        x1, x2 = max(x, 0), min(x + w, sw_bg)
        y1, y2 = max(y, 0), min(y + h, sh_bg)
        ov_x1, ov_x2 = x1 - x, x2 - x
        ov_y1, ov_y2 = y1 - y, y2 - y
        if x1 < x2 and y1 < y2:
            visible_ov = ov[ov_y1:ov_y2, ov_x1:ov_x2]
            visible_bg = bg[y1:y2, x1:x2]
            if visible_ov.shape[2] == 4:
                alpha = visible_ov[:, :, 3] / 255.0
                for c in range(3):
                    visible_bg[:, :, c] = (
                        alpha * visible_ov[:, :, c] + (1 - alpha) * visible_bg[:, :, c]
                    ).astype(np.uint8)


# ====================================================
# PAGE 4: GAME PAGE
# ====================================================
class GamePage(QWidget):
    game_over_signal = pyqtSignal(int, float, float)
    exit_signal = pyqtSignal()

    def __init__(self, screen_size):
        super().__init__()
        self.setFixedSize(screen_size)
        self.ssize = screen_size
        self.pose = mp.solutions.pose.Pose()

        self.bg = QLabel(self)
        self.bg.setFixedSize(screen_size)
        img = cv2.imread(resource_path("background.jpg"))
        if img is not None:
            img = cv2.cvtColor(
                cv2.resize(img, (screen_size.width(), screen_size.height())),
                cv2.COLOR_BGR2RGB,
            )
            self.bg.setPixmap(
                QPixmap.fromImage(
                    QImage(
                        img.data,
                        screen_size.width(),
                        screen_size.height(),
                        QImage.Format.Format_RGB888,
                    )
                )
            )

        self.video_lbl = QLabel(self)
        self.video_lbl.setFixedSize(screen_size)

        self.active_balloon = False
        self.nods = 0
        self.nod_times = []
        self.is_paused = False
        self.auto_paused_by_boundary = False
        self.session_accumulated_time = 0
        self.session_start_time = time.time()
        self.bx = 0
        self.target_by_norm = 0.0
        self.floating_pop_text = []
        self.success_glow_frames = 0
        self.cal = None
        self.last_activity_time = time.time()
        self.last_state = "SIT"

        self.hud_panel = QFrame(self)
        self.hud_panel.setGeometry(30, 30, 280, 160)
        self.hud_panel.setStyleSheet(
            f"background: {GLASS_BG}; border: 2px solid {GLASS_BORDER}; border-radius: 25px;"
        )
        hud_layout = QVBoxLayout(self.hud_panel)

        self.n_lbl = QLabel("NODS: 0")
        self.n_lbl.setStyleSheet(
            "color: #64DC78; font-size: 34px; font-weight: 900; border:none; background:transparent;"
        )
        self.t_lbl = QLabel("00:00")
        self.t_lbl.setStyleSheet(
            "color: blue; font-size: 52px; font-weight: 900; border:none; background:transparent;"
        )
        hud_layout.addWidget(self.n_lbl)
        hud_layout.addWidget(self.t_lbl)

        self.instr_bar = QFrame(self)
        self.instr_bar.setFixedSize(450, 90)
        self.instr_bar.move(
            (screen_size.width() - 450) // 2, screen_size.height() - 130
        )
        self.instr_bar.setStyleSheet(
            f"background: {GLASS_BG}; border: 2px solid {GLASS_BORDER}; border-radius: 45px;"
        )
        instr_layout = QHBoxLayout(self.instr_bar)
        self.instr_txt = QLabel("GET READY")
        self.instr_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr_txt.setStyleSheet(
            "color: white; font-size: 42px; font-weight: 900; border: none; background: transparent;"
        )
        instr_layout.addWidget(self.instr_txt)

        self.exit_btn = RealisticQuitButton(self)
        self.exit_btn.move(screen_size.width() - 150, 30)
        self.exit_btn.clicked.connect(lambda: self.exit_signal.emit())

        self.balloon_red = cv2.imread(
            resource_path("balloon.png"), cv2.IMREAD_UNCHANGED
        )
        self.balloon_green = cv2.imread(
            resource_path("balloon_green.png"), cv2.IMREAD_UNCHANGED
        )
        self.up_arrow = cv2.imread(resource_path("arrow_up.png"), cv2.IMREAD_UNCHANGED)
        self.down_arrow = cv2.imread(
            resource_path("arrow_down.png"), cv2.IMREAD_UNCHANGED
        )

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.session_accumulated_time += time.time() - self.session_start_time
        else:
            self.session_start_time = time.time()
            self.auto_paused_by_boundary = False

    def start_game(self, cap, duration_min, cal_data, level):
        self.cap = cap
        self.session_time = duration_min * 60
        self.cal = cal_data
        sw = self.ssize.width()
        self.zone_width = int(self.cal["SHOULDER_WIDTH"] * sw * 1.8)
        self.zone_left = (sw - self.zone_width) // 2
        self.zone_right = self.zone_left + self.zone_width
        self.nods = 0
        self.nod_times = []
        self.floating_pop_text = []
        self.is_paused = False
        self.session_accumulated_time = 0
        self.session_start_time = time.time()
        self.last_activity_time = time.time()
        self.timer.start(30)

    def update_game(self):
        if not self.cal:
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        sw, sh = self.ssize.width(), self.ssize.height()
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (sw, sh))

        elapsed = int(
            self.session_accumulated_time
            + (
                time.time() - self.session_start_time
                if not self.is_paused
                else 0
            )
        )
        current_time = min(self.session_time, elapsed)
        self.t_lbl.setText(f"{current_time//60:02d}:{current_time%60:02d}")
        
        # Stop game if time is up
        if elapsed >= self.session_time:
            self.timer.stop()
            self.game_over_signal.emit(self.nods, 100.0, 100.0)
            return

        res = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark
            head_x_px = lm[0].x * sw
            in_play_zone = self.zone_left < head_x_px < self.zone_right

            if not in_play_zone and not self.is_paused:
                self.auto_paused_by_boundary = True
                self.toggle_pause()
            if in_play_zone and self.is_paused and self.auto_paused_by_boundary:
                self.toggle_pause()

            cv2.rectangle(
                frame,
                (self.zone_left, 50),
                (self.zone_right, sh - 50),
                ((100, 220, 120) if in_play_zone else (60, 60, 220)),
                3,
            )

            if not self.is_paused:
                hip_y = (lm[23].y + lm[24].y) / 2
                mid = (self.cal["SIT"] + self.cal["STAND"]) / 2
                stretched = abs(lm[0].y - hip_y) >= (self.cal["TRUNK"] * 0.95)

                current_state = "SIT" if hip_y > mid else "STAND"
                if current_state != self.last_state:
                    self.last_state = current_state
                    self.last_activity_time = time.time()

                idle_elapsed = time.time() - self.last_activity_time
                if idle_elapsed > 10.0:
                    if int(time.time() * 2) % 2 == 0:
                        self.instr_bar.setStyleSheet(
                            "background: rgba(255, 77, 77, 0.4); border: 2px solid white; border-radius: 45px;"
                        )
                    else:
                        self.instr_bar.setStyleSheet(
                            f"background: {GLASS_BG}; border: 2px solid {GLASS_BORDER}; border-radius: 45px;"
                        )
                else:
                    self.instr_bar.setStyleSheet(
                        f"background: {GLASS_BG}; border: 2px solid {GLASS_BORDER}; border-radius: 45px;"
                    )

                if not self.active_balloon:
                    self.instr_txt.setText("SIT")
                    arrow = self.down_arrow
                    if hip_y > mid + 0.05:
                        self.spawn_balloon()
                else:
                    self.instr_txt.setText("NOD!" if stretched else "STAND!")
                    arrow = self.up_arrow
                    ty_px = int(self.target_by_norm * sh)
                    self.draw_balloon_at_coord(frame, self.balloon_red, self.bx, ty_px)
                    if (
                        math.sqrt(
                            (head_x_px - self.bx) ** 2 + (lm[0].y * sh - ty_px) ** 2
                        )
                        < 75
                        and stretched
                        and hip_y < mid
                    ):
                        self.pop_balloon()
                        self.last_activity_time = time.time()

                arr_img = cv2.resize(arrow, (140, 140))
                pulse = int(math.sin(time.time() * 6) * 15)
                self.overlay_png(
                    frame, arr_img, self.zone_left - 160, sh // 2 - 70 + pulse
                )
                self.overlay_png(
                    frame, arr_img, self.zone_right + 20, sh // 2 - 70 + pulse
                )

        for f in self.floating_pop_text[:]:
            f[0] -= 4
            f[1] -= 0.05
            cv2.putText(
                frame,
                "+1",
                (f[2], int(f[0])),
                cv2.FONT_HERSHEY_DUPLEX,
                2.5,
                (100, 220, 120),
                5,
            )
            if f[1] <= 0:
                self.floating_pop_text.remove(f)

        if self.success_glow_frames > 0:
            self.draw_balloon_at_coord(
                frame, self.balloon_green, self.bx, int(self.target_by_norm * sh)
            )
            self.success_glow_frames -= 1

        if self.is_paused:
            ov = frame.copy()
            cv2.rectangle(ov, (0, 0), (sw, sh), (0, 0, 0), -1)
            cv2.addWeighted(ov, 0.6, frame, 0.4, 0, frame)
            msg = "CENTER YOURSELF!" if self.auto_paused_by_boundary else "PAUSED"
            cv2.putText(
                frame,
                msg,
                (sw // 2 - 320, sh // 2),
                cv2.FONT_HERSHEY_DUPLEX,
                2.5,
                (255, 255, 255),
                4,
            )

        self.video_lbl.setPixmap(
            QPixmap.fromImage(
                QImage(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).data,
                    sw,
                    sh,
                    QImage.Format.Format_RGB888,
                )
            )
        )
        if elapsed >= self.session_time:
            self.finish_game()

    def overlay_png(self, bg, ov, x, y):
        h, w = ov.shape[:2]
        sh_bg, sw_bg = bg.shape[:2]
        x1, x2 = max(x, 0), min(x + w, sw_bg)
        y1, y2 = max(y, 0), min(y + h, sh_bg)
        ov_x1, ov_x2 = x1 - x, x2 - x
        ov_y1, ov_y2 = y1 - y, y2 - y
        if x1 < x2 and y1 < y2:
            visible_ov = ov[ov_y1:ov_y2, ov_x1:ov_x2]
            visible_bg = bg[y1:y2, x1:x2]
            if visible_ov.shape[2] == 4:
                alpha = visible_ov[:, :, 3] / 255.0
                for c in range(3):
                    visible_bg[:, :, c] = (
                        alpha * visible_ov[:, :, c] + (1 - alpha) * visible_bg[:, :, c]
                    ).astype(np.uint8)

    def draw_balloon_at_coord(self, frame, img, x, y):
        bh, bw = img.shape[:2]
        aspect = bw / bh
        new_w = int(130 * aspect)
        self.overlay_png(frame, cv2.resize(img, (new_w, 130)), x - new_w // 2, y - 65)

    def spawn_balloon(self):
        self.active_balloon = True
        self.rep_timer = time.time()
        self.bx = random.randint(self.zone_left + 60, self.zone_right - 60)
        self.target_by_norm = max(0.1, self.cal["HEAD_Y"] - 0.05)

    def pop_balloon(self):
        self.active_balloon = False
        self.success_glow_frames = 15
        self.nods += 1
        self.nod_times.append(time.time() - self.rep_timer)
        self.floating_pop_text.append(
            [int(self.target_by_norm * self.ssize.height()), 1.0, self.bx]
        )
        self.n_lbl.setText(f"NODS: {self.nods}")
        play_pop_sound()

    def finish_game(self):
        self.timer.stop()
        f = min(self.nod_times) if self.nod_times else 0.0
        a = sum(self.nod_times) / len(self.nod_times) if self.nod_times else 0.0
        self.game_over_signal.emit(self.nods, f, a)


# ====================================================
# PAGE 5: RESULTS (Summary Page)
# ====================================================
class ResultsPage(QWidget):
    restart_signal = pyqtSignal()
    menu_signal = pyqtSignal()
    quit_signal = pyqtSignal()

    def __init__(self, screen_size):
        super().__init__()
        self.setFixedSize(screen_size)

        self.bg = QLabel(self)
        self.bg.setFixedSize(screen_size)
        img = cv2.imread(resource_path("background.jpg"))
        if img is not None:
            img = cv2.cvtColor(
                cv2.resize(img, (screen_size.width(), screen_size.height())),
                cv2.COLOR_BGR2RGB,
            )
            self.bg.setPixmap(
                QPixmap.fromImage(
                    QImage(
                        img.data,
                        screen_size.width(),
                        screen_size.height(),
                        QImage.Format.Format_RGB888,
                    )
                )
            )

        self.exit_btn = RealisticQuitButton(self)
        self.exit_btn.move(screen_size.width() - 150, 30)
        self.exit_btn.clicked.connect(lambda: self.quit_signal.emit())

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        glass = QFrame()
        glass.setFixedSize(850, 580)
        glass.setStyleSheet(
            f"background: {GLASS_BG}; border: 2px solid {GLASS_BORDER}; border-radius: 50px;"
        )

        v = QVBoxLayout(glass)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(15)

        t = QLabel("SESSION COMPLETE")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(
            f"color: {COLOR_ACCENT}; font-size: 55px; font-weight: 900; font-family: 'Trebuchet MS'; border: none; background: transparent;"
        )

        self.r1 = QLabel("NODS: 0")
        self.r2 = QLabel("FASTEST: 0.00s")
        self.r3 = QLabel("AVERAGE: 0.00s")

        for l in [self.r1, self.r2, self.r3]:
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet(
                "color: white; font-size: 32px; font-weight: 600; font-family: 'Trebuchet MS'; border: none; background: transparent;"
            )

        btn_style = f"""
            QPushButton {{ 
                background: {COLOR_ACCENT}; 
                color: {COLOR_NAVY_BLUE}; 
                font-size: 24px; 
                font-weight: bold; 
                border-radius: 35px; 
                font-family: 'Trebuchet MS'; 
            }} 
            QPushButton:hover {{ 
                background: {COLOR_SELECTED}; 
                color: white; 
            }}
        """

        self.restart_btn = QPushButton("RESTART SESSION")
        self.restart_btn.setFixedSize(320, 70)
        self.restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_btn.clicked.connect(lambda: self.restart_signal.emit())
        self.restart_btn.setStyleSheet(btn_style)

        self.menu_btn = QPushButton("MAIN MENU")
        self.menu_btn.setFixedSize(320, 70)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.clicked.connect(lambda: self.menu_signal.emit())
        self.menu_btn.setStyleSheet(btn_style)

        v.addWidget(t)
        v.addSpacing(5)
        v.addWidget(self.r1)
        v.addWidget(self.r2)
        v.addWidget(self.r3)
        v.addSpacing(15)
        v.addWidget(self.restart_btn, 0, Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.menu_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(glass, 0, Qt.AlignmentFlag.AlignCenter)

    def set_results(self, n, f, a):
        self.r1.setText(f"TOTAL NODS: {n}")
        self.r2.setText(f"FASTEST SPEED: {f:.2f}s")
        self.r3.setText(f"AVERAGE SPEED: {a:.2f}s")


# ====================================================
# MAIN APPLICATION
# ====================================================
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()
        screen = QGuiApplication.primaryScreen()
        self.ss = screen.geometry().size()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.cap = cv2.VideoCapture(0)
        self.cal_data = None
        self.dur = 2

        self.splash = SplashScreen(self.ss)
        self.stack.addWidget(self.splash)

        self.splash.finished.connect(lambda: self.fade_to(1))

        # Show splash immediately, then load heavy pages
        QTimer.singleShot(100, self.load_heavy_pages)

    def load_heavy_pages(self):
        self.setup = UnifiedSetupPage(self.ss)
        self.calib = CalibrationPage(self.ss)
        self.game = GamePage(self.ss)
        self.results = ResultsPage(self.ss)

        self.setup.quit_app.connect(self.close)
        self.setup.start_signal.connect(self.begin_cal)

        self.calib.back_signal.connect(lambda: self.fade_to(1))
        self.calib.exit_signal.connect(self.close)
        self.calib.calibration_finished.connect(self.on_cal_done)

        self.game.exit_signal.connect(self.game.finish_game)
        self.game.game_over_signal.connect(self.show_results)

        self.results.restart_signal.connect(self.restart_with_calibration)
        self.results.menu_signal.connect(lambda: self.fade_to(1))
        self.results.quit_signal.connect(self.close)

        self.stack.addWidget(self.setup)
        self.stack.addWidget(self.calib)
        self.stack.addWidget(self.game)
        self.stack.addWidget(self.results)



    def fade_to(self, idx):
        self.target_idx = idx
        self.eff = QGraphicsOpacityEffect(self.stack.currentWidget())
        self.stack.currentWidget().setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.complete_fade)
        self.anim.start()

    def complete_fade(self):
        self.stack.setCurrentIndex(self.target_idx)
        new_w = self.stack.currentWidget()
        self.eff2 = QGraphicsOpacityEffect(new_w)
        new_w.setGraphicsEffect(self.eff2)
        self.anim2 = QPropertyAnimation(self.eff2, b"opacity")
        self.anim2.setDuration(300)
        self.anim2.setStartValue(0.0)
        self.anim2.setEndValue(1.0)
        self.anim2.start()

    def begin_cal(self, d, l):
        self.dur = d
        self.fade_to(2)
        self.calib.start_camera(self.cap)

    def on_cal_done(self, data):
        self.cal_data = data
        self.fade_to(3)
        self.game.start_game(self.cap, self.dur, self.cal_data, 1)

    def restart_with_calibration(self):
        if self.cal_data:
            self.fade_to(3)
            self.game.start_game(self.cap, self.dur, self.cal_data, 1)
        else:
            self.fade_to(2)
            self.calib.start_camera(self.cap)

    def show_results(self, n, f, a):
        self.results.set_results(n, f, a)
        self.fade_to(4)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())
