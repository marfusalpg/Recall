from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from recall.config.credentials import CredentialStoreError, get_api_key
from recall.config.settings import AppSettings, SettingsStore
from recall.engine.controller import EngineController
from recall.ui.overlay import AnswerOverlay
from recall.ui.pages.dashboard import DashboardPage
from recall.ui.pages.settings import SettingsPage
from recall.ui.pages.workspace import WorkspacePage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Recall")
        self.resize(1120, 740)
        self.setMinimumSize(860, 620)

        self._settings_store = SettingsStore()
        self._settings = self._settings_store.load()
        self._close_pending = False
        self.engine = EngineController()
        self.overlay = AnswerOverlay()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(208)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 15)
        sidebar_layout.setSpacing(8)

        brand = QHBoxLayout()
        brand_icon = QLabel("R")
        brand_icon.setObjectName("brandIcon")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(32, 32)
        brand_name = QLabel("Recall")
        brand_name.setObjectName("brandName")
        brand.addWidget(brand_icon)
        brand.addWidget(brand_name)
        brand.addStretch()
        sidebar_layout.addLayout(brand)
        sidebar_layout.addSpacing(28)

        nav_label = QLabel("APPLICATION")
        nav_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(nav_label)
        sidebar_layout.addSpacing(5)

        self.dashboard = DashboardPage()
        self.engine_page = WorkspacePage(self._settings)
        self.settings_page = SettingsPage(
            self._settings.custom_prompt, self._settings.ai_provider
        )
        self.pages = QStackedWidget()
        for page in (self.dashboard, self.engine_page, self.settings_page):
            self.pages.addWidget(page)

        self.navigation_buttons: dict[int, QPushButton] = {}
        for label, index in (
            ("Overview", 0),
            ("Engine", 1),
            ("Settings", 2),
        ):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, page_index=index: self.navigate(page_index)
            )
            self.navigation_buttons[index] = button
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()
        local_status = QFrame()
        local_status.setObjectName("profileCard")
        local_layout = QVBoxLayout(local_status)
        local_layout.setContentsMargins(11, 11, 11, 11)
        local_layout.setSpacing(4)
        local_title = QLabel("Local utility")
        local_title.setObjectName("profileTitle")
        local_detail = QLabel("API keys stay on this device")
        local_detail.setObjectName("mutedText")
        local_detail.setWordWrap(True)
        local_layout.addWidget(local_title)
        local_layout.addWidget(local_detail)
        sidebar_layout.addWidget(local_status)

        content = QWidget()
        content.setObjectName("mainContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 23, 28, 22)
        content_layout.setSpacing(18)
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title_group.setSpacing(4)
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("mutedText")
        title_group.addWidget(self.page_title)
        title_group.addWidget(self.page_subtitle)
        header.addLayout(title_group)
        header.addStretch()
        version = QLabel("DESKTOP")
        version.setObjectName("versionBadge")
        header.addWidget(version, alignment=Qt.AlignmentFlag.AlignTop)
        content_layout.addLayout(header)
        content_layout.addWidget(self.pages, 1)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.dashboard.start_requested.connect(
            lambda: self.engine.start(self._settings)
        )
        self.dashboard.stop_requested.connect(self.engine.stop)
        self.dashboard.open_engine.connect(lambda: self.navigate(1))
        self.engine_page.settings_saved.connect(self._save_engine_settings)
        self.settings_page.custom_prompt_saved.connect(self._save_custom_prompt)
        self.settings_page.provider_saved.connect(self._save_ai_provider)
        self.settings_page.credentials_refreshed.connect(
            self._refresh_configuration_status
        )

        self.engine.state_changed.connect(self._on_engine_state_changed)
        self.engine.operation_status_changed.connect(
            self._on_operation_status_changed
        )
        self.engine.operation_error.connect(self._on_operation_error)
        self.engine.answer_ready.connect(self._show_answer)

        self._refresh_configuration_status()
        self._on_engine_state_changed(self.engine.state)
        self.navigate(0)

    def navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        titles = {
            0: ("Overview", "Live engine and integration status"),
            1: ("Engine", "Configure capture, OCR, trigger and overlay"),
            2: ("Settings", "API credentials and local preferences"),
        }
        self.page_title.setText(titles[index][0])
        self.page_subtitle.setText(titles[index][1])
        for button_index, button in self.navigation_buttons.items():
            button.setChecked(button_index == index)

    def _save_engine_settings(self, settings: AppSettings) -> None:
        settings = AppSettings(
            ai_provider=self._settings.ai_provider,
            ocr_language=settings.ocr_language,
            tesseract_path=settings.tesseract_path,
            trigger_key=settings.trigger_key,
            custom_prompt=settings.custom_prompt,
            overlay_duration_ms=settings.overlay_duration_ms,
            overlay_opacity=settings.overlay_opacity,
            overlay_size=settings.overlay_size,
        )
        self._settings_store.save(settings)
        self._settings = settings
        self.engine_page.settings_were_saved()
        self._refresh_configuration_status()

    def _save_custom_prompt(self, prompt: str) -> None:
        self._settings = AppSettings(
            ai_provider=self._settings.ai_provider,
            ocr_language=self._settings.ocr_language,
            tesseract_path=self._settings.tesseract_path,
            trigger_key=self._settings.trigger_key,
            custom_prompt=prompt,
            overlay_duration_ms=self._settings.overlay_duration_ms,
            overlay_opacity=self._settings.overlay_opacity,
            overlay_size=self._settings.overlay_size,
        )
        self._settings_store.save(self._settings)
        self.engine_page.set_custom_prompt(prompt)

    def _save_ai_provider(self, provider: str) -> None:
        self._settings = AppSettings(
            ai_provider=provider,
            ocr_language=self._settings.ocr_language,
            tesseract_path=self._settings.tesseract_path,
            trigger_key=self._settings.trigger_key,
            custom_prompt=self._settings.custom_prompt,
            overlay_duration_ms=self._settings.overlay_duration_ms,
            overlay_opacity=self._settings.overlay_opacity,
            overlay_size=self._settings.overlay_size,
        )
        self._settings_store.save(self._settings)
        self._refresh_configuration_status()

    def _refresh_configuration_status(self) -> None:
        try:
            configured = bool(get_api_key(self._settings.ai_provider))
        except CredentialStoreError as exc:
            self.dashboard.refresh_configuration(self._settings, False)
            self.dashboard.api_value.setText("Credential store unavailable")
            self.dashboard.set_error(str(exc))
            return
        self.dashboard.refresh_configuration(self._settings, configured)

    def _on_engine_state_changed(self, state: str) -> None:
        self.dashboard.set_engine_state(state)
        self.engine_page.set_engine_state(state)
        self.settings_page.set_engine_state(state)
        if state == "starting":
            self.dashboard.clear_error()
            self.engine_page.clear_error()
        if self._close_pending and state == "stopped":
            QTimer.singleShot(0, self.close)

    def _on_operation_status_changed(self, message: str) -> None:
        self.dashboard.set_operation_status(message)
        self.engine_page.set_status(message)

    def _on_operation_error(self, message: str) -> None:
        self.dashboard.set_error(message)
        self.engine_page.set_error(message)

    def _show_answer(self, answer: str) -> None:
        self.dashboard.clear_error()
        self.engine_page.clear_error()
        self.overlay.show_answer(answer, self._settings)

    def closeEvent(self, event) -> None:
        if self.engine.state != "stopped":
            self._close_pending = True
            self.engine.shutdown()
            event.ignore()
            return
        self.overlay.close()
        super().closeEvent(event)
