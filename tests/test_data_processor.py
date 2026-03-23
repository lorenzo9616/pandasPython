"""Tests for PythonScripts/data_processor.py"""

import pytest
import data_processor


class TestLoadAndValidate:
    def test_loads_valid_file(self, sample_xlsx):
        df = data_processor.load_and_validate(sample_xlsx)
        assert len(df) == 20
        assert "Product" in df.columns

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            data_processor.load_and_validate("/nonexistent/file.xlsx")

    def test_raises_on_bad_extension(self, tmp_path):
        bad_file = tmp_path / "data.csv"
        bad_file.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match="Only .xlsx"):
            data_processor.load_and_validate(str(bad_file))


class TestSummarizeByColumn:
    def test_group_by_category(self, sample_xlsx):
        result = data_processor.summarize_by_column(sample_xlsx, "Category")
        assert "Electronics" in result
        assert "Accessories" in result
        assert "Audio" in result

    def test_group_by_region(self, sample_xlsx):
        result = data_processor.summarize_by_column(sample_xlsx, "Region")
        assert "North" in result
        assert "South" in result

    def test_raises_on_missing_column(self, sample_xlsx):
        with pytest.raises(KeyError, match="not found"):
            data_processor.summarize_by_column(sample_xlsx, "NonExistent")


class TestFilterRows:
    def test_filter_by_category(self, sample_xlsx):
        result = data_processor.filter_rows(sample_xlsx, "Category", "Audio")
        assert "Headset" in result

    def test_filter_case_insensitive(self, sample_xlsx):
        result = data_processor.filter_rows(sample_xlsx, "Region", "north")
        assert "North" in result or "north" in result.lower()

    def test_filter_no_match(self, sample_xlsx):
        result = data_processor.filter_rows(sample_xlsx, "Region", "Antarctica")
        assert "No rows found" in result

    def test_filter_raises_on_missing_column(self, sample_xlsx):
        with pytest.raises(KeyError, match="not found"):
            data_processor.filter_rows(sample_xlsx, "Fake", "value")


class TestGetSchema:
    def test_returns_column_info(self, sample_xlsx):
        schema = data_processor.get_schema(sample_xlsx)
        assert "Columns:" in schema
        assert "Revenue" in schema
        assert "Product" in schema
