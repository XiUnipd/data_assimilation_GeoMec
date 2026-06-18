"""Observation year detection and ordered vector/model assembly."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config


def map_year_columns(
    df: pd.DataFrame, year_min: int = 1900, year_max: int = 2100
) -> dict[int, object]:
    """Map recognized four-digit years to their first matching column."""
    mapping: dict[int, object] = {}
    for column in df.columns:
        normalized = str(column).strip().replace("\u00a0", " ")
        match = re.search(r"(19|20)\d{2}", normalized)
        if match:
            year = int(match.group(0))
            if year_min <= year <= year_max and year not in mapping:
                mapping[year] = column
    return mapping


def extract_matrix_from_obs_df(
    df: pd.DataFrame,
    years: list[int] | None = None,
    x_col: str = "X_mean",
    y_col: str = "Y_mean",
    year_min: int = config.YEAR_MIN,
    year_max: int = config.YEAR_MAX,
) -> tuple[np.ndarray, np.ndarray, list[int], list[object]]:
    """Extract the dense observation-year matrix and point coordinates."""
    year_map = map_year_columns(df, year_min=year_min, year_max=year_max)
    if years is None:
        years = sorted(year_map)
    else:
        years = [int(year) for year in years if int(year) in year_map]
    if not years:
        raise ValueError(
            "没有在表头里识别到年份列。请检查表头是否类似 '2012年12月水位'；"
            f"\n当前表头示例：{list(df.columns)[:8]}"
        )
    year_cols = [year_map[year] for year in years]
    if x_col not in df.columns or y_col not in df.columns:
        raise KeyError(
            f"坐标列不存在：x_col='{x_col}' y_col='{y_col}'；"
            f"现有列：{list(df.columns)[:8]} ..."
        )
    coordinates = np.column_stack(
        [
            pd.to_numeric(df[x_col], errors="coerce"),
            pd.to_numeric(df[y_col], errors="coerce"),
        ]
    )
    matrix = df[year_cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    print(f"OBS matrix is:\n{matrix}")
    return matrix, coordinates, years, year_cols


def get_years_with_records_per_point(
    df: pd.DataFrame,
    year_min: int = config.YEAR_MIN,
    year_max: int = config.YEAR_MAX,
    x_col: str = "X",
    y_col: str = "Y",
) -> tuple[np.ndarray, list[list[int]], list[np.ndarray], list[object]]:
    """Return ascending non-NaN observation years and values for each row."""
    year_map = map_year_columns(df, year_min=year_min, year_max=year_max)
    if not year_map:
        raise ValueError("未在 observation CSV 中识别到年份列")
    years_sorted = sorted(year_map)
    year_cols = [year_map[year] for year in years_sorted]
    if x_col not in df.columns or y_col not in df.columns:
        raise KeyError(
            f"坐标列不存在：x_col='{x_col}' y_col='{y_col}'；"
            f"现有列：{list(df.columns)[:8]} ..."
        )
    coords = np.column_stack(
        [
            pd.to_numeric(df[x_col], errors="coerce"),
            pd.to_numeric(df[y_col], errors="coerce"),
        ]
    )
    matrix = df[year_cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    years_per_point: list[list[int]] = []
    values_per_point: list[np.ndarray] = []
    for row in matrix:
        point_years: list[int] = []
        point_values: list[float] = []
        for column_index, year in enumerate(years_sorted):
            value = row[column_index]
            if not np.isnan(value):
                point_years.append(int(year))
                point_values.append(float(value))
        years_per_point.append(point_years)
        values_per_point.append(np.asarray(point_values, dtype=float))
    return coords, years_per_point, values_per_point, year_cols


def assemble_obs_and_Y_model(
    multi_sim_matrix: np.ndarray,
    tags_1based: list[int],
    sim_years_ref: list[int],
    years_pp: list[list[int]],
    values_pp: list[np.ndarray],
) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]], np.ndarray]:
    """Build observations and ``Y_model`` in point-major/year-major order."""
    ensemble_count = multi_sim_matrix.shape[0]
    sim_year_to_idx = {int(year): index for index, year in enumerate(sim_years_ref)}
    observations: list[float] = []
    plan: list[tuple[int, int]] = []
    for point_index, (point_years, point_values) in enumerate(
        zip(years_pp, values_pp)
    ):
        for year, value in zip(point_years, point_values):
            year_index = sim_year_to_idx.get(int(year))
            if year_index is None:
                continue
            observations.append(float(value))
            plan.append((point_index, year_index))
    observations_vec = np.asarray(observations, dtype=float)
    Y_model = np.empty((len(observations), ensemble_count), dtype=float)

    # tags_1based are node tags; tags_idx are zero-based NumPy row indices.
    tags_idx = np.asarray(tags_1based, dtype=int) - 1
    for row_index, (point_index, year_index) in enumerate(plan):
        node_index = tags_idx[point_index]
        Y_model[row_index, :] = multi_sim_matrix[:, node_index, year_index]
    return observations_vec, Y_model, plan, tags_idx
