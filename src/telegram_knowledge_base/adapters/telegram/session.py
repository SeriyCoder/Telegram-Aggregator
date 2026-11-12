import sys
from dataclasses import dataclass
from typing import Protocol


class SecretBackend(Protocol):
    secure: bool

    def set_secret(self, value: str) -> None: ...

    def get_secret(self) -> str | None: ...


class SessionStorageError(Exception):
    pass


class WindowsCredentialBackend:
    _SERVICE = "telegram-knowledge-base"
    _USERNAME = "telegram-session"

    def __init__(self) -> None:
        self.secure = False
        self._keyring = None
        if sys.platform != "win32":
            return
        try:
            import keyring
            from keyring.backends.Windows import WinVaultKeyring

            backend = keyring.get_keyring()
        except Exception:
            return
        if isinstance(backend, WinVaultKeyring):
            self.secure = True
            self._keyring = keyring

    def set_secret(self, value: str) -> None:
        if not self.secure or self._keyring is None:
            raise SessionStorageError("Windows Credential Manager is unavailable.")
        self._keyring.set_password(self._SERVICE, self._USERNAME, value)

    def get_secret(self) -> str | None:
        if not self.secure or self._keyring is None:
            raise SessionStorageError("Windows Credential Manager is unavailable.")
        value = self._keyring.get_password(self._SERVICE, self._USERNAME)
        if value is not None and not isinstance(value, str):
            raise SessionStorageError(
                "Windows Credential Manager returned invalid data."
            )
        return value


@dataclass
class SessionStore:
    backend: SecretBackend

    def save(self, value: str) -> None:
        if not self.backend.secure:
            raise SessionStorageError("A secure session store is unavailable.")
        if not value:
            raise ValueError("Session material must not be empty.")
        try:
            self.backend.set_secret(value)
        except Exception:
            raise SessionStorageError("Telegram session could not be stored.") from None

    def load(self) -> str | None:
        if not self.backend.secure:
            raise SessionStorageError("A secure session store is unavailable.")
        try:
            return self.backend.get_secret()
        except Exception:
            raise SessionStorageError("Telegram session could not be read.") from None
