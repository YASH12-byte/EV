"""
EV Market Growth Prediction — Project Configuration
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models" / "saved"
SECRET_KEY = os.getenv("SECRET_KEY", "ev-market-hybrid-ml-secret-key-2026")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ev-jwt-secret-key-change-in-prod")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'backend' / 'ev_market.db'}")

# Model hyperparameters
SEQUENCE_LENGTH = 12  # months lookback
FORECAST_HORIZON = 6  # months ahead
TEST_RATIO = 0.2
VAL_RATIO = 0.1
RANDOM_SEED = 42

FEATURE_COLUMNS = [
    "ev_sales",
    "charging_stations",
    "battery_cost",
    "electricity_price",
    "fuel_price",
    "gdp_index",
    "population",
    "carbon_emission",
    "gov_policy_index",
    "grid_capacity",
    "battery_degradation_index",
]

TARGET_COLUMN = "ev_sales"

CNN_FILTERS = [64, 128]
LSTM_UNITS = 128
ATTENTION_UNITS = 64
DROPOUT = 0.3
LEARNING_RATE = 1e-3
EPOCHS = 50
BATCH_SIZE = 32

# Physics-informed weights
PHYSICS_LAMBDA_BATTERY = 0.05
PHYSICS_LAMBDA_GRID = 0.08
PHYSICS_LAMBDA_CHARGE = 0.05
