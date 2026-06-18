"""Observation-aligned standard-deviation to variance construction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .io_utils import load_table_auto
from .observation import get_years_with_records_per_point


def build_diagonal_covariance(
    covariance_file: str | Path,
    observation_df: pd.DataFrame,
    sim_years_ref: list[int],
    observations: np.ndarray,
    year_min: int = config.YEAR_MIN,
    year_max: int = config.YEAR_MAX,
    x_col: str = "X_mean",
    y_col: str = "Y_mean",
) -> np.ndarray:
    """Build variances in exactly the observation-vector row order."""
    covariance_df = load_table_auto(covariance_file)
    covariance_coords, covariance_years, covariance_values, _ = (
        get_years_with_records_per_point(
            covariance_df,
            year_min=year_min,
            year_max=year_max,
            x_col=x_col,
            y_col=y_col,
        )
    )
    observation_coords, observation_years, _, _ = get_years_with_records_per_point(
        observation_df,
        year_min=year_min,
        year_max=year_max,
        x_col=x_col,
        y_col=y_col,
    )
    if covariance_coords.shape != observation_coords.shape:
        raise ValueError(
            f"Covariance file row count {covariance_coords.shape[0]} != "
            f"observation row count {observation_coords.shape[0]}"
        )
    if not np.allclose(covariance_coords, observation_coords, equal_nan=True):
        raise ValueError(
            "Coordinates in covariance file do not match observation file. "
            "Please make sure the row order and X/Y columns are identical."
        )

    simulation_years = {int(year) for year in sim_years_ref}
    ordered_standard_deviations: list[float] = []
    for point_index, (obs_years, cov_years, cov_values) in enumerate(
        zip(observation_years, covariance_years, covariance_values)
    ):
        covariance_map = {
            int(year): float(value)
            for year, value in zip(cov_years, cov_values)
            if not np.isnan(value)
        }
        for year in obs_years:
            year = int(year)
            if year not in simulation_years:
                continue
            if year not in covariance_map:
                raise ValueError(
                    f"Missing covariance value at point index {point_index} "
                    f"for year {year}."
                )
            ordered_standard_deviations.append(covariance_map[year])

    std_vec = np.asarray(ordered_standard_deviations, dtype=float)
    covariance_vec = std_vec**2
    if covariance_vec.size != int(np.asarray(observations).size):
        raise ValueError(
            f"Covariance length {covariance_vec.size} != number of observations "
            f"{int(np.asarray(observations).size)}"
        )
    if np.any(~np.isfinite(covariance_vec)):
        raise ValueError("Covariance vector contains NaN or inf.")
    if np.any(covariance_vec <= 0):
        raise ValueError("Covariance vector must be strictly positive.")
    print(f"Loaded covariance vector from {covariance_file}")
    print(f"covariance_vec.shape = {covariance_vec.shape}")
    print(f"First 10 covariance values: {covariance_vec[:10]}")
    return covariance_vec
