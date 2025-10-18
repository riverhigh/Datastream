from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body, Depends
from fastapi.responses import FileResponse, JSONResponse
from app.utils.data_processing import (
    process_csv, group_by_aggregate, sort_data, compute_correlation,
    detect_outliers, clean_data, generate_plot, get_descriptive_stats, get_value_counts
)
from app.config import limiter  # Import limiter from config
import pandas as pd
import io
import uuid
import json
import os
from typing import List, Optional

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/upload", summary="Upload and Analyze File (New: Group By, Sort, Correlation, etc.)")
@limiter.limit("5/minute")  # Use limiter directly
async def upload_file(
    request,  # Required for slowapi
    file: UploadFile = File(None),
    json_data: Optional[dict] = Body(None),
    stats: List[str] = Query(["mean", "median"], description="Stats to calculate (mean, median, min, max)"),
    filter_column: Optional[str] = Query(None, description="Column to filter"),
    filter_value: Optional[float] = Query(None, description="Value to filter by (e.g., sales > value)"),
    group_by: Optional[str] = Query(None, description="Column to group by (New Feature 1)"),
    sort_by: Optional[str] = Query(None, description="Column to sort by (New Feature 2)"),
    ascending: bool = Query(True, description="Sort ascending? (New Feature 2)"),
    clean: bool = Query(False, description="Clean data (remove duplicates, fill NaN)? (New Feature 5)"),
    detect_outliers_flag: bool = Query(False, description="Detect outliers? (New Feature 4)"),
    correlation: bool = Query(False, description="Compute correlation matrix? (New Feature 3)"),
    plot: bool = Query(False, description="Generate bar chart plot? (New Feature 6)"),
    descriptive: bool = Query(False, description="Get descriptive stats? (New Feature 9)"),
    value_counts_col: Optional[str] = Query(None, description="Column for value counts (New Feature 10)")
):
    if not file and not json_data:
        raise HTTPException(status_code=400, detail="Provide either a file or JSON data")
    
    try:
        if file:
            if not file.filename.endswith((".csv", ".xlsx", ".xls")):
                raise HTTPException(status_code=400, detail="Only CSV or Excel files allowed")
            if file.size > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large")
            content = await file.read()
            if file.filename.endswith(".csv"):
                df = pd.read_csv(io.StringIO(content.decode("utf-8")))
            else:
                df = pd.read_excel(io.BytesIO(content))
            filename = file.filename
        else:
            df = pd.DataFrame(json_data["data"])
            filename = "json_input"

        if clean:
            df = clean_data(df)

        if filter_column and filter_value is not None:
            if filter_column not in df.columns:
                raise HTTPException(status_code=400, detail="Filter column not found")
            df = df[df[filter_column] > filter_value]

        if sort_by:
            df = sort_data(df, sort_by, ascending)

        result = process_csv(df, stats)

        if group_by:
            result["group_by"] = group_by_aggregate(df, group_by, stats)

        if correlation:
            result["correlation"] = compute_correlation(df)

        if detect_outliers_flag:
            result["outliers"] = detect_outliers(df)

        if descriptive:
            result["descriptive_stats"] = get_descriptive_stats(df)

        if value_counts_col:
            result["value_counts"] = get_value_counts(df, value_counts_col)

        if plot:
            plot_image = generate_plot(df, stats)
            result["plot_image_base64"] = plot_image

        analysis_id = str(uuid.uuid4())
        os.makedirs("storage", exist_ok=True)
        with open(f"storage/{analysis_id}.json", "w") as f:
            json.dump(result, f)
        
        return {"filename": filename, "analysis_id": analysis_id, "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing: {str(e)}")

@router.get("/results/{analysis_id}", summary="Retrieve Past Analysis")
async def get_analysis(analysis_id: str):
    try:
        with open(f"storage/{analysis_id}.json", "r") as f:
            result = json.load(f)
        return {"analysis_id": analysis_id, "analysis": result}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Analysis not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving: {str(e)}")

@router.post("/feedback", summary="Submit Feedback")
async def submit_feedback(feedback: str = Body(...), rating: int = Body(..., ge=1, le=5)):
    try:
        feedback_id = str(uuid.uuid4())
        feedback_data = {"feedback": feedback, "rating": rating}
        os.makedirs("storage/feedback", exist_ok=True)
        with open(f"storage/feedback/{feedback_id}.json", "w") as f:
            json.dump(feedback_data, f)
        return {"message": "Thanks for your feedback!", "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")

@router.get("/export/{analysis_id}", summary="Export Analysis to CSV (New Feature 8)")
async def export_analysis(analysis_id: str):
    try:
        with open(f"storage/{analysis_id}.json", "r") as f:
            result = json.load(f)
        df_export = pd.DataFrame({"key": list(result.keys()), "value": list(result.values())})
        export_path = f"storage/{analysis_id}_export.csv"
        df_export.to_csv(export_path, index=False)
        return FileResponse(export_path, media_type="text/csv", filename=f"{analysis_id}_analysis.csv")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Analysis not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting: {str(e)}")

@router.get("/health", summary="Check API Status")
async def health_check():
    return {"status": "API is running - now with 10 new features!"}