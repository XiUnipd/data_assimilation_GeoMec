"""Terminal/file tee for preserving the workflow's existing print output."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
import traceback
from typing import Iterator, TextIO


class TeeTextIO:
    """Write and flush text to multiple streams."""

    def __init__(self, *streams: TextIO) -> None:
        self._streams = streams

    def write(self, text: str) -> int:
        for stream in self._streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(stream.isatty() for stream in self._streams)

    @property
    def encoding(self) -> str | None:
        return self._streams[0].encoding


@contextmanager
def capture_console_output(
    log_file: str | Path,
    *,
    enabled: bool = True,
    mode: str = "w",
) -> Iterator[None]:
    """Mirror stdout/stderr to ``log_file`` for one complete program run."""
    if not enabled:
        yield
        return
    if mode not in {"w", "a"}:
        raise ValueError(f"Unsupported run-log mode: {mode!r}")

    output_path = Path(log_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    separator = "=" * 80
    failed = False

    with output_path.open(mode, encoding="utf-8", buffering=1) as log_stream:
        sys.stdout = TeeTextIO(original_stdout, log_stream)
        sys.stderr = TeeTextIO(original_stderr, log_stream)
        try:
            print(separator)
            print(f"ES-MDA run started: {datetime.now().isoformat(timespec='seconds')}")
            print(f"Log file: {output_path.resolve()}")
            print(separator)
            yield
        except BaseException:
            failed = True
            traceback.print_exc()
            raise
        finally:
            print(separator)
            status = "FAILED" if failed else "COMPLETED"
            print(
                f"ES-MDA run {status}: "
                f"{datetime.now().isoformat(timespec='seconds')}"
            )
            print(separator)
            sys.stdout = original_stdout
            sys.stderr = original_stderr
