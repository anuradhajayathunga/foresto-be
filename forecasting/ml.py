# forecasting/ml.py
import os
import joblib
from django.conf import settings

_MODEL = None

def get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    path = getattr(settings, "FORECAST_MODEL_PATH", "")
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Forecast model not found: {path}")

    _MODEL = joblib.load(path)  # requires xgboost installed
    return _MODEL
