"""
monkeyLog Entry GUI
PyQt6 form for inserting records into the monkeyLog MySQL/MariaDB table.

Dependencies:
    pip install pymysql
    pip install PyQt6

Usage:
    python monkey_log_gui.py
"""

import sys
from datetime import datetime, date, time
import base64

import pymysql
from pymysql import Error

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QTextEdit, QDateEdit, QTimeEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame,
    QStatusBar, QCheckBox
)
from PyQt6.QtCore import Qt, QDate, QTime, QSettings
from PyQt6.QtGui import QFont


# ── Database configuration ──────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "100.122.138.128",
    "port":     3306,
    "database": "smiledb",
    "user":     "rs350044",
    "password": "SECRET",
}

# ── Settings helpers ──────────────────────────────────────────────────────────

def get_settings() -> QSettings:
    """Return a QSettings instance scoped to this app (stored in registry on Windows)."""
    return QSettings("BatistaLab", "MonkeyLog")


def load_connection_settings(username: str) -> dict:
    """Load saved connection settings for a given username."""
    s = get_settings()
    s.beginGroup(f"connections/{username}")
    result = {
        "host":            s.value("host",     DB_CONFIG["host"]),
        "port":            int(s.value("port", DB_CONFIG["port"])),
        "database":        s.value("database", DB_CONFIG["database"]),
        "remember_password": s.value("remember_password", False, type=bool),
        "password":        "",
    }
    if result["remember_password"]:
        encoded = s.value("password", "")
        result["password"] = base64.b64decode(encoded.encode()).decode() if encoded else ""
    s.endGroup()
    return result


def save_connection_settings(username: str, host: str, port: int,
                             database: str, remember: bool, password: str):
    """Save connection settings for a given username."""
    s = get_settings()
    s.beginGroup(f"connections/{username}")
    s.setValue("host",     host)
    s.setValue("port",     port)
    s.setValue("database", database)
    s.setValue("remember_password", remember)
    if remember:
        # Obfuscate password (not true encryption, but prevents casual shoulder surfing in registry)
        s.setValue("password", base64.b64encode(password.encode()).decode())
    else:
        s.remove("password")
    s.endGroup()


def date_to_yyyymmdd(d: date) -> int:
    """Convert a Python date to a YYYYMMDD integer (e.g. 2026-02-24 → 20260224)."""
    return int(d.strftime("%Y%m%d"))


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ── Widgets ───────────────────────────────────────────────────────────────────

def make_group(title: str) -> tuple[QGroupBox, QFormLayout]:
    box = QGroupBox(title)
    box.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 6px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #333;
        }
    """)
    layout = QFormLayout(box)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    layout.setSpacing(8)
    layout.setContentsMargins(12, 16, 12, 12)
    return box, layout


def yes_no_combo(allow_blank: bool = True) -> QComboBox:
    cb = QComboBox()
    if allow_blank:
        cb.addItem("", None)
    cb.addItem("True", "True")
    cb.addItem("False", "False")
    return cb


def double_spin(min_val=0.0, max_val=99999.0, decimals=2, step=0.1) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(min_val, max_val)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setSpecialValueText(" ")   # blank when at minimum (used as "empty")
    sb.setValue(min_val)
    return sb


# ── Main Window ───────────────────────────────────────────────────────────────

class MonkeyLogForm(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("monkeyLog")
        self.setMinimumWidth(680)
        self.setMinimumHeight(680)
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Central scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("🐒  Monkey Log")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # ── Group 0: Database Connection ─────────────────────────────────────
        g0, f0 = make_group("Database Connection")

        self.db_host = QLineEdit(DB_CONFIG["host"])
        f0.addRow("Host:", self.db_host)

        self.db_port = QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(DB_CONFIG["port"])
        f0.addRow("Port:", self.db_port)

        self.db_name = QLineEdit(DB_CONFIG["database"])
        f0.addRow("Database:", self.db_name)

        self.db_user = QLineEdit(DB_CONFIG["user"])
        self.db_user.setPlaceholderText("your username")
        self.db_user.editingFinished.connect(self._on_username_changed)
        f0.addRow("User:", self.db_user)

        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_password.setPlaceholderText("password")
        f0.addRow("Password:", self.db_password)

        self.remember_password = QCheckBox("Remember password for this user")
        f0.addRow("", self.remember_password)

        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setFixedHeight(30)
        self.btn_test.setStyleSheet("background-color: #2196F3; color: white; border-radius: 4px;")
        self.btn_test.clicked.connect(self._test_connection)
        f0.addRow("", self.btn_test)

        main_layout.addWidget(g0)

        # Load saved settings for the default user (if any)
        self._load_settings_for_user(self.db_user.text().strip())

        # ── Group 1: Session Info ────────────────────────────────────────────
        g1, f1 = make_group("Session Info")

        self.subject = QLineEdit()
        self.subject.setPlaceholderText("e.g. Hercules")
        f1.addRow("Subject:", self.subject)

        self.experiment_date = QDateEdit(QDate.currentDate())
        self.experiment_date.setCalendarPopup(True)
        self.experiment_date.setDisplayFormat("yyyy-MM-dd")
        f1.addRow("Experiment Date:", self.experiment_date)

        self.trainer = QLineEdit()
        self.trainer.setPlaceholderText("Trainer name")
        f1.addRow("Trainer:", self.trainer)

        self.rig = double_spin(0.0, 99.0, decimals=0, step=1.0)
        self.rig.setSpecialValueText(" ")
        f1.addRow("Rig:", self.rig)

        main_layout.addWidget(g1)

        # ── Group 2: Animal Care ─────────────────────────────────────────────
        g2, f2 = make_group("Animal Care")

        self.water = QLineEdit()
        self.water.setPlaceholderText("e.g. 200 mL")
        self.water.setMaxLength(14)
        f2.addRow("Water:", self.water)

        self.extra_water = QLineEdit()
        self.extra_water.setPlaceholderText("e.g. 50 mL")
        self.extra_water.setMaxLength(14)
        f2.addRow("Extra Water:", self.extra_water)

        self.weight = double_spin(0.0, 50.0, decimals=2, step=0.01)
        f2.addRow("Weight (kg):", self.weight)

        self.enrichment = QLineEdit()
        self.enrichment.setPlaceholderText("e.g. puzzle feeder")
        f2.addRow("Enrichment:", self.enrichment)

        self.fruit_vegetable = QLineEdit()
        self.fruit_vegetable.setPlaceholderText("e.g. apple, carrot")
        f2.addRow("Fruit / Vegetable:", self.fruit_vegetable)

        self.cleaned_margins = yes_no_combo()
        f2.addRow("Cleaned Margins:", self.cleaned_margins)

        self.trimmed_hair = yes_no_combo()
        f2.addRow("Trimmed Hair:", self.trimmed_hair)

        main_layout.addWidget(g2)

        # ── Group 3: Experiment ──────────────────────────────────────────────
        g3, f3 = make_group("Experiment")

        self.trained = yes_no_combo()
        f3.addRow("Trained:", self.trained)

        self.start_time = QTimeEdit(QTime.currentTime())
        self.start_time.setDisplayFormat("HH:mm")
        f3.addRow("Start Time:", self.start_time)

        self.end_time = QTimeEdit(QTime.currentTime())
        self.end_time.setDisplayFormat("HH:mm")
        f3.addRow("End Time:", self.end_time)

        self.task = QLineEdit()
        f3.addRow("Task:", self.task)

        self.total_trials = double_spin(0, 99999, decimals=0, step=1)
        f3.addRow("Total Trials:", self.total_trials)

        self.successful_trials = double_spin(0, 99999, decimals=0, step=1)
        f3.addRow("Successful Trials:", self.successful_trials)

        self.success_rate = double_spin(0.0, 100.0, decimals=2, step=0.01)
        f3.addRow("Success Rate (%):", self.success_rate)

        self.parameter_file = QLineEdit()
        self.parameter_file.setPlaceholderText("path/to/params.mat")
        f3.addRow("Parameter File:", self.parameter_file)

        self.experiment_stage = QLineEdit()
        f3.addRow("Experiment Stage:", self.experiment_stage)

        self.task_arm = QLineEdit()
        f3.addRow("Task Arm:", self.task_arm)

        self.tank = QLineEdit()
        f3.addRow("Tank:", self.tank)

        self.controller = QLineEdit()
        self.controller.setPlaceholderText("Controller identifier")
        f3.addRow("Controller:", self.controller)

        main_layout.addWidget(g3)

        # ── Group 4: Hardware / Setup ────────────────────────────────────────
        g4, f4 = make_group("Hardware / Setup")

        self.implant = QLineEdit()
        f4.addRow("Implant:", self.implant)

        self.eyes_tracked = yes_no_combo()
        f4.addRow("Eyes Tracked:", self.eyes_tracked)

        self.publish_quality = yes_no_combo()
        f4.addRow("Publish Quality:", self.publish_quality)

        main_layout.addWidget(g4)

        # ── Group 5: Notes ───────────────────────────────────────────────────
        g5, f5 = make_group("Notes")

        self.health_notes = QTextEdit()
        self.health_notes.setFixedHeight(70)
        f5.addRow("Health Notes:", self.health_notes)

        self.system_notes = QTextEdit()
        self.system_notes.setFixedHeight(70)
        f5.addRow("System Notes:", self.system_notes)

        self.notes = QTextEdit()
        self.notes.setFixedHeight(70)
        f5.addRow("General Notes:", self.notes)

        main_layout.addWidget(g5)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        self.btn_clear = QPushButton("Clear Form")
        self.btn_clear.setFixedHeight(36)
        self.btn_clear.setStyleSheet("background-color: #e0e0e0; border-radius: 4px;")
        self.btn_clear.clicked.connect(self._clear_form)

        self.btn_submit = QPushButton("Submit Entry")
        self.btn_submit.setFixedHeight(36)
        self.btn_submit.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px;"
        )
        self.btn_submit.clicked.connect(self._submit)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_submit)
        main_layout.addLayout(btn_layout)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    # ── Logic ────────────────────────────────────────────────────────────────

    def _collect_data(self) -> dict:
        """Read all widgets and return a dict ready for SQL insertion."""

        def text_or_none(widget) -> str | None:
            v = widget.text().strip()
            return v if v else None

        def combo_val(widget) -> str | None:
            return widget.currentData()

        def spin_or_none(widget) -> float | None:
            # QDoubleSpinBox with specialValueText at minimum means "empty"
            if widget.value() == widget.minimum():
                return None
            return widget.value()

        def textedit_or_none(widget) -> str | None:
            v = widget.toPlainText().strip()
            return v if v else None

        exp_date = date_to_yyyymmdd(self.experiment_date.date().toPyDate())

        return {
            "Subject":          text_or_none(self.subject),
            "ExperimentDate":   exp_date,
            "Trainer":          text_or_none(self.trainer),
            "Water":            text_or_none(self.water),
            "Weight":           spin_or_none(self.weight),
            "Enrichment":       text_or_none(self.enrichment),
            "FruitVegetable":   text_or_none(self.fruit_vegetable),
            "Trained":          combo_val(self.trained),
            "StartTime":        self.start_time.time().toString("HH:mm"),
            "EndTime":          self.end_time.time().toString("HH:mm"),
            "Task":             text_or_none(self.task),
            "TotalTrials":      spin_or_none(self.total_trials),
            "SuccessfulTrials": spin_or_none(self.successful_trials),
            "SuccessRate":      spin_or_none(self.success_rate),
            "ParameterFile":    text_or_none(self.parameter_file),
            "Tank":             text_or_none(self.tank),
            "Controller":       text_or_none(self.controller),   # stored as bytes
            "ExperimentStage":  text_or_none(self.experiment_stage),
            "TaskArm":          text_or_none(self.task_arm),
            "Implant":          text_or_none(self.implant),
            "HealthNotes":      textedit_or_none(self.health_notes),
            "SystemNotes":      textedit_or_none(self.system_notes),
            "Notes":            textedit_or_none(self.notes),
            "CleanedMargins":   combo_val(self.cleaned_margins),
            "TrimmedHair":      combo_val(self.trimmed_hair),
            "EyesTracked":      combo_val(self.eyes_tracked),
            "PublishQuality":   combo_val(self.publish_quality),
            "Rig":              spin_or_none(self.rig),
            "ExtraWater":       text_or_none(self.extra_water),
        }

    def _load_settings_for_user(self, username: str):
        """Populate connection fields from saved settings for this username."""
        if not username:
            return
        saved = load_connection_settings(username)
        self.db_host.setText(saved["host"])
        self.db_port.setValue(saved["port"])
        self.db_name.setText(saved["database"])
        self.remember_password.setChecked(saved["remember_password"])
        if saved["remember_password"] and saved["password"]:
            self.db_password.setText(saved["password"])
        else:
            self.db_password.clear()

    def _on_username_changed(self):
        """When the user field loses focus, reload saved settings for that username."""
        self._load_settings_for_user(self.db_user.text().strip())

    def _save_current_settings(self):
        """Persist current connection settings for the current username."""
        username = self.db_user.text().strip()
        if not username:
            return
        save_connection_settings(
            username=username,
            host=self.db_host.text().strip(),
            port=self.db_port.value(),
            database=self.db_name.text().strip(),
            remember=self.remember_password.isChecked(),
            password=self.db_password.text(),
        )

    def _get_db_config(self) -> dict:
        """Read connection settings from the UI fields."""
        return {
            "host":     self.db_host.text().strip(),
            "port":     self.db_port.value(),
            "database": self.db_name.text().strip(),
            "user":     self.db_user.text().strip(),
            "password": self.db_password.text(),
        }

    def _test_connection(self):
        try:
            print("Attempting connection...")
            conn = pymysql.connect(**self._get_db_config())
            print("Connected, closing...")
            conn.close()
            print("Saving settings...")
            self._save_current_settings()
            print("Updating status bar...")
            self.status.showMessage("✔ Connection successful")
            print("Showing message box...")
            QMessageBox.information(self, "Connection Test", "Connected to database successfully.")
            print("Done.")
        except Error as e:
            self.status.showMessage("✘ Connection failed")
            QMessageBox.critical(self, "Connection Failed", str(e))

    def _submit(self):
        data = self._collect_data()

        # Basic validation: ExperimentDate is NOT NULL
        if data["ExperimentDate"] is None:
            QMessageBox.warning(self, "Validation Error", "Experiment Date is required.")
            return

        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join([f"`{c}`" for c in columns])
        sql = f"INSERT INTO `monkeyLog` ({col_names}) VALUES ({placeholders})"
        values = [data[c] for c in columns]

        try:
            conn = pymysql.connect(**self._get_db_config())
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()
            cursor.close()
            conn.close()
            self._save_current_settings()

            self.status.showMessage(
                f"✔ Entry inserted successfully — {datetime.now().strftime('%H:%M:%S')}"
            )
            QMessageBox.information(self, "Success", "Record inserted into monkeyLog.")
            self._clear_form()

        except Error as e:
            self.status.showMessage("✘ Database error")
            QMessageBox.critical(self, "Database Error", str(e))

    def _clear_form(self):
        """Reset all widgets to their default/empty state."""
        for w in [self.subject, self.trainer, self.water, self.extra_water,
                  self.enrichment, self.fruit_vegetable, self.task,
                  self.parameter_file, self.experiment_stage, self.task_arm,
                  self.tank, self.controller, self.implant]:
            w.clear()

        for te in [self.health_notes, self.system_notes, self.notes]:
            te.clear()

        for cb in [self.trained, self.cleaned_margins, self.trimmed_hair,
                   self.eyes_tracked, self.publish_quality]:
            cb.setCurrentIndex(0)

        for sb in [self.weight, self.total_trials, self.successful_trials,
                   self.success_rate, self.rig]:
            sb.setValue(sb.minimum())

        self.experiment_date.setDate(QDate.currentDate())
        self.start_time.setTime(QTime.currentTime())
        self.end_time.setTime(QTime.currentTime())

        self.status.showMessage("Form cleared")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MonkeyLogForm()
    window.show()
    sys.exit(app.exec())
