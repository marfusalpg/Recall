
import requests
from recall.config.credentials import get_api_key

key = get_api_key("gemini")

if not key:
    raise SystemExit("Recall nema dostupny Gemini API klic.")

try:
    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": key},
        timeout=20,
    )

    print("HTTP status:", response.status_code)
    print("Response:", response.text[:1500])

except requests.RequestException as exc:
    print("Sitova chyba:", type(exc).__name__)
    print(str(exc))