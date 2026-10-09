import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from recall.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Recall")
    app.setOrganizationName("Recall")

    stylesheet_path = (
        Path(__file__).parent / "resources" / "styles.qss"
    )
    app.setStyleSheet(
        stylesheet_path.read_text(encoding="utf-8")
    )

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())