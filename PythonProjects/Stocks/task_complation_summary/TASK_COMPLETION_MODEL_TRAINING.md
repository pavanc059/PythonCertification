# Task Completion: Ensemble Model Training (CLI + Dashboard Button)

**Status:** Completed ✅
**Date:** 2026-06-30

## Files
- `stockiq/models/ensemble/trainer.py` — New reusable trainer: `train_and_cache_ensemble()` builds a real feature matrix across tickers, fits the ensemble, and caches it. Returns a `TrainingResult`.
- `train_model.py` — New project-root CLI to train and cache the model (`--tickers`, `--lookback`, `--estimators`, `--max-depth`). ASCII-safe console output for Windows.
- `stockiq/ui/dashboards/daily_brief.py` — Added `_render_train_model_button()` (in-app "Train prediction model" button), `_reset_predictor_cache()`, and `_cache_clear_predictions()`. Fixed stdlib-logger calls that used structlog-style kwargs.
- `stockiq/models/ensemble/predictor.py` — Switched module logger from stdlib `logging` to `structlog` (root-cause fix for prediction loading failures at INFO log level); made SHAP explainer initialization in `train()` and `load_from_cache()` resilient so a broken torch/SHAP install no longer blocks training or prediction.

## What Was Implemented
A complete path to populate the trained-model cache so the Daily Market Brief shows live predictions instead of sample data:
- **CLI:** `python train_model.py --tickers AAPL MSFT NVDA --lookback 365`
- **In-app:** a "🛠️ Train prediction model" button appears under the predictions panel whenever sample data is being shown; it trains on live data, clears caches, and reruns to display real forecasts.

Both routes call the shared `train_and_cache_ensemble()`, which fetches real yfinance feature data, aligns common feature columns across tickers, drops NaN/inf rows, trains RandomForest + GradientBoosting + XGBoost, and caches under `model:ensemble:predictor` (24h TTL).

## Two real bugs fixed along the way
1. **Predictions silently fell back to sample data** because `predictor.py` used a stdlib logger with structlog-style keyword args; at INFO level those calls raised `TypeError` inside `load_from_cache`, killing model loading. Fixed by switching to `structlog`.
2. **Model loading/training crashed** on this machine with `WinError 1114` (torch `c10.dll` init failure) when initializing the SHAP explainer. SHAP is explainability-only, so its initialization is now wrapped in try/except and degrades to `shap_explainer = None`; `_calculate_shap_values` already handled that case.

## Tests
Verified end-to-end (no automated unit tests added; none requested):
- CLI training: trained on 1092 samples / 64 features, R² 0.88, model cached, exit 0.
- Dashboard path with INFO logging: `_real_prediction('AAPL')` returns a real prediction (`is_sample: False`); `_fetch_predictions(['AAPL','MSFT','NVDA'])` returns 3 real predictions.
- `get_diagnostics` clean on all four files.

## Requirements
Supports Requirement 4.4 (daily predictions with confidence) by making the predictions real rather than mock.

## Notes
- Predictions are most useful once a broader/representative training universe is used; the default set is small for speed.
- The torch DLL issue on this machine only affected SHAP explainability; feature-importance factors will be empty until torch is repaired, but predictions, confidence, and ranges are fully functional.
- Trained model TTL is 24h; rerun training (CLI or button) to refresh.
