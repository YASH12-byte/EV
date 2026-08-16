# IEEE-style Paper Draft Outline

**Title:** Hybrid CNN-LSTM-Attention Forecasting of Electric Vehicle Market Growth with Explainable and Physics-Informed Constraints

## Abstract
This paper presents a hybrid deep learning framework for EV market growth forecasting that integrates convolutional and recurrent temporal modeling with attention, explainable AI, federated cross-region learning, and physics-informed feasibility constraints. Experimental comparisons against ARIMA, Prophet, tree ensembles, and deep baselines demonstrate improved error metrics and actionable interpretability for stakeholders.

## I. Introduction
Motivation, contribution list (hybrid architecture, XAI, FedAvg, physics constraints, deployable system).

## II. Related Work
CNN-LSTM, Transformers, STGCN, boosting regressors, SHAP/LIME, federated learning, PINNs.

## III. Problem Formulation
Multi-region monthly forecasting with exogenous economic, policy, infrastructure, and grid variables.

## IV. Proposed Methodology
A. Data and preprocessing  
B. Hybrid CNN-LSTM-Attention  
C. Physics-informed loss / post-processing  
D. Federated FedAvg across cities  
E. Explainability module  

## V. System Implementation
Flask REST API, JWT auth, SQLite, interactive dashboard.

## VI. Experimental Results
MAE/MSE/RMSE/MAPE/R² tables, ablation (w/ and w/o attention/physics), latency.

## VII. Discussion
Policy sensitivity, infrastructure elasticity, limitations.

## VIII. Conclusion and Future Work

## References
Use IEEE numbered format from `docs/research/RESEARCH_DOCUMENT.md`.
