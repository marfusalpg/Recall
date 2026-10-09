
from google import genai
from recall.config.credentials import get_api_key

api_key = get_api_key("gemini")

if not api_key:
    raise SystemExit(
        "Recall nema dostupny Gemini API klic. "
        "Zkontroluj nastaveni aplikace."
    )

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Reply with exactly: API OK",
    )

    print("GEMINI GENEROVANI FUNGUJE")
    print("Odpoved:", response.text)

except Exception as exc:
    print("GEMINI GENEROVANI SELHALO")
    print("Typ chyby:", type(exc).__name__)
    print("Detail:", str(exc))