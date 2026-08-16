# EVForecast — Predictive Analytics for Electric Vehicle Market Growth

**Hybrid Machine Learning + Time-Series** BE Computer Engineering major project.

Primary data source: **`DataSet.zip`** (Vahan-style registrations, transactions, revenue).  
No fabricated metrics — MAE / RMSE / MAPE / R² are computed from chronological test predictions.

---

## Quick Start (Real Dataset Pipeline)

```bash
cd EV-Market-Growth-Prediction
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows

pip install -r requirements.txt

# Place / extract DataSet.zip under data/raw/ (already supported path):
#   data/raw/DataSet/DataSet/...

python run_project.py          # inspect → clean → FE → train → XAI
python run.py                  # Flask app
```

Open **http://127.0.0.1:5000/login** (not Live Server HTTPS).

### Demo login
- Admin: `admin@evforecast.edu` / `Admin@123`

---

## Important: GitHub is not the website

https://github.com/YASH12-byte/EV shows **source code only** (README text / files).  
It does **not** run Flask. Do **not** upload a Windows `venv/` folder — hosting platforms install packages from `requirements-deploy.txt`.

### Deploy the live website (Render)

1. Push this repo to GitHub (already done).
2. On [Render](https://render.com): **New → Web Service** → connect `YASH12-byte/EV`.
3. Settings:
   - **Build command:** `pip install -r requirements-deploy.txt`
   - **Start command:** `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
   - **Python version:** `3.11.9` (see `runtime.txt`)
4. Deploy → open the `https://….onrender.com` URL (that is the real website).

Local `venv` stays on your PC only:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Dataset (from DataSet.zip)

### Register (annual + distributions)
| File | Role |
|------|------|
| `ev_yearwise_registration.csv` | **Primary target** — State, VehicleType, Year, Registrations |
| `registration_2010-2026.csv` | Nested `data`/`labels` lists → expanded carefully |
| `fuel_type_ev_data.csv` | Fuel-type distribution |
| `ev_emission_distribution.csv` | Emission standards |
| `ev_vehicle_class_distribution.csv` | Vehicle class |
| `top5_vehicle_makers_all_states.csv` | Makers |
| `dashboardcount_all_states.csv` | Totals with dict-string counts |

### Revenue / Transactions (monthly)
| Folder | Columns |
|--------|---------|
| `Revenue_fee_line_chart(2010-2026)/` | State, Year, Month, Revenue |
| `Transaction_data(2010_2026)/` | State, Year, Month, EV_Transactions |
| `top_transaction_rto(2010-26)/` | State, RTO_or_State, EV_Transactions |

**Not in zip (do not claim):** charging stations, battery health sensors, true geo deep learning.

---

## Commands

```bash
python src/data_inspection.py
python src/data_preprocessing.py
python src/eda.py
python src/feature_engineering.py
python src/train_all_real.py
python src/xai_shap.py
python src/xai_lime.py
python src/forecast.py
python run_project.py --serve
```

---

## Models & Evaluation

| Approach | Models |
|----------|--------|
| Annual registrations | Naive, ARIMA, Random Forest, XGBoost, CNN, LSTM, **CNN-LSTM** |
| Split | Chronological ~70/15/15 by year (no shuffle) |
| Metrics | MAE, RMSE, MAPE, R² — from test predictions only |
| Derived UI metric | `Approx Accuracy = 100 − MAPE` (clearly labeled) |

Best model by RMSE is reported honestly in `outputs/best_model.json`.  
CNN-LSTM remains the **proposed research model** even if a baseline wins on error.

Leakage controls:
- Scaler / encoders fit on **train years only**
- Lags use `shift(1)` (no current-target leakage)
- Monthly series not joined onto annual rows at mismatched frequency

---

## Key Outputs

```
outputs/
  data_profile.json / data_profile.csv
  cleaning_log.json
  final_results.csv
  model_comparison.png
  actual_vs_predicted.png
  future_forecast.png
  objective_achievement.md
  xai/shap_*.png, feature_importance.json
data/processed/
  ev_registrations_annual.csv
  ev_transactions_monthly.csv
  ev_revenue_monthly.csv
  features_*.csv
models/saved/
  random_forest.pkl, xgboost_model.pkl, arima_model.pkl
  cnn_model.keras, lstm_model.keras, cnn_lstm_model.keras
```

---

## Project Structure

```
EV-Market-Growth-Prediction/
├── data/raw/DataSet/     # Extracted DataSet.zip
├── data/processed/       # Cleaned forecasting tables
├── src/                  # Inspection → train → XAI → forecast
├── models/saved/         # Trained artifacts
├── outputs/              # Metrics, figures, XAI
├── backend/              # Flask API (wired to real processed data)
├── frontend/             # Login, dashboard, prediction UI
├── run_project.py        # End-to-end pipeline
└── run.py                # Web app
```

## Website

Login (cinematic) · Dashboard · Dataset · Prediction · Model Comparison · Research · Admin

Flask APIs prefer real `data/processed` + `outputs/metrics` when present.

---

## Research Objectives

See `outputs/objective_achievement.md` for mapping of Objectives 1–4 to implemented artifacts.
