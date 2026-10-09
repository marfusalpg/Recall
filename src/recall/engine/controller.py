import importlib.util

from PySide6.QtCore import QObject, QThread, Signal, Slot

from recall.config.credentials import (
    CredentialStoreError,
    get_api_key,
    get_api_key_environment_variable,
)
from recall.config.settings import (
    AI_PROVIDER_GEMINI,
    AI_PROVIDER_OPENAI,
    AI_PROVIDERS,
    AppSettings,
    tesseract_path_error,
)
from recall.workers.engine_worker import EngineWorker


class EngineController(QObject):
    state_changed = Signal(str)
    operation_status_changed = Signal(str)
    operation_error = Signal(str)
    answer_ready = Signal(str)
    trigger_received = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.trigger_received.connect(self._handle_trigger)
        self._settings = AppSettings.defaults()
        self._thread: QThread | None = None
        self._worker: EngineWorker | None = None
        self._hotkey_handle = None
        self._trigger_is_down = False
        self._busy = False
        self._stopping = False
        self._final_state = "stopped"
        self._state = "stopped"

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def is_stopping(self) -> bool:
        return self._stopping

    def start(self, settings: AppSettings) -> bool:
        if self._state in ("starting", "running", "stopping"):
            return False

        self._set_state("starting")
        self.operation_status_changed.emit("Validating engine configuration…")
        self._settings = settings
        try:
            api_key = (
                get_api_key(settings.ai_provider)
                if settings.ai_provider in AI_PROVIDERS
                else ""
            )
        except CredentialStoreError as exc:
            self._final_state = "error"
            self._set_state("error")
            self.operation_error.emit(str(exc))
            return False
        errors = self._validate_startup(settings, api_key)
        if errors:
            self._final_state = "error"
            self._set_state("error")
            self.operation_error.emit("\n".join(errors))
            return False

        self._stopping = False
        self._final_state = "stopped"
        self._thread = QThread(self)
        self._worker = EngineWorker(settings, api_key)
        self._worker.moveToThread(self._thread)
        self._worker.operation_started.connect(self._on_operation_started)
        self._worker.answer_ready.connect(self._on_answer_ready)
        self._worker.operation_error.connect(self._on_operation_error)
        self._worker.operation_finished.connect(self._on_operation_finished)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

        try:
            import keyboard

            self._trigger_is_down = False
            self._hotkey_handle = keyboard.hook(self._handle_keyboard_event)
        except Exception as exc:
            self._final_state = "error"
            self._stopping = True
            message = str(exc).replace(api_key, "[redacted]")
            self.operation_error.emit(
                f"Could not register hotkey '{settings.trigger_key}': {message}"
            )
            self._stop_worker_thread()
            return False

        self._set_state("running")
        self.operation_status_changed.emit(
            f"Listening for {settings.trigger_key}."
        )
        return True

    def stop(self) -> None:
        if self._state == "stopped" and self._thread is None:
            return

        self._remove_hotkey()
        self._stopping = True
        self._final_state = "stopped"
        self._set_state("stopping")
        if self._busy:
            self.operation_status_changed.emit(
                "Engine stopped listening; the current operation will finish."
            )
            return
        self._stop_worker_thread()

    def _validate_startup(self, settings: AppSettings, api_key: str) -> list[str]:
        errors = []
        if settings.ai_provider not in AI_PROVIDERS:
            errors.append(f"Unsupported AI provider: {settings.ai_provider}")
        if not api_key:
            environment_variable = (
                get_api_key_environment_variable(settings.ai_provider)
                if settings.ai_provider in AI_PROVIDERS
                else "OPENAI_API_KEY or GEMINI_API_KEY"
            )
            provider_name = (
                "Gemini" if settings.ai_provider == AI_PROVIDER_GEMINI else "OpenAI"
            )
            errors.append(
                f"{provider_name} API key is missing. Set the "
                f"{environment_variable} environment variable, then restart Recall."
            )
        if not settings.ocr_language.strip():
            errors.append("Choose at least one OCR language in Engine settings.")
        if not settings.custom_prompt.strip():
            errors.append("Set a Custom Prompt in Settings.")
        if not settings.trigger_key.strip():
            errors.append("Set a trigger key in Engine settings.")

        path_error = tesseract_path_error(settings.tesseract_path)
        if path_error:
            errors.append(path_error)

        ai_dependency = (
            "google.genai"
            if settings.ai_provider == AI_PROVIDER_GEMINI
            else "openai"
        )
        for dependency in ("keyboard", ai_dependency, "pyautogui", "pytesseract"):
            try:
                available = importlib.util.find_spec(dependency) is not None
            except (ImportError, ValueError):
                available = False
            if not available:
                errors.append(
                    f"Required package '{dependency}' is missing. "
                    "Install dependencies with: pip install -r requirements.txt"
                )
        return errors

    @Slot()
    def _handle_trigger(self) -> None:
        if self._state != "running" or self._worker is None:
            return
        if self._busy:
            self.operation_status_changed.emit(
                "Trigger ignored: an operation is already in progress."
            )
            return

        self._busy = True
        self.operation_status_changed.emit("Capturing screen and processing OCR…")
        self._worker.request_operation.emit("")

    def _handle_keyboard_event(self, event) -> None:
        if event.name.casefold() != self._settings.trigger_key.casefold():
            return
        if event.event_type == "down" and not self._trigger_is_down:
            self._trigger_is_down = True
            self.trigger_received.emit()
        elif event.event_type == "up":
            self._trigger_is_down = False

    @Slot()
    def _on_operation_started(self) -> None:
        provider = (
            "Gemini"
            if self._settings.ai_provider == AI_PROVIDER_GEMINI
            else "OpenAI"
        )
        self.operation_status_changed.emit(
            f"Reading screen and contacting {provider}…"
        )

    @Slot(str)
    def _on_answer_ready(self, answer: str) -> None:
        self.answer_ready.emit(answer)

    @Slot(str)
    def _on_operation_error(self, message: str) -> None:
        self.operation_error.emit(message)

    @Slot(bool)
    def _on_operation_finished(self, succeeded: bool) -> None:
        self._busy = False
        if not self._stopping:
            self.operation_status_changed.emit(
                "Answer received." if succeeded else "Operation failed."
            )
            return
        self._stop_worker_thread()

    def _remove_hotkey(self) -> None:
        if self._hotkey_handle is None:
            return
        try:
            import keyboard

            keyboard.unhook(self._hotkey_handle)
        except (ImportError, KeyError, ValueError):
            self.operation_error.emit(
                "The global hotkey could not be removed cleanly."
            )
        finally:
            self._hotkey_handle = None
            self._trigger_is_down = False

    def _stop_worker_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
        elif self._stopping:
            self._stopping = False
            self._set_state(self._final_state)

    @Slot()
    def _on_thread_finished(self) -> None:
        thread = self._thread
        if thread is not None:
            thread.deleteLater()
        self._thread = None
        self._worker = None
        self._busy = False
        self._stopping = False
        self._set_state(self._final_state)

    def _set_state(self, state: str) -> None:
        self._state = state
        self.state_changed.emit(state)

    def shutdown(self) -> None:
        self.stop()
