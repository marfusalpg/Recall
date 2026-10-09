from dataclasses import dataclass
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QSettings


DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
AI_PROVIDER_OPENAI = "openai"
AI_PROVIDER_GEMINI = "gemini"
AI_PROVIDERS = (AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI)
DEFAULT_PROMPT = (
    "The text contains a test question and answers A/B/C/D or numbered "
    "options. Determine the correct answer. Return ONLY one letter or "
    "number. Do not add any other text."
)


@dataclass(frozen=True)
class AppSettings:
    ai_provider: str = AI_PROVIDER_OPENAI
    ocr_language: str = "ces+eng"
    tesseract_path: str = ""
    trigger_key: str = "left shift"
    custom_prompt: str = DEFAULT_PROMPT
    overlay_duration_ms: int = 5000
    overlay_opacity: float = 0.9
    overlay_size: int = 64

    @classmethod
    def defaults(cls) -> "AppSettings":
        return cls(tesseract_path=shutil.which("tesseract") or "")


def tesseract_path_error(path: str) -> str | None:
    if not path.strip():
        return "Tesseract is not configured. Set its executable path in Engine settings."

    executable = Path(path)
    if not executable.is_file():
        return f"Tesseract executable was not found: {path}"
    if os.name == "nt" and executable.suffix.casefold() != ".exe":
        return "Select the Tesseract executable file (tesseract.exe)."
    if os.name != "nt" and not os.access(executable, os.X_OK):
        return f"Tesseract is not executable: {path}"
    return None


class SettingsStore:
    """Persist non-secret preferences using the operating system's settings store."""

    def __init__(self) -> None:
        self._settings = QSettings("Recall", "Recall")

    def load(self) -> AppSettings:
        defaults = AppSettings.defaults()
        return AppSettings(
            ai_provider=str(
                self._settings.value("engine/ai_provider", defaults.ai_provider)
            ),
            ocr_language=str(
                self._settings.value("engine/ocr_language", defaults.ocr_language)
            ),
            tesseract_path=str(
                self._settings.value("engine/tesseract_path", defaults.tesseract_path)
            ),
            trigger_key=str(
                self._settings.value("engine/trigger_key", defaults.trigger_key)
            ),
            custom_prompt=str(
                self._settings.value("engine/custom_prompt", defaults.custom_prompt)
            ),
            overlay_duration_ms=int(
                self._settings.value(
                    "overlay/duration_ms", defaults.overlay_duration_ms
                )
            ),
            overlay_opacity=float(
                self._settings.value("overlay/opacity", defaults.overlay_opacity)
            ),
            overlay_size=int(
                self._settings.value("overlay/size", defaults.overlay_size)
            ),
        )

    def save(self, values: AppSettings) -> None:
        self._settings.setValue("engine/ai_provider", values.ai_provider)
        self._settings.setValue("engine/ocr_language", values.ocr_language)
        self._settings.setValue("engine/tesseract_path", values.tesseract_path)
        self._settings.setValue("engine/trigger_key", values.trigger_key)
        self._settings.setValue("engine/custom_prompt", values.custom_prompt)
        self._settings.setValue("overlay/duration_ms", values.overlay_duration_ms)
        self._settings.setValue("overlay/opacity", values.overlay_opacity)
        self._settings.setValue("overlay/size", values.overlay_size)
        self._settings.sync()
