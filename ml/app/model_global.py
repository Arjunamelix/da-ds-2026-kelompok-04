"""Pembangun model gabungan untuk S3 (dipakai notebook, dan aplikasi mulai S6).

Semua model memprediksi y = ln P[t+h] - ln P[t] dari fitur `fitur_global.FITUR_TERPILIH`.
Langkah praproses (imputasi, standardisasi, one-hot) ada di dalam pipeline, jadi statistiknya selalu
dihitung dari data latih saja ketika `fit` dipanggil.
"""
from __future__ import annotations

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .fitur_global import KATEGORI

ALGORITMA = ("linear_regression", "ridge", "random_forest", "hist_gb", "lightgbm")

PARAM_BAWAAN = {
    "linear_regression": {},
    "ridge": {"alpha": 1.0},
    "random_forest": {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 50, "max_features": 0.5, "max_samples": 0.5},
    "hist_gb": {"max_iter": 300, "learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 50, "l2_regularization": 1.0},
    "lightgbm": {"objective": "l1", "n_estimators": 400, "learning_rate": 0.03, "num_leaves": 31, "min_child_samples": 50,
                 "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "reg_lambda": 1.0},
}


def buat_model(nama: str, param: dict | None, kolom: list[str], seed: int = 42):
    """Estimator scikit-learn siap `fit(X[kolom], y)`."""
    p = {**PARAM_BAWAAN[nama], **(param or {})}
    kat = [c for c in kolom if c in KATEGORI]
    num = [c for c in kolom if c not in KATEGORI]
    if nama in ("ridge", "linear_regression"):
        pra = ColumnTransformer([
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), num),
            ("kat", OneHotEncoder(handle_unknown="ignore"), kat),
        ])
        # Linear Regression murni = baseline panduan; one-hot lengkap + intercept diselesaikan lstsq (solusi norma minimum)
        reg = Ridge(alpha=p["alpha"]) if nama == "ridge" else LinearRegression()
        return Pipeline([("pra", pra), ("model", reg)])
    if nama == "random_forest":
        pra = ColumnTransformer([("num", SimpleImputer(strategy="median", add_indicator=True), num),
                                 ("kat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), kat)])
        return Pipeline([("pra", pra), ("model", RandomForestRegressor(random_state=seed, n_jobs=-1, **p))])
    if nama == "hist_gb":
        return HistGradientBoostingRegressor(loss="absolute_error", early_stopping=False, random_state=seed,
                                             categorical_features=[c in KATEGORI for c in kolom], **p)
    if nama == "lightgbm":
        return _LGBM(kolom, kat, seed, p)
    raise ValueError(f"algoritma tidak dikenal: {nama}")


class _LGBM:
    """LightGBM dengan kolom kategori bertipe category (dibuat di sini agar urutan kategori tetap)."""

    def __init__(self, kolom, kat, seed, param):
        import lightgbm as lgb
        self.kolom, self.kat = kolom, kat
        self.model = lgb.LGBMRegressor(random_state=seed, n_jobs=-1, verbose=-1, **param)

    def _siap(self, X):
        X = X[self.kolom].copy()
        for c in self.kat:
            X[c] = X[c].astype("int64").astype("category").cat.set_categories(range(64))
        return X

    def fit(self, X, y):
        self.model.fit(self._siap(X), y)
        return self

    def predict(self, X):
        return self.model.predict(self._siap(X))


def susut(pred: np.ndarray, ambang: float) -> np.ndarray:
    """Penyusutan lunak ke nol: prediksi perubahan yang lebih kecil dari `ambang` (skala log) dianggap 0,
    sisanya dikurangi `ambang`. Untuk harga yang lengket, tebakan "tetap" sering lebih tepat daripada gerak kecil."""
    return np.sign(pred) * np.maximum(np.abs(pred) - ambang, 0.0)