"""
FastAPI Backend for Hybrid Demand Model
Restaurant demand prediction API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add rules directory to path
sys.path.append(str(Path(__file__).parent / "rules"))
from rule_engine import apply_rules

app = FastAPI(
    title="Restaurant Demand Prediction API",
    description="Hybrid ML + Rule-based demand forecasting",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained model
MODEL_PATH = Path(__file__).parent / "models" / "random_forest_model.pkl"
try:
    model = joblib.load(MODEL_PATH)
    print(f"✅ Model loaded from {MODEL_PATH}")
except Exception as e:
    print(f"⚠️ Warning: Could not load model - {e}")
    model = None


class PredictionRequest(BaseModel):
    """Input features for demand prediction"""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    menu_category: int = Field(..., ge=0, le=4, description="Menu category (0-4)")
    is_festival: int = Field(default=0, ge=0, le=1, description="Is it a festival day? (0 or 1)")
    festival_type: int = Field(default=2, ge=0, le=4, description="Festival type encoded (0-4, 2=None)")
    is_poya_day: int = Field(default=0, ge=0, le=1, description="Is it a Poya day? (0 or 1)")
    temperature_avg: float = Field(..., ge=15, le=40, description="Average temperature (°C)")
    rainfall_mm: float = Field(default=0.0, ge=0, description="Rainfall in mm")
    is_heavy_rain: int = Field(default=0, ge=0, le=1, description="Is there heavy rain? (0 or 1)")
    supplier_invoice_qty: int = Field(..., ge=0, description="Supplier invoice quantity")
    is_weekend: int = Field(default=0, ge=0, le=1, description="Is it a weekend? (0 or 1)")
    

class PredictionResponse(BaseModel):
    """Output prediction result"""
    ml_prediction: float
    adjusted_prediction: float
    adjustment_factor: float
    status: str


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Restaurant Demand Prediction API",
        "status": "running",
        "model_loaded": model is not None
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_available": model is not None,
        "model_path": str(MODEL_PATH),
        "version": "1.0.0"
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict_demand(request: PredictionRequest):
    """
    Predict restaurant demand using hybrid ML + rules approach
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        print(f"Received request: {request}")  # Debug logging
        # Prepare features for ML model in correct order
        features = pd.DataFrame({
            'day_of_week': [request.day_of_week],
            'is_weekend': [request.is_weekend],
            'month': [request.month],
            'menu_category': [request.menu_category],
            'is_festival': [request.is_festival],
            'festival_type': [request.festival_type],
            'is_poya_day': [request.is_poya_day],
            'temperature_avg': [request.temperature_avg],
            'rainfall_mm': [request.rainfall_mm],
            'is_heavy_rain': [request.is_heavy_rain],
            'supplier_invoice_qty': [request.supplier_invoice_qty],
        })
        
        # Get ML model prediction
        ml_prediction = float(model.predict(features)[0])
        
        # Map festival type back to string for rule engine
        festival_map = {0: "Sinhala_Tamil_New_Year", 1: "Vesak", 2: "None", 3: "Christmas", 4: "Diwali"}
        festival_name = festival_map.get(request.festival_type, "None")
        
        # Apply rule-based adjustments
        adjusted_prediction = apply_rules(
            base_prediction=ml_prediction,
            is_festival=request.is_festival,
            festival_type=festival_name,
            is_poya_day=request.is_poya_day,
            is_heavy_rain=request.is_heavy_rain,
            is_weekend=request.is_weekend
        )
        
        # Calculate adjustment factor
        adjustment_factor = round(adjusted_prediction / ml_prediction, 3) if ml_prediction > 0 else 1.0
        
        return PredictionResponse(
            ml_prediction=round(ml_prediction, 2),
            adjusted_prediction=adjusted_prediction,
            adjustment_factor=adjustment_factor,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/festivals")
async def get_festivals():
    """Get list of supported festivals"""
    return {
        "festivals": [
            "None",
            "Sinhala_Tamil_New_Year",
            "Vesak",
            "Christmas",
            "Diwali"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
