import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from scipy import stats  # For Z-score in outliers

def process_csv(df: pd.DataFrame, stats: list[str]) -> dict:
    try:
        if df.empty:
            return {"error": "Empty DataFrame provided"}
        
        numeric_df = df.select_dtypes(include=["float64", "int64"])
        if numeric_df.empty:
            return {"error": "No numeric columns found for analysis"}
        
        stat_functions = {
            "mean": lambda x: x.mean(),
            "median": lambda x: x.median(),
            "min": lambda x: x.min(),
            "max": lambda x: x.max()
        }
        
        result = {
            "summary": {
                "row_count": len(df),
                "numeric_columns": list(numeric_df.columns)
            },
            "column_stats": {
                col: {stat: stat_functions[stat](numeric_df[col]) for stat in stats if stat in stat_functions}
                for col in numeric_df.columns
            }
        }
        
        # Text-based chart
        for col in numeric_df.columns:
            mean = numeric_df[col].mean()
            result["column_stats"][col]["text_chart"] = "*" * int(mean // 10)
        
        return result
    except Exception as e:
        raise Exception(f"Error in data processing: {str(e)}")

# New Feature 1: Group by aggregation
def group_by_aggregate(df: pd.DataFrame, group_by: str, stats: list[str]) -> dict:
    if group_by not in df.columns:
        raise ValueError("Group by column not found")
    agg_funcs = {stat: stat for stat in stats}  # Simple agg
    grouped = df.groupby(group_by).agg(agg_funcs)
    return grouped.to_dict()

# New Feature 2: Sort data
def sort_data(df: pd.DataFrame, sort_by: str, ascending: bool) -> pd.DataFrame:
    if sort_by not in df.columns:
        raise ValueError("Sort column not found")
    return df.sort_values(by=sort_by, ascending=ascending)

# New Feature 3: Compute correlation
def compute_correlation(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include=["float64", "int64"])
    if len(numeric_df.columns) < 2:
        return {"error": "Need at least 2 numeric columns"}
    return numeric_df.corr().to_dict()

# New Feature 4: Detect outliers (using Z-score > 3)
def detect_outliers(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include=["float64", "int64"])
    z_scores = stats.zscore(numeric_df)
    outliers = (abs(z_scores) > 3).any(axis=1)
    return {"outlier_rows": df[outliers].to_dict(orient="records")}

# New Feature 5: Clean data
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates()  # Remove duplicates
    df = df.fillna(df.mean(numeric_only=True))  # Fill NaN with mean for numeric
    return df

# New Feature 6: Generate plot (bar chart of means)
def generate_plot(df: pd.DataFrame, stats: list[str]) -> str:
    numeric_df = df.select_dtypes(include=["float64", "int64"])
    means = numeric_df.mean()
    fig, ax = plt.subplots()
    means.plot(kind="bar", ax=ax)
    ax.set_title("Mean Values Bar Chart")
    img_io = io.BytesIO()
    fig.savefig(img_io, format="png")
    img_io.seek(0)
    return base64.b64encode(img_io.read()).decode("utf-8")  # Base64 for response

# New Feature 9: Descriptive stats
def get_descriptive_stats(df: pd.DataFrame) -> dict:
    return df.describe().to_dict()

# New Feature 10: Value counts
def get_value_counts(df: pd.DataFrame, column: str) -> dict:
    if column not in df.columns:
        raise ValueError("Column not found for value counts")
    return df[column].value_counts().to_dict()