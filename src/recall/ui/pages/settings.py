import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from recall.config.credentials import (
    CredentialStoreError,
    get_api_key,
    get_api_key_environment_variable,
    save_api_key,
)
from recall.config.settings import (
    AI_PROVIDER_GEMINI,
    AI_PROVIDER_OPENAI,
    DEFAULT_PROMPT,
)


class SettingsPage(QWidget):
    credentials_refreshed = Signal()
    custom_prompt_saved = Signal(str)
    provider_saved = Signal(str)

    def __init__(
        self, custom_prompt: str, ai_provider: str = AI_PROVIDER_OPENAI
    ) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        intro = QLabel(
            "Choose an AI provider, set its API key and customize the "
            "instructions sent with each screen capture."
        )
        intro.setObjectName("mutedText")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        credential_card = QFrame()
        credential_card.setObjectName("settingsCard")
        credential_layout = QVBoxLayout(credential_card)
        credential_layout.setContentsMargins(18, 16, 18, 16)
        credential_layout.setSpacing(9)

        credential_title = QLabel("Your API key")
        credential_title.setObjectName("sectionTitle")
        self.provider = QComboBox()
        self.provider.addItem("OpenAI", AI_PROVIDER_OPENAI)
        self.provider.addItem("Google Gemini", AI_PROVIDER_GEMINI)
        provider_index = self.provider.findData(ai_provider)
        self.provider.setCurrentIndex(provider_index if provider_index >= 0 else 0)
        self.provider.currentIndexChanged.connect(self._on_provider_changed)
        credential_description = QLabel(
            "Saved in the operating system credential vault. The key is "
            "never shown again or written to Recall settings. Environment "
            "variables take precedence over saved keys."
        )
        credential_description.setObjectName("mutedText")
        credential_description.setWordWrap(True)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        selected_provider = self.provider.currentData()
        provider_name = (
            "Google Gemini"
            if selected_provider == AI_PROVIDER_GEMINI
            else "OpenAI"
        )
        self.api_key.setPlaceholderText(f"Paste your {provider_name} API key")
        self.credential_status = QLabel()
        self.credential_status.setObjectName("mutedText")

        credential_actions = QHBoxLayout()
        self.save_key_button = QPushButton("Save API key")
        self.save_key_button.setObjectName("primaryButton")
        self.save_key_button.clicked.connect(self._save_key)
        self.remove_key_button = QPushButton("Remove saved key")
        self.remove_key_button.setObjectName("secondaryButton")
        self.remove_key_button.clicked.connect(self._remove_key)
        credential_actions.addWidget(self.save_key_button)
        credential_actions.addWidget(self.remove_key_button)
        credential_actions.addStretch()

        credential_layout.addWidget(credential_title)
        credential_layout.addWidget(QLabel("AI provider"))
        credential_layout.addWidget(self.provider)
        credential_layout.addWidget(credential_description)
        credential_layout.addWidget(self.api_key)
        credential_layout.addLayout(credential_actions)
        credential_layout.addWidget(self.credential_status)
        layout.addWidget(credential_card)

        prompt_card = QFrame()
        prompt_card.setObjectName("settingsCard")
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setContentsMargins(18, 16, 18, 16)
        prompt_layout.setSpacing(9)
        prompt_title = QLabel("Custom Prompt")
        prompt_title.setObjectName("sectionTitle")
        prompt_description = QLabel(
            "These instructions are sent first. The recognized screen text is "
            "appended after a blank line."
        )
        prompt_description.setObjectName("mutedText")
        prompt_description.setWordWrap(True)
        self.custom_prompt = QPlainTextEdit()
        self.custom_prompt.setObjectName("promptEditor")
        self.custom_prompt.setPlaceholderText(DEFAULT_PROMPT)
        self.custom_prompt.setPlainText(custom_prompt)
        self.custom_prompt.setMinimumHeight(110)
        prompt_actions = QHBoxLayout()
        self.prompt_status = QLabel("Default prompt is in English.")
        self.prompt_status.setObjectName("mutedText")
        self.save_prompt_button = QPushButton("Save custom prompt")
        self.save_prompt_button.setObjectName("secondaryButton")
        self.save_prompt_button.clicked.connect(self._save_prompt)
        prompt_actions.addWidget(self.prompt_status, 1)
        prompt_actions.addWidget(self.save_prompt_button)
        prompt_layout.addWidget(prompt_title)
        prompt_layout.addWidget(prompt_description)
        prompt_layout.addWidget(self.custom_prompt)
        prompt_layout.addLayout(prompt_actions)
        layout.addWidget(prompt_card)
        layout.addStretch()

        self._refresh_status()

    @property
    def api_key_configured(self) -> bool:
        try:
            return bool(get_api_key(self.provider.currentData()))
        except CredentialStoreError:
            return False

    def _save_key(self) -> None:
        api_key = self.api_key.text().strip()
        if not api_key:
            self.credential_status.setText("Paste an API key before saving.")
            return
        try:
            save_api_key(api_key, self.provider.currentData())
        except CredentialStoreError as exc:
            self.credential_status.setText(str(exc))
            return

        self.api_key.clear()
        self.credential_status.setText("API key saved to the system credential vault.")
        self._refresh_status()

    def _remove_key(self) -> None:
        try:
            save_api_key("", self.provider.currentData())
        except CredentialStoreError as exc:
            self.credential_status.setText(str(exc))
            return
        self.credential_status.setText("Saved API key removed.")
        self._refresh_status()

    def _save_prompt(self) -> None:
        prompt = self.custom_prompt.toPlainText().strip()
        if not prompt:
            self.prompt_status.setText("Custom Prompt cannot be empty.")
            return
        self.custom_prompt_saved.emit(prompt)
        self.prompt_status.setText("Custom prompt saved.")

    def _refresh_status(self) -> None:
        try:
            provider = self.provider.currentData()
            environment_variable = get_api_key_environment_variable(provider)
            if get_api_key(provider):
                if self._environment_key_is_set(environment_variable):
                    self.credential_status.setText(
                        f"{environment_variable} is active and takes "
                        "precedence over a saved key."
                    )
                else:
                    self.credential_status.setText(
                        "An API key is available from the system credential vault."
                    )
            else:
                self.credential_status.setText("No API key is configured.")
        except CredentialStoreError as exc:
            self.credential_status.setText(str(exc))
        self.credentials_refreshed.emit()

    @staticmethod
    def _environment_key_is_set(environment_variable: str) -> bool:
        return bool(os.environ.get(environment_variable, "").strip())

    def _on_provider_changed(self, index: int) -> None:
        provider = self.provider.itemData(index)
        display_name = "Google Gemini" if provider == AI_PROVIDER_GEMINI else "OpenAI"
        self.api_key.setPlaceholderText(f"Paste your {display_name} API key")
        self.provider_saved.emit(provider)
        self._refresh_status()

    def set_engine_state(self, state: str) -> None:
        self.provider.setEnabled(state not in ("starting", "running", "stopping"))
