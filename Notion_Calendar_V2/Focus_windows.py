from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar, QApplication, \
    QMainWindow
from PyQt6.QtCore import Qt, QTimer, QTime, QDate
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl
from datetime import datetime, date, time as dt_time
from pathlib import Path
import sys, json

from notion_calendar_sync import save_tasks_to_json

DATA_FILE = Path(__file__).parent / "tasks.json"

def load_data():
    save_tasks_to_json()

    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

class FocusWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.data = load_data()

        # trạng thái
        self.is_counting = False
        self.is_paused = False
        self.remaining_seconds = 0
        self.current_task = None

        # sound
        # self.start_sound_path = "sounds/game-start.mp3"
        # self.end_sound_path = "sounds/success.mp3"

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._on_countdown_tick)
        self.remaining_seconds = None
        self.total_seconds = None
        self.current_task_title = None

        # Cửa sổ
        self.setWindowTitle("Focus Mode")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.container = QWidget()
        self.container.setStyleSheet("""
            background-color: rgba(20,20,20,220);
            color: white;
            border-radius: 12px;
        """)
        inner = QVBoxLayout(self.container)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.datetime_label = QLabel()
        self.datetime_label.setFont(QFont("Arial", 10))
        inner.addWidget(self.datetime_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.task_label = QLabel("No Task")
        self.task_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        inner.addWidget(self.task_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.timer_label = QLabel("--:--")
        self.timer_label.setFont(QFont("Consolas", 32, QFont.Weight.Bold))
        inner.addWidget(self.timer_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("QLabel { background-color: rgba(0, 0, 0, 0.1); }() }")

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setMinimumWidth(180)
        self.progress.setMaximumWidth(280)
        self.progress.setStyleSheet("""
            QProgressBar {
                border-radius:3px;
                background-color:#2a2a2a;
            }
            QProgressBar::chunk {
                border-radius:3px;
                background-color:#00d47e;
            }
        """)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border-radius:3px; background-color:#333; }
            QProgressBar::chunk { border-radius:3px; background-color:#4caf50; }
        """)
        inner.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        self.refresh = QPushButton("Refresh")
        self.close_btn = QPushButton("Đóng")
        for b in (self.refresh, self.close_btn):
            b.setStyleSheet("""
                QPushButton { background-color:#444; color:white; padding:6px 10px; border-radius:6px; }
                QPushButton:hover { background-color:#666; }
            """)
        btn_layout.addWidget(self.refresh)
        btn_layout.addWidget(self.close_btn)
        inner.addLayout(btn_layout)

        layout.addWidget(self.container)

        # Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_datetime)
        self.clock_timer.start(1000)
        self.update_datetime()

        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.auto_check_task)
        self.check_timer.start(5000)
        self.auto_check_task()

        # events
        self.refresh.clicked.connect(self.reload)
        self.close_btn.clicked.connect(QApplication.quit)

        # drag
        self.drag_pos = None
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        for child in self.container.findChildren(QWidget):
            child.setMouseTracking(True)

    def reload(self):
        self.data = load_data()

        print(self.data)

        self.auto_check_task()

    def update_datetime(self):
        now = QTime.currentTime().toString("HH:mm:ss")
        today = QDate.currentDate().toString("dd/MM/yyyy")
        self.datetime_label.setText(f"{today} | {now}")

    def play_sound(self, file_path):
        try:
            audio_output = QAudioOutput()
            player = QMediaPlayer()
            player.setAudioOutput(audio_output)
            player.setSource(QUrl.fromLocalFile(file_path))
            audio_output.setVolume(1.0)
            player.play()
            self._player = player
            self._audio_output = audio_output
        except Exception as e:
            print("Không phát được âm thanh:", e)

    # countdown control
    def start_countdown(self, seconds, title=None, total_seconds=None):
        if seconds <= 0:
            return

        # nếu countdown đang chạy nhưng info mới khác -> reset
        if self.is_counting:
            if (self.current_task.get("title") != title) or (self.remaining_seconds != seconds):
                self.stop_countdown()
            else:
                return  # task trùng và remaining chưa thay đổi

        self.remaining_seconds = int(seconds)
        if title:
            self.task_label.setText(title)
            self.current_task = {"title": title}
            if total_seconds:
                self.current_task["duration_seconds"] = int(total_seconds)

        self._update_timer_label()
        self._update_progress()
        self.is_counting = True
        self.is_paused = False

        self.countdown_timer.start(1000)

    def stop_countdown(self):
        if self.countdown_timer.isActive():
            self.countdown_timer.stop()
        self.is_counting = False
        self.is_paused = False
        self.remaining_seconds = 0
        self.current_task = None
        self.timer_label.setText("--:--")
        self.progress.setValue(100)

    def _on_countdown_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_timer_label()
            self._update_progress()
        else:
            self.countdown_timer.stop()
            self.is_counting = False
            self.timer_label.setText("Hết giờ!")
            self.current_task = None

    def _update_timer_label(self):
        m, s = divmod(self.remaining_seconds, 60)
        self.timer_label.setText(f"{m:02}:{s:02}")

    def _update_progress(self):
        total = None
        if isinstance(self.current_task, dict):
            total = self.current_task.get("duration_seconds")
        if total:
            try:
                pct = int(self.remaining_seconds / total * 100)
                self.progress.setValue(max(0, min(100, pct)))
            except Exception:
                self.progress.setValue(100)
        else:
            self.progress.setValue(100)

    def auto_check_task(self):
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = self.data.get(today, [])
        now_dt = datetime.now()
        active = None

        for task in tasks:
            t_from = task.get("time")
            t_to = task.get("to")
            if not t_from or not t_to:
                continue
            try:
                start_dt = datetime.combine(date.today(), dt_time(int(t_from.split(':')[0]), int(t_from.split(':')[1])))
                end_dt = datetime.combine(date.today(), dt_time(int(t_to.split(':')[0]), int(t_to.split(':')[1])))
            except Exception:
                continue

            if end_dt <= start_dt:
                end_dt = end_dt.replace(day=end_dt.day + 1)

            if start_dt <= now_dt < end_dt:
                active = (task, start_dt, end_dt)
                break

        if active:
            task, start_dt, end_dt = active
            remaining = int((end_dt - now_dt).total_seconds())
            total_seconds = int((end_dt - start_dt).total_seconds())
            task_info = dict(task)
            task_info["duration_seconds"] = total_seconds

            # luôn reset countdown nếu remaining hoặc task info khác
            if (not self.is_counting) or (self.current_task is None) \
                    or (self.current_task.get("title") != task_info.get("title")) \
                    or (self.remaining_seconds != remaining):
                self.current_task = task_info
                self.start_countdown(remaining, title=task_info.get("title"), total_seconds=total_seconds)
        else:
            if self.is_counting:
                self.stop_countdown()
            self.timer_label.setText("--:--")
            self.task_label.setText("No Task")

    # kéo thả
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self.drag_pos:
            diff = e.globalPosition().toPoint() - self.drag_pos
            self.move(self.x() + diff.x(), self.y() + diff.y())
            self.drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self.drag_pos = None

    def update_countdown(self):
        """Cập nhật thời gian còn lại mỗi giây"""
        if self.remaining_seconds is None:
            return

        self.remaining_seconds -= 1

        if self.remaining_seconds <= 0:
            # Hết giờ task
            self.countdown_timer.stop()
            self.timer_label.setText("--:--")
            self.current_task_title = None
            return

        # Cập nhật label hiển thị thời gian còn lại (mm:ss)
        mins, secs = divmod(self.remaining_seconds, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def enterEvent(self, event):
        """Khi chuột đi vào khung Focus"""
        self.show_controls(True)
        self.setFixedSize(320, 220)  # kích thước bình thường
        self.timer_label.setFont(QFont("Consolas", 32, QFont.Weight.Bold))
        self.progress.setFixedWidth(self.width() - 40)
        self.timer_label.setStyleSheet("QLabel { "
                                       "background-color: rgba(0, 0, 0, 0.1); "
                                       "color: #fff; }() }")
        event.accept()

    def leaveEvent(self, event):
        """Khi chuột rời khỏi khung Focus"""
        self.show_controls(False)
        self.setFixedSize(180, 150)  # thu nhỏ lại, chỉ hiện đồng hồ
        self.timer_label.setFont(QFont("Consolas", 26, QFont.Weight.Bold))
        self.progress.setFixedWidth(self.width() - 40)
        self.timer_label.setStyleSheet("QLabel { "
                                       "background-color: rgba(0, 0, 0, 0.1); "
                                       "color: #00B0F0; }() }")
        event.accept()

    def show_controls(self, visible: bool):
        """Ẩn/hiện các nút điều khiển"""
        for btn in [self.refresh, self.close_btn]:
            btn.setVisible(visible)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FocusWindow()
    window.show()
    sys.exit(app.exec())
