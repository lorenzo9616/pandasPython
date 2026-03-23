"""Tests for PythonScripts/compare_engine.py — multi-file comparison engine."""

import os
import subprocess
import sys
import pytest
import pandas as pd
import compare_engine


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

SAMPLE_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "SampleData")
)
Q1_XLSX = os.path.join(SAMPLE_DIR, "sales_q1.xlsx")
Q2_XLSX = os.path.join(SAMPLE_DIR, "sales_q2.xlsx")
Q3_XLSX = os.path.join(SAMPLE_DIR, "sales_q3.xlsx")


@pytest.fixture(scope="module", autouse=True)
def _generate_compare_data():
    """Generate quarterly sales files if they don't exist."""
    if not all(os.path.isfile(f) for f in [Q1_XLSX, Q2_XLSX, Q3_XLSX]):
        subprocess.check_call(
            [sys.executable, "generate_compare_data.py"],
            cwd=SAMPLE_DIR,
        )
    yield


@pytest.fixture
def two_files():
    return [Q1_XLSX, Q2_XLSX]


@pytest.fixture
def three_files():
    return [Q1_XLSX, Q2_XLSX, Q3_XLSX]


@pytest.fixture
def frames(three_files):
    return compare_engine.load_files(three_files)


# ------------------------------------------------------------------ #
#  Tests: file loading                                                 #
# ------------------------------------------------------------------ #

class TestLoadFiles:
    def test_loads_two_files(self, two_files):
        frames = compare_engine.load_files(two_files)
        assert len(frames) == 2
        for df in frames.values():
            assert len(df) > 0

    def test_loads_three_files(self, three_files):
        frames = compare_engine.load_files(three_files)
        assert len(frames) == 3

    def test_raises_on_single_file(self):
        with pytest.raises(ValueError, match="at least 2"):
            compare_engine.load_files([Q1_XLSX])

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            compare_engine.load_files([Q1_XLSX, "/nonexistent/file.xlsx"])

    def test_loads_csv_files(self, tmp_path):
        csv1 = tmp_path / "a.csv"
        csv2 = tmp_path / "b.csv"
        csv1.write_text("x,y\n1,2\n3,4\n")
        csv2.write_text("x,y\n5,6\n7,8\n")
        frames = compare_engine.load_files([str(csv1), str(csv2)])
        assert len(frames) == 2


# ------------------------------------------------------------------ #
#  Tests: schema comparison                                            #
# ------------------------------------------------------------------ #

class TestCompareSchemas:
    def test_identifies_shared_columns(self, frames):
        result = compare_engine.compare_schemas(frames)
        assert "Shared columns" in result
        # All three files share Product, Revenue, etc.
        assert "Product" in result or "Revenue" in result

    def test_identifies_files_compared(self, frames):
        result = compare_engine.compare_schemas(frames)
        assert "Files compared" in result
        assert "3" in result


# ------------------------------------------------------------------ #
#  Tests: shape comparison                                             #
# ------------------------------------------------------------------ #

class TestCompareShapes:
    def test_shows_rows_and_columns(self, frames):
        result = compare_engine.compare_shapes(frames)
        assert "Rows" in result
        assert "Columns" in result
        assert "File" in result

    def test_each_file_listed(self, frames):
        result = compare_engine.compare_shapes(frames)
        for fname in frames:
            assert fname in result


# ------------------------------------------------------------------ #
#  Tests: numeric summary                                              #
# ------------------------------------------------------------------ #

class TestCompareNumericSummaries:
    def test_shows_mean_and_sum(self, frames):
        result = compare_engine.compare_numeric_summaries(frames)
        assert "Mean" in result
        assert "Sum" in result

    def test_covers_shared_numeric_columns(self, frames):
        result = compare_engine.compare_numeric_summaries(frames)
        # UnitsSold and Revenue are numeric and shared
        assert "UnitsSold" in result or "Revenue" in result


# ------------------------------------------------------------------ #
#  Tests: deltas                                                       #
# ------------------------------------------------------------------ #

class TestComputeDeltas:
    def test_pairwise_deltas(self, frames):
        result = compare_engine.compute_deltas(frames)
        assert "vs" in result
        assert "delta" in result.lower()

    def test_with_key_col(self, frames):
        result = compare_engine.compute_deltas(frames, key_col="ProductID")
        assert "Matched" in result or "Only in" in result

    def test_without_key_col(self, frames):
        result = compare_engine.compute_deltas(frames)
        # Should still produce aggregate deltas
        assert "Mean" in result


# ------------------------------------------------------------------ #
#  Tests: categorical comparison                                       #
# ------------------------------------------------------------------ #

class TestCompareCategorical:
    def test_shows_unique_values(self, frames):
        result = compare_engine.compare_categorical(frames)
        # Quarter column differs across files
        if result:  # Only if there are shared categorical columns
            assert "unique" in result.lower() or "Common" in result


# ------------------------------------------------------------------ #
#  Tests: end-to-end context builder                                   #
# ------------------------------------------------------------------ #

class TestBuildCompareContext:
    def test_returns_full_report(self, three_files):
        context = compare_engine.build_compare_context(three_files)
        assert "Comparison Report" in context
        assert "3 files" in context
        assert "File Shapes" in context

    def test_with_key_col(self, three_files):
        context = compare_engine.build_compare_context(
            three_files, key_col="ProductID"
        )
        assert "Comparison Report" in context

    def test_two_files_works(self, two_files):
        context = compare_engine.build_compare_context(two_files)
        assert "2 files" in context

    def test_get_compare_schema(self, three_files):
        schema = compare_engine.get_compare_schema(three_files)
        assert "Files loaded" in schema
        assert "rows" in schema
