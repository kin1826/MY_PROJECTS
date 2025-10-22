import sys, json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem,
    QCalendarWidget, QListWidget, QPushButton, QLabel, QMessageBox, QCheckBox, QDialog,
    QLineEdit, QTextEdit, QSpinBox, QTimeEdit
)
from PyQt6.QtGui import QIcon, QTextCharFormat, QColor, QFont, QShortcut, QKeySequence
from PyQt6.QtCore import QDate, QTime, QSize, QTimer
from datetime import datetime, timedelta
from focus_window import FocusWindow

DATA_FILE = Path(__file__).parent / 'data.json'

def load_data():
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# TaskDialog
# ============================================================
class TaskDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle('Task')
        self.data = data or {}
        layout = QVBoxLayout(self)

        self.title_inp = QLineEdit(self.data.get('title', ''))
        layout.addWidget(QLabel('Title'))
        layout.addWidget(self.title_inp)

        self.time_inp = QTimeEdit()
        self.time_inp.setDisplayFormat('HH:mm')
        if self.data.get('time'):
            try:
                h, m = map(int, self.data['time'].split(':'))
                self.time_inp.setTime(QTime(h, m))
            except:
                pass
        layout.addWidget(QLabel('Start time'))
        layout.addWidget(self.time_inp)

        self.to_inp = QTimeEdit()
        self.to_inp.setDisplayFormat('HH:mm')
        if self.data.get('to'):
            try:
                h, m = map(int, self.data['to'].split(':'))
                self.to_inp.setTime(QTime(h, m))
            except:
                pass
        layout.addWidget(QLabel('End time'))
        layout.addWidget(self.to_inp)

        self.desc_inp = QTextEdit(self.data.get('description', ''))
        layout.addWidget(QLabel('Description'))
        layout.addWidget(self.desc_inp)

        self.pri_inp = QSpinBox()
        self.pri_inp.setRange(0, 10)
        self.pri_inp.setValue(self.data.get('priority', 0))
        layout.addWidget(QLabel('Priority (0 low - 10 high)'))
        layout.addWidget(self.pri_inp)

        btns = QHBoxLayout()
        ok = QPushButton('OK')
        cancel = QPushButton('Cancel')
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def get_data(self):
        t1 = self.time_inp.time()
        t2 = self.to_inp.time()
        return {
            'title': self.title_inp.text().strip(),
            'time': t1.toString('HH:mm'),
            'to': t2.toString('HH:mm'),
            'description': self.desc_inp.toPlainText().strip(),
            'priority': self.pri_inp.value(),
            'done': self.data.get('done', False)
        }

# ============================================================
# MainWindow
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Calendar + To-Do')
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(800, 600)
        self.data = load_data()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Calendar
        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self.load_tasks)
        layout.addWidget(self.calendar, 1)

        # Task list
        right = QVBoxLayout()
        right.addWidget(QLabel('Tasks'))
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.edit_task)
        right.addWidget(self.list_widget, 1)

        today = QDate.currentDate()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#4caf50"))
        fmt.setForeground(QColor("white"))
        fmt.setFontWeight(QFont.Weight.Bold)
        self.calendar.setDateTextFormat(today, fmt)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton('Add')
        self.btn_edit = QPushButton('Edit')
        self.btn_delete = QPushButton('Delete')
        self.btn_toggle = QPushButton('Toggle Done')
        self.btn_start = QPushButton('Open Clock')

        for b in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_toggle, self.btn_start):
            b.setStyleSheet("padding: 6px; border-radius: 6px; background-color: #444; color: white;")

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_toggle)
        btn_row.addWidget(self.btn_start)
        right.addLayout(btn_row)

        # Checkbox
        self.show_done = QCheckBox('Show done tasks')
        self.show_done.setChecked(True)
        self.show_done.stateChanged.connect(self.load_tasks)
        right.addWidget(self.show_done)

        self.auto_clean = QCheckBox('Automatic delete task after 7 days')
        self.auto_clean.setChecked(True)
        right.addWidget(self.auto_clean)

        layout.addLayout(right, 1)

        # Events
        self.btn_add.clicked.connect(self.add_task)
        self.btn_edit.clicked.connect(self.edit_task)
        self.btn_delete.clicked.connect(self.delete_task)
        self.btn_toggle.clicked.connect(self.toggle_done)
        self.btn_start.clicked.connect(self.open_focus_clock)

        # Shortcut
        shortcut_today = QShortcut(QKeySequence("Space"), self)
        shortcut_today.activated.connect(self.go_today)

        # Auto clean
        if self.auto_clean.isChecked():
            self.clean_old_tasks()

        self.load_tasks()
        self.start_task_watcher()

    # ========== core ==========
    def go_today(self):
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.load_tasks()

    def get_selected_date(self):
        return self.calendar.selectedDate().toString('yyyy-MM-dd')

    def load_tasks(self):
        date = self.get_selected_date()
        self.list_widget.clear()
        tasks = self.data.get(date, [])
        show_done = self.show_done.isChecked()
        self._tasks = [t for t in tasks if show_done or not t.get('done')]

        for t in self._tasks:
            done = t.get('done', False)
            title = t.get('title', 'No title')
            desc = t.get('description', '')
            time = t.get('time', '')
            to = t.get('to', '')

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 60))
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setContentsMargins(12, 6, 12, 6)
            layout.setSpacing(2)

            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

            lbl_info = QLabel(f"{time} → {to}   |   {desc}")
            lbl_info.setFont(QFont("Segoe UI", 10))
            lbl_info.setStyleSheet("color: #DCDCDC;")

            if done:
                w.setStyleSheet("background-color: #e8f5e9; border-radius: 8px;")
                lbl_title.setStyleSheet("color: #2e7d32; text-decoration: line-through;")
                lbl_info.setStyleSheet("color: #81c784; text-decoration: line-through;")
            else:
                w.setStyleSheet("background-color: #363636; border-radius: 8px;")

            layout.addWidget(lbl_title)
            layout.addWidget(lbl_info)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)

    # ========== task actions ==========
    def save_current(self):
        save_data(self.data)

    def get_selected_task(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._tasks):
            return None, None
        date = self.get_selected_date()
        all_tasks = self.data.get(date, [])
        task = self._tasks[row]
        idx = all_tasks.index(task)
        return date, idx

    def add_task(self):
        date = self.get_selected_date()
        dlg = TaskDialog(self)
        if dlg.exec():
            task = dlg.get_data()
            for existing in self.data.get(date, []):
                if existing.get("time") == task["time"]:
                    QMessageBox.warning(self, "Trùng giờ", f"Đã có task khác bắt đầu lúc {task['time']}!")
                    return
            self.data.setdefault(date, []).append(task)
            self.save_current()
            self.load_tasks()

    def edit_task(self):
        date, idx = self.get_selected_task()
        if date is None:
            QMessageBox.information(self, 'No selection', 'Chọn task để sửa.')
            return
        task = self.data[date][idx]
        dlg = TaskDialog(self, task)
        if dlg.exec():
            new_task = dlg.get_data()
            for i, existing in enumerate(self.data.get(date, [])):
                if i != idx and existing.get("time") == new_task["time"]:
                    QMessageBox.warning(self, "Trùng giờ", f"Đã có task khác bắt đầu lúc {new_task['time']}!")
                    return
            self.data[date][idx] = new_task
            self.save_current()
            self.load_tasks()

    def delete_task(self):
        date, idx = self.get_selected_task()
        if date is None:
            return
        ans = QMessageBox.question(self, 'Confirm', 'Xóa task này?')
        if ans == QMessageBox.StandardButton.Yes:
            del self.data[date][idx]
            if not self.data[date]:
                del self.data[date]
            self.save_current()
            self.load_tasks()

    def clean_old_tasks(self, days_to_keep=7):
        import datetime
        today = datetime.date.today()
        new_data = {}
        for date_str, tasks in self.data.items():
            try:
                d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if (today - d).days <= days_to_keep:
                new_data[date_str] = tasks
        self.data = new_data
        save_data(self.data)

    def toggle_done(self):
        date, idx = self.get_selected_task()
        if date is None:
            return
        task = self.data[date][idx]
        task['done'] = not task.get('done', False)
        self.save_current()
        self.load_tasks()

    # ========== Focus integration ==========
    def open_focus_clock(self):
        """
        Mở FocusWindow, truyền provider động (đọc self.data mỗi lần get_tasks()).
        """

        # provider động: FocusWindow sẽ gọi lambda này mỗi lần cần task hôm nay
        provider = lambda: self.data.get(datetime.now().strftime("%Y-%m-%d"), [])
        if not hasattr(self, "focus_window") or not getattr(self.focus_window, "isVisible", lambda: False)():
            self.focus_window = FocusWindow(provider)
            self.focus_window.show()
        else:
            self.focus_window.raise_()
            self.focus_window.activateWindow()

    def start_task_watcher(self):
        self.timer_check = QTimer()
        self.timer_check.timeout.connect(self.check_upcoming_tasks)
        self.timer_check.start(60 * 1000)

    def check_upcoming_tasks(self):
        today = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M")
        tasks = self.data.get(today, [])

        for t in tasks:
            if not t.get("done") and t.get("time") == now_time:
                if not self.focus_window.isVisible():
                    self.notify_start_task(t)
                return

    def notify_start_task(self, task):
        msg = QMessageBox()
        msg.setWindowTitle("⏰ Đến giờ rồi!")
        msg.setText(f"Đã đến lúc: <b>{task['title']}</b><br>{task['time']} → {task['to']}<br>{task.get('description','')}")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.button(QMessageBox.StandardButton.Yes).setText("Bắt đầu ngay")
        msg.button(QMessageBox.StandardButton.No).setText("Để sau")
        choice = msg.exec()
        if choice == QMessageBox.StandardButton.Yes:
            self.start_focus_mode(task)

    def start_focus_mode(self, task):
        """
        Mở FocusWindow và gọi auto_check một lần để nó bắt ngay (nếu window đã mở).
        """
        provider = lambda: self.data.get(datetime.now().strftime("%Y-%m-%d"), [])
        if not hasattr(self, "focus_window") or not getattr(self.focus_window, "isVisible", lambda: False)():
            self.focus_window = FocusWindow(provider)
            self.focus_window.show()
        # ép FocusWindow kiểm tra ngay (nếu có task đang chạy nó sẽ start countdown)
        try:
            self.focus_window.auto_check_task()
        except Exception:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
