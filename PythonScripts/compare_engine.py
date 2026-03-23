"""
compare_engine.py — Multi-File Comparison Engine
-------------------------------------------------
Compares N Excel/CSV files side-by-side.  Detects shared columns,
computes per-file summary statistics, cross-file deltas, and schema
differences.  Returns Markdown-formatted context for a RAG pipeline.

Supports 2+ files (not limited to pairs).
"""

import os
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from analysis_engine import _load_file  # reuse validated file loading


# ------------------------------------------------------------------ #
#  Multi-file loading                                                  #
# ------------------------------------------------------------------ #

def load_files(file_paths: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Load multiple Excel/CSV files.

    Returns a dict mapping filename (without directory) to DataFrame.
    Raises if fewer than 2 paths are supplied or any file fails to load.
    """
    if len(file_paths) < 2:
        raise ValueError("Compare mode requires at least 2 files.")

    frames: Dict[str, pd.DataFrame] = {}
    for path in file_paths:
        label = os.path.basename(path)
        # Deduplicate labels if the same filename appears from different dirs
        if label in frames:
            label = path
        frames[label] = _load_file(path)

    return frames


# ------------------------------------------------------------------ #
#  Schema comparison                                                   #
# ------------------------------------------------------------------ #

def compare_schemas(frames: Dict[str, pd.DataFrame]) -> str:
    """
    Compare column names and types across all files.

    Returns a Markdown section showing:
      - Columns shared by ALL files
      - Columns unique to specific files
      - Type mismatches for shared columns
    """
    all_cols: Dict[str, Dict[str, str]] = {}  # col -> {file: dtype}
    file_names = list(frames.keys())

    for fname, df in frames.items():
        for col in df.columns:
            all_cols.setdefault(col, {})[fname] = str(df[col].dtype)

    shared = [c for c, m in all_cols.items() if len(m) == len(frames)]
    unique_to_file: Dict[str, List[str]] = {f: [] for f in file_names}
    for col, mapping in all_cols.items():
        if len(mapping) < len(frames):
            for fname in mapping:
                if col not in shared:
                    unique_to_file[fname].append(col)

    # Type mismatches among shared columns
    mismatches = []
    for col in shared:
        types = all_cols[col]
        unique_types = set(types.values())
        if len(unique_types) > 1:
            detail = ", ".join(f"{f}: `{t}`" for f, t in types.items())
            mismatches.append(f"| {col} | {detail} |")

    lines = ["#### Schema Comparison\n"]

    lines.append(f"**Files compared:** {len(frames)}")
    lines.append(f"**Shared columns ({len(shared)}):** {', '.join(shared) if shared else 'None'}\n")

    for fname, unique in unique_to_file.items():
        if unique:
            lines.append(f"**Unique to {fname}:** {', '.join(unique)}")

    if mismatches:
        lines.append("\n**Type mismatches in shared columns:**\n")
        lines.append("| Column | Types per file |")
        lines.append("| --- | --- |")
        lines.extend(mismatches)

    return "\n".join(lines)


# ------------------------------------------------------------------ #
#  Numeric summary comparison                                          #
# ------------------------------------------------------------------ #

def compare_numeric_summaries(
    frames: Dict[str, pd.DataFrame],
) -> str:
    """
    For each numeric column shared across all files, compute per-file
    count, mean, median, std, min, max and present as a comparison table.
    """
    file_names = list(frames.keys())
    shared_numeric: List[str] = []

    # Find numeric columns common to all files
    sets = [
        set(df.select_dtypes(include="number").columns) for df in frames.values()
    ]
    if sets:
        shared_numeric = sorted(set.intersection(*sets))

    if not shared_numeric:
        return "#### Numeric Comparison\n\nNo shared numeric columns found."

    sections = ["#### Numeric Comparison\n"]

    for col in shared_numeric:
        rows = []
        for fname in file_names:
            s = frames[fname][col]
            rows.append({
                "File": fname,
                "Count": int(s.count()),
                "Mean": round(float(s.mean()), 2),
                "Median": round(float(s.median()), 2),
                "Std": round(float(s.std()), 2),
                "Min": round(float(s.min()), 2),
                "Max": round(float(s.max()), 2),
                "Sum": round(float(s.sum()), 2),
            })
        tbl = pd.DataFrame(rows)
        sections.append(f"**{col}:**\n")
        sections.append(tbl.to_markdown(index=False))
        sections.append("")

    return "\n".join(sections)


# ------------------------------------------------------------------ #
#  Row count & shape comparison                                        #
# ------------------------------------------------------------------ #

def compare_shapes(frames: Dict[str, pd.DataFrame]) -> str:
    """Compare row counts and column counts across files."""
    rows_data = []
    for fname, df in frames.items():
        rows_data.append({
            "File": fname,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Null cells": int(df.isnull().sum().sum()),
            "Numeric cols": len(df.select_dtypes(include="number").columns),
            "Text cols": len(df.select_dtypes(include=["object", "string"]).columns),
        })
    tbl = pd.DataFrame(rows_data)
    return "#### File Shapes\n\n" + tbl.to_markdown(index=False)


# ------------------------------------------------------------------ #
#  Cross-file delta (pairwise)                                         #
# ------------------------------------------------------------------ #

def compute_deltas(
    frames: Dict[str, pd.DataFrame],
    key_col: Optional[str] = None,
) -> str:
    """
    For each pair of files, compute deltas on shared numeric columns.

    If *key_col* is provided and exists in both files, the comparison is
    done row-by-row after aligning on that key.  Otherwise, aggregate
    deltas (mean vs mean, sum vs sum) are reported.
    """
    file_names = list(frames.keys())
    sets = [
        set(df.select_dtypes(include="number").columns) for df in frames.values()
    ]
    if not sets:
        return ""
    shared_numeric = sorted(set.intersection(*sets))
    if not shared_numeric:
        return ""

    sections = ["#### Cross-File Deltas\n"]

    for i in range(len(file_names)):
        for j in range(i + 1, len(file_names)):
            fa, fb = file_names[i], file_names[j]
            da, db = frames[fa], frames[fb]

            sections.append(f"**{fa} vs {fb}:**\n")

            if key_col and key_col in da.columns and key_col in db.columns:
                # Row-level delta on the key
                merged = pd.merge(
                    da, db, on=key_col, suffixes=(f"_{fa}", f"_{fb}"),
                    how="outer", indicator=True,
                )
                only_a = int((merged["_merge"] == "left_only").sum())
                only_b = int((merged["_merge"] == "right_only").sum())
                both = int((merged["_merge"] == "both").sum())
                sections.append(
                    f"- Rows only in {fa}: {only_a}  |  "
                    f"Only in {fb}: {only_b}  |  "
                    f"Matched: {both}"
                )

            # Aggregate delta
            delta_rows = []
            for col in shared_numeric:
                mean_a = float(da[col].mean())
                mean_b = float(db[col].mean())
                sum_a = float(da[col].sum())
                sum_b = float(db[col].sum())
                delta_rows.append({
                    "Column": col,
                    f"Mean ({fa})": round(mean_a, 2),
                    f"Mean ({fb})": round(mean_b, 2),
                    "Mean delta": round(mean_b - mean_a, 2),
                    "Mean delta %": (
                        round(((mean_b - mean_a) / mean_a) * 100, 1)
                        if mean_a != 0 else "N/A"
                    ),
                    f"Sum ({fa})": round(sum_a, 2),
                    f"Sum ({fb})": round(sum_b, 2),
                    "Sum delta": round(sum_b - sum_a, 2),
                })
            tbl = pd.DataFrame(delta_rows)
            sections.append(tbl.to_markdown(index=False))
            sections.append("")

    return "\n".join(sections)


# ------------------------------------------------------------------ #
#  Categorical comparison                                              #
# ------------------------------------------------------------------ #

def compare_categorical(frames: Dict[str, pd.DataFrame]) -> str:
    """
    For shared categorical/text columns, compare unique value counts
    and highlight values that appear in one file but not another.
    """
    file_names = list(frames.keys())
    sets = [
        set(df.select_dtypes(include=["object", "string"]).columns) for df in frames.values()
    ]
    if not sets:
        return ""
    shared_cat = sorted(set.intersection(*sets))
    if not shared_cat:
        return ""

    sections = ["#### Categorical Comparison\n"]

    for col in shared_cat:
        value_sets = {fname: set(frames[fname][col].dropna().unique())
                      for fname in file_names}
        all_values = set.union(*value_sets.values())
        common = set.intersection(*value_sets.values())

        sections.append(f"**{col}:**")
        sections.append(f"- Total unique values: {len(all_values)}")
        sections.append(f"- Common across all files: {len(common)}")

        for fname in file_names:
            unique_to = value_sets[fname] - common
            if unique_to:
                display = ", ".join(str(v) for v in sorted(unique_to)[:10])
                sections.append(f"- Unique to {fname}: {display}")
        sections.append("")

    return "\n".join(sections)


# ------------------------------------------------------------------ #
#  High-level entry point (called from C#)                             #
# ------------------------------------------------------------------ #

def build_compare_context(
    file_paths: List[str],
    key_col: Optional[str] = None,
) -> str:
    """
    End-to-end multi-file comparison context builder.

    1. Load all files.
    2. Compare schemas, shapes, numeric summaries, categorical values.
    3. Compute pairwise deltas.
    4. Return a single Markdown string for RAG injection.

    Parameters
    ----------
    file_paths : list of str
        Paths to 2+ Excel/CSV files.
    key_col : str, optional
        Shared key column for row-level alignment (e.g. "EmployeeID").
    """
    frames = load_files(file_paths)

    sections = [
        f"## Multi-File Comparison Report ({len(frames)} files)\n",
        compare_shapes(frames),
        "",
        compare_schemas(frames),
        "",
        compare_numeric_summaries(frames),
        "",
        compute_deltas(frames, key_col),
        "",
        compare_categorical(frames),
    ]
    return "\n\n".join(s for s in sections if s)


def get_compare_schema(file_paths: List[str]) -> str:
    """Return a combined schema overview of all files being compared."""
    frames = load_files(file_paths)
    lines = []
    for fname, df in frames.items():
        lines.append(f"\n{fname} ({len(df)} rows, {len(df.columns)} cols):")
        for col, dtype in zip(df.columns, df.dtypes):
            lines.append(f"  - {col} ({dtype})")
    return "Files loaded:" + "\n".join(lines)
