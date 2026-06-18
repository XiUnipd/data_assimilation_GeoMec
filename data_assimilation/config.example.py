"""Public configuration template for the ES-MDA workflow.

Copy this file to ``config.py`` and customize local paths, or override the
settings with the documented environment variables. Do not commit a local
``config.py`` containing private machine paths.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path_from_env(name: str, default: str | Path) -> Path:
    """Return an expanded ``Path`` from an environment override or default."""
    return Path(os.getenv(name, str(default))).expanduser()


# Example layout. Change DATA_DIR or override individual paths via environment.
DATA_DIR = _path_from_env("ESMDA_DATA_DIR", PROJECT_ROOT / "data")
INPUT_DIR = _path_from_env("ESMDA_INPUT_DIR", DATA_DIR / "mesh")
MESH_GRID_FILE = _path_from_env(
    "ESMDA_MESH_GRID_FILE", INPUT_DIR / "mesh.grid_zones"
)
POT_DIR = _path_from_env("ESMDA_POT_DIR", DATA_DIR / "solbox")
NODE_DIR = _path_from_env("ESMDA_NODE_FILE", DATA_DIR / "node_to_be_DA.xlsx")
OBS_FILE = _path_from_env("ESMDA_OBS_FILE", DATA_DIR / "observations.xlsx")
COVARIANCE_FILE = _path_from_env(
    "ESMDA_COVARIANCE_FILE", DATA_DIR / "standard_deviations.xlsx"
)
MAT_DIR = _path_from_env("ESMDA_MAT_DIR", DATA_DIR / "cm_prior")

RESULTS_DIR = _path_from_env("ESMDA_RESULTS_DIR", PROJECT_ROOT / "results")
FIGURES_DIR = _path_from_env("ESMDA_FIGURES_DIR", RESULTS_DIR / "Figures")

N_ENSEMBLE = int(os.getenv("ESMDA_N_ENSEMBLE", "100"))
N_ASSIM = int(os.getenv("ESMDA_ROUNDS", "3"))
YEAR_MIN = int(os.getenv("ESMDA_YEAR_MIN", "1900"))
YEAR_MAX = int(os.getenv("ESMDA_YEAR_MAX", "2099"))

X_COLUMN = os.getenv("ESMDA_X_COLUMN", "X_mean")
Y_COLUMN = os.getenv("ESMDA_Y_COLUMN", "Y_mean")
SEED = 1688
INVERSION = "subspace"
PARAM_NAMES = ("Gravel", "Sand", "Silty", "Clay")


# ==============================================================================
# +--------------------------------------------------------------------------+
# | DEBUG / COMPARISON MODE                                                  |
# |                                                                          |
# | DEFAULT: OFF                                                             |
# | These switches only control consistency-test checkpoint/debug storage.   |
# | They do not change the ES-MDA algorithm or normal production outputs.    |
# +--------------------------------------------------------------------------+
# ==============================================================================
COMPARISON_MODE = os.getenv("ESMDA_COMPARISON_MODE", "0") == "1"

_comparison_output_dir = os.getenv("ESMDA_COMPARISON_OUTPUT_DIR")
COMPARISON_OUTPUT_DIR = (
    Path(_comparison_output_dir).expanduser() if _comparison_output_dir else None
)

COMPARISON_MEMMAP = os.getenv("ESMDA_COMPARISON_MEMMAP", "0") == "1"
