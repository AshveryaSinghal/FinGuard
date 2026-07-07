# Deployment

## Required runtime assets
The repository includes the trained IEEE-CIS V3 payment artifacts in `artifacts/`. The large replay datasets/feature store are intentionally not duplicated in the application image. Before starting payment replay, provide:

- `data/processed/v3_model_features.parquet`
- imported SQLite database or the raw IEEE-CIS files needed by the build/import scripts

The URL engine is intentionally marked **experimental/rejected**. Do not enable automated URL decisions until a replacement artifact passes the acceptance suite.

## Local one-command containers

```bash
docker compose up --build
```

Frontend: `http://localhost:5173`  
Gateway: `http://localhost:3000`  
FastAPI docs: `http://localhost:8000/docs`

## Production topology
Deploy the three containers behind one HTTPS reverse proxy. Do not expose port 8000 publicly; route browser traffic only through the gateway. Set explicit CORS origins and add authentication before any non-portfolio use.

## Known deployment limits
- SQLite is single-instance demo storage; use PostgreSQL for multi-instance deployment.
- Gateway rate limiting is in-memory; use a shared store for horizontal scaling.
- Batch analysis is synchronous.
- Payment scoring is historical replay, not raw live-transaction inference.
