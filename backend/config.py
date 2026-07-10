import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PORTAL_ROOT = BASE_DIR.parent
MADHU_ROOT = PORTAL_ROOT.parent

# Prefer local .env, then fall back to dataops-copilot shared credentials
load_dotenv(PORTAL_ROOT / ".env")
load_dotenv(MADHU_ROOT / "dataops-copilot" / ".env")

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "").strip()
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "").strip()
DATABRICKS_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
DATABRICKS_CATALOG = os.environ.get("DATABRICKS_CATALOG", "workspace").strip()
DATABRICKS_SCHEMA = os.environ.get("DATABRICKS_SCHEMA", "dataops_copilot").strip()
USE_DATABRICKS = os.environ.get("USE_DATABRICKS", "true").lower() == "true"

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
PORT = int(os.environ.get("PORT", "5001"))
