# FlameSync

FlameSync is an experimental combustion-research dashboard for exploring NASA investigation data, comparing source records, ranking records against mission scenarios, estimating CFI-G burn time, and asking questions over indexed research documents.

> **Safety notice:** FlameSync is a research/demo application. Its model estimates and ranking scores are not certified or approved for operational fire-safety decisions.

## What the application does

- **Explorer** reads local CSV and XLS files from `data/raw_datasets` through the FastAPI backend. It exposes normalized fields alongside the original source-row values, filename, and row number.
- **Compare** lets users select up to four Explorer or Ranking records and compare their normalized fields and original columns. Missing values appear as `N/A`.
- **Ranking** sorts local records by keyword overlap with the mission scenario and constraints. The returned percentage is a term-match score, not a learned relevance probability or AI assessment.
- **Predict** estimates CFI-G experimental burn time from fuel type, oxygen fraction, chamber pressure, and mass flow. It displays the model's global feature importances and grouped validation measurements.
- **Assistant** retrieves excerpts from a local Chroma vector database built from PDFs placed in the local `data/docs` directory and the configured NASA web pages, then sends the excerpts and question to an OpenRouter chat model. Retrieved files and URLs are shown as sources.
- **Home** links mission cards to Ranking with the selected scenario prefilled, research-area cards to filtered Explorer results, and summary cards to Explorer. Research filters search for `flame` (Flammability), `sensor` (Detection), and `extinguish` (Suppression).

The app uses local datasets and an indexed document store; it does not fetch the raw investigation data from a live NASA API.

## Repository layout

```text
FlameSync/
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI route handlers
│   │   ├── schemas/             # Request and response models
│   │   └── services/            # Ranking, prediction, and validation logic
│   ├── flamesync_rf_model.pkl   # CFI-G burn-time Random Forest
│   └── requirements.txt
├── data/
│   ├── docs/                    # Local-only research PDFs for RAG (not included in the repository)
│   ├── raw_datasets/            # Local NASA PSI CSVs and DAFT XLS
│   └── vector_db/               # Persisted Chroma index for the Assistant
├── flamesync-frontend/
│   └── src/                     # React, TypeScript, and Tailwind UI
└── scripts/                     # Ingestion, validation, and ML scripts
```

## Requirements

- Python with `pip` and `venv`
- Node.js and npm
- Network access on first RAG setup so the embedding model and configured web pages can be downloaded
- An OpenRouter API key to generate Assistant answers

The serialized Random Forest was trained with scikit-learn 1.8.0. The backend requirements pin that version to avoid loading the artifact with a mismatched scikit-learn version.

## Local setup

Run commands from the project root unless specified otherwise.

### Backend

```powershell
cd C:\path\to\FlameSync\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create `FlameSync\.env` (the project-root `.env` file) and set:

```dotenv
OPENROUTER_API_KEY=your_key_here
```

Do not commit `.env` or share its contents. The key is needed for Assistant chat; the investigation and prediction routes do not need it.

Start the API from the backend directory:

```powershell
python -m uvicorn app.main:app --reload
```

The API listens at `http://127.0.0.1:8000`. Health check: `http://127.0.0.1:8000/api/health`. Interactive API docs are at `http://127.0.0.1:8000/docs`.

### Frontend

In another terminal:

```powershell
cd C:\path\to\FlameSync\flamesync-frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal. The current frontend API client uses `http://127.0.0.1:8000/api` as its backend base URL.

## API overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend health status |
| `GET` | `/api/investigations` | Parsed local dataset records |
| `POST` | `/api/rankings` | Rank local records by scenario/constraint keyword overlap |
| `GET` | `/api/predictions/validation` | Leave-one-day-out CFI-G validation summary and input ranges |
| `POST` | `/api/predictions/burn-time` | Predict burn time in seconds |
| `POST` | `/api/assistant/chat` | Retrieve indexed context and generate a cited answer |

Prediction request example:

```json
{
  "fuel_type": "ethane",
  "oxygen_concentration": 0.21,
  "chamber_pressure_bar": 1.0,
  "mass_flow_rate_mg_s": 1.0
}
```

Inputs must be within the ranges in the validation response. These ranges reflect the CFI-G training data, not a safe operating envelope. Supported fuel labels are `ethane`, `propane`, `30% butane`, `50% butane`, `30% ethane`, and `30% propane`.

The former `/api/predictions/spread-rate` path remains as a compatibility alias; it also returns burn-time predictions. Use `/api/predictions/burn-time` for new clients.

## Dataset and document workflows

### Investigation data

Place supported `.csv` or `.xls` source files in `data/raw_datasets`. The API reads them from disk when `/api/investigations` is requested. The current workspace has 11 unique files after excluding a byte-identical duplicate, producing approximately 1,330 records, including 771 DAFT sensor measurements. Counts change when source files change.

The parser preserves each source row in `raw_data`; normalized values such as oxygen, pressure, and flow are populated only when recognizable in the source columns. Not all files contain the same measurements.

### PDF and web RAG index

The `data/docs` directory and its PDFs are not included in the repository. Create `data/docs` locally and add any research PDFs you want indexed. The ingestion script also loads the NASA web pages listed in `scripts/ingest_documents.py`. From the project root, build/update the local Chroma store with:

```powershell
python scripts\ingest_documents.py
```

The Assistant opens the project-root `data/vector_db`, regardless of the backend's current working directory. Rebuilding an existing Chroma store may add repeated chunks; back up the index before changing ingestion behavior or rebuilding it.

## Prediction validation and retraining

The burn-time model is trained from `data/raw_datasets/PSI-159_Experimental table_CFI-G_Normal Flames.csv`. Validation holds out each complete experimental day in turn (`GroupKFold` / leave-one-day-out cross-validation), avoiding a random row split that could mix measurements from one day across training and test folds.

The current validation run covered 175 complete rows across 11 days and reported approximately:

- MAE: **33.2 seconds**
- RMSE: **50.1 seconds**
- R²: **0.386**
- Within ±10 seconds: **34.9%** of held-out rows

These are internal validation results on one dataset, not independent validation or safety certification. Retrain and print fresh validation metrics with:

```powershell
python scripts\train_model.py
```

The script evaluates using grouped folds, compares with a mean-prediction baseline, then refits on all complete rows and replaces `backend/flamesync_rf_model.pkl`.

## Frontend quality checks

```powershell
cd C:\path\to\FlameSync\flamesync-frontend
npm run build
npm run lint
```

## Important limitations

- Burn-time predictions are experimental estimates with substantial validation error. Do not use them to make real fire-safety decisions.
- Prediction input bounds are the observed training-data ranges, not safety limits or guarantees of model accuracy within those ranges.
- The displayed feature importance is global Random Forest importance, not an explanation for a particular prediction.
- Ranking currently uses explicit token overlap against source-row text. It is not semantic ranking and its percentage is not a probability.
- The Assistant's retrieved context depends on the local Chroma index being populated and on a working OpenRouter API key/network connection.
- NASA source files may have differing schemas, units, and completeness. Review source rows before interpreting normalized fields.
