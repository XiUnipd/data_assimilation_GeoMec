"""Shape validation and the unchanged physical-space ES-MDA update loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import config
from .comparison import save_comparison_array
from .forward_model import run_forward_model_for_ensemble
from .plotting import (
    plot_round_clay_ecdf,
    plot_round_current_scatter,
    plot_round_pre_post_ecdf,
    plot_round_pre_post_scatter,
)
from .transforms import nscore_forward


def resolve_assimilated_indices(
    parameter_names: Sequence[str],
    assimilated_lithologies: Sequence[str],
    n_parameter_rows: int,
) -> np.ndarray:
    """Validate configured lithologies and return canonical matrix-row indices.

    Selection is strict and case-sensitive. The returned order always follows
    ``parameter_names`` rather than the configured selection order.
    """
    names = list(parameter_names)
    selected = list(assimilated_lithologies)
    if len(names) != n_parameter_rows:
        raise ValueError(
            f"PARAMETER_NAMES has {len(names)} entries but mat_matrix has "
            f"{n_parameter_rows} parameter rows."
        )
    if len(set(names)) != len(names):
        raise ValueError(f"PARAMETER_NAMES contains duplicates: {names}")
    if not selected:
        raise ValueError("ASSIMILATED_LITHOLOGIES must contain at least one lithology.")
    if len(set(selected)) != len(selected):
        raise ValueError(
            f"ASSIMILATED_LITHOLOGIES contains duplicates: {selected}"
        )
    unknown = [name for name in selected if name not in names]
    if unknown:
        raise ValueError(
            f"Unknown ASSIMILATED_LITHOLOGIES values: {unknown}. "
            f"Allowed values are {names}; matching is case-sensitive."
        )
    selected_set = set(selected)
    return np.asarray(
        [index for index, name in enumerate(names) if name in selected_set],
        dtype=int,
    )


def validate_assimilation_shapes(
    observations: np.ndarray,
    Y_model: np.ndarray,
    mat_matrix: np.ndarray,
    covariance: np.ndarray,
) -> None:
    """Validate output and ensemble dimensions before constructing ESMDA."""
    observations = np.asarray(observations)
    covariance = np.asarray(covariance)
    if observations.ndim != 1:
        raise ValueError(f"observations must be 1D, got {observations.shape}")
    if covariance.ndim != 1:
        raise ValueError(f"covariance must be 1D, got {covariance.shape}")
    if Y_model.ndim != 2:
        raise ValueError(f"Y_model must be 2D, got {Y_model.shape}")
    if mat_matrix.ndim != 2:
        raise ValueError(f"mat_matrix must be 2D, got {mat_matrix.shape}")
    if covariance.size != observations.size:
        raise ValueError(
            f"Mismatch in #outputs: covariance has {covariance.size}, "
            f"observations has {observations.size}"
        )
    if Y_model.shape[0] != observations.size:
        raise ValueError(
            f"Mismatch in #outputs: obs has {observations.size}, "
            f"Y_model has {Y_model.shape[0]}"
        )
    if mat_matrix.shape[1] != Y_model.shape[1]:
        raise ValueError(
            f"Mismatch in #ensembles: X has {mat_matrix.shape[1]}, "
            f"Y has {Y_model.shape[1]}"
        )


def run_assimilation(
    observations: np.ndarray,
    Y_model: np.ndarray,
    mat_matrix: np.ndarray,
    covariance: np.ndarray,
    n_assim: int,
    figures_dir: str | Path,
    seed: int = config.SEED,
    inversion: str = config.INVERSION,
    parameter_names: Sequence[str] = tuple(config.PARAMETER_NAMES),
    assimilated_lithologies: Sequence[str] = tuple(
        config.ASSIMILATED_LITHOLOGIES
    ),
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Run the original ES-MDA loop and return posterior arrays and diagnostics.

    Despite the source-file title mentioning a positive limitation, this loop
    contains no clipping or bounds. It also computes normal scores for plotting
    but deliberately assimilates ``X_curr_log`` directly, not ``Z_curr``.
    """
    validate_assimilation_shapes(observations, Y_model, mat_matrix, covariance)
    if n_assim <= 0:
        raise ValueError(f"n_assim must be positive, got {n_assim}")
    selected_indices = resolve_assimilated_indices(
        parameter_names,
        assimilated_lithologies,
        mat_matrix.shape[0],
    )
    all_indices = np.arange(mat_matrix.shape[0], dtype=int)
    unselected_indices = np.setdiff1d(all_indices, selected_indices)
    selected_names = [parameter_names[index] for index in selected_indices]
    print(f"Assimilated lithologies: {selected_names}")
    print(f"Assimilated parameter row indices: {selected_indices.tolist()}")

    # Lazy import keeps package imports free of assimilation execution and lets
    # pure reader/ordering tests run without this optional runtime dependency.
    from iterative_ensemble_smoother import ESMDA

    smoother = ESMDA(
        covariance=covariance,
        observations=observations,
        alpha=n_assim,
        seed=seed,
        inversion=inversion,
    )
    X_curr = np.array(mat_matrix, dtype=float)
    X_curr_log = X_curr
    print(f"X_curr_log: \n{X_curr_log}")
    X_init = X_curr.copy()
    save_comparison_array("X_init", X_init)
    print(f"The shape of X_curr is {X_curr.shape}")
    Z_curr: np.ndarray | None = None
    rounds: list[dict[str, Any]] = []

    for iteration, alpha_value in enumerate(smoother.alpha, 1):
        print(
            f"ES-MDA round {iteration}/{smoother.num_assimilations()} "
            f"with α={alpha_value}"
        )
        Z_curr, _nscore_ref = nscore_forward(X_curr_log)
        plot_round_current_scatter(X_curr_log, iteration, figures_dir)

        Y_curr = run_forward_model_for_ensemble(X_curr, Y_model)
        max_y_difference = float(np.max(np.abs(Y_curr - Y_model)))
        mean_y_variance = float(np.mean(np.var(Y_curr, axis=1)))
        parameter_std = np.std(X_curr_log, axis=1)
        print(f"Y_curr - Y_model: {max_y_difference}")
        print("Var(Y_curr by column) =", mean_y_variance)
        print("Std(X_curr_log) per param =", parameter_std)

        X_pre_log = X_curr_log.copy()
        selected_prior = X_curr_log[selected_indices, :].copy()
        selected_posterior = smoother.assimilate(selected_prior, Y=Y_curr)
        X_curr_log[selected_indices, :] = selected_posterior
        if unselected_indices.size and not np.array_equal(
            X_curr_log[unselected_indices, :], X_init[unselected_indices, :]
        ):
            raise RuntimeError(
                "An unselected lithology changed during ES-MDA assimilation."
            )
        save_comparison_array(
            f"X_after_assim_round_{iteration}", X_curr_log
        )
        plot_round_pre_post_ecdf(
            X_pre_log, X_curr_log, iteration, figures_dir
        )
        plot_round_pre_post_scatter(
            X_pre_log, X_curr_log, iteration, figures_dir
        )
        X_curr = X_curr_log
        plot_round_clay_ecdf(X_init, X_curr, alpha_value, figures_dir)
        rounds.append(
            {
                "iteration": iteration,
                "alpha": float(alpha_value),
                "max_abs_y_difference": max_y_difference,
                "mean_y_variance": mean_y_variance,
                "parameter_std": parameter_std.copy(),
                "assimilated_lithologies": selected_names.copy(),
                "assimilated_indices": selected_indices.copy(),
            }
        )

    if Z_curr is None:
        raise RuntimeError("ES-MDA produced no assimilation rounds")
    X_posterior = X_curr
    if unselected_indices.size and not np.array_equal(
        X_posterior[unselected_indices, :], X_init[unselected_indices, :]
    ):
        raise RuntimeError("Final posterior changed an unselected lithology.")
    # Preserve source semantics: this is Z computed before the final update.
    Z_posterior = Z_curr
    save_comparison_array("X_final_posterior", X_posterior)
    return X_posterior, Z_posterior, {
        "rounds": rounds,
        "assimilated_lithologies": selected_names,
        "assimilated_indices": selected_indices.copy(),
        "unselected_indices": unselected_indices.copy(),
    }
