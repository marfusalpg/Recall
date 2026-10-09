# Recall

Recall is a compact PySide6 desktop utility that listens for a configurable
global hotkey, captures the screen, extracts text with Tesseract OCR, sends
that text to the OpenAI Responses API or Google Gemini API, and displays the
returned answer in a small reusable overlay.

## Requirements

- Windows (the provided launcher is PowerShell-based)
- Python 3.10 or newer
- Tesseract OCR installed separately, including the language data you use
  (Czech and English by default)
- An OpenAI or Google Gemini API key

## Setup

From the repository directory, install the Python dependencies into the
existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install Tesseract OCR and note the full path to `tesseract.exe`. The Engine page
can browse to this executable. The OCR language data (for example `ces` and
`eng`) must also be available to that Tesseract installation.

Choose OpenAI or Google Gemini on the **Settings** page, enter that provider's
key, and save it to the Windows credential vault. `OPENAI_API_KEY` and
`GEMINI_API_KEY` respectively take precedence over saved keys for their
provider. Recall does not write credentials to its configuration or repository.

OCR language, Tesseract path, trigger key, custom prompt, and overlay settings
are saved locally using Qt's platform settings store. The OpenAI model is fixed
to `gpt-5.2`; the Gemini model is fixed to `gemini-2.5-flash`.

## Launch

Preferred launcher:

```powershell
.\run.ps1
```

Or launch directly from PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path $PWD "src")
.\.venv\Scripts\python.exe -m recall.main
```

Open **Engine** to configure Tesseract, OCR language, trigger key, and overlay
appearance. Click the trigger field, press the key you want (left Shift by
default; left and right Shift are distinguished), then save settings. In
**Settings**, select your AI provider, save its API key and optionally edit the
English default Custom Prompt. The recognized screen text is appended after the
prompt. Start the engine from **Overview**. The capture/OCR/API work runs off
the UI thread; a
trigger pressed while an operation is already running is ignored and reported
in the status panel. Stop the engine to remove its keyboard listener. The
answer overlay samples the screen beside its position every 200 ms and
switches between light and dark text for contrast.

## Troubleshooting

- **Missing API key:** select the provider on the Settings page and enter its
  key, or define `OPENAI_API_KEY` / `GEMINI_API_KEY` before launching Recall.
- **Tesseract path required:** select the installed `tesseract.exe` on the
  Engine page and save.
- **OCR language error:** install the matching Tesseract language data and
  select the language(s) that are installed.
- **Hotkey registration error:** choose a valid key or key combination that is
  not blocked by the operating system or another application.
- The Overview and Engine pages display the latest operation status and
  readable error details.

## Tests

Run the engine unit tests with:

```powershell
$env:PYTHONPATH = (Join-Path $PWD "src")
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
