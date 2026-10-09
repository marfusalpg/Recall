from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from recall.config.settings import (
    AI_PROVIDER_GEMINI,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    AppSettings,
    tesseract_path_error,
)


class DashboardPage(QWidget):
    start_requested = Signal()
    stop_requested = Signal()
    open_engine = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        intro = QVBoxLayout()
        eyebrow = QLabel("LOCAL DESKTOP ENGINE")
        eyebrow.setObjectName("eyebrow")
        heading = QLabel("Screen capture, OCR, response.")
        heading.setObjectName("heroTitle")
        description = QLabel(
            "Recall listens for your configured trigger and runs the real "
            "Tesseract and selected AI provider pipeline in the background."
        )
        description.setObjectName("heroDescription")
        description.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(heading)
        intro.addWidget(description)
        layout.addLayout(intro)

        status_grid = QGridLayout()
        status_grid.setSpacing(12)
        self.engine_value = self._add_status_card(
            status_grid, 0, "ENGINE", "Stopped"
        )
        self.api_value = self._add_status_card(
            status_grid, 1, "AI API", "Checking configuration"
        )
        self.api_title = self.api_value.parentWidget().layout().itemAt(0).widget()
        self.ocr_value = self._add_status_card(
            status_grid, 2, "OCR / TESSERACT", "Checking configuration"
        )
        self.model_value = self._add_status_card(
            status_grid, 3, "MODEL / TRIGGER", "—"
        )
        layout.addLayout(status_grid)

        self.error_card = QFrame()
        self.error_card.setObjectName("statusCard")
        error_layout = QVBoxLayout(self.error_card)
        error_layout.setContentsMargins(16, 14, 16, 14)
        error_layout.setSpacing(7)
        error_title = QLabel("Latest engine / API error")
        error_title.setObjectName("cardTitle")
        self.error_details = QLabel()
        self.error_details.setObjectName("errorText")
        self.error_details.setWordWrap(True)
        error_layout.addWidget(error_title)
        error_layout.addWidget(self.error_details)
        self.error_card.hide()
        layout.addWidget(self.error_card)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start engine")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.start_requested.emit)
        self.stop_button = QPushButton("Stop engine")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        self.config_button = QPushButton("Engine configuration")
        self.config_button.setObjectName("secondaryButton")
        self.config_button.clicked.connect(self.open_engine.emit)
        controls.addWidget(self.config_button)
        layout.addLayout(controls)

        recent = QFrame()
        recent.setObjectName("statusCard")
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(16, 14, 16, 14)
        recent_layout.setSpacing(7)
        title = QLabel("Recent operation")
        title.setObjectName("cardTitle")
        self.operation_status = QLabel("No operation has run yet.")
        self.operation_status.setObjectName("mutedText")
        recent_layout.addWidget(title)
        recent_layout.addWidget(self.operation_status)
        layout.addWidget(recent)
        layout.addStretch()

    @staticmethod
    def _add_status_card(
        grid: QGridLayout, column: int, title: str, value: str
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("infoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 13, 15, 13)
        card_layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("sectionLabel")
        value_label = QLabel(value)
        value_label.setObjectName("statusValue")
        value_label.setWordWrap(True)
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        grid.addWidget(card, 0, column)
        return value_label

    def refresh_configuration(
        self, settings: AppSettings, api_key_configured: bool
    ) -> None:
        self.api_value.setText(
            "Configured" if api_key_configured else "Missing API key"
        )
        self.ocr_value.setText(
            "Configured"
            if tesseract_path_error(settings.tesseract_path) is None
            else "Tesseract path required"
        )
        is_gemini = settings.ai_provider == AI_PROVIDER_GEMINI
        provider = "Gemini" if is_gemini else "OpenAI"
        model = DEFAULT_GEMINI_MODEL if is_gemini else DEFAULT_OPENAI_MODEL
        self.api_title.setText(f"{provider.upper()} API")
        self.model_value.setText(f"{model}  ·  {settings.trigger_key}")

    def set_engine_state(self, state: str) -> None:
        labels = {
            "stopped": "Stopped",
            "starting": "Starting",
            "running": "Running",
            "stopping": "Stopping",
            "error": "Error",
        }
        self.engine_value.setText(labels.get(state, state.title()))
        self.start_button.setEnabled(state in ("stopped", "error"))
        self.stop_button.setEnabled(state in ("starting", "running", "stopping"))

    def set_operation_status(self, message: str) -> None:
        self.operation_status.setText(message)

    def set_error(self, message: str) -> None:
        self.error_details.setText(message)
        self.error_card.setVisible(bool(message))

    def clear_error(self) -> None:
        self.error_details.clear()
        self.error_card.hide()
