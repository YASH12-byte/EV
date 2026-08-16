# Research Documentation — EV Market Growth Hybrid Forecasting

## 1. Introduction

Electric mobility is reshaping transportation, energy demand, and industrial policy. Accurate forecasting of EV market growth is essential for charging infrastructure planning, grid investment, OEM production scheduling, and subsidy design. This project proposes a **hybrid CNN-LSTM-Attention** forecasting framework enhanced with explainable AI, federated learning, and physics-informed constraints.

## 2. Current Scenario

Global EV adoption is accelerating, yet growth is uneven across regions due to policy incentives, battery costs, charging availability, fuel prices, and grid readiness. Forecasting tools used by many agencies still rely on univariate statistical models that under-represent multi-driver nonlinear effects.

## 3. Importance of the Problem

Errors in EV demand forecasts cascade into under/over-built chargers, transformer overloads, stranded battery supply, and misallocated subsidies. A trustworthy, interpretable, privacy-aware forecasting system reduces these risks.

## 4. Real-World Applications

- Government EV policy impact simulation  
- OEM demand and production planning  
- Investor market-sizing and risk analysis  
- Charging network rollout prioritization  
- Utility transformer and feeder capacity planning  

## 5. Problem Statement

Develop a hybrid forecasting framework that captures spatial-temporal and nonlinear EV market dynamics, provides interpretable drivers, preserves multi-city data privacy, and respects battery/grid physical limits.

## 6. Existing Problem

Traditional ARIMA/SARIMA/Prophet and standalone ML models fail to jointly model sequential dependencies, exogenous shocks, interpretability, privacy, and physical feasibility.

## 7. Research Gap

Few end-to-end systems combine deep hybrid sequence learning + XAI + federated cross-city training + physics-informed constraints + a deployable decision dashboard.

## 8. Objectives

1. Hybrid CNN-LSTM-Attention model for spatial-temporal feature extraction  
2. Preprocessing, denoising, feature engineering, normalization  
3. SHAP / LIME / attention-based explainability  
4. Federated learning for decentralized training  
5. Physics-informed battery degradation and grid constraints  
6. Comparative evaluation against classical and ML baselines  

## 9. Literature Survey (Summary Table)

| Paper / Theme | Year | Algorithm | Dataset Type | Findings | Limitations | Gap |
|---|---|---|---|---|---|---|
| Hybrid CNN-LSTM traffic/energy papers | 2019–2023 | CNN-LSTM | Time-series sensors | Strong short-term accuracy | Limited XAI / privacy | No EV policy+grid physics |
| CNN-GRU load forecasting | 2020–2024 | CNN-GRU | Power load | Efficient temporal encoding | Weak spatial graphing | Not EV market multi-driver |
| Temporal Fusion / Transformer | 2021–2024 | Transformer | Multi-horizon series | Long-range dependency | Data hungry | Rarely physics-constrained |
| STGCN / STGT-CNN | 2018–2023 | Graph Conv | Road networks | Spatial dependency | Needs graph topology | Charging graph scarce |
| XGBoost/LightGBM/CatBoost EV studies | 2019–2025 | Boosting | Registrations | High tabular accuracy | No deep sequence memory | Limited interpretability depth |
| SHAP/LIME trustworthy AI | 2017–2024 | XAI | Tabular/DL | Local/global explanations | Approximation cost | Not coupled to FL+physics |
| Flower / TFF federated learning | 2019–2024 | FedAvg | Cross-silo | Privacy-preserving training | Comm. overhead | Rare in EV market apps |
| Physics-Informed NN | 2019–2024 | PINN/regularizers | Physical systems | Constraint satisfaction | Soft penalties only | Sparse EV market use |

### Representative IEEE-style references (expand in final report)

[1] S. Hochreiter and J. Schmidhuber, “Long Short-Term Memory,” *Neural Computation*, 1997.  
[2] A. Vaswani et al., “Attention Is All You Need,” *NeurIPS*, 2017.  
[3] T. Chen and C. Guestrin, “XGBoost,” *KDD*, 2016.  
[4] S. M. Lundberg and S.-I. Lee, “A Unified Approach to Interpreting Model Predictions (SHAP),” *NeurIPS*, 2017.  
[5] M. T. Ribeiro et al., “Why Should I Trust You? (LIME),” *KDD*, 2016.  
[6] B. McMahan et al., “Communication-Efficient Learning of Deep Networks from Decentralized Data,” *AISTATS*, 2017.  
[7] M. Raissi et al., “Physics-Informed Neural Networks,” *J. Comput. Phys.*, 2019.  
[8] B. Yu et al., “Spatio-Temporal Graph Convolutional Networks,” *IJCAI*, 2018.  
[9] IEA, “Global EV Outlook,” International Energy Agency (annual).  
[10] Flower Labs, “Flower: A Friendly Federated Learning Framework,” 2020–.

## 10. Methodology

1. Collect/generate multi-region monthly EV indicators  
2. Clean, denoise, engineer lags/seasonality features  
3. Train baselines + proposed hybrid model  
4. Apply physics-informed penalties / post-process bounds  
5. Explain predictions via SHAP/LIME/feature insights  
6. Simulate FedAvg across regions  
7. Deploy Flask API + interactive dashboard  

### Mathematical sketch

Let \( x_{t} \in \mathbb{R}^{d} \) be feature vector at month \( t \).  
Sequence window \( X_{t} = [x_{t-L+1},\ldots,x_{t}] \).  
CNN extracts local motifs: \( H = \mathrm{CNN}(X_{t}) \).  
LSTM encodes temporal state: \( S = \mathrm{LSTM}(H) \).  
Attention aggregates: \( c = \sum_{i} \alpha_{i} S_{i} \).  
Forecast: \( \hat{y}_{t+1} = f(c) \).  
Physics-informed objective:
\[
\mathcal{L} = \mathrm{MSE}(y,\hat{y}) + \lambda_b \mathcal{L}_{batt} + \lambda_g \mathcal{L}_{grid} + \lambda_c \mathcal{L}_{charge}
\]

## 11. Proposed System

Web dashboard + JWT auth + REST prediction APIs + hybrid model service + XAI panel + admin analytics.

## 12. Existing System

Univariate statistical dashboards or spreadsheet forecasts without deep hybrid learning, privacy federation, or constraint-aware outputs.

## 13. Advantages

Higher accuracy potential, interpretable drivers, privacy-preserving multi-city learning, physically plausible forecasts, deployable UI for viva/demo.

## 14. Future Scope

Real IEA/Open Charge Map ingestion, STGCN charger-graph module, secure aggregation in Flower production, uncertainty intervals, mobile app, multimodal policy text features.

## 15. Conclusion

The project delivers a complete research-oriented BE system uniting hybrid deep forecasting, explainability, federated learning concepts, and physics-informed constraints for EV market growth analytics.
