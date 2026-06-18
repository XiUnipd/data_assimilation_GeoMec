"""Per-round/final ES-MDA plots and posterior CSV export."""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .transforms import _ecd_1d


def _pyplot():
    """Import pyplot lazily so importing this module performs no plotting work."""
    from matplotlib import pyplot as plt

    return plt


def plot_round_current_scatter(
    X_curr_log: np.ndarray, iteration: int, figures_dir: str | Path
) -> Path:
    """Save the original first-two-parameter current-ensemble scatter plot."""
    plt = _pyplot()
    output_dir = Path(figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"X_curr_round{iteration}.png"
    plt.figure()
    plt.scatter(X_curr_log[0, :], X_curr_log[1, :])
    plt.savefig(output)
    plt.close()
    return output


def plot_round_pre_post_ecdf(
    X_pre_log: np.ndarray,
    X_curr_log: np.ndarray,
    iteration: int,
    figures_dir: str | Path,
) -> Path:
    """Save the original all-parameter pre/current ECDF figure."""
    plt = _pyplot()
    output_dir = Path(figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"ECDF_X_pre_log_and_X_curr_log_alpha{iteration}.png"
    plt.figure(figsize=(16, 9))
    for index in range(X_curr_log.shape[0]):
        x_pre, frequency_pre = _ecd_1d(X_pre_log[index, :])
        x_post, frequency_post = _ecd_1d(X_curr_log[index, :])
        plt.step(
            x_pre,
            frequency_pre,
            where="post",
            linewidth=1.6,
            label=f"Cm_pre{index}",
        )
        plt.step(
            x_post,
            frequency_post,
            where="post",
            linewidth=1.6,
            linestyle="--",
            label=f"Cm_curr{index}",
        )
    plt.xlabel("Cm - ")
    plt.ylabel("Empirical CDF")
    plt.title(f"ECDF, alpha={iteration}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    print(f"Saved: {output}")
    return output


def plot_round_pre_post_scatter(
    X_pre_log: np.ndarray,
    X_curr_log: np.ndarray,
    iteration: int,
    figures_dir: str | Path,
) -> Path:
    """Save the original first-two-parameter pre/current scatter figure."""
    plt = _pyplot()
    output_dir = Path(figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"Z_curr_round{iteration}.png"
    plt.figure()
    plt.scatter(X_pre_log[0, :], X_pre_log[1, :], label="Z_pre")
    plt.scatter(X_curr_log[0, :], X_curr_log[1, :], label="Z_curr")
    plt.grid(True)
    plt.xlabel("Z1")
    plt.ylabel("Z2")
    plt.title("Z_pre vs Z_curr")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    return output


def plot_round_clay_ecdf(
    X_init: np.ndarray,
    X_curr: np.ndarray,
    alpha_value: float,
    figures_dir: str | Path,
) -> Path:
    """Save the Clay ECDF using parameter row index 3, unchanged from source."""
    plt = _pyplot()
    output_dir = Path(figures_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"ECDF_X_curr_alpha{alpha_value}.png"
    x_current, frequency_current = _ecd_1d(X_curr[3, :])
    x_initial, frequency_initial = _ecd_1d(X_init[3, :])
    plt.figure(figsize=(16, 9))
    plt.step(
        x_initial,
        frequency_initial,
        where="post",
        linewidth=1.6,
        label="Clay_init",
    )
    plt.step(
        x_current,
        frequency_current,
        where="post",
        linewidth=1.6,
        label="Clay_curr",
    )
    plt.xlabel("The Cm after assimilation")
    plt.ylabel("Empirical CDF")
    plt.title(f"ECDF of X_curr, alpha={alpha_value}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    return output


def plot_linear_and_z_results(
    mat_matrix: np.ndarray,
    Z_prior: np.ndarray,
    X_posterior: np.ndarray,
    Z_posterior: np.ndarray,
    param_names: tuple[str, ...] | list[str] | None = None,
    out_prefix: str = "ESMDA_K",
    out_dir: str | Path = ".",
    show: bool = False,
) -> tuple[Path, Path]:
    """Create the original final normal-score and linear-space comparisons."""
    plt = _pyplot()
    mat_matrix = np.asarray(mat_matrix, float)
    Z_prior = np.asarray(Z_prior, float)
    X_posterior = np.asarray(X_posterior, float)
    Z_posterior = np.asarray(Z_posterior, float)
    if mat_matrix.shape != X_posterior.shape:
        raise ValueError(
            f"mat_matrix {mat_matrix.shape} != X_posterior {X_posterior.shape}"
        )
    if Z_prior.shape != Z_posterior.shape:
        raise ValueError(
            f"Z_prior {Z_prior.shape} != Z_posterior {Z_posterior.shape}"
        )
    if mat_matrix.shape[0] != Z_prior.shape[0]:
        raise ValueError("Linear/Z arrays must have same #params (rows).")
    n_params = X_posterior.shape[0]
    if param_names is None:
        param_names = [f"p{index + 1}" for index in range(n_params)]
    if len(param_names) != n_params:
        raise ValueError(
            f"param_names length {len(param_names)} != #params {n_params}"
        )
    x_positions = np.arange(n_params)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    time.strftime("%Y%m%d-%H%M%S")  # Retain the source's timestamp evaluation.

    plt.figure(figsize=(9, 3.6))
    for member in range(Z_posterior.shape[1]):
        plt.scatter(
            x_positions,
            Z_posterior[:, member],
            s=6,
            color="black",
            alpha=0.25,
            label="Posterior samples" if member == 0 else None,
        )
    for member in range(Z_prior.shape[1]):
        plt.scatter(
            x_positions,
            Z_prior[:, member],
            s=6,
            color="tab:red",
            alpha=0.20,
            label="Prior samples" if member == 0 else None,
        )
    plt.plot(
        x_positions,
        np.mean(Z_prior, axis=1),
        "x-",
        color="tab:red",
        label="Prior mean (Z)",
    )
    plt.plot(
        x_positions,
        np.mean(Z_posterior, axis=1),
        "o-",
        color="tab:blue",
        label="Posterior mean (Z)",
    )
    plt.xticks(x_positions, param_names)
    plt.ylabel("Normal score Z (N(0,1))")
    plt.title("Assimilation in normal-score space (Z)")
    plt.grid(True, ls="--", alpha=0.4)
    plt.legend(ncol=2)
    plt.tight_layout()
    z_figure = output_dir / f"{out_prefix}z_a2.png"
    plt.savefig(z_figure, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()

    epsilon = 1e-30
    mat_positive = np.clip(mat_matrix, epsilon, None)
    posterior_positive = np.clip(X_posterior, epsilon, None)
    plt.figure(figsize=(9, 3.6))
    for member in range(posterior_positive.shape[1]):
        plt.scatter(
            x_positions,
            posterior_positive[:, member],
            s=6,
            color="black",
            alpha=0.25,
            label="Posterior samples" if member == 0 else None,
        )
    for member in range(mat_positive.shape[1]):
        plt.scatter(
            x_positions,
            mat_positive[:, member],
            s=6,
            color="tab:red",
            alpha=0.20,
            label="Prior samples" if member == 0 else None,
        )
    plt.plot(
        x_positions,
        np.mean(mat_positive, axis=1),
        "x-",
        color="tab:red",
        label="Prior mean",
    )
    plt.plot(
        x_positions,
        np.mean(posterior_positive, axis=1),
        "o-",
        color="tab:blue",
        label="Posterior mean",
    )
    plt.xticks(x_positions, param_names)
    plt.xlim(-0.5, n_params - 0.5)
    plt.ylabel("Cm")
    plt.title("Assimilation result in linear space")
    plt.grid(True, which="both", ls="--", alpha=0.4)
    plt.legend(ncol=2)
    plt.tight_layout()
    linear_figure = output_dir / f"{out_prefix}linear_logya2.png"
    plt.savefig(linear_figure, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()
    print("Saved figures:")
    print(" -", os.path.abspath(z_figure))
    print(" -", os.path.abspath(linear_figure))
    return z_figure, linear_figure


def export_posterior_csvs(
    X_posterior: np.ndarray,
    Z_posterior: np.ndarray,
    param_names: tuple[str, ...] | list[str],
    out_dir: str | Path,
) -> tuple[Path, Path]:
    """Export posterior physical and normal-score ensembles with original names."""
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    linear = pd.DataFrame(
        X_posterior,
        index=param_names,
        columns=[f"Ens_{index + 1}" for index in range(X_posterior.shape[1])],
    )
    normal_score = pd.DataFrame(
        Z_posterior,
        index=param_names,
        columns=[f"Ens_{index + 1}" for index in range(Z_posterior.shape[1])],
    )
    linear_path = output_dir / "ESMDA_K_posterior_lineara2.csv"
    z_path = output_dir / "ESMDA_K_posterior_z.csv"
    linear.to_csv(linear_path)
    normal_score.to_csv(z_path)
    print(f"Saved posterior parameter CSVs:\n - {linear_path}\n - {z_path}")
    return linear_path, z_path

