"""Numeric Cm-file sorting and fixed-layout parameter loading."""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np


PARAMETER_ORDER = ("Gravel", "Sand", "Silty", "Clay")


def num_key(name: str) -> int:
    """Return trailing filename digits, sorting non-members such as mat_mean last."""
    match = re.search(r"(\d+)$", os.path.splitext(name)[0])
    return int(match.group(1)) if match else 10**9


def read_mat_matrix(mat_dir: str | Path, n_ensemble: int = 100) -> np.ndarray:
    """Read four Cm values per member and return ``(4, n_ensemble)``.

    The four fixed rows are Gravel, Sand, Silty, and Clay, in that order.
    """
    directory = Path(mat_dir)
    if not directory.is_dir():
        raise NotADirectoryError(f"Cm directory does not exist: {directory}")
    file_names = sorted(
        [path.name for path in directory.iterdir() if path.is_file()], key=num_key
    )
    if n_ensemble > len(file_names):
        raise ValueError(
            "loop time must be an integer and must not exceed the length of "
            "MAT_FILE_LIST."
        )

    matrix_rows: list[list[float]] = []
    for mat_file in file_names[:n_ensemble]:
        print(f"Processing {mat_file}...")
        with (directory / mat_file).open("r") as stream:
            row_values: list[float] = []
            stream.readline()
            for _parameter_name in PARAMETER_ORDER:
                fields = stream.readline().strip().split()
                row_values.append(float(fields[1]))
            print(f"Cm = {row_values}")
        # The source appended the empty list first and then relied on Python's
        # mutable-list reference semantics while filling it. Appending after
        # all four values are read is equivalent but makes that intent explicit.
        matrix_rows.append(row_values)
    matrix = np.asarray(matrix_rows, dtype=float).T
    if matrix.shape != (len(PARAMETER_ORDER), n_ensemble):
        raise ValueError(
            f"Unexpected Cm matrix shape {matrix.shape}; "
            f"expected {(len(PARAMETER_ORDER), n_ensemble)}"
        )
    return matrix
