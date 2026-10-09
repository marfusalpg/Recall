from PySide6.QtCore import QObject, Signal, Slot

from recall.config.settings import AppSettings
from recall.engine.ai_client import ask_ai
from recall.engine.ocr import get_text_from_screen


class EngineWorker(QObject):
    request_operation = Signal(str)
    operation_started = Signal()
    answer_ready = Signal(str)
    operation_error = Signal(str)
    operation_finished = Signal(bool)

    def __init__(self, settings: AppSettings, api_key: str) -> None:
        super().__init__()
        self._settings = settings
        self._api_key = api_key
        self.request_operation.connect(self.process_operation)

    @Slot(str)
    def process_operation(self, supplied_text: str) -> None:
        self.operation_started.emit()
        success = False
        try:
            text = supplied_text
            if not text:
                text = get_text_from_screen(
                    self._settings.ocr_language,
                    self._settings.tesseract_path,
                )
            if not text.strip():
                raise RuntimeError(
                    "No readable text was found. Make sure the screen shows "
                    "text and the selected OCR languages are installed."
                )

            answer = ask_ai(
                text,
                self._settings.custom_prompt,
                self._api_key,
                self._settings.ai_provider,
            )
            if not answer:
                raise RuntimeError("The AI response did not contain an answer.")
            self.answer_ready.emit(answer)
            success = True
        except Exception as exc:
            message = str(exc).replace(self._api_key, "[redacted]")
            self.operation_error.emit(message or exc.__class__.__name__)
        finally:
            self.operation_finished.emit(success)
