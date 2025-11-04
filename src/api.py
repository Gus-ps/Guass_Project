from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict
import logging
import json
from datetime import datetime, date

from src.backend import generate_company_report
from src import config

logger = logging.getLogger("llm_stock_insights.api")

# Custom JSON encoder to handle datetime/Timestamp objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):  # pandas Timestamp
            return obj.isoformat()
        if hasattr(obj, 'item'):  # numpy types
            return obj.item()
        return super().default(obj)

app = FastAPI(title="LLM Stock Insights API")

# CORS - allow frontend origin or localhost for dev
origins = [config.API_URL, "http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/report")
def post_report(payload: Dict[str, str]):
    """Accept JSON payload {"ticker": "AAPL"} and return the structured report."""
    logger.info("Api is being called")
    ticker = payload.get("ticker")
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required in JSON body")
    try:
        report = generate_company_report(ticker)
        json_str = json.dumps(report, cls=CustomJSONEncoder)
        return JSONResponse(content=json.loads(json_str))
    except Exception as e:
        logger.exception("Failed to generate report for %s", ticker)
        raise HTTPException(status_code=500, detail=str(e))
