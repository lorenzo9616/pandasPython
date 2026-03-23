"""
analysis_engine.py — The "Office Auditor" Context Engine
--------------------------------------------------------
Called from C# via pythonnet.  Takes two data sources (Staff List + Task Logs),
merges them on a common key, calculates productivity metrics, and returns
Markdown-formatted context for a RAG pipeline.

Functions are designed to be invoked individually from C# or composed
together via ``build_audit_context()``.
"""

import os
from typing import Tuple

import pandas as pd


# ------------------------------------------------------------------ #
#  File loading                                                        #
# ------------------------------------------------------------------ #

_SUPPORTED_EXT = (".xlsx", ".xls", ".csv")


def _load_file(file_path: str) -> pd.DataFrame:
    """Load an Excel or CSV file into a DataFrame."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _SUPPORTED_EXT:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(_SUPPORTED_EXT)}"
        )

    if ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path, engine="openpyxl")

    if df.empty:
        raise ValueError(f"File is empty: {file_path}")
    return df


def load_and_merge(
    staff_path: str,
    tasks_path: str,
    merge_key: str = "EmployeeID",
) -> pd.DataFrame:
    """
    Load the staff list and task logs, then inner-join on *merge_key*.

    Returns the merged DataFrame.  Raises ``KeyError`` if the merge key
    is missing from either file.
    """
    staff_df = _load_file(staff_path)
    tasks_df = _load_file(tasks_path)

    if merge_key not in staff_df.columns:
        raise KeyError(
            f"Merge key '{merge_key}' not found in staff file. "
            f"Available: {', '.join(staff_df.columns)}"
        )
    if merge_key not in tasks_df.columns:
        raise KeyError(
            f"Merge key '{merge_key}' not found in tasks file. "
            f"Available: {', '.join(tasks_df.columns)}"
        )

    merged = pd.merge(staff_df, tasks_df, on=merge_key, how="inner")
    if merged.empty:
        raise ValueError(
            f"Merge produced no rows — no matching '{merge_key}' values "
            "between the two files."
        )
    return merged


# ------------------------------------------------------------------ #
#  Productivity metrics                                                #
# ------------------------------------------------------------------ #

def calculate_productivity(
    merged_df: pd.DataFrame,
    employee_col: str = "EmployeeName",
    hours_col: str = "HoursWorked",
    tasks_col: str = "TasksCompleted",
) -> pd.DataFrame:
    """
    Group by employee and compute:
      - total_hours        — sum of hours worked
      - total_tasks        — sum of tasks completed
      - tasks_per_hour     — total_tasks / total_hours
      - workload_pct       — employee's hours as % of team total
    """
    for col in (employee_col, hours_col, tasks_col):
        if col not in merged_df.columns:
            raise KeyError(
                f"Column '{col}' not found. "
                f"Available: {', '.join(merged_df.columns)}"
            )

    grouped = (
        merged_df
        .groupby(employee_col, as_index=False)
        .agg(
            total_hours=(hours_col, "sum"),
            total_tasks=(tasks_col, "sum"),
        )
    )

    grouped["tasks_per_hour"] = (
        grouped["total_tasks"] / grouped["total_hours"]
    ).round(3)

    team_total_hours = grouped["total_hours"].sum()
    grouped["workload_pct"] = (
        (grouped["total_hours"] / team_total_hours) * 100
    ).round(1)

    return grouped.sort_values("tasks_per_hour", ascending=False)


# ------------------------------------------------------------------ #
#  Markdown formatters                                                 #
# ------------------------------------------------------------------ #

def _df_to_markdown(df: pd.DataFrame, title: str) -> str:
    """Convert a DataFrame to a Markdown table with a heading."""
    header = "| " + " | ".join(df.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    rows = []
    for _, row in df.iterrows():
        cells = " | ".join(str(v) for v in row.values)
        rows.append(f"| {cells} |")
    return f"#### {title}\n\n{header}\n{sep}\n" + "\n".join(rows)


def format_top_bottom(
    productivity_df: pd.DataFrame,
    n: int = 5,
) -> str:
    """Return Markdown tables of the top-N and bottom-N performers."""
    top = productivity_df.head(n)
    bottom = productivity_df.tail(n)

    parts = [
        _df_to_markdown(top, f"Top {len(top)} Performers (highest tasks/hour)"),
        "",
        _df_to_markdown(bottom, f"Bottom {len(bottom)} Performers (lowest tasks/hour)"),
    ]
    return "\n\n".join(parts)


def format_summary_stats(productivity_df: pd.DataFrame) -> str:
    """Return team-wide summary statistics as Markdown."""
    total_hours = productivity_df["total_hours"].sum()
    total_tasks = productivity_df["total_tasks"].sum()
    avg_tph = productivity_df["tasks_per_hour"].mean()
    median_tph = productivity_df["tasks_per_hour"].median()
    std_tph = productivity_df["tasks_per_hour"].std()
    headcount = len(productivity_df)

    most_hours_row = productivity_df.loc[productivity_df["total_hours"].idxmax()]
    least_eff_row = productivity_df.loc[productivity_df["tasks_per_hour"].idxmin()]

    return f"""#### Team Summary Statistics

| Metric | Value |
| --- | --- |
| Headcount | {headcount} |
| Total team hours | {total_hours:.1f} |
| Total tasks completed | {int(total_tasks)} |
| Avg tasks/hour | {avg_tph:.3f} |
| Median tasks/hour | {median_tph:.3f} |
| Std-dev tasks/hour | {std_tph:.3f} |
| Most hours worked | {most_hours_row.iloc[0]} ({most_hours_row['total_hours']:.1f} hrs) |
| Lowest efficiency | {least_eff_row.iloc[0]} ({least_eff_row['tasks_per_hour']:.3f} tasks/hr) |"""


# ------------------------------------------------------------------ #
#  High-level entry point (called from C#)                             #
# ------------------------------------------------------------------ #

def build_audit_context(
    staff_path: str,
    tasks_path: str,
    merge_key: str = "EmployeeID",
    employee_col: str = "EmployeeName",
    hours_col: str = "HoursWorked",
    tasks_col: str = "TasksCompleted",
    top_n: int = 5,
) -> str:
    """
    End-to-end context builder for the Office Auditor RAG mode.

    1. Load and merge the two files on *merge_key*.
    2. Calculate productivity metrics.
    3. Format top/bottom performers + summary stats as Markdown.

    Returns a single string ready to be injected into an LLM prompt.
    """
    merged = load_and_merge(staff_path, tasks_path, merge_key)
    productivity = calculate_productivity(
        merged, employee_col, hours_col, tasks_col
    )

    sections = [
        "## Office Audit — Productivity Report\n",
        format_summary_stats(productivity),
        "",
        format_top_bottom(productivity, n=top_n),
        "",
        "#### Full Ranking\n",
        productivity.to_markdown(index=False),
    ]
    return "\n\n".join(sections)


def get_merged_schema(
    staff_path: str,
    tasks_path: str,
    merge_key: str = "EmployeeID",
) -> str:
    """Return column names/types of the merged DataFrame."""
    merged = load_and_merge(staff_path, tasks_path, merge_key)
    lines = [f"- {col} ({dtype})" for col, dtype in zip(merged.columns, merged.dtypes)]
    return f"Merged schema ({len(merged)} rows):\n" + "\n".join(lines)
