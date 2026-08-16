# Objective Achievement Mapping

## Objective 1
Study existing ML and XAI techniques for EV market trend analysis and sales forecasting.

**Achievement:** Implemented and compared Naive, ARIMA, Random Forest, XGBoost (if available), CNN, LSTM, and Hybrid CNN-LSTM on real Vahan-style registration data. Added SHAP (primary) and LIME (secondary/tabular) explainability modules.

## Objective 2
Develop a Hybrid ML-Time-Series model for EV market growth prediction.

**Achievement:** Implemented Causal Conv1D → MaxPool → LSTM → Dense Hybrid CNN-LSTM for national annual EV registrations, with EarlyStopping and ReduceLROnPlateau.

## Objective 3
Improve forecasting accuracy using CNN, LSTM and advanced time-series techniques.

**Achievement:** Evaluated all models on a chronological test split using MAE, RMSE, MAPE, and R² computed from actual predictions (see `outputs/final_results.csv`). Best model is selected by lowest RMSE without fabricating scores. Approximate accuracy is reported only as `100 - MAPE` and labeled as derived.

## Objective 4
Extract temporal and state-level patterns from EV registration and transaction/revenue data and explain predictions using XAI.

**Achievement:** Built annual registration and monthly transaction/revenue processed datasets from DataSet.zip; produced state-wise EDA figures; SHAP feature rankings for the tabular model; forecast endpoints for registrations.

## Dataset limitations honestly reported
- No charging-station columns in DataSet.zip.
- `registration_2010-2026.csv` uses nested list encodings that were expanded carefully without inventing values.
- Monthly revenue/transactions are not naively joined onto annual registration rows at mismatched frequency.
