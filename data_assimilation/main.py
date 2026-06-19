"""Single executable entry point for the modular ES-MDA workflow."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any

import numpy as np

# Support both ``python -m data_assimilation.main`` and direct execution as
# ``python data_assimilation/main.py`` without creating a second entry point.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_assimilation import config
from data_assimilation.assimilation import run_assimilation
from data_assimilation.comparison import save_comparison_array, save_comparison_json
from data_assimilation.covariance import build_diagonal_covariance
from data_assimilation.io_utils import load_table_auto
from data_assimilation.logging_utils import capture_console_output
from data_assimilation.mesh_mapping import (
    _load_tags,
    _load_tags_xyz_helper,
    find_nearest_points,
    load_mesh_grid,
)
from data_assimilation.observation import (
    assemble_obs_and_Y_model,
    extract_matrix_from_obs_df,
    get_years_with_records_per_point,
)
from data_assimilation.parameter_reader import read_mat_matrix
from data_assimilation.plotting import export_posterior_csvs, plot_linear_and_z_results
from data_assimilation.simulation_reader import load_simulation_ensemble
from data_assimilation.transforms import nscore_forward


def _print_observation_diagnostics(
    observation_df,
    sim_years_ref: list[int],
    years_pp: list[list[int]],
    values_pp: list[np.ndarray],
) -> None:
    """Preserve the source script's observation/year filtering diagnostics."""
    _, years_pp_1991, values_pp_1991, _ = get_years_with_records_per_point(
        observation_df,
        year_min=1991,
        year_max=config.YEAR_MAX,
        x_col=config.X_COLUMN,
        y_col=config.Y_COLUMN,
    )
    total_non_nan = sum(len(values) for values in values_pp_1991)
    print("观测中非 NaN 条目总数（未与模拟求交集） =", total_non_nan)
    print(
        "sim_years_ref: len =",
        len(sim_years_ref),
        "min =",
        min(sim_years_ref),
        "max =",
        max(sim_years_ref),
    )
    print("sim_years_ref 头尾 =", sim_years_ref[:10], "...", sim_years_ref[-10:])

    simulation_years = {int(year) for year in sim_years_ref}
    dropped = []
    for point_years, point_values in zip(years_pp_1991, values_pp_1991):
        for year, value in zip(point_years, point_values):
            if not np.isnan(value) and int(year) not in simulation_years:
                dropped.append(int(year))
    print("被年份轴过滤掉的观测条目数 =", len(dropped))
    print("Top 缺失年份 =", Counter(dropped).most_common(10))

    counts_all = Counter(
        year
        for point_years, point_values in zip(years_pp, values_pp)
        for year, value in zip(point_years, point_values)
        if not np.isnan(value)
    )
    counts_kept = Counter(
        year
        for point_years, point_values in zip(years_pp, values_pp)
        for year, value in zip(point_years, point_values)
        if not np.isnan(value) and int(year) in simulation_years
    )
    print("各年份保留率：year -> kept/total")
    for year in sorted(counts_all):
        print(year, "->", f"{counts_kept.get(year, 0)}/{counts_all[year]}")


def main() -> dict[str, Any]:
    """Run input assembly, ES-MDA, plotting, and posterior export in order."""
    mesh_grid = load_mesh_grid(config.MESH_GRID_FILE)
    observation_df = load_table_auto(config.OBS_FILE)
    observation_matrix, _obs_coordinates, obs_years, obs_columns = (
        extract_matrix_from_obs_df(
            observation_df,
            years=None,
            x_col=config.X_COLUMN,
            y_col=config.Y_COLUMN,
            year_min=config.YEAR_MIN,
            year_max=config.YEAR_MAX,
        )
    )
    print("匹配到年份 → 列名：", dict(zip(obs_years, obs_columns)))
    print("obs_matrix.shape =", observation_matrix.shape)

    node_df = _load_tags(config.NODE_DIR)
    expected_node_ids = node_df["Node"].to_numpy(dtype=int)
    multi_sim_matrix, sim_years_ref = load_simulation_ensemble(
        config.POT_DIR,
        mesh_grid,
        config.N_ENSEMBLE,
        expected_node_ids=expected_node_ids,
    )
    coords, years_pp, values_pp, _year_columns = (
        get_years_with_records_per_point(
            observation_df,
            year_min=config.YEAR_MIN,
            year_max=config.YEAR_MAX,
            x_col=config.X_COLUMN,
            y_col=config.Y_COLUMN,
        )
    )
    coords_matrix = _load_tags_xyz_helper(node_df, mesh_grid)
    _, _, _, tags_1based = find_nearest_points(coords, coords_matrix)
    observations, Y_model, plan, tags_idx = assemble_obs_and_Y_model(
        multi_sim_matrix=multi_sim_matrix,
        tags_1based=tags_1based,
        sim_years_ref=sim_years_ref,
        years_pp=years_pp,
        values_pp=values_pp,
    )
    print("构建完成：")
    print(" - observations_vec.shape =", observations.shape)
    print(" - Y_model_2d.shape      =", Y_model.shape)
    print(f"The first five row of Y_model is: {Y_model[:5]}")
    save_comparison_array("observations_vec", observations)
    save_comparison_array("Y_model_2d", Y_model)
    save_comparison_array("tags_idx", tags_idx)
    save_comparison_array("plan", np.asarray(plan, dtype=int))
    save_comparison_array("sim_years_ref", np.asarray(sim_years_ref, dtype=int))
    _print_observation_diagnostics(
        observation_df, sim_years_ref, years_pp, values_pp
    )

    covariance = build_diagonal_covariance(
        config.COVARIANCE_FILE,
        observation_df,
        sim_years_ref,
        observations,
        year_min=config.YEAR_MIN,
        year_max=config.YEAR_MAX,
        x_col=config.X_COLUMN,
        y_col=config.Y_COLUMN,
    )
    mat_matrix = read_mat_matrix(config.MAT_DIR, config.N_ENSEMBLE)
    print(mat_matrix)
    save_comparison_array("covariance_vec", covariance)
    save_comparison_array("mat_matrix_prior", mat_matrix)
    save_comparison_json(
        "run_config",
        {
            "n_ensemble": config.N_ENSEMBLE,
            "n_assim": config.N_ASSIM,
            "seed": config.SEED,
            "inversion": config.INVERSION,
            "year_min": config.YEAR_MIN,
            "year_max": config.YEAR_MAX,
            "observation_file": str(config.OBS_FILE),
            "covariance_file": str(config.COVARIANCE_FILE),
            "mesh_file": str(config.MESH_GRID_FILE),
            "solbox_dir": str(config.POT_DIR),
            "cm_prior_dir": str(config.MAT_DIR),
            "parameter_names": list(config.PARAMETER_NAMES),
            "assimilated_lithologies": list(config.ASSIMILATED_LITHOLOGIES),
        },
    )
    Z_prior, _ = nscore_forward(mat_matrix)
    X_posterior, Z_posterior, diagnostics = run_assimilation(
        observations=observations,
        Y_model=Y_model,
        mat_matrix=mat_matrix,
        covariance=covariance,
        n_assim=config.N_ASSIM,
        figures_dir=config.FIGURES_DIR,
        seed=config.SEED,
        inversion=config.INVERSION,
        parameter_names=config.PARAMETER_NAMES,
        assimilated_lithologies=config.ASSIMILATED_LITHOLOGIES,
    )
    plot_linear_and_z_results(
        mat_matrix,
        Z_prior,
        X_posterior,
        Z_posterior,
        param_names=config.PARAMETER_NAMES,
        out_prefix="ESMDA_K",
        out_dir=config.RESULTS_DIR,
        show=False,
    )
    export_posterior_csvs(
        X_posterior,
        Z_posterior,
        config.PARAMETER_NAMES,
        config.RESULTS_DIR,
    )
    return {
        "multi_sim_matrix": multi_sim_matrix,
        "observations": observations,
        "Y_model": Y_model,
        "plan": plan,
        "tags_idx": tags_idx,
        "covariance": covariance,
        "mat_matrix": mat_matrix,
        "X_posterior": X_posterior,
        "Z_posterior": Z_posterior,
        "diagnostics": diagnostics,
    }


if __name__ == "__main__":
    with capture_console_output(
        config.RUN_LOG_FILE,
        enabled=config.RUN_LOG_ENABLED,
        mode=config.RUN_LOG_MODE,
    ):
        main()
