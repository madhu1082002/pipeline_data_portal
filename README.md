# Pipeline Data Portal

A data entry application for managing pipeline metadata in the **same Databricks database** used by [DataOps Copilot](../dataops-copilot/).

Changes made here are written directly to `workspace.dataops_copilot` tables and appear in DataOps Copilot when you refresh its dashboard.

## Shared Database

Both apps read and write the same three Databricks Delta tables:

| Table | Used by DataOps Copilot for |
|-------|----------------------------|
| `pipeline_runs` | Pipeline Status Assistant |
| `failure_logs` | Failure Diagnosis Assistant |
| `cluster_metrics` | Optimization Assistant |

```
Pipeline Data Portal (port 5001)  ──write──►  Databricks Tables  ◄──read──  DataOps Copilot (port 5000)
```

## Quick Start

```powershell
cd pipeline-portal
py -m pip install -r requirements.txt
cd backend
py app.py
```

Open **http://localhost:5001** in your browser.

The portal automatically loads Databricks credentials from:
1. `pipeline-portal/.env` (if present)
2. `dataops-copilot/.env` (fallback — no duplicate config needed)

## Run Both Apps Together

Terminal 1 — DataOps Copilot (read + AI chat):
```powershell
cd dataops-copilot\backend
py app.py
```

Terminal 2 — Pipeline Data Portal (data entry):
```powershell
cd pipeline-portal\backend
py app.py
```

After adding or editing data in the portal, refresh the DataOps Copilot dashboard at http://localhost:5000 to see the updated pipeline status, failures, and cluster metrics.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/databricks/status` | Database connection status |
| GET/POST | `/pipelines` | List or create pipeline runs |
| PUT/DELETE | `/pipelines/<name>` | Update or delete a pipeline |
| GET/POST | `/failures` | List or create failure logs |
| PUT/DELETE | `/failures/<name>?failure_time=...` | Update or delete a failure |
| GET/POST | `/clusters` | List or create cluster metrics |
| PUT/DELETE | `/clusters/<id>` | Update or delete a cluster |

## Project Structure

```
pipeline-portal/
├── backend/
│   ├── app.py              # Flask API (CRUD)
│   ├── config.py           # Shared Databricks config
│   └── services/
│       └── databricks_service.py
├── frontend/               # Data entry UI
├── requirements.txt
└── README.md
```
