"""
AgriGIS Backend  |  gee_auth.py
──────────────────────────────────────────────────────────────
Google Earth Engine authentication using a Service Account.

HOW TO SET UP (one-time):
1. Go to https://console.cloud.google.com
2. Create (or select) a project  →  note the Project ID
3. Enable "Earth Engine API" in APIs & Services → Library
4. Go to IAM & Admin → Service Accounts → Create Service Account
   - Name: agrigis-sa  (any name)
   - Role: Earth Engine Resource Viewer
5. Click the service account → Keys tab → Add Key → JSON
6. Save the downloaded file as  backend/service_account.json
7. Register your GCP project in Earth Engine:
   https://code.earthengine.google.com/register
8. Fill in backend/.env  (see .env.example)
"""

import ee
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()          # reads backend/.env
logger = logging.getLogger("agrigis.gee_auth")
_ready = False


def initialize() -> None:
    """
    Authenticate and initialise the Earth Engine Python client.
    Called once when the FastAPI server starts (see main.py lifespan).

    Priority:
      1. Service account JSON (recommended for production)
      2. Application Default Credentials (handy during local dev with gcloud)
    """
    global _ready

    project_id  = os.getenv("GEE_PROJECT_ID", "").strip()
    sa_email    = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL", "").strip()
    sa_key_file = os.getenv("GEE_SERVICE_ACCOUNT_KEY", "service_account.json").strip()

    if not project_id:
        raise EnvironmentError(
            "GEE_PROJECT_ID is not set in backend/.env\n"
            "Add:  GEE_PROJECT_ID=your-gcp-project-id"
        )

    # Resolve relative path relative to this file's directory
    if not os.path.isabs(sa_key_file):
        sa_key_file = os.path.join(os.path.dirname(__file__), sa_key_file)

    # ── Option 1: Service Account ──────────────────────────────
    if os.path.exists(sa_key_file):
        # Read email from .env; fall back to reading it from the JSON file
        if not sa_email:
            with open(sa_key_file) as fh:
                sa_info   = json.load(fh)
                sa_email  = sa_info.get("client_email", "")
            if not sa_email:
                raise EnvironmentError("client_email not found in service_account.json")

        logger.info(f"Authenticating via service account: {sa_email}")
        credentials = ee.ServiceAccountCredentials(
            email=sa_email,
            key_file=sa_key_file,
        )
        ee.Initialize(credentials, project=project_id)

    # ── Option 2: Application Default Credentials ──────────────
    else:
        logger.warning(
            "service_account.json not found — trying Application Default Credentials.\n"
            "Run:  gcloud auth application-default login"
        )
        ee.Initialize(project=project_id)

    _ready = True
    logger.info(f"GEE initialised  ·  project: {project_id}")


def is_ready() -> bool:
    """Returns True if ee.Initialize() has succeeded."""
    return _ready
