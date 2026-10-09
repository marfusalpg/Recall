from time import sleep

from recall.config.settings import (
    AI_PROVIDER_GEMINI,
    AI_PROVIDER_OPENAI,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
)

_GEMINI_MAX_ATTEMPTS = 3


def ask_openai(text: str, prompt: str, api_key: str) -> str:
    """Send OCR text to the OpenAI Responses API using the configured prompt."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI support is unavailable. Install the project requirements."
        ) from exc

    client = OpenAI(api_key=api_key, timeout=60.0)
    response = client.responses.create(
        model=DEFAULT_OPENAI_MODEL,
        input=f"{prompt.rstrip()}\n\n{text}",
    )
    return response.output_text.strip()


def ask_gemini(text: str, prompt: str, api_key: str) -> str:
    """Send OCR text to the Gemini API using the configured prompt."""
    try:
        from google import genai
        from google.genai.errors import ServerError
    except ImportError as exc:
        raise RuntimeError(
            "Gemini support is unavailable. Install the project requirements."
        ) from exc

    client = genai.Client(api_key=api_key)
    for attempt in range(_GEMINI_MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=DEFAULT_GEMINI_MODEL,
                contents=f"{prompt.rstrip()}\n\n{text}",
            )
            return (response.text or "").strip()
        except ServerError as exc:
            if exc.code != 503 or attempt == _GEMINI_MAX_ATTEMPTS - 1:
                raise
            sleep(2**attempt)

    raise RuntimeError("Gemini request ended without a response.")


def ask_ai(text: str, prompt: str, api_key: str, provider: str) -> str:
    if provider == AI_PROVIDER_OPENAI:
        return ask_openai(text, prompt, api_key)
    if provider == AI_PROVIDER_GEMINI:
        return ask_gemini(text, prompt, api_key)
    raise ValueError(f"Unsupported AI provider: {provider}")
