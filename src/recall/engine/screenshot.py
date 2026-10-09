def capture_screen():
    """Capture the current desktop using the original pyautogui pipeline."""
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError(
            "Screenshot support is unavailable. Install the project requirements."
        ) from exc

    return pyautogui.screenshot()
