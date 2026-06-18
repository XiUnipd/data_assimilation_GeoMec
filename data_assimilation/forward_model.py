"""Current fixed forward-model boundary and future simulator integration notes."""

from __future__ import annotations

import numpy as np


def run_forward_model_for_ensemble(
    X_current: np.ndarray, Y_model: np.ndarray
) -> np.ndarray:
    """Return the precomputed prior predictions for every ES-MDA round.

    The current workflow does **not** write updated Cm parameters, invoke an
    external numerical solver, or rebuild predictions. ``X_current`` is
    therefore intentionally unused and the same prior ``Y_model`` is returned
    at every round, exactly as in the source script.

    A future implementation may write each member's parameters, run the solver,
    parse its POT/CSV output, and rebuild rows using the preserved observation
    extraction plan. That behavior is deliberately not activated here.
    """
    del X_current
    return Y_model

