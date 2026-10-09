import os


API_KEY_ENVIRONMENT_VARIABLE = "OPENAI_API_KEY"
_KEYRING_SERVICE = "Recall"
_PROVIDER_CREDENTIALS = {
    "openai": ("OPENAI_API_KEY", "openai_api_key"),
    "gemini": ("GEMINI_API_KEY", "gemini_api_key"),
}


class CredentialStoreError(RuntimeError):
    """Raised when the operating system credential store is unavailable."""


def get_api_key_environment_variable(provider: str = "openai") -> str:
    try:
        return _PROVIDER_CREDENTIALS[provider][0]
    except KeyError as exc:
        raise ValueError(f"Unsupported AI provider: {provider}") from exc


def get_api_key(provider: str = "openai") -> str:
    """Return the selected provider's environment key or stored credential."""
    try:
        environment_variable, keyring_username = _PROVIDER_CREDENTIALS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported AI provider: {provider}") from exc

    environment_key = os.environ.get(environment_variable, "").strip()
    if environment_key:
        return environment_key

    try:
        import keyring

        return (
            keyring.get_password(_KEYRING_SERVICE, keyring_username) or ""
        ).strip()
    except Exception as exc:
        raise CredentialStoreError(
            "The operating system credential store is unavailable."
        ) from exc


def save_api_key(api_key: str, provider: str = "openai") -> None:
    """Save the selected provider's API key in the operating system keyring."""
    try:
        _, keyring_username = _PROVIDER_CREDENTIALS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported AI provider: {provider}") from exc

    try:
        import keyring

        if api_key.strip():
            keyring.set_password(_KEYRING_SERVICE, keyring_username, api_key.strip())
            return

        try:
            keyring.delete_password(_KEYRING_SERVICE, keyring_username)
        except keyring.errors.PasswordDeleteError:
            pass
    except Exception as exc:
        raise CredentialStoreError(
            "Could not save the API key to the operating system credential store."
        ) from exc
