"""
data_processor.py
-----------------
Called from C# via pythonnet.  Loads an Excel file with Pandas,
applies GroupBy / filter operations, and returns a text "context"
string suitable for injection into a RAG prompt.
"""

import os
import pandas as pd


def load_and_validate(file_path: str) -> pd.DataFrame:
    """Load an Excel file after basic validation."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    if not file_path.lower().endswith((".xlsx", ".xls")):
        raise ValueError("Only .xlsx / .xls files are supported.")

    df = pd.read_excel(file_path, engine="openpyxl")
    if df.empty:
        raise ValueError("The Excel file is empty.")
    return df


def summarize_by_column(file_path: str, group_col: str) -> str:
    """
    Group the data by *group_col* and return an aggregated summary
    as a plain-text table that can be used as RAG context.

    For numeric columns the summary contains count, mean, sum.
    For non-numeric columns the summary contains count and unique values.
    """
    df = load_and_validate(file_path)

    if group_col not in df.columns:
        available = ", ".join(df.columns.tolist())
        raise KeyError(
            f"Column '{group_col}' not found. Available columns: {available}"
        )

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if group_col in numeric_cols:
        numeric_cols.remove(group_col)

    if numeric_cols:
        summary = (
            df.groupby(group_col)[numeric_cols]
            .agg(["count", "mean", "sum"])
            .reset_index()
        )
    else:
        summary = (
            df.groupby(group_col)
            .agg("count")
            .reset_index()
        )

    return summary.to_string(index=False)


def filter_rows(file_path: str, column: str, value: str) -> str:
    """
    Filter the DataFrame where *column* equals *value* and return
    the matching rows as a plain-text table (RAG context).
    """
    df = load_and_validate(file_path)

    if column not in df.columns:
        available = ", ".join(df.columns.tolist())
        raise KeyError(
            f"Column '{column}' not found. Available columns: {available}"
        )

    mask = df[column].astype(str).str.lower() == str(value).lower()
    filtered = df[mask]

    if filtered.empty:
        return f"No rows found where '{column}' == '{value}'."

    return filtered.to_string(index=False)


def get_schema(file_path: str) -> str:
    """Return column names and dtypes as a string for schema-aware prompting."""
    df = load_and_validate(file_path)
    lines = [f"- {col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)]
    return "Columns:\n" + "\n".join(lines)
