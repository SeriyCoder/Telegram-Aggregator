import asyncio
import errno
import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import BinaryIO


class AccountInUse(Exception):
    pass


@dataclass
class AccountLock:
    path: Path
    _file: BinaryIO | None = None

    def __enter__(self) -> None:
        self._acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._release()

    async def __aenter__(self) -> None:
        await asyncio.to_thread(self._acquire)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await asyncio.to_thread(self._release)

    def _acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            handle.seek(0)
            if handle.read(1) == b"":
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EPERM}:
                raise AccountInUse("Telegram account is already in use.") from None
            raise
        self._file = handle

    def _release(self) -> None:
        if self._file is None:
            return
        handle = self._file
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self._file = None
