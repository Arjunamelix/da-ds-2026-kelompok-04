"""Model: baseline naif dan boosting (Project.md 6.4)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from . import config


def buat_boosting() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(**config.BOOSTING)


def latih(x: pd.DataFrame, y: pd.Series) -> GradientBoostingRegressor:
    m = buat_boosting()
    m.fit(x.values, y.values)
    return m


def prediksi_log(m: GradientBoostingRegressor, x: pd.DataFrame) -> np.ndarray:
    return m.predict(x.values)


def baseline_log(n: int) -> np.ndarray:
    """Baseline naif: harga hari ini berlaku h hari lagi, yaitu perubahan log = 0."""
    return np.zeros(n)