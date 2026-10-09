import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from recall.config.credentials import get_api_key, save_api_key
from recall.config.settings import (
    AI_PROVIDER_GEMINI,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_PROMPT,
    AppSettings,
    tesseract_path_error,
)
from recall.engine.ai_client import ask_gemini, ask_openai
from recall.engine.controller import EngineController
from recall.ui.overlay import background_and_foreground
from recall.ui.pages.dashboard import DashboardPage
from recall.ui.pages.settings import SettingsPage
from recall.ui.pages.workspace import KeyCaptureLineEdit
from recall.workers.engine_worker import EngineWorker


class EnginePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_tesseract_path_validation_reports_missing_executable(self) -> None:
        self.assertIn("not configured", tesseract_path_error(""))
        self.assertIn(
            "not found",
            tesseract_path_error("C:\\missing\\tesseract.exe"),
        )

    def test_controller_reports_missing_configuration_before_listening(self) -> None:
        controller = EngineController()
        errors = []
        controller.operation_error.connect(errors.append)

        with patch("recall.engine.controller.get_api_key", return_value=""):
            started = controller.start(AppSettings(tesseract_path=""))

        self.assertFalse(started)
        self.assertEqual(controller.state, "error")
        self.assertEqual(errors, [
            "OpenAI API key is missing. Set the OPENAI_API_KEY environment "
            "variable, then restart Recall.\n"
            "Tesseract is not configured. Set its executable path in "
            "Engine settings."
        ])

    def test_openai_request_uses_fixed_model_and_custom_prompt(self) -> None:
        recorded = {}

        class Responses:
            def create(self, *, model: str, input: str):
                recorded["model"] = model
                recorded["input"] = input
                return types.SimpleNamespace(output_text="  C  ")

        class Client:
            def __init__(self, *, api_key: str, timeout: float):
                recorded["api_key"] = api_key
                recorded["timeout"] = timeout
                self.responses = Responses()

        fake_openai = types.ModuleType("openai")
        fake_openai.OpenAI = Client
        with patch.dict(sys.modules, {"openai": fake_openai}):
            answer = ask_openai(
                "Question text", "Return the best answer.", "secret-test-value"
            )

        self.assertEqual(answer, "C")
        self.assertEqual(recorded["model"], DEFAULT_OPENAI_MODEL)
        self.assertEqual(recorded["api_key"], "secret-test-value")
        self.assertEqual(recorded["timeout"], 60.0)
        self.assertEqual(
            recorded["input"], "Return the best answer.\n\nQuestion text"
        )

    def test_gemini_request_uses_fixed_model_and_custom_prompt(self) -> None:
        recorded = {}

        class Models:
            def generate_content(self, *, model: str, contents: str):
                recorded["model"] = model
                recorded["contents"] = contents
                return types.SimpleNamespace(text="  B  ")

        class Client:
            def __init__(self, *, api_key: str):
                recorded["api_key"] = api_key
                self.models = Models()

        fake_genai = types.ModuleType("google.genai")
        fake_genai.Client = Client
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        with patch.dict(
            sys.modules, {"google": fake_google, "google.genai": fake_genai}
        ):
            answer = ask_gemini(
                "Question text", "Return the best answer.", "gemini-test-key"
            )

        self.assertEqual(answer, "B")
        self.assertEqual(recorded["model"], "gemini-2.5-flash")
        self.assertEqual(recorded["api_key"], "gemini-test-key")
        self.assertEqual(
            recorded["contents"], "Return the best answer.\n\nQuestion text"
        )

    def test_default_prompt_is_english(self) -> None:
        self.assertIn("The text contains a test question", DEFAULT_PROMPT)
        self.assertIn("Return ONLY one letter or number.", DEFAULT_PROMPT)

    def test_api_key_is_saved_and_read_through_keyring(self) -> None:
        store = {}
        fake_keyring = types.ModuleType("keyring")
        fake_keyring.get_password = lambda service, username: store.get(username)
        fake_keyring.set_password = lambda service, username, value: store.update(
            {username: value}
        )
        fake_keyring.delete_password = lambda service, username: store.pop(username)

        with (
            patch.dict(sys.modules, {"keyring": fake_keyring}),
            patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "", "GEMINI_API_KEY": ""},
            ),
        ):
            save_api_key("test-key")
            self.assertEqual(get_api_key(), "test-key")
            save_api_key("gemini-test-key", AI_PROVIDER_GEMINI)
            self.assertEqual(get_api_key(AI_PROVIDER_GEMINI), "gemini-test-key")
            self.assertEqual(get_api_key(), "test-key")
            save_api_key("")
            self.assertEqual(get_api_key(), "")
            self.assertEqual(
                get_api_key(AI_PROVIDER_GEMINI), "gemini-test-key"
            )
            save_api_key("", AI_PROVIDER_GEMINI)
            self.assertEqual(get_api_key(AI_PROVIDER_GEMINI), "")

    def test_settings_page_selects_gemini_and_emits_provider(self) -> None:
        with patch("recall.ui.pages.settings.get_api_key", return_value="test-key"):
            page = SettingsPage(DEFAULT_PROMPT)
            selected = []
            page.provider_saved.connect(selected.append)
            page.provider.setCurrentIndex(1)

        self.assertEqual(selected, [AI_PROVIDER_GEMINI])
        self.assertEqual(
            page.api_key.placeholderText(), "Paste your Google Gemini API key"
        )
        page.close()

    def test_dashboard_shows_engine_error_until_cleared(self) -> None:
        dashboard = DashboardPage()

        self.assertTrue(dashboard.error_card.isHidden())
        dashboard.set_error("Gemini API request failed.")
        self.assertFalse(dashboard.error_card.isHidden())
        self.assertEqual(
            dashboard.error_details.text(), "Gemini API request failed."
        )

        dashboard.clear_error()
        self.assertTrue(dashboard.error_card.isHidden())
        self.assertEqual(dashboard.error_details.text(), "")
        dashboard.close()

    def test_trigger_field_waits_for_and_captures_key(self) -> None:
        field = KeyCaptureLineEdit()
        captured = []
        field.key_captured.connect(captured.append)
        field.show()
        QTest.mouseClick(field, Qt.MouseButton.LeftButton)
        self.assertEqual(field.text(), "Waiting for input")
        QTest.keyClick(field, Qt.Key.Key_Shift)
        self.assertEqual(captured, ["left shift"])
        self.assertEqual(field.text(), "Left Shift")
        field.close()

    def test_trigger_field_distinguishes_left_and_right_shift(self) -> None:
        field = KeyCaptureLineEdit()
        captured = []
        field.key_captured.connect(captured.append)

        for scan_code, expected in ((42, "left shift"), (54, "right shift")):
            field._waiting_for_key = True
            event = Mock()
            event.key.return_value = Qt.Key.Key_Shift.value
            event.nativeScanCode.return_value = scan_code
            field.keyPressEvent(event)
            self.assertEqual(captured[-1], expected)
            self.assertEqual(field.text(), expected.title())

    def test_global_listener_triggers_once_on_selected_shift_keydown(self) -> None:
        controller = EngineController()
        controller._settings = AppSettings(trigger_key="right shift")
        received = []
        controller.trigger_received.connect(lambda: received.append(True))

        for name, event_type in (
            ("left shift", "down"),
            ("right shift", "down"),
            ("right shift", "down"),
            ("right shift", "up"),
            ("right shift", "down"),
        ):
            controller._handle_keyboard_event(
                types.SimpleNamespace(name=name, event_type=event_type)
            )

        self.assertEqual(received, [True, True])

    def test_overlay_selects_contrasting_text_for_sampled_background(self) -> None:
        self.assertEqual(
            background_and_foreground(5, 5, 5), ("#050505", "#ffffff")
        )
        self.assertEqual(
            background_and_foreground(250, 250, 250), ("#fafafa", "#000000")
        )

    def test_worker_runs_real_pipeline_functions_and_emits_answer(self) -> None:
        settings = AppSettings(
            ocr_language="ces+eng",
            tesseract_path="tesseract.exe",
        )
        worker = EngineWorker(settings, "worker-test-key")
        answers = []
        errors = []
        completed = []
        worker.answer_ready.connect(answers.append)
        worker.operation_error.connect(errors.append)
        worker.operation_finished.connect(completed.append)

        with (
            patch(
                "recall.workers.engine_worker.get_text_from_screen",
                return_value="Recognized screen text",
            ) as capture,
            patch(
                "recall.workers.engine_worker.ask_ai",
                return_value="A",
            ) as request,
        ):
            worker.process_operation("")

        capture.assert_called_once_with("ces+eng", "tesseract.exe")
        request.assert_called_once_with(
            "Recognized screen text", DEFAULT_PROMPT, "worker-test-key", "openai"
        )
        self.assertEqual(answers, ["A"])
        self.assertEqual(errors, [])
        self.assertEqual(completed, [True])

    def test_worker_routes_request_to_selected_gemini_provider(self) -> None:
        settings = AppSettings(
            ai_provider=AI_PROVIDER_GEMINI,
            ocr_language="eng",
            tesseract_path="tesseract.exe",
        )
        worker = EngineWorker(settings, "worker-gemini-key")

        with (
            patch(
                "recall.workers.engine_worker.get_text_from_screen",
                return_value="Recognized screen text",
            ),
            patch(
                "recall.workers.engine_worker.ask_ai",
                return_value="B",
            ) as request,
        ):
            worker.process_operation("")

        request.assert_called_once_with(
            "Recognized screen text",
            DEFAULT_PROMPT,
            "worker-gemini-key",
            AI_PROVIDER_GEMINI,
        )

    def test_worker_redacts_api_key_from_operation_errors(self) -> None:
        worker = EngineWorker(AppSettings(), "worker-test-key")
        errors = []
        completed = []
        worker.operation_error.connect(errors.append)
        worker.operation_finished.connect(completed.append)

        with patch(
            "recall.workers.engine_worker.get_text_from_screen",
            side_effect=RuntimeError("bad token worker-test-key"),
        ):
            worker.process_operation("")

        self.assertEqual(errors, ["bad token [redacted]"])
        self.assertEqual(completed, [False])


if __name__ == "__main__":
    unittest.main()
