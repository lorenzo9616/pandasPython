"""Tests for PythonScripts/analysis_engine.py — the Office Auditor context engine."""

import os
import pytest
import pandas as pd
import analysis_engine


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

SAMPLE_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "SampleData")
)
STAFF_XLSX = os.path.join(SAMPLE_DIR, "staff_list.xlsx")
TASKS_XLSX = os.path.join(SAMPLE_DIR, "task_logs.xlsx")


@pytest.fixture(scope="module", autouse=True)
def _generate_audit_data():
    """Generate staff/task Excel files if they don't exist."""
    import subprocess, sys
    if not os.path.isfile(STAFF_XLSX) or not os.path.isfile(TASKS_XLSX):
        subprocess.check_call(
            [sys.executable, "generate_audit_data.py"],
            cwd=SAMPLE_DIR,
        )
    yield


@pytest.fixture
def staff_path():
    return STAFF_XLSX


@pytest.fixture
def tasks_path():
    return TASKS_XLSX


@pytest.fixture
def merged_df(staff_path, tasks_path):
    return analysis_engine.load_and_merge(staff_path, tasks_path)


@pytest.fixture
def productivity_df(merged_df):
    return analysis_engine.calculate_productivity(merged_df)


# ------------------------------------------------------------------ #
#  Tests: file loading                                                 #
# ------------------------------------------------------------------ #

class TestLoadFile:
    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            analysis_engine._load_file("/nonexistent/file.xlsx")

    def test_raises_on_unsupported_extension(self, tmp_path):
        bad = tmp_path / "data.json"
        bad.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported"):
            analysis_engine._load_file(str(bad))

    def test_loads_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n")
        df = analysis_engine._load_file(str(csv_file))
        assert len(df) == 2
        assert list(df.columns) == ["a", "b"]


# ------------------------------------------------------------------ #
#  Tests: merge                                                        #
# ------------------------------------------------------------------ #

class TestLoadAndMerge:
    def test_merge_produces_rows(self, staff_path, tasks_path):
        merged = analysis_engine.load_and_merge(staff_path, tasks_path)
        assert len(merged) > 0
        assert "EmployeeName" in merged.columns
        assert "TasksCompleted" in merged.columns

    def test_merge_key_missing_in_staff(self, staff_path, tasks_path):
        with pytest.raises(KeyError, match="staff file"):
            analysis_engine.load_and_merge(staff_path, tasks_path, merge_key="FakeKey")

    def test_merge_has_all_employee_ids(self, staff_path, tasks_path):
        merged = analysis_engine.load_and_merge(staff_path, tasks_path)
        unique_ids = merged["EmployeeID"].nunique()
        assert unique_ids == 15  # all 15 employees appear in both files


# ------------------------------------------------------------------ #
#  Tests: productivity calculation                                     #
# ------------------------------------------------------------------ #

class TestCalculateProductivity:
    def test_output_columns(self, productivity_df):
        expected = {"EmployeeName", "total_hours", "total_tasks",
                    "tasks_per_hour", "workload_pct"}
        assert expected.issubset(set(productivity_df.columns))

    def test_fifteen_employees(self, productivity_df):
        assert len(productivity_df) == 15

    def test_sorted_descending_by_efficiency(self, productivity_df):
        tph = productivity_df["tasks_per_hour"].tolist()
        assert tph == sorted(tph, reverse=True)

    def test_workload_pct_sums_to_100(self, productivity_df):
        total = productivity_df["workload_pct"].sum()
        assert abs(total - 100.0) < 1.0  # allow rounding tolerance

    def test_tasks_per_hour_is_positive(self, productivity_df):
        assert (productivity_df["tasks_per_hour"] > 0).all()

    def test_raises_on_missing_column(self, merged_df):
        with pytest.raises(KeyError, match="not found"):
            analysis_engine.calculate_productivity(
                merged_df, hours_col="NonExistentCol"
            )


# ------------------------------------------------------------------ #
#  Tests: formatting                                                   #
# ------------------------------------------------------------------ #

class TestFormatting:
    def test_top_bottom_contains_markdown_table(self, productivity_df):
        result = analysis_engine.format_top_bottom(productivity_df, n=3)
        assert "Top 3 Performers" in result
        assert "Bottom 3 Performers" in result
        assert "|" in result  # Markdown table pipes

    def test_summary_stats_contains_metrics(self, productivity_df):
        result = analysis_engine.format_summary_stats(productivity_df)
        assert "Headcount" in result
        assert "Total team hours" in result
        assert "tasks/hour" in result.lower()
        assert "Lowest efficiency" in result


# ------------------------------------------------------------------ #
#  Tests: end-to-end context builder                                   #
# ------------------------------------------------------------------ #

class TestBuildAuditContext:
    def test_returns_full_report(self, staff_path, tasks_path):
        context = analysis_engine.build_audit_context(staff_path, tasks_path)
        assert "Productivity Report" in context
        assert "Top" in context
        assert "Bottom" in context
        assert "Headcount" in context

    def test_get_merged_schema(self, staff_path, tasks_path):
        schema = analysis_engine.get_merged_schema(staff_path, tasks_path)
        assert "EmployeeID" in schema
        assert "EmployeeName" in schema
        assert "HoursWorked" in schema
