import logging
from pathlib import Path

import joblib
import pandas as pd

from ..schemas.prediction import PredictionInput, PredictionOutput

logger = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    pass


class PredictionService:
    FEATURE_NAMES = [
        "oxygen_concentration",
        "chamber_pressure_bar",
        "mass_flow_rate_mg_s",
        "fuel_type_30% ethane",
        "fuel_type_30% propane",
        "fuel_type_50% butane",
        "fuel_type_ethane",
        "fuel_type_propane",
    ]

    def __init__(self, model_path: Path | str | None = None):
        if model_path is None:
            model_path = Path(__file__).resolve().parents[2] / "flamesync_rf_model.pkl"
        self.model_path = Path(model_path)
        try:
            self.model = joblib.load(self.model_path)
        except FileNotFoundError:
            self.model = None
            logger.warning("Prediction model not found at %s", self.model_path)

    def predict_burn_time(self, input_data: PredictionInput) -> PredictionOutput:
        if self.model is None:
            raise ModelUnavailableError(
                f"Prediction model is unavailable at {self.model_path}"
            )

        features = [
            input_data.oxygen_concentration,
            input_data.chamber_pressure_bar,
            input_data.mass_flow_rate_mg_s,
            1 if input_data.fuel_type == "30% ethane" else 0,
            1 if input_data.fuel_type == "30% propane" else 0,
            1 if input_data.fuel_type == "50% butane" else 0,
            1 if input_data.fuel_type == "ethane" else 0,
            1 if input_data.fuel_type == "propane" else 0
        ]

        model_features = getattr(self.model, "feature_names_in_", self.FEATURE_NAMES)
        if list(model_features) != self.FEATURE_NAMES:
            raise RuntimeError(
                "Prediction model features do not match the current prediction input schema"
            )

        prediction = float(
            self.model.predict(pd.DataFrame([features], columns=self.FEATURE_NAMES))[0]
        )

        if prediction > 40:
            risk = "CRITICAL: SUSTAINED FLAME"
        elif prediction > 15:
            risk = "WARNING: PROLONGED BURN"
        else:
            risk = "SAFE: RAPID EXTINGUISHMENT"

        importances = getattr(self.model, "feature_importances_", None)
        importance = (
            {
                name: float(value)
                for name, value in zip(self.FEATURE_NAMES, importances, strict=True)
            }
            if importances is not None
            else {}
        )

        return PredictionOutput(
            predicted_burn_time_sec=round(prediction, 2),
            risk_level=risk,
            feature_importance=importance
        )

prediction_service = PredictionService()