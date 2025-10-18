# app/routes/analytics.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
import io
import hashlib
import uuid
import json
import os
import logging

from app.config import limiter
from slowapi.util import get_remote_address
from slowapi import Limiter

from app.utils.data_processing import (
    process_csv,
    group_by_aggregate,
    sort_data,
    compute_correlation,
    detect_outliers,
    clean_data,
    generate_plot,
    get_descriptive_stats,
    get_value_counts,
)

from app.utils.db import save_analysis_db, get_analysis_db

logger = logging.getLogger("datastream.analytics")
router = APIRouter(tags=["analytics"])

# Request model for validated parameters
class AnalysisParams(BaseModel):
    stats: List[str] = Field(default_factory=lambda: ["mean", "median"])
    filter_column: Optional[str] = None
    filter_value: Optional[float] = None
    group_by: Optional[str] = None
    sort_by: Optional[str] = None
    ascending: bool = True
    clean: bool = False
    detect_outliers_flag: bool = False
    correlation: bool = False
    plot: bool = False
    descriptive: bool = False
    value_counts_col: Optional[str] = None

# simple in-memory cache mapping file_hash -> analysis_id
CACHE: dict = {}

# apply limiter per route using limiter from config
route_limit = limiter.limit

@router.post("/upload", summary="Upload and analyze a file (CSV/Excel) or JSON body")
@route_limit("10/minute")
async def upload_file(
    request: Request,
    params: AnalysisParams = Depends(),
    file: UploadFile = File(None),
    json_data: Optional[dict] = Body(None),
):
    if not file and not json_data:
        raise HTTPException(status_code=400, detail="Provide either a file upload or JSON data in the request body.")

    try:
        # --- load dataframe ---
        if file:
            filename = file.filename or "uploaded"
            content = await file.read()
            size = len(content)
            max_size = 8 * 1024 * 1024  # 8 MB
            if size > max_size:
                raise HTTPException(status_code=413, detail="File too large (max 8 MB).")
            lower = filename.lower()
            if lower.endswith(".csv"):
                df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="replace")))
            elif lower.endswith((".xls", ".xlsx")):
                df = pd.read_excel(io.BytesIO(content))
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or Excel.")
            file_hash = hashlib.md5(content).hexdigest()
        else:
            # accept {"data": [ {..}, {...} ] } or a direct list
            if isinstance(json_data, dict) and "data" in json_data:
                df = pd.DataFrame(json_data["data"])
            elif isinstance(json_data, list):
                df = pd.DataFrame(json_data)
            else:
                raise HTTPException(status_code=400, detail="JSON body must be a list or contain 'data' key with list.")
            filename = "json_input"
            file_hash = hashlib.md5(json.dumps(json_data, sort_keys=True).encode()).hexdigest()

        # --- serve cached analysis if present ---
        if file_hash in CACHE:
            cached_id = CACHE[file_hash]
            rec = get_analysis_db(cached_id)
            if rec:
                return {"cached": True, "analysis_id": cached_id, "analysis": json.loads(rec["result"])}

        # --- cleaning ---
        if params.clean:
            df = clean_data(df)

        # --- filtering ---
        if params.filter_column and params.filter_value is not None:
            if params.filter_column not in df.columns:
                raise HTTPException(status_code=400, detail="Filter column not found.")
            df = df[df[params.filter_column] > params.filter_value]

        # --- sorting ---
        if params.sort_by:
            if params.sort_by not in df.columns:
                raise HTTPException(status_code=400, detail="Sort column not found.")
            df = sort_data(df, params.sort_by, params.ascending)

        # --- main analysis ---
        result = process_csv(df, params.stats)

        if params.group_by:
            if params.group_by not in df.columns:
                raise HTTPException(status_code=400, detail="Group-by column not found.")
            result["group_by"] = group_by_aggregate(df, params.group_by, params.stats)

        if params.correlation:
            result["correlation"] = compute_correlation(df)

        if params.detect_outliers_flag:
            result["outliers"] = detect_outliers(df)

        if params.descriptive:
            result["descriptive_stats"] = get_descriptive_stats(df)

        if params.value_counts_col:
            if params.value_counts_col not in df.columns:
                raise HTTPException(status_code=400, detail="Value counts column not found.")
            result["value_counts"] = get_value_counts(df, params.value_counts_col)

        if params.plot:
            plot_b64 = generate_plot(df, params.stats)
            result["plot_image_base64"] = plot_b64

        analysis_id = str(uuid.uuid4())
        save_analysis_db(analysis_id, result)
        CACHE[file_hash] = analysis_id

        return {"filename": filename, "analysis_id": analysis_id, "analysis": result}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error processing upload")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(exc)}")


@router.get("/results/{analysis_id}", summary="Retrieve saved analysis")
async def get_analysis(analysis_id: str):
    rec = get_analysis_db(analysis_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"analysis_id": analysis_id, "analysis": json.loads(rec["result"])}


@router.post("/feedback", summary="Submit feedback")
@route_limit("20/minute")
async def submit_feedback(payload: dict = Body(...)):
    if "feedback" not in payload or "rating" not in payload:
        raise HTTPException(status_code=400, detail="Provide 'feedback' and 'rating' fields")
    feedback_id = str(uuid.uuid4())
    os.makedirs("storage/feedback", exist_ok=True)
    with open(f"storage/feedback/{feedback_id}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return {"message": "Feedback received", "feedback_id": feedback_id}


@router.get("/export/{analysis_id}", summary="Export saved analysis to CSV")
async def export_analysis(analysis_id: str):
    rec = get_analysis_db(analysis_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = json.loads(rec["result"])
    # Flatten for export
    rows = []
    for k, v in result.items():
        rows.append({"key": k, "value": json.dumps(v)})
    df_export = pd.DataFrame(rows)
    os.makedirs("storage", exist_ok=True)
    path = f"storage/{analysis_id}_export.csv"
    df_export.to_csv(path, index=False)
    return {"download_path": path}
