from functools import lru_cache
from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.dummy import DummyRegressor

from ..schemas.prediction import BurnTimeValidationOutput, ValidationRange

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw_datasets"
    / "PSI-159_Experimental table_CFI-G_Normal Flames.csv"
)

MODEL_FEATURES = [
    "oxygen_concentration",
    "chamber_pressure_bar",
    "mass_flow_rate_mg_s",
    "fuel_type_30% ethane",
    "fuel_type_30% propane",
    "fuel_type_50% butane",
    "fuel_type_ethane",
    "fuel_type_propane",
]

NUMERIC_COLUMNS = {
    " XO2 before test": "oxygen_concentration",
    "approx p (bar)": "chamber_pressure_bar",
    "mHC (mg/s)": "mass_flow_rate_mg_s",
    "burn time (sec)": "burn_time_sec",
}


def load_training_data() -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"CFI-G training dataset not found: {DATASET_PATH}")

    data = pd.read_csv(DATASET_PATH)
    required = [*NUMERIC_COLUMNS, "Fuel", "Day"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"CFI-G dataset is missing required columns: {', '.join(missing)}")

    selected = data[required].copy()
    selected = selected.rename(
        columns={**NUMERIC_COLUMNS, "Fuel": "fuel_type"}
    )
    for column in NUMERIC_COLUMNS.values():
        selected[column] = pd.to_numeric(selected[column], errors="coerce")

    selected["fuel_type"] = selected["fuel_type"].astype("string").str.strip()
    selected["Day"] = pd.to_numeric(selected["Day"], errors="coerce")
    selected = selected.dropna(
        subset=[
            "oxygen_concentration",
            "chamber_pressure_bar",
            "mass_flow_rate_mg_s",
            "burn_time_sec",
            "fuel_type",
            "Day",
        ]
    )
    if selected.empty:
        raise ValueError("CFI-G dataset contains no complete training rows")

    encoded = pd.get_dummies(
        selected[
            [
                "oxygen_concentration",
                "chamber_pressure_bar",
                "mass_flow_rate_mg_s",
                "fuel_type",
            ]
        ],
        columns=["fuel_type"],
        dtype=float,
    )
    X = encoded.reindex(columns=MODEL_FEATURES, fill_value=0.0)
    y = selected["burn_time_sec"].astype(float)
    groups = selected["Day"]
    return X, y, groups


@lru_cache(maxsize=1)
def get_burn_time_validation() -> BurnTimeValidationOutput:
    X, y, groups = load_training_data()
    unique_days = groups.nunique()
    if unique_days < 2:
        raise ValueError("Grouped validation requires at least two experimental days")

    splitter = GroupKFold(n_splits=unique_days)
    estimator = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
    )
    predictions = cross_val_predict(estimator, X, y, groups=groups, cv=splitter)
    baseline_predictions = cross_val_predict(
        DummyRegressor(strategy="mean"),
        X,
        y,
        groups=groups,
        cv=splitter,
    )
    errors = abs(y.to_numpy() - predictions)

    ranges = {
        feature: ValidationRange(
            minimum=float(X[feature].min()),
            maximum=float(X[feature].max()),
        )
        for feature in MODEL_FEATURES[:3]
    }

    return BurnTimeValidationOutput(
        validation_method="Leave-one-experimental-day-out cross-validation",
        samples=len(y),
        held_out_days=unique_days,
        mae_sec=float(mean_absolute_error(y, predictions)),
        rmse_sec=float(mean_squared_error(y, predictions) ** 0.5),
        r2=float(r2_score(y, predictions)),
        mean_baseline_mae_sec=float(mean_absolute_error(y, baseline_predictions)),
        within_10_sec_fraction=float((errors <= 10).mean()),
        within_20_sec_fraction=float((errors <= 20).mean()),
        target_range_sec=ValidationRange(
            minimum=float(y.min()),
            maximum=float(y.max()),
        ),
        input_ranges=ranges,
    )
