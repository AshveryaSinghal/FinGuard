# FinGuard AI

FinGuard AI is a fraud-operations portfolio system built around a real
payment-fraud model and an explicitly rejected experimental URL model.

## Product workflow

1.  Browse imported IEEE-CIS transactions without exposing the
    historical fraud label.
2.  Run the saved V3 payment artifact against the exact precomputed
    feature contract.
3.  Map the probability through artifact-defined thresholds: Low,
    Monitor, Review, Automatic case.
4.  Review-tier and Automatic-case assessments create operational
    alerts.
5.  Analysts can acknowledge, dismiss, or escalate alerts.
    Automatic-case assessments open investigations immediately.
6.  Investigations support status changes, notes, and resolution.
7.  The separate Evaluation workspace replays held-out transactions and
    reveals the historical label only after inference.

## ML scope

Payment V3 uses the IEEE-CIS Fraud Detection dataset with a
chronological train/validation/test split. Global held-out metrics
stored in the training artifacts are ROC-AUC 0.9116 and PR-AUC 0.5629.
Payment inference is intentionally replay-only: the model scores
transactions present in the reproducible V3 feature store and does not
claim live raw-transaction feature computation.

URL Analysis uses an experimental PhiUSIIL lexical model. Automated
enforcement is disabled because independent legitimate-domain stress
tests failed. The project does not hide that failure or use a
hand-maintained allowlist to claim the model is fixed.

## Run locally

The commands below are for Windows PowerShell. Run them from the project
root unless stated otherwise.

### Prerequisites

Install Python 3.11 (or a compatible project version), Node.js, and npm.
Keep the trained artifacts in `artifacts/` and the V3 feature store in
its expected `data/` location. If these already exist, **do not retrain
the models**.

### 1. Open the project root

``` powershell
cd C:\path\to\finguard
```

Confirm that the folder contains `app`, `scripts`, `server`, `tests`,
`web`, and `requirements.txt`.

### 2. Create and activate the Python environment

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

``` powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

``` powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Initialize the operational database

``` powershell
python -m scripts.init_db
```

Expected output:

``` text
Database schema created. No fake or synthetic records were inserted.
```

When upgrading from an older FinGuard version, an old SQLite schema may
cause missing-table or missing-column errors. Rebuild only the local
operational database:

``` powershell
Remove-Item .\data\finguard.db
python -m scripts.init_db
```

Do not delete trained artifacts, raw datasets, or the feature store.

### 4. Import the real IEEE-CIS transaction catalog

``` powershell
python -m scripts.import_ieee
```

Verified final setup:

``` text
Imported 590,540 real IEEE-CIS rows into the operational database.
```

### 5. Build the feature store only if it is missing

Skip this step if the V3 feature store already exists.

``` powershell
python -m scripts.build_feature_store
```

Do not run `scripts.train_models` unless you intentionally want to
retrain and fully revalidate the model.

## Start the application

Run the three services in separate PowerShell terminals.

### Terminal 1 --- FastAPI backend

``` powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.api:app --reload --port 8000
```

### Terminal 2 --- Node/Express gateway

``` powershell
cd server
npm ci
npm run dev
```

### Terminal 3 --- React frontend

``` powershell
cd web
npm ci
npm run dev
```

Open the local Vite URL printed in the frontend terminal. Recommended
startup order: backend → gateway → frontend.

## Verification

Run backend tests from the project root with the virtual environment
active:

``` powershell
python -m pytest -q
```

Final verified result: **10 tests passed**.

Verify the production frontend build:

``` powershell
cd web
npm run build
```

Final verified result: **1,598 modules transformed and the production
build passed**. The final JavaScript bundle was approximately **219.54
kB**. React Router `"use client"` messages are dependency warnings and
do not indicate a failed build.

## Known limitations

-   Payment scoring requires a transaction already present in the V3
    feature store; it is not live raw-transaction inference.
-   Human-readable evidence is rule-generated context, not SHAP.
-   Shared-device analytics are transparent counts, not graph-based
    fraud-ring detection.
-   URL automation is disabled because the current model failed
    independent acceptance tests.
-   The portfolio deployment has no authentication or role-based access
    control.
-   Gateway rate limiting is in-memory and the FastAPI service must not
    be exposed publicly in production.
-   Batch analysis is synchronous; there is no queue or worker
    architecture.
-   Thresholds are static artifact-defined operating points and do not
    automatically recalibrate.
-   Drift monitoring is offline replay monitoring using assessed-score
    distributions; it is not connected to a live production stream.

See `MODEL_GOVERNANCE.md` and `DEPLOYMENT.md` for the full scope and
deployment constraints.

## Final workflow improvements

The alert queue preserves full analyst history through status filters
instead of hiding closed work. Evaluation samples are selected
server-side from the complete held-out period; outcome scenarios
(TP/TN/FP/FN) operate only on already-assessed records and still keep
the historical label hidden until explicit reveal.

The Models page includes lightweight offline replay drift monitoring. It
uses Population Stability Index over chronological assessed-score
distributions and explicitly reports when there is not enough data. This
is not presented as live production drift monitoring.

## Suggested demo flow

1.  Open **Overview** to show the operational state.
2.  Open **Transactions** and analyse an unassessed transaction.
3.  Show how probability maps to Low, Monitor, Review, or Automatic
    case.
4.  Open **Alerts** and demonstrate history filters and analyst actions.
5.  Escalate a Review alert into an investigation.
6.  Open **Investigations**, add a note, update status, and record a
    resolution.
7.  Open **Evaluation** and run a hidden-label scenario.
8.  Reveal the historical label only after inference.
9.  Demonstrate TP/TN/FP/FN sampling from already-assessed records.
10. Open **Models** to show artifact-defined thresholds and offline PSI
    monitoring.
11. Open **URL Analysis** and explain why automated enforcement remains
    disabled.

## Final verified status

``` text
590,540 real IEEE-CIS rows imported
10 backend tests passed
TypeScript compilation passed
Vite production build passed
```

FinGuard AI demonstrates model training, model governance, threshold
policy, leak-resistant evaluation, analyst operations, investigation
workflow, failure analysis, and honest deployment boundaries.
