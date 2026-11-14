import logging

from fastapi import APIRouter, HTTPException

from ..schemas.prediction import PredictionInput, PredictionOutput
from ..schemas.prediction import BurnTimeValidationOutput
from ..services.burn_time_validation import get_burn_time_validation
from ..services.prediction_service import (
    ModelUnavailableError,
    prediction_service,
)

router = APIRouter(tags=["Predict"])
logger = logging.getLogger(__name__)


@router.get(
    "/api/predictions/validation",
    response_model=BurnTimeValidationOutput,
)
async def get_prediction_validation():
    return get_burn_time_validation()


@router.post("/api/predictions/burn-time", response_model=PredictionOutput)
@router.post(
    "/api/predictions/spread-rate",
    response_model=PredictionOutput,
    include_in_schema=False,
)
async def predict_burn_time(payload: PredictionInput):
    try:
        return prediction_service.predict_burn_time(payload)
    except ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Burn-time prediction failed")
        raise HTTPException(status_code=500, detail="Burn-time prediction failed") from error