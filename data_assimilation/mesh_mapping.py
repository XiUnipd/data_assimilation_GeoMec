"""Mesh loading and observation-coordinate to node-tag matching."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .io_utils import require_file


def load_mesh_grid(mesh_grid_file: str | Path) -> np.ndarray:
    """Load a GEOST mesh using the original header-derived skip-row count."""
    mesh_path = require_file(mesh_grid_file)
    with mesh_path.open("r") as stream:
        number = stream.readline().strip().split()
    if len(number) < 2:
        raise ValueError(f"Invalid mesh header in {mesh_path}: {number}")
    mesh_row_to_skip = int(number[1]) + 2
    return np.loadtxt(mesh_path, skiprows=mesh_row_to_skip)


def _load_tags(node_file: str | Path) -> pd.DataFrame:
    """Load the workbook containing 1-based mesh node tags."""
    return pd.read_excel(require_file(node_file))


def _load_tags_xyz_helper(
    node_df: pd.DataFrame, mesh_grid: np.ndarray
) -> np.ndarray:
    """Return ``[tag, X, Y, Z]`` rows for requested 1-based node tags."""
    mesh_dict = {
        mesh_grid[i, 0]: [mesh_grid[i, 1], mesh_grid[i, 2], mesh_grid[i, 3]]
        for i in range(mesh_grid.shape[0])
    }
    node_tags = node_df["Node"].to_numpy(dtype=int)
    coords_matrix = []
    for tag in node_tags:
        xyz = mesh_dict[tag]
        coords_matrix.append([tag, *xyz])
    coords_matrix = np.asarray(coords_matrix, dtype=float)
    print(f"The shape of coords matrix is: {coords_matrix.shape}")
    print(f"First 5 rows of coords_matrix: \n{coords_matrix[:5]}")
    return coords_matrix


def find_nearest_points(
    coordinates: np.ndarray, coords_matrix: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    """Match XY coordinates to nearest candidate nodes using ``cKDTree``.

    ``tags_1based`` in the return value are mesh node tags. They are not NumPy
    indices; observation assembly converts them to ``tags_idx`` by subtracting
    one.
    """
    layer = coords_matrix
    tree = cKDTree(layer[:, 1:3])
    dist, idx = tree.query(coordinates, k=1)
    picked = layer[idx, :]
    tags_1based = picked[:, 0].astype(int).tolist()
    return picked, dist, idx, tags_1based

