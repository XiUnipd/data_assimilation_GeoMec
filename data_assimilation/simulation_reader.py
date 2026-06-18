"""Solbox CSV/POT readers and simulation-ensemble assembly."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .comparison import comparison_memmap_enabled, comparison_output_dir


_NUM_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
_FIND_ALL_NUMBERS = re.compile(_NUM_PATTERN)


def pair_tag_with_pot_file(
    pot_file: str | Path, n_nodes: int
) -> tuple[np.ndarray, list[int]]:
    """Parse legacy TIME blocks from a POT file without changing semantics."""
    pot_path = Path(pot_file)
    if not pot_path.is_file():
        raise FileNotFoundError(f"找不到 pot 文件：{pot_path}")

    years_pot: list[int] = []
    columns: list[np.ndarray] = []
    collecting = False
    block_lines: list[str] = []

    with pot_path.open("r", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            stripped = line.strip()
            if not stripped:
                continue
            if "time" in stripped.lower():
                if collecting and block_lines:
                    values = np.fromstring(" ".join(block_lines), sep=" ")
                    if values.size >= n_nodes:
                        columns.append(values[:n_nodes])
                    block_lines = []
                numbers = _FIND_ALL_NUMBERS.findall(stripped)
                if numbers:
                    years_pot.append(int(float(numbers[-1])))
                    collecting = True
                    continue
                collecting = False
                block_lines = []
                continue
            if collecting:
                block_lines.append(stripped)

    if collecting and block_lines:
        values = np.fromstring(" ".join(block_lines), sep=" ")
        if values.size >= n_nodes:
            columns.append(values[:n_nodes])

    if columns:
        values = np.column_stack(columns)
        if values.shape[1] <= 8:
            raise ValueError(
                f"{pot_path.name} 的 TIME 个数不足以裁剪到 [8, -2)"
            )
        return values, years_pot

    text = pot_path.read_text(encoding="utf-8", errors="ignore")
    all_numbers = np.fromstring(text, sep=" ")
    if all_numbers.size % n_nodes == 0 and all_numbers.size > 0:
        values = all_numbers.reshape(-1, n_nodes).T
        if values.shape[1] <= 8:
            raise ValueError(
                f"{pot_path.name} 无 TIME，且 T 太短，无法裁剪到 [8, -2)"
            )
        return values, years_pot
    raise ValueError(
        f"在 {pot_path.name} 中没有解析到 TIME，且无法按 n_nodes={n_nodes} 整分。"
    )


def _normalized_node_ids(values: pd.Series, csv_file: Path) -> np.ndarray:
    """Validate and return integer node IDs from a solbox table."""
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.isna().any():
        raise ValueError(f"CSV contains missing or non-numeric node IDs: {csv_file}")
    node_ids = numeric.to_numpy(dtype=int)
    if np.unique(node_ids).size != node_ids.size:
        raise ValueError(f"CSV contains duplicate node IDs: {csv_file}")
    return node_ids


def read_pot_csv_matrix(
    csv_file: str | Path,
    n_nodes: int,
    mesh_grid: np.ndarray,
    expected_node_ids: Iterable[int] | None = None,
) -> tuple[np.ndarray, list[int]]:
    """Read cumulative solbox values and return mesh-aligned annual differences.

    Current inputs label columns with calendar years such as ``1991.0``.  The
    historical code calls them time-days but only normalizes each numeric label
    with ``int``; no division by 365 or calendar offset is introduced here.
    """
    csv_path = Path(csv_file)
    if not csv_path.is_file():
        raise FileNotFoundError(f"找不到 CSV: {csv_path}")
    if mesh_grid.shape[0] != n_nodes:
        raise ValueError(
            f"n_nodes={n_nodes} does not match mesh_grid rows={mesh_grid.shape[0]}"
        )
    dataframe = pd.read_csv(csv_path)
    if dataframe.empty:
        raise ValueError(f"空 CSV: {csv_path}")

    node_column = dataframe.columns[0]
    value_columns = [column for column in dataframe.columns if column != node_column]
    if not value_columns:
        raise ValueError(f"未发现时间列: {csv_path}")

    times: list[float] = []
    for column in value_columns:
        if isinstance(column, (int, float, np.integer, np.floating)):
            time_value = float(column)
        else:
            match = re.search(
                r"[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?",
                str(column).strip(),
            )
            if not match:
                raise ValueError(f"无法从列名解析时间: {column}")
            time_value = float(match.group(0))
        times.append(time_value)
    years = [int(value) for value in times]

    mesh_nodes = np.asarray(mesh_grid[:, 0], dtype=int)
    if np.unique(mesh_nodes).size != mesh_nodes.size:
        raise ValueError("mesh_grid contains duplicate node IDs")
    csv_nodes = _normalized_node_ids(dataframe[node_column], csv_path)
    mesh_node_set = set(mesh_nodes.tolist())
    unknown_nodes = sorted(set(csv_nodes.tolist()) - mesh_node_set)
    if unknown_nodes:
        raise ValueError(
            f"CSV contains node IDs not present in mesh_grid: {unknown_nodes[:10]}"
        )
    if expected_node_ids is not None:
        expected_set = {int(node) for node in expected_node_ids}
        actual_set = set(csv_nodes.tolist())
        if actual_set != expected_set:
            missing = sorted(expected_set - actual_set)
            unexpected = sorted(actual_set - expected_set)
            raise ValueError(
                "CSV node IDs do not match the node workbook; "
                f"missing={missing[:10]}, unexpected={unexpected[:10]}"
            )

    row_index = {node_id: index for index, node_id in enumerate(mesh_nodes)}
    values = np.full((n_nodes, len(value_columns)), np.nan, dtype=float)
    value_data = (
        dataframe[value_columns]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(float)
    )
    for source_row, node_id in enumerate(csv_nodes):
        values[row_index[int(node_id)], :] = value_data[source_row, :]

    if values.shape[1] < 2:
        raise ValueError(
            f"CSV 时间列不足 2 列，无法由累积量计算年差值: {csv_path}"
        )
    values_annual = (values[:, 1:] - values[:, :-1]) * 1e3
    years_annual = years[1:]
    return values_annual, years_annual


def load_simulation_ensemble(
    csv_dir: str | Path,
    mesh_grid: np.ndarray,
    n_ensemble: int,
    expected_node_ids: Iterable[int] | None = None,
) -> tuple[np.ndarray, list[int]]:
    """Load, year-align, and stack ``solbox001`` through the requested count."""
    directory = Path(csv_dir)
    matrices: list[np.ndarray] = []
    use_memmap = comparison_memmap_enabled()
    mapped_ensemble: np.memmap | None = None
    loaded_count = 0
    sim_years_ref: list[int] | None = None
    for member in range(1, n_ensemble + 1):
        csv_path = directory / f"solbox{member:03d}.csv"
        if not csv_path.exists():
            print(f"[WARN] 缺失: {csv_path.name}, 跳过")
            continue
        values, years_from_csv = read_pot_csv_matrix(
            csv_path,
            n_nodes=mesh_grid.shape[0],
            mesh_grid=mesh_grid,
            expected_node_ids=expected_node_ids,
        )
        current_years = list(map(int, years_from_csv))
        if sim_years_ref is None:
            sim_years_ref = current_years
            if use_memmap:
                output_dir = comparison_output_dir()
                assert output_dir is not None
                mapped_ensemble = np.memmap(
                    output_dir / "multi_sim_matrix.memmap",
                    mode="w+",
                    dtype=float,
                    shape=(n_ensemble, values.shape[0], values.shape[1]),
                )
        elif current_years != sim_years_ref:
            index_map = {year: index for index, year in enumerate(current_years)}
            aligned = np.full(
                (values.shape[0], len(sim_years_ref)), np.nan, dtype=float
            )
            for reference_index, year in enumerate(sim_years_ref):
                source_index = index_map.get(int(year))
                if source_index is not None:
                    aligned[:, reference_index] = values[:, source_index]
            values = aligned
        if use_memmap:
            assert mapped_ensemble is not None
            mapped_ensemble[loaded_count, :, :] = values
        else:
            matrices.append(values)
        loaded_count += 1
        print(f"[OK] parsed {csv_path.name} -> vals shape {values.shape}")

    if loaded_count == 0 or sim_years_ref is None:
        raise ValueError(f"No solbox CSV files were loaded from {directory}")
    if loaded_count != n_ensemble:
        raise ValueError(
            f"Loaded {loaded_count} simulation members; expected {n_ensemble}"
        )
    if use_memmap:
        assert mapped_ensemble is not None
        mapped_ensemble.flush()
        multi_sim_matrix = mapped_ensemble
    else:
        multi_sim_matrix = np.stack(matrices, axis=0)
    print("multi_sim_matrix:", multi_sim_matrix.shape)
    return multi_sim_matrix, sim_years_ref


def select_values_from_sim_matrix(
    multi_sim_matrix: np.ndarray,
    list_of_tags: list[int],
    year_idx: list[int] | np.ndarray | None = None,
) -> np.ndarray:
    """Select 1-based node tags and return ``(locations, time, ensembles)``."""
    tags_idx = np.asarray(list_of_tags, dtype=int) - 1
    data = multi_sim_matrix[:, tags_idx, :]
    if year_idx is not None:
        data = data[..., year_idx]
    return np.transpose(data, (1, 2, 0))
