from typing import Dict, Literal

from pydantic import BaseModel, Field

OXYGEN_MIN = 0.179685675
OXYGEN_MAX = 0.3997
PRESSURE_MIN_BAR = 0.50665
PRESSURE_MAX_BAR = 3.0399
MASS_FLOW_MIN_MG_S = 0.0
MASS_FLOW_MAX_MG_S = 3.215


class PredictionInput(BaseModel):
    fuel_type: Literal[
        "ethane",
        "propane",
        "30% butane",
        "50% butane",
        "30% ethane",
        "30% propane",
    ] = Field(default="ethane", description="Fuel mixture used by the trained model")
    oxygen_concentration: float = Field(
        ...,
        ge=OXYGEN_MIN, le=OXYGEN_MAX,
        allow_inf_nan=False,
        description="Oxygen fraction within the training data range",
    )
    chamber_pressure_bar: float = Field(
        ...,
        ge=PRESSURE_MIN_BAR, le=PRESSURE_MAX_BAR,
        allow_inf_nan=False,
        description="Pressure within the training data range, in bar",
    )
    mass_flow_rate_mg_s: float = Field(
        ...,
        ge=MASS_FLOW_MIN_MG_S, le=MASS_FLOW_MAX_MG_S,
        allow_inf_nan=False,
        description="Mass flow within the training data range, in mg/s",
    )

class PredictionOutput(BaseModel):
    predicted_burn_time_sec: float
    feature_importance: Dict[str, float]


class ValidationRange(BaseModel):
    minimum: float
    maximum: float


class BurnTimeValidationOutput(BaseModel):
    validation_method: str
    samples: int
    held_out_days: int
    mae_sec: float
    rmse_sec: float
    r2: float
    mean_baseline_mae_sec: float
    within_10_sec_fraction: float
    within_20_sec_fraction: float
    target_range_sec: ValidationRange
    input_ranges: Dict[str, ValidationRange]