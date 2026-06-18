"""Opt-in persistence helpers for original/refactored consistency checks.

Normal runs are unchanged. Arrays are written only when
``ESMDA_COMPARISON_MODE=1`` and ``ESMDA_COMPARISON_OUTPUT_DIR`` is set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from . import config


def comparison_enabled() -> bool:
    """Return whether comparison output is explicitly enabled."""
    return config.COMPARISON_MODE


def comparison_memmap_enabled() -> bool:
    """Return whether debug-only disk-backed simulation storage is enabled."""
    return config.COMPARISON_MODE and config.COMPARISON_MEMMAP


def comparison_output_dir() -> Path | None:
    """Return and create the configured comparison directory when enabled."""
    if not comparison_enabled():
        return None
    output_dir = config.COMPARISON_OUTPUT_DIR
    if output_dir is None:
        raise ValueError(
            "ESMDA_COMPARISON_OUTPUT_DIR is required when "
            "ESMDA_COMPARISON_MODE=1"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_comparison_array(name: str, array: Any) -> Path | None:
    """Save one numeric comparison checkpoint as ``<name>.npy``."""
    output_dir = comparison_output_dir()
    if output_dir is None:
        return None
    output_path = output_dir / f"{name}.npy"
    np.save(output_path, np.asarray(array))
    return output_path


def save_comparison_json(name: str, value: Any) -> Path | None:
    """Save JSON metadata used to interpret a comparison run."""
    output_dir = comparison_output_dir()
    if output_dir is None:
        return None
    output_path = output_dir / f"{name}.json"
    with output_path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
    return output_path
