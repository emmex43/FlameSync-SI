from fastapi import APIRouter
from pydantic import BaseModel
from ..services.ranking_service import calculate_relevance_rankings, RankingResponse

router = APIRouter(tags=["Rankings"])

class RankingRequest(BaseModel):
    mission_scenario: str
    constraints: str

@router.post("/api/rankings", response_model=RankingResponse)
async def get_scenario_rankings(payload: RankingRequest):
    """
    Rank local NASA dataset records against the requested mission and constraints.
    """
    result = calculate_relevance_rankings(
        mission_scenario=payload.mission_scenario,
        constraints=payload.constraints
    )
    return result