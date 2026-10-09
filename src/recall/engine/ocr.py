from recall.engine.screenshot import capture_screen


def get_text_from_screen(language: str, tesseract_path: str) -> str:
    """Capture the screen and extract text with the configured Tesseract engine."""
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "OCR support is unavailable. Install the project requirements."
        ) from exc

    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    screenshot = capture_screen()
    return pytesseract.image_to_string(screenshot, lang=language)
