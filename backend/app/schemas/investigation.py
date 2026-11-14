from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class SafetyDomain(str, Enum):
    PREVENTION = "Prevention"
    DETECTION = "Detection"
    SUPPRESSION = "Suppression"
    OTHER = "Other"

class FuelType(str, Enum):
    SOLID = "Solid"
    LIQUID = "Liquid"
    GASEOUS = "Gaseous"
    OTHER = "Other"

class InvestigationRecord(BaseModel):
    investigation_id: str
    investigation_name: str
    project: Optional[str] = None
    safety_domain: SafetyDomain
    fuel_type: FuelType
    oxygen_concentration_pct: Optional[float] = None
    flow_velocity_cm_s: Optional[float] = None
    hardware: Optional[str] = None
    objectives: Optional[str] = None
    measurements: List[str] = []
    source_url: Optional[HttpUrl] = None
    data_completeness: List[str] = []