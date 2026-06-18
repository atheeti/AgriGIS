# AgriGIS — Crop Health Intelligence

Real-time crop health analysis using **Google Earth Engine** + **Sentinel-2** satellite imagery.

```
AgriGIS/
├── backend/          ← FastAPI + GEE Python API
│   ├── main.py           App entry point
│   ├── gee_auth.py       GEE service account auth
│   ├── indices.py        All 11 index calculations
│   ├── schemas.py        Request / response models
│   ├── requirements.txt  Python dependencies
│   ├── .env.example      Template — copy to .env
│   └── service_account.json  ← YOU ADD THIS (see step 4)
│
└── frontend/         ← Leaflet.js + Chart.js (no GEE code)
    ├── index.html
    ├── css/style.css
    └── js/
        ├── config.js     Index display config
        ├── map.js        Leaflet + Google Satellite + Nominatim
        ├── draw.js       Drawing tools + Turf.js area
        ├── api.js        Calls FastAPI backend
        └── ui.js         Results, legend, histogram, PDF
```

---

## One-Time GCP Setup

### 1 — Create a Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click **New Project** → give it a name → note the **Project ID** (e.g. `my-agrigis-app`)

### 2 — Enable Earth Engine API
1. In your project: **APIs & Services → Library**
2. Search `Earth Engine` → click **Earth Engine API** → **Enable**

### 3 — Create a Service Account
1. **IAM & Admin → Service Accounts → Create Service Account**
2. Name: `agrigis-sa` (or any name)
3. Role: **Earth Engine Resource Viewer**
4. Click the service account → **Keys** tab → **Add Key → JSON**
5. Save the downloaded file as **`backend/service_account.json`**

### 4 — Register your project in Earth Engine
Go to https://code.earthengine.google.com/register and register your GCP project.
(Takes a few seconds to a few minutes.)

---

## Running the App

### Step 1 — Set up the backend

```bash
# Open a terminal in VS Code (Ctrl+`)
cd backend

# Create a Python virtual environment
python -m venv venv

# Activate it
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Mac / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2 — Configure credentials

```bash
# Copy the template
cp .env.example .env

# Open .env and fill in your values:
# GEE_PROJECT_ID=your-gcp-project-id
# GEE_SERVICE_ACCOUNT_KEY=service_account.json
```

Your `backend/.env` should look like:
```
GEE_PROJECT_ID=my-agrigis-app
GEE_SERVICE_ACCOUNT_EMAIL=agrigis-sa@my-agrigis-app.iam.gserviceaccount.com
GEE_SERVICE_ACCOUNT_KEY=service_account.json
```

*(The email can be left blank — it will be read from service_account.json automatically.)*

### Step 3 — Start the backend

```bash
# Make sure you're in the backend/ folder with venv active
uvicorn main:app --reload --port 8000
```

You should see:
```
✓ Google Earth Engine initialized successfully
Open http://localhost:8000 in your browser
```

### Step 4 — Open the dashboard

Open your browser and go to:
```
http://localhost:8000
```

The backend serves the frontend automatically — no Live Server needed.

---

## Using the Dashboard

1. **Search** a location (village, district, coordinates)
2. **Draw** your field using Rectangle, Polygon, Circle, or Freehand
3. **Select** a spectral index from the 11 available
4. Choose a **date range** and **max cloud cover**
5. Click **Run on Earth Engine**
6. View the **classified map overlay**, statistics, and histogram
7. **Download** a PDF report or export the plot as GeoJSON

---

## Supported Indices

| Index  | Full Name                                  | What it measures |
|--------|--------------------------------------------|------------------|
| NDVI   | Normalized Difference Vegetation Index     | Vegetation density & health |
| NDMI   | Normalized Difference Moisture Index       | Canopy moisture content |
| EVI    | Enhanced Vegetation Index                  | Vegetation with atmospheric correction |
| MDWI   | Modified Difference Water Index            | Water bodies & wet areas |
| SAVI   | Soil Adjusted Vegetation Index             | Vegetation on bare/sparse soils |
| GNDVI  | Green NDVI                                 | Chlorophyll content |
| GCI    | Green Chlorophyll Index                    | Chlorophyll concentration |
| SIPI   | Structure Insensitive Pigment Index        | Carotenoid:Chlorophyll ratio |
| NBR    | Normalized Burn Ratio                      | Burn severity |
| MGRVI  | Modified Green Red Vegetation Index        | Biomass (visible bands) |
| NDWI   | Normalized Difference Water Index          | Surface water |

---

## API Reference

| Method | Endpoint          | Description |
|--------|-------------------|-------------|
| GET    | `/api/health`     | Backend + GEE status |
| GET    | `/api/indices`    | List of supported indices |
| POST   | `/api/calculate`  | Run index analysis |
| GET    | `/api/docs`       | Swagger UI (auto-generated) |

**POST /api/calculate — request body:**
```json
{
  "index":     "NDVI",
  "geometry":  { "type": "Polygon", "coordinates": [[[lon,lat], ...]] },
  "days_back": 30,
  "max_cloud": 20
}
```

**Response:**
```json
{
  "mean": 0.6823,
  "min":  0.2341,
  "max":  0.8912,
  "std":  0.1124,
  "scene_date":  "12 Jun 2026",
  "tile_url":    "https://earthengine.googleapis.com/...",
  "histogram":   [{"center": -0.185, "count": 12}, ...],
  "image_count": 4
}
```

---

## Troubleshooting

**"Backend Offline" in the dashboard**
→ The FastAPI server is not running. Run `uvicorn main:app --reload` in the `backend/` folder.

**"GEE not ready" after backend starts**
→ Check the terminal for error messages. Common causes:
  - `.env` file not found or missing `GEE_PROJECT_ID`
  - `service_account.json` not in `backend/`
  - Earth Engine API not enabled in GCP
  - Project not registered at earthengine.google.com

**"No imagery found" when calculating**
→ Try a wider date range (60 or 90 days) or increase the cloud cover limit.

**PowerShell execution policy error**
→ Run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
