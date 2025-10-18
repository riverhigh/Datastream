# app/utils/data_processing.py
import pandas as pd
import numpy as np
import io
import base64
import matplotlib.pyplot as plt
from scipy import stats

def process_csv(df: pd.DataFrame, stats: list) -> dict:
    if df is None or df.empty:
        return {"error": "Empty DataFrame"}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    result = {"rows": len(df), "columns": df.columns.tolist()}
    result["columns_stats"] = {}
    for col in numeric_cols:
        col_stats = {}
        series = df[col].dropna()
        if "mean" in stats:
            col_stats["mean"] = float(series.mean()) if not series.empty else None
        if "median" in stats:
            col_stats["median"] = float(series.median()) if not series.empty else None
        if "min" in stats:
            col_stats["min"] = float(series.min()) if not series.empty else None
        if "max" in stats:
            col_stats["max"] = float(series.max()) if not series.empty else None
        if "std" in stats:
            col_stats["std"] = float(series.std()) if not series.empty else None
        # small text visualization
        if not series.empty:
            mean_val = series.mean()
            col_stats["text_chart"] = "*" * min(50, int(mean_val // max(1, (abs(mean_val) // 10) or 1)))
        result["columns_stats"][col] = col_stats
    return result

def group_by_aggregate(df: pd.DataFrame, col: str, stats: list) -> dict:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    grouped = df.groupby(col)
    agg_result = {}
    for name, group in grouped:
        agg_result[name] = {}
        for c in numeric_cols:
            values = {}
            if "mean" in stats:
                values["mean"] = float(group[c].mean()) if not group[c].empty else None
            if "sum" in stats:
                values["sum"] = float(group[c].sum()) if not group[c].empty else None
            if values:
                agg_result[name][c] = values
    return agg_result

def sort_data(df: pd.DataFrame, by: str, ascending: bool = True) -> pd.DataFrame:
    return df.sort_values(by=by, ascending=ascending)

def compute_correlation(df: pd.DataFrame) -> dict:
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return {}
    return numeric.corr().fillna(0).to_dict()

def detect_outliers(df: pd.DataFrame, z_thresh: float = 3.0) -> dict:
    numeric = df.select_dtypes(include=[np.number])
    if numeric.empty:
        return {}
    z = np.abs(stats.zscore(numeric.dropna()))
    outliers = {}
    if z.ndim == 1:
        mask = z > z_thresh
        outliers[numeric.columns[0]] = numeric[mask].tolist()
    else:
        for idx, col in enumerate(numeric.columns):
            mask = z[:, idx] > z_thresh
            if mask.any():
                outliers[col] = numeric[col][mask].tolist()
    return outliers

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.drop_duplicates()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        median = df[col].median()
        df[col] = df[col].fillna(median)
    return df

def generate_plot(df: pd.DataFrame, stats: list) -> str:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return None
    col = numeric_cols[0]
    series = df[col].dropna().head(100)
    fig, ax = plt.subplots(figsize=(8, 4))
    series.plot(kind="bar", ax=ax)
    ax.set_title(f"Sample of {col}")
    ax.set_xlabel("index")
    ax.set_ylabel(col)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def get_descriptive_stats(df: pd.DataFrame) -> dict:
    numeric = df.select_dtypes(include=[np.number])
    if numeric.empty:
        return {}
    return numeric.describe().to_dict()

def get_value_counts(df: pd.DataFrame, col: str) -> dict:
    if col not in df.columns:
        return {}
    return df[col].value_counts().to_dict()
