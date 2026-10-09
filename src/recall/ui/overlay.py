from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from recall.config.settings import AppSettings


def background_and_foreground(red: int, green: int, blue: int) -> tuple[str, str]:
    background = f"#{red:02x}{green:02x}{blue:02x}"
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    foreground = "#ffffff" if luminance < 128 else "#000000"
    return background, foreground


class AnswerOverlay(QWidget):
    """Reusable, topmost answer window owned by the main Qt application."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("answerOverlay")
        self._label = QLabel(self)
        self._label.setObjectName("answerOverlayText")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._background_timer = QTimer(self)
        self._background_timer.setInterval(200)
        self._background_timer.timeout.connect(self._update_background)
        self._background = "#111116"
        self._foreground = "#ffffff"

    def show_answer(self, answer: str, settings: AppSettings) -> None:
        self._label.setText(answer)
        self._label.setGeometry(self.rect())
        self.setFixedSize(settings.overlay_size, settings.overlay_size)
        self.setWindowOpacity(settings.overlay_opacity)
        self._label.setStyleSheet(
            f"font-size: {max(12, int(settings.overlay_size * 0.32))}px;"
        )

        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(
                area.right() - self.width() - 18,
                area.bottom() - self.height() - 24,
            )

        self.show()
        self.raise_()
        self._update_background()
        self._background_timer.start()
        self._timer.start(settings.overlay_duration_ms)

    def _update_background(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None or not self.isVisible():
            return

        sample_x = max(0, self.x() - 2)
        sample_y = self.y() + min(2, self.height() - 1)
        pixel = screen.grabWindow(0, sample_x, sample_y, 1, 1).toImage()
        color = pixel.pixelColor(0, 0)
        self._background, self._foreground = background_and_foreground(
            color.red(), color.green(), color.blue()
        )
        self.setStyleSheet(
            "#answerOverlay {"
            f"background-color: {self._background};"
            "border: 1px solid #8b5cf6;"
            "}"
            "#answerOverlayText {"
            f"color: {self._foreground};"
            "font-weight: 700;"
            "}"
        )

    def resizeEvent(self, event) -> None:
        self._label.setGeometry(self.rect())
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._background_timer.stop()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:
        self._background_timer.stop()
        super().hideEvent(event)
