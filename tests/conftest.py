"""Shared fixtures for the RAG test suite."""

import os
import subprocess
import sys
import pytest
import pandas as pd

# Ensure PythonScripts is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonScripts"))

SAMPLE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "SampleData"))
SAMPLE_XLSX = os.path.join(SAMPLE_DIR, "sales.xlsx")


@pytest.fixture(scope="session", autouse=True)
def generate_sample_data():
    """Create the sample Excel file once before all tests."""
    if not os.path.isfile(SAMPLE_XLSX):
        subprocess.check_call(
            [sys.executable, "generate_sample.py"],
            cwd=SAMPLE_DIR,
        )
    yield


@pytest.fixture
def sample_xlsx():
    """Return the path to the sample Excel file."""
    return SAMPLE_XLSX


@pytest.fixture
def sample_df():
    """Return the sample DataFrame loaded from Excel."""
    return pd.read_excel(SAMPLE_XLSX, engine="openpyxl")
