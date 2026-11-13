# TrendScope — Earth System Trend Detective

NASA Space Apps Challenge monorepo.

## Team Workflow (No Direct Pushes to `main`)
1. Clone and sync Python environment:
   ```bash
   uv sync --frozen
   ```
2. Create or switch to your role branch:
   - `feat/data-fetch` — Data Engineer (`src/data/fetch.py`, `data/processed/`)
   - `feat/stats` — Statistics Lead (`src/stats/stats.py`)
   - `feat/web` — Web Developer (`src/web/`)
   - `feat/validation` — Validation & Presentation (`tests/test_stats.py`)
3. Run checks before opening a PR:
   ```bash
   uv run ruff check .
   uv run python scripts/validate_schema.py data/mock/results.mock.json
   uv run pytest -v
   ```

## Shared Contract
All pipeline outputs consumed by the frontend must validate against [`schemas/trend_result.schema.json`](schemas/trend_result.schema.json).
Mock data for immediate frontend development is in [`data/mock/results.mock.json`](data/mock/results.mock.json).

## Fetch NASA Data
```bash
uv run python -m src.data.fetch --region cairo --lat 30.0444 --lon 31.2357 --vars T2M PRECTOTCORR --start 2001 --end 2025
```
