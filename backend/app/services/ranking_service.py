import re
from typing import List, Set

from pydantic import BaseModel

from ..api.investigations import Investigation, load_canonical_data


class RankedInvestigation(BaseModel):
    investigation_id: str
    investigation: Investigation
    relevance_score: int
    reasoning: str


class RankingResponse(BaseModel):
    mission_scenario: str
    rankings: List[RankedInvestigation]


STOP_WORDS = {
    "and", "for", "from", "high", "into", "low", "mission", "scenario",
    "the", "with", "without",
}


def _query_terms(mission_scenario: str, constraints: str) -> Set[str]:
    words = re.findall(r"[a-z0-9]+", f"{mission_scenario} {constraints}".lower())
    return {word for word in words if len(word) > 2 and word not in STOP_WORDS}


def _record_terms(investigation: Investigation) -> Set[str]:
    values = [
        investigation.name,
        investigation.project,
        investigation.fuel_type,
        investigation.source_file,
        *investigation.raw_data.keys(),
        *investigation.raw_data.values(),
    ]
    words = re.findall(r"[a-z0-9]+", " ".join(values).lower())
    terms = set(words)
    if investigation.oxygen_pct is not None:
        terms.update({"oxygen", "o2"})
    if investigation.max_flow_velocity_cm_s is not None:
        terms.update({"flow", "velocity"})
    if investigation.pressure_bar is not None:
        terms.add("pressure")
    return terms


def calculate_relevance_rankings(
    mission_scenario: str,
    constraints: str,
) -> RankingResponse:
    """Rank local NASA records by explicit term overlap with their source data."""
    investigations = load_canonical_data()
    query_terms = _query_terms(mission_scenario, constraints)
    scored = []

    for investigation in investigations:
        matches = query_terms.intersection(_record_terms(investigation))
        if not matches:
            continue

        score = round(100 * len(matches) / len(query_terms)) if query_terms else 0
        completeness = sum(
            value is not None
            for value in (
                investigation.oxygen_pct,
                investigation.max_flow_velocity_cm_s,
                investigation.pressure_bar,
            )
        )
        scored.append((score, completeness, investigation.id, investigation, matches))

    scored.sort(key=lambda result: (-result[0], -result[1], result[2]))
    rankings = [
        RankedInvestigation(
            investigation_id=investigation.id,
            investigation=investigation,
            relevance_score=score,
            reasoning=(
                f"Matched {', '.join(sorted(matches))} in the dataset record; "
                f"source: {investigation.source_file}, row {investigation.source_row}."
            ),
        )
        for score, _, _, investigation, matches in scored[:50]
    ]
    return RankingResponse(mission_scenario=mission_scenario, rankings=rankings)
