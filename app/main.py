# main.py
import os
import io
import json
import uuid
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import pandas as pd
import matplotlib.pyplot as plt

from app.utils.db import (
    init_db,
    save_analysis_db,
    get_analysis_db,
    list_all_analyses,
    delete_analysis_db,
    create_user,
    get_user,
    get_user_by_credentials
)

from fastapi.staticfiles import StaticFiles

# ============================================================
# App Setup
# ============================================================
app = FastAPI(
    title="DataStream API",
    description="A professional API for intelligent data analytics and visualization.",
    version="1.2.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded. Try again later."})

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key auth
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
async def get_api_key(api_key: str = Security(API_KEY_HEADER)):
    user = get_user(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return user

# Initialize DB
@app.on_event("startup")
def on_startup():
    init_db()

# ============================================================
# Mount frontend dashboard
# ============================================================
app.mount("/dashboard", StaticFiles(directory="frontend", html=True), name="dashboard")

# ============================================================
# User Endpoints
# ============================================================
@app.post("/register", summary="Register a new user")
async def register_user(username: str = Body(...), password: str = Body(...)):
    api_key = str(uuid.uuid4())
    create_user(username, password, api_key)
    return {"message": f"User '{username}' created", "api_key": api_key}

@app.post("/login", summary="Login user and get API key")
async def login_user(username: str = Body(...), password: str = Body(...)):
    user = get_user_by_credentials(username, password)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid username or password")
    return {"username": username, "api_key": user["api_key"]}

# ============================================================
# Root
# ============================================================
@app.get("/")
async def home():
    return {"message": "Welcome to DataStream — your modern data analytics API."}

# ============================================================
# Upload & Analyze CSV
# ============================================================
@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze_file(file: UploadFile = File(...), user: dict = Security(get_api_key)):
    try:
        df = pd.read_csv(file.file)
        summary = {
            "rows": len(df),
            "columns": len(df.columns),
            "columns_list": df.columns.tolist(),
            "preview": df.head(5).to_dict(orient="records")
        }

        analysis_id = str(uuid.uuid4())
        save_analysis_db(analysis_id, summary, user_id=user["id"])

        return {
            "message": "Analysis completed successfully.",
            "analysis_id": analysis_id,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error analyzing file: {str(e)}")

# ============================================================
# Retrieve Past Analysis
# ============================================================
@app.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str, user: dict = Security(get_api_key)):
    record = get_analysis_db(analysis_id, user_id=user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    record["result"] = json.loads(record["result"])
    return record

# ============================================================
# List All User Analyses
# ============================================================
@app.get("/records")
async def list_records(user: dict = Security(get_api_key)):
    records = list_all_analyses(user_id=user["id"])
    return {"count": len(records), "records": records}

# ============================================================
# Delete Analysis
# ============================================================
@app.delete("/delete/{analysis_id}")
async def delete_analysis(analysis_id: str, user: dict = Security(get_api_key)):
    deleted = delete_analysis_db(analysis_id, user_id=user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found or already deleted.")
    return {"message": f"Analysis {analysis_id} deleted successfully."}

# ============================================================
# Visualization
# ============================================================
@app.post("/visualize")
@limiter.limit("3/minute")
async def visualize_column(file: UploadFile = File(...), column: str = None, user: dict = Security(get_api_key)):
    try:
        df = pd.read_csv(file.file)
        if column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{column}' not found in file.")

        plt.figure(figsize=(8, 5))
        df[column].hist(bins=20, color='skyblue', edgecolor='black')
        plt.title(f"Distribution of {column}")
        plt.xlabel(column)
        plt.ylabel("Frequency")

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        return {"column": column, "histogram_base64": encoded}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating visualization: {str(e)}")

# ============================================================
# Health Check
# ============================================================
@app.get("/health")
async def health():
    return {"status": "OK", "message": "DataStream API is running properly."}
