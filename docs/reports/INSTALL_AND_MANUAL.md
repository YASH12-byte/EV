# Installation & User Manual

## Installation Guide

1. Install Python 3.10+ and Git  
2. `cd EV-Market-Growth-Prediction`  
3. Create venv and activate  
4. `pip install -r requirements.txt`  
5. `python scripts/generate_dataset.py`  
6. (Optional) `python -m ml.training.train_all --fast`  
7. `python run.py`  
8. Open http://127.0.0.1:5000  

### Notes on heavy packages

TensorFlow, Prophet, CatBoost, and SHAP can take time to install on Windows. If a package fails, the app still runs with heuristic fallbacks and demo comparison metrics.

Minimal install for UI demo:

```bash
pip install flask flask-cors flask-jwt-extended flask-sqlalchemy werkzeug python-dotenv numpy pandas scikit-learn joblib
```

## User Manual

### Register / Login
1. Open `/register`, create account (animated signup UI).  
2. Or login at `/login`.  
3. Admin demo: `admin@evforecast.edu` / `Admin@123`.  

### Prediction
1. Go to **Prediction**.  
2. Choose region and adjust drivers (stations, battery cost, policy…).  
3. Click **Predict** to view forecast + top XAI drivers.  

### Dashboard
View history/forecast Plotly chart, feature importance, RMSE comparison, charging demand.

### Admin
View users, prediction logs, and counts (admin JWT required).

## Testing Checklist

- [ ] Home page loads national chart  
- [ ] Register creates user and redirects to dashboard  
- [ ] Login rejects bad password  
- [ ] Prediction returns numeric forecast  
- [ ] Comparison table renders  
- [ ] Admin pages blocked for non-admin  
- [ ] Dataset summary API returns rows/regions  

## PPT Outline (25–30 slides)

1 Title  
2 Team/Guide  
3 Abstract  
4 Introduction  
5 Current Scenario  
6 Problem Statement  
7 Objectives  
8 Literature Survey  
9 Research Gap  
10 Dataset  
11 Preprocessing  
12 Proposed Architecture  
13 CNN block  
14 LSTM + Attention  
15 Physics-informed constraints  
16 Federated learning  
17 Explainable AI  
18 System architecture  
19 Database / ER  
20 Website modules  
21 Implementation screenshots  
22 Results & comparison  
23 Advantages  
24 Limitations  
25 Future scope  
26 Conclusion  
27 References  
28 Demo / Q&A  

## Project Report Skeleton (100+ pages)

Expand each research section in `RESEARCH_DOCUMENT.md` with figures, full literature table (12–20 papers), algorithm pseudocode, screenshots, testing tables, Gantt chart, and IEEE references.
