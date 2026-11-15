import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Explorer"])

DATASET_DIR = Path(__file__).resolve().parents[3] / "data" / "raw_datasets"


class Investigation(BaseModel):
    id: str
    name: str
    project: str
    safety_domain: str
    fuel_type: str
    oxygen_pct: Optional[float] = None
    max_flow_velocity_cm_s: Optional[float] = None
    pressure_bar: Optional[float] = None
    source_file: str
    source_row: int
    raw_data: Dict[str, str]
    source_updated_at: Optional[datetime] = None


def _read_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xls":
        return pd.read_excel(path, dtype=object, engine="xlrd")

    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="cp1252")


def _column_value(row: Dict[str, str], *terms: str) -> Optional[tuple[str, str]]:
    for column, value in row.items():
        normalized = column.strip().lower()
        if value.strip() and any(term in normalized for term in terms):
            return column, value.strip()
    return None


def _number(value: str) -> Optional[float]:
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def _numeric_field(row: Dict[str, str], *terms: str) -> Optional[tuple[str, float]]:
    for column, value in row.items():
        normalized = column.strip().lower()
        if not value.strip() or not any(term in normalized for term in terms):
            continue
        if "restrictor" in normalized:
            continue
        number = _number(value)
        if number is not None:
            return column, number
    return None


def _project_name(path: Path) -> str:
    name = re.sub(r"^PSI-\d+_Experimental table_", "", path.stem, flags=re.IGNORECASE)
    return name.replace("_", " ").strip()


def _read_xls_records(path: Path, source_updated_at: datetime) -> List[Investigation]:
    workbook = pd.ExcelFile(path, engine="xlrd")
    investigations: List[Investigation] = []
    project = path.stem.split()[0]

    for sheet_name in workbook.sheet_names:
        sheet = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
        header_row = next(
            (
                index
                for index, row in sheet.iterrows()
                if any(
                    isinstance(value, str) and value.strip().lower() == "time (sec)"
                    for value in row
                )
            ),
            None,
        )
        if header_row is None:
            continue

        header = sheet.iloc[header_row]
        value_columns = [
            index
            for index, value in enumerate(header)
            if isinstance(value, str) and "number of points" in value.lower()
        ]
        if not value_columns:
            raise ValueError(f"Could not identify measurement columns in {path.name}:{sheet_name}")

        columns = []
        metadata = sheet.iloc[:header_row]
        for value_column in value_columns:
            time_column = value_column - 1
            device = str(metadata.iloc[0, value_column]).replace("Instrument:", "").strip()
            unit = str(metadata.iloc[6, value_column]).replace("Units:", "").strip()
            columns.extend(
                [
                    (time_column, f"{device} time (sec)"),
                    (value_column, f"{device} reading ({unit})"),
                ]
            )

        for index in range(header_row + 1, len(sheet)):
            raw_data = {}
            for column, label in columns:
                value = sheet.iat[index, column]
                raw_data[label] = "" if pd.isna(value) else str(value).strip()
            if not any(raw_data.values()):
                continue
            measurement_number = len(investigations) + 1
            investigations.append(
                Investigation(
                    id=f"{project}-{sheet_name}-{measurement_number:04d}",
                    name=f"{project} sensor measurement {measurement_number}",
                    project=project,
                    safety_domain="Not classified",
                    fuel_type="Not specified",
                    source_file=path.name,
                    source_row=index + 1,
                    raw_data=raw_data,
                    source_updated_at=source_updated_at,
                )
            )

    if not investigations:
        raise ValueError(f"No tabular measurements found in Excel dataset {path.name}")
    return investigations


def load_canonical_data() -> List[Investigation]:
    """Load unique investigation/test rows from the local NASA dataset files."""
    if not DATASET_DIR.is_dir():
        raise FileNotFoundError(f"NASA dataset directory not found: {DATASET_DIR}")

    files = sorted(
        (
            path for path in DATASET_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in {".csv", ".xls"}
        ),
        key=lambda path: ("(1)" in path.stem, path.name.casefold()),
    )
    if not files:
        raise FileNotFoundError(f"No CSV or XLS datasets found in {DATASET_DIR}")

    investigations: List[Investigation] = []
    seen_files = set()

    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_files:
            continue
        seen_files.add(digest)
        source_updated_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)

        if path.suffix.lower() == ".xls":
            investigations.extend(_read_xls_records(path, source_updated_at))
            continue

        dataset = _read_dataset(path)
        project = _project_name(path)
        source_id = re.match(r"PSI-(\d+)", path.name, flags=re.IGNORECASE)
        id_prefix = f"PSI-{source_id.group(1)}" if source_id else path.stem

        for row_number, values in enumerate(dataset.to_dict(orient="records"), start=2):
            raw_data = {
                str(column).strip(): "" if pd.isna(value) else str(value).strip()
                for column, value in values.items()
            }
            if not any(raw_data.values()):
                continue

            title = _column_value(
                raw_data,
                "experiment title",
                "description",
                "fuel sample material",
                "sample material",
                "sample (fuel type)",
                "material",
                "fuel",
                "flame type",
                "sample type",
            )
            fuel = _column_value(
                raw_data, "fuel sample material", "sample material", "sample (fuel type)",
                "material", "fuel", "sample type",
            )

            oxygen = _numeric_field(raw_data, "oxygen", "o2", "xo2")
            oxygen_pct = oxygen[1] if oxygen else None
            if oxygen and oxygen_pct is not None and 0 < oxygen_pct <= 1:
                oxygen_pct *= 100

            flow = _numeric_field(raw_data, "flow", "velocity")
            pressure = _numeric_field(raw_data, "pressure", "approx p")
            pressure_bar = pressure[1] if pressure else None
            if pressure and "atm" in pressure[0].lower() and pressure_bar is not None:
                pressure_bar *= 1.01325

            investigations.append(
                Investigation(
                    id=f"{id_prefix}-{row_number:04d}",
                    name=title[1] if title else f"{project} record {row_number - 1}",
                    project=project,
                    safety_domain="Not classified",
                    fuel_type=fuel[1] if fuel else "Not specified",
                    oxygen_pct=oxygen_pct,
                    max_flow_velocity_cm_s=flow[1] if flow else None,
                    pressure_bar=pressure_bar,
                    source_file=path.name,
                    source_row=row_number,
                    raw_data=raw_data,
                    source_updated_at=source_updated_at,
                )
            )

    if not investigations:
        raise ValueError(f"No data rows found in NASA datasets under {DATASET_DIR}")
    return investigations


@router.get("/api/investigations", response_model=List[Investigation])
async def get_all_investigations():
    """Return records parsed from the NASA dataset files stored in the repository."""
    return load_canonical_data()
