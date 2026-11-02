# EpiSense: Production Deployment & Verification Report

**Document Authority:** Lead AI & Platform Deployment Engineering  
**Deployment Date:** November 2, 2026  
**System Clock / Reference Date:** `2026-11-02T07:45:00+05:30` (Asia/Kolkata)  
**Workspace:** `C:\Users\ajaya\Desktop\NLP`  
**GitHub Repository:** [https://github.com/Boomikav/episense](https://github.com/Boomikav/episense) (Branch: `main`)  

---

## 1. Executive Deployment Ledger & Status Classification

In accordance with strict operational auditing rules, all system components are categorized below:

| Component | Target Provider | Operational Status | Verification Evidence / Action Required |
| :--- | :--- | :--- | :--- |
| **Frontend Web App** | Vercel | **Successfully Deployed & Verified** | Public HTTPS loads with HTTP 200 at `https://frontend-navy-eta-74.vercel.app`; 0 localhost references in JS bundle. |
| **SPA Route Handling** | Vercel (`vercel.json`) | **Successfully Deployed & Verified** | Direct navigation to `/alerts`, `/forecasting`, `/map`, `/workbench` returns HTTP 200 with `index.html`. |
| **GitHub Repository** | GitHub (`Boomikav/episense`) | **Successfully Deployed & Synchronized** | Repository initialized, pushed to `main`; `render.yaml`, `Dockerfile`, `requirements.txt` (with `pymupdf`), and all datasets tracked. |
| **Backend Code & Persistence** | Codebase (`src/episense`) | **Ready & Verified** | `SurveillanceDatabase` copy-on-first-boot safeguard verified; WAL mode active; `EPISENSE_DB_PATH` integrated across panel and data sufficiency modules. |
| **CORS Middleware** | FastAPI (`app.py`) | **Ready & Verified** | Configured for exact origin `https://frontend-navy-eta-74.vercel.app` + regex `r"https://.*\.vercel\.app"`; OPTIONS preflight returns HTTP 200. |
| **Backend Test Suites** | Local Python 3.11 | **441 Passed / 0 Failed** | All 441 unit and integration tests passing cleanly; 21 frontend Vitest tests passing cleanly. |
| **Permanent Render Web Service** | Render Cloud (`render.yaml`) | **Awaiting Manual User Approval** | Render requires user OAuth connection and payment method authorization for the Starter Plan ($7/mo) + Persistent Disk ($0.25/mo). |
| **Temporary Backend Gateway** | localhost.run (`lhr.life`) | **Transitional Fallback (Active)** | Active only while Render provisioning is pending. Must be decommissioned once Render is live. |

```
+---------------------------------------------------------------------------------------------------+
| ENDPOINT DIRECTORY                                                                                |
+---------------------------------------------------------------------------------------------------+
| 1. Production Vercel Frontend:       https://frontend-navy-eta-74.vercel.app                      |
|    - Direct Deployment Alias:        https://frontend-ptd9t1x0x-ajayajay17at19-4269.vercel.app     |
|    - Status:                         ACTIVE & VERIFIED                                            |
|                                                                                                   |
| 2. GitHub Source Repository:         https://github.com/Boomikav/episense                         |
|    - Target Branch:                  main (latest commit: 38901da)                                |
|    - Status:                         SYNCHRONIZED                                                 |
|                                                                                                   |
| 3. Render Blueprint Deployment URL:  https://render.com/deploy?repo=https://github.com/Boomikav/episense |
|    - Target Service:                 episense-api (Web Service + 1GB Persistent Disk at /var/data)|
|    - Expected Domain:                https://episense-api.onrender.com (or user-chosen slug)      |
|    - Status:                         AWAITING USER AUTHORIZATION & PAYMENT APPROVAL               |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Render Deployment: Exact Manual Action Required

> [!IMPORTANT]
> **Render Account Authorization & Payment Approval Gate**  
> Render is an external third-party cloud provider. Automated CLI or API provisioning cannot proceed autonomously because:
> 1. Render requires OAuth authorization connecting your GitHub account (`Boomikav`) to your Render organization.
> 2. The persistent SQLite architecture requires a **Persistent Disk** mounted at `/var/data`. Render policy strictly restricts persistent disks to the **Starter Plan** ($7.00/month instance + $0.25/GB-month disk = **$7.25/month**). Persistent disks are not permitted on Render's Free tier.
> 3. Render requires a valid payment method on file to approve the blueprint.

### Exact User Instructions to Deploy on Render

1. Open your browser and navigate to the one-click blueprint deploy URL:  
   👉 **[https://render.com/deploy?repo=https://github.com/Boomikav/episense](https://render.com/deploy?repo=https://github.com/Boomikav/episense)**

2. Sign in or authenticate with your GitHub account: `Boomikav`.

3. Render will parse `render.yaml` and display the **Blueprint Specification**:
   - **Service Name:** `episense-api`
   - **Environment:** `Python 3.11`
   - **Plan:** `Starter` ($7/mo)
   - **Disk:** `episense-storage` (1 GB mounted at `/var/data`, $0.25/mo)
   - **Health Check:** `/api/v1/health`
   - **Environment Variables:** `PORT=10000`, `HOST=0.0.0.0`, `EPISENSE_DB_PATH=/var/data/surveillance_store.sqlite`, `CORS_ORIGINS=https://frontend-navy-eta-74.vercel.app,http://localhost:5173`

4. Click **"Apply"** (confirm payment/card if prompted by Render).

5. Render will initiate the build:
   - Installs pip packages from `requirements.txt` (including `fastapi`, `uvicorn`, `pymupdf`, `spacy`, `en_core_web_sm`, `en_core_sci_sm`).
   - Attaches the 1GB persistent volume to `/var/data`.
   - Starts the server with `python run_server.py`.
   - Health check will verify `GET /api/v1/health` and mark the service **Live**.

6. Once the status shows **Live**, copy your assigned service URL (e.g., `https://episense-api.onrender.com` or `https://episense-api-xxxx.onrender.com`).

---

## 3. Persistent SQLite Storage Safeguards

### 3.1 Persistence Architecture
- **Persistent Volume Mount:** `/var/data`
- **Database File:** `/var/data/surveillance_store.sqlite`
- **Environment Variable:** `EPISENSE_DB_PATH=/var/data/surveillance_store.sqlite`
- **WAL Mode:** Activated on every connection via `PRAGMA journal_mode=WAL;` and `PRAGMA foreign_keys=ON;`.
- **Concurrency & Locking:** Thread-local connections with 30.0s connection timeouts eliminate cross-thread locking under burst traffic.

### 3.2 Non-Destructive Copy-on-First-Boot Logic
The database initialization in [`src/episense/persistence/database.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/persistence/database.py#L37-L66) implements strict safeguards:
```python
seed_db = Path("data/surveillance_store.sqlite").resolve()
if seed_if_missing and not self.db_path.exists() and seed_db.exists() and self.db_path != seed_db:
    logger.info("Persistent DB not found at %s. Seeding from repository database...", self.db_path)
    shutil.copy2(str(seed_db), str(self.db_path))
    for ext in ("-wal", "-shm"):
        if (seed_ext := Path(str(seed_db) + ext)).exists():
            shutil.copy2(str(seed_ext), str(self.db_path) + ext)
elif self.db_path.exists():
    logger.info("Using existing persistent database at %s (%d bytes).", self.db_path, self.db_path.stat().st_size)
```
- **First Boot:** On a fresh disk, `/var/data/surveillance_store.sqlite` does not exist. The application copies the repository seed database (48.2 MB) containing all 1,781 historical documents, 2,422 fused events, 1,011 signals, and 11 forecasts.
- **Subsequent Restarts / Rebuilds:** The database file already exists. The application detects it and **NEVER overwrites** existing persistent data.

### 3.3 Dynamic Path Resolution Across Modules
All analytical and persistence components resolve the path dynamically from `EPISENSE_DB_PATH`:
- [`SurveillanceDatabase`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/persistence/database.py#L28)
- [`evaluate_eight_disease_sufficiency`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/surveillance/data_sufficiency.py#L165)
- [`DataSufficiencyProfiler`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/surveillance/data_sufficiency.py#L184)
- [`SurveillancePanelBuilder`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/surveillance/panel.py#L30)

---

## 4. Production CORS Configuration

The backend CORS implementation in [`src/episense/api/app.py`](file:///C:/Users/ajaya/Desktop/NLP/src/episense/api/app.py#L130-L150) supports both exact origins and regex pattern matching:

```python
env_cors = os.environ.get("CORS_ORIGINS")
if env_cors:
    cors_origins = [o.strip() for o in env_cors.split(",") if o.strip()]
    allow_origin_regex = r"https://.*\.vercel\.app"
elif cfg.cors_origins:
    cors_origins = cfg.cors_origins
    allow_origin_regex = None if "*" in cors_origins else r"https://.*\.vercel\.app"
else:
    cors_origins = ["*"]
    allow_origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Verified Preflight & Credentials Behavior
- **Browser Origin:** `https://frontend-navy-eta-74.vercel.app`
- **Preflight Check:** `OPTIONS /api/v1/health` returns `HTTP 200 OK`.
- **Response Headers:**
  - `Access-Control-Allow-Origin: https://frontend-navy-eta-74.vercel.app`
  - `Access-Control-Allow-Credentials: true`
  - `Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT`
- **Preview & Staging Domains:** Handled safely via `allow_origin_regex=r"https://.*\.vercel\.app"` without requiring wildcard `*`.

---

## 5. Connecting Vercel to Render (Post-Deployment Step)

Once the Render service is Live and you have obtained its URL:

1. Update the environment variable on Vercel:
   ```bash
   cd frontend
   npx vercel env add VITE_API_BASE_URL production
   # When prompted for value: https://your-actual-render-url.onrender.com
   ```
   Or trigger a direct production build:
   ```bash
   cd frontend
   npx vercel deploy --prod --yes --build-env VITE_API_BASE_URL=https://your-actual-render-url.onrender.com
   ```

2. Confirm that the compiled JavaScript bundle (`frontend/dist/assets/index-*.js`) contains the new Render URL and zero references to `localhost` or `lhr.life`.

---

## 6. Scientific Safeguards & Eight-Disease Gating

The application maintains strict epidemiological qualification boundaries across all 8 canonical diseases:

| Pathogen | Observation Cadence | Historical Observations | Data Sufficiency Decision | Scientific Qualification |
| :--- | :--- | :--- | :--- | :--- |
| **Malaria** | Monthly (NCVBDC MMIS) | 32 consecutive months (Jan 2024–Aug 2026) | **SUFFICIENT** | **FORECAST_READY** (Negative Binomial & Seasonal Naive validated; holdout MASE 1.121) |
| **Dengue** | Annual / Weekly (OpenDengue + IDSP) | 29 annual + 83 district series | **SUFFICIENT (Retrospective)** | **EVALUATED_RETROSPECTIVELY** (Spatiotemporal Panel Poisson GLM across 7 focal states) |
| **Cholera** | Episodic Outbreak | 12 discrete bulletins | **INSUFFICIENT (Sparse)** | **BASELINE_ONLY** (Historical Reference Baseline, ML forecasting suppressed) |
| **Japanese Encephalitis** | Episodic Outbreak | 21 narrative mentions | **INSUFFICIENT (Narrative)** | **BASELINE_ONLY** (Event surveillance active; count autoregression suppressed) |
| **Kala-Azar** | Annual National | 5 annual observations | **INSUFFICIENT (N < 10)** | **INSUFFICIENT_HISTORICAL_DATA** (Numerical ML suppressed; historical baseline only) |
| **Leptospirosis** | Episodic Outbreak | 14 discrete bulletins | **INSUFFICIENT (Sparse)** | **BASELINE_ONLY** (Heuristic event fusion active; numerical forecasting suppressed) |
| **Measles** | Episodic Outbreak | 30 discrete bulletins | **INSUFFICIENT (Sparse)** | **BASELINE_ONLY** (Historical reference only; no continuous monthly series) |
| **Scrub Typhus** | Annual Clustered | 7 annual observations | **INSUFFICIENT (N < 10)** | **INSUFFICIENT_HISTORICAL_DATA** (Annual reference baseline; numerical ML suppressed) |

---

## 7. Verification Audit Summary

- **Local Backend Pytest:** `441 passed, 0 failed, 5 warnings in 147.63s`
- **Frontend Vitest:** `21 passed, 0 failed across 9 test files in 12.99s`
- **Frontend Vite Build:** `tsc -b && vite build` clean (0 errors, 290ms)
- **Vercel SPA Deployment:** `https://frontend-navy-eta-74.vercel.app` (HTTP 200 on all deep routes)
- **GitHub Repository State:** `https://github.com/Boomikav/episense` synced to `main` with all fixes
- **Pending Cloud Action:** User approval on Render to launch the persistent service and persistent disk
