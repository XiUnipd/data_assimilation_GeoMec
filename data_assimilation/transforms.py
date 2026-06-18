"""Array flattening, normal-score transforms, and empirical CDF helpers."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, rankdata


def flatten_matrix(matrix: np.ndarray) -> np.ndarray:
    """Flatten a matrix in the original C order."""
    return matrix.ravel(order="C")


def flatten_3d_matrix(matrix: np.ndarray) -> np.ndarray:
    """Flatten each ensemble slice in C order and return outputs by ensemble."""
    num_ensemble = matrix.shape[2]
    return np.stack(
        [matrix[:, :, index].ravel(order="C") for index in range(num_ensemble)]
    ).T


def nscore_forward(
    X: np.ndarray, eps: float = 1e-6
) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
    """Apply the original empirical row-wise normal-score transform."""
    X = np.asarray(X, float)
    n_params, ensemble_count = X.shape
    Z = np.empty_like(X)
    z_ref_sorted = np.empty_like(X)
    x_ref_sorted = np.empty_like(X)
    for index in range(n_params):
        values = X[index, :]
        ranks = rankdata(values, method="average")
        probabilities = (ranks - 0.5) / ensemble_count
        probabilities = np.clip(probabilities, eps, 1 - eps)
        transformed = norm.ppf(probabilities)
        Z[index, :] = transformed
        x_ref_sorted[index, :] = np.sort(values)
        z_ref_sorted[index, :] = np.sort(transformed)
    print(f"Mean of Z: {np.mean(Z)} and Standard Deviation of Z: {np.std(Z)}")
    return Z, (z_ref_sorted, x_ref_sorted)


def nscore_inverse(
    Z: np.ndarray, reference: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
    """Invert normal scores through the original row-wise interpolation."""
    z_ref_sorted, x_ref_sorted = reference
    Z = np.asarray(Z, float)
    n_params, _ensemble_count = Z.shape
    X = np.empty_like(Z)
    for index in range(n_params):
        X[index, :] = np.interp(
            Z[index, :], z_ref_sorted[index, :], x_ref_sorted[index, :]
        )
    return X


def _ecd_1d(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the original empirical CDF coordinates for one-dimensional data."""
    values = np.sort(np.asarray(samples, float))
    frequencies = np.arange(1, values.size + 1) / values.size
    return values, frequencies

