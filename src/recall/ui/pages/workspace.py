from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from recall.config.settings import AppSettings, tesseract_path_error


class KeyCaptureLineEdit(QLineEdit):
    key_captured = Signal(str)
    capture_started = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setPlaceholderText("Click here, then press a key")
        self._waiting_for_key = False

    def mousePressEvent(self, event) -> None:
        self._waiting_for_key = True
        self.setText("Waiting for input")
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.capture_started.emit()
        event.accept()

    def keyPressEvent(self, event) -> None:
        if not self._waiting_for_key:
            event.ignore()
            return

        key = event.key()
        special_keys = {
            Qt.Key.Key_Control: "left ctrl",
            Qt.Key.Key_Alt: "left alt",
            Qt.Key.Key_Meta: "windows",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
        }
        name = special_keys.get(key)
        if key == Qt.Key.Key_Shift:
            name = {42: "left shift", 54: "right shift"}.get(
                event.nativeScanCode(), "left shift"
            )
        if name is None:
            text = event.text().strip()
            if text and text.isprintable():
                name = text.casefold()
            elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
                name = f"f{key - Qt.Key.Key_F1 + 1}"

        if name:
            self._waiting_for_key = False
            self.setText(name.title())
            self.key_captured.emit(name)
            event.accept()
            return
        event.ignore()


class WorkspacePage(QWidget):
    settings_saved = Signal(object)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        intro = QLabel(
            "Configure the live screenshot, OCR, hotkey and answer overlay "
            "pipeline. Tesseract language data must be installed separately."
        )
        intro.setObjectName("mutedText")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        settings_card = QFrame()
        settings_card.setObjectName("settingsCard")
        form = QFormLayout(settings_card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(11)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self.language = QComboBox()
        for label, code in (
            ("Czech + English", "ces+eng"),
            ("English", "eng"),
            ("Czech", "ces"),
        ):
            self.language.addItem(label, code)
        self.trigger = KeyCaptureLineEdit()

        path_row = QHBoxLayout()
        self.tesseract_path = QLineEdit()
        self.tesseract_path.setPlaceholderText(
            "Path to tesseract.exe (for example C:\\Program Files\\Tesseract-OCR\\tesseract.exe)"
        )
        browse = QPushButton("Browse…")
        browse.setObjectName("secondaryButton")
        browse.clicked.connect(self._browse_tesseract)
        path_row.addWidget(self.tesseract_path, 1)
        path_row.addWidget(browse)
        self._browse_button = browse

        self.duration = QSpinBox()
        self.duration.setRange(500, 60000)
        self.duration.setSingleStep(500)
        self.duration.setSuffix(" ms")
        self.opacity = QSpinBox()
        self.opacity.setRange(10, 100)
        self.opacity.setSuffix(" %")
        self.size = QSpinBox()
        self.size.setRange(32, 240)
        self.size.setSuffix(" px")
        self._saved_custom_prompt = settings.custom_prompt
        self._ai_provider = settings.ai_provider

        form.addRow("OCR language", self.language)
        form.addRow("Tesseract executable", path_row)
        form.addRow("Global trigger key", self.trigger)
        form.addRow("Result display duration", self.duration)
        form.addRow("Overlay opacity", self.opacity)
        form.addRow("Overlay size", self.size)
        layout.addWidget(settings_card)

        actions = QHBoxLayout()
        self.feedback = QLabel("Settings are stored locally on this device.")
        self.feedback.setObjectName("mutedText")
        self.save_button = QPushButton("Save engine settings")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._save_settings)
        actions.addWidget(self.feedback, 1)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        diagnostics = QFrame()
        diagnostics.setObjectName("statusCard")
        diagnostics_layout = QVBoxLayout(diagnostics)
        diagnostics_layout.setContentsMargins(16, 14, 16, 14)
        diagnostics_layout.setSpacing(7)
        title = QLabel("Engine diagnostics")
        title.setObjectName("cardTitle")
        self.engine_status = QLabel("Engine stopped.")
        self.engine_status.setObjectName("mutedText")
        self.last_error = QLabel("No recent errors.")
        self.last_error.setObjectName("errorText")
        self.last_error.setWordWrap(True)
        diagnostics_layout.addWidget(title)
        diagnostics_layout.addWidget(self.engine_status)
        diagnostics_layout.addWidget(self.last_error)
        layout.addWidget(diagnostics)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.set_settings(settings)

    def set_settings(self, settings: AppSettings) -> None:
        self._ai_provider = settings.ai_provider
        index = self.language.findData(settings.ocr_language)
        if index >= 0:
            self.language.setCurrentIndex(index)
        self.tesseract_path.setText(settings.tesseract_path)
        self.trigger.setText(settings.trigger_key)
        self.duration.setValue(settings.overlay_duration_ms)
        self.opacity.setValue(round(settings.overlay_opacity * 100))
        self.size.setValue(settings.overlay_size)

    def set_engine_state(self, state: str) -> None:
        running = state in ("starting", "running", "stopping")
        self.save_button.setEnabled(not running)
        self._browse_button.setEnabled(not running)
        self.engine_status.setText(f"Engine {state}.")
        if running:
            self.feedback.setText(
                "Stop the engine before changing its active configuration."
            )

    def set_status(self, message: str) -> None:
        self.engine_status.setText(message)

    def set_error(self, message: str) -> None:
        self.last_error.setText(message)

    def clear_error(self) -> None:
        self.last_error.setText("No recent errors.")

    def _browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Tesseract executable",
            self.tesseract_path.text(),
            "Tesseract executable (tesseract.exe);;All files (*)",
        )
        if path:
            self.tesseract_path.setText(path)

    def _save_settings(self) -> None:
        trigger = self.trigger.text().strip()
        tesseract_path = self.tesseract_path.text().strip()
        if not trigger or trigger == "Waiting for input":
            self.feedback.setText("Click the trigger field and press a key first.")
            return
        path_error = tesseract_path_error(tesseract_path)
        if tesseract_path and path_error:
            self.feedback.setText(path_error)
            return

        settings = AppSettings(
            ai_provider=self._ai_provider,
            ocr_language=self.language.currentData(),
            tesseract_path=tesseract_path,
            trigger_key=trigger,
            custom_prompt=self._saved_custom_prompt,
            overlay_duration_ms=self.duration.value(),
            overlay_opacity=self.opacity.value() / 100.0,
            overlay_size=self.size.value(),
        )
        self.feedback.setText("Saving settings…")
        self.settings_saved.emit(settings)

    def set_custom_prompt(self, prompt: str) -> None:
        self._saved_custom_prompt = prompt

    def settings_were_saved(self) -> None:
        self.feedback.setText(
            "Settings saved. Changes apply the next time the engine starts."
        )
