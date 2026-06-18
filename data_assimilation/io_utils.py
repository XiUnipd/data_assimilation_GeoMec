"""Shared file validation and CSV/Excel table loading."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def require_file(path: str | Path) -> Path:
    """Return ``path`` as a ``Path`` or raise a clear missing-file error."""
    resolved = Path(path).expanduser()
    if not resolved.is_file():
        raise FileNotFoundError(f"File does not exist: {resolved}")
    return resolved


def require_directory(path: str | Path) -> Path:
    """Return ``path`` as a ``Path`` or raise a clear directory error."""
    resolved = Path(path).expanduser()
    if not resolved.is_dir():
        raise NotADirectoryError(f"Directory does not exist: {resolved}")
    return resolved


def load_table_auto(path: str | Path) -> pd.DataFrame:
    """Load a CSV, XLS, or XLSX table according to its file extension."""
    table_path = require_file(path)
    extension = table_path.suffix.lower()
    if extension == ".csv":
        return pd.read_csv(table_path)
    if extension in {".xls", ".xlsx"}:
        return pd.read_excel(table_path)
    raise ValueError(
        f"Unsupported file format '{extension}' for {table_path}. "
        "Supported formats are .csv, .xls, and .xlsx."
    )

