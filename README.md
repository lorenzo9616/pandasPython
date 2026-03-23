# Simple RAG System — .NET (C#) + Python (Pandas)

A complete sample project that implements **Retrieval-Augmented Generation (RAG)** using:

- **C# / .NET 8** as the host application (via `pythonnet`)
- **Python / Pandas** for Excel data processing
- **Sentence-Transformers** for local embeddings
- **Ollama** for local LLM inference

Everything runs locally with **open-source libraries only** — no API keys required.

---

## Project Structure

```
pandasPython/
├── RagHost/                    # .NET 8 console application
│   ├── RagHost.csproj
│   └── Program.cs              # C# interop layer (pythonnet + GIL)
├── PythonScripts/
│   ├── data_processor.py       # Pandas: load Excel, GroupBy, filter
│   └── rag_engine.py           # Embeddings, vector store, Ollama calls
├── SampleData/
│   └── generate_sample.py      # Script to create a sample sales.xlsx
├── tests/
│   ├── conftest.py             # Shared fixtures (auto-generates sample data)
│   ├── test_data_processor.py  # Unit tests for Pandas operations
│   └── test_rag_engine.py      # Unit tests for RAG pipeline
├── scripts/
│   ├── setup.sh                # One-command local setup
│   └── run_tests.sh            # Test runner
├── Dockerfile                  # Multi-stage: .NET 8 + Python 3.11
├── docker-compose.yml          # App + Ollama + test services
├── .dockerignore
├── requirements.txt            # Python dependencies
├── RagHost.sln
└── README.md
```

---

## Quick Start

### Option A: Docker (recommended)

```bash
# Build and run (data retrieval only — no LLM needed)
docker compose up --build rag-app

# Run with Ollama for full RAG pipeline
docker compose up --build

# Run tests inside Docker
docker compose --profile test run --rm tests

# Custom query (override the default command)
docker compose run --rm rag-app \
    --file /app/SampleData/sales.xlsx \
    --group Category \
    --query "Which category has the highest revenue?"
```

### Option B: Local Setup

```bash
# One-command setup (installs deps, generates sample data, restores .NET)
bash scripts/setup.sh

# Or step-by-step:
pip install -r requirements.txt
pip install pytest
cd SampleData && python generate_sample.py && cd ..
cd RagHost && dotnet restore && cd ..
```

---

## Installation

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| .NET SDK | 8.0+ | Build & run the C# host |
| Python | 3.10 – 3.12 | Runtime for Pandas + embeddings |
| Docker | 24+ | Containerised deployment (optional) |
| Ollama | latest | Local LLM server (optional for RAG step) |

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
pip install pytest           # for running tests
```

**What gets installed:**

| Package | Version | Purpose |
|---------|---------|---------|
| `pandas` | >= 2.0 | DataFrame operations on Excel data |
| `openpyxl` | >= 3.1 | Excel .xlsx read/write engine |
| `sentence-transformers` | >= 2.2 | Local embedding model (all-MiniLM-L6-v2) |
| `numpy` | >= 1.24 | Vector operations for similarity search |
| `pytest` | latest | Test framework |

### 2. Install .NET NuGet packages

```bash
cd RagHost
dotnet restore          # pulls pythonnet 3.0.3 from NuGet
```

Or add manually:

```bash
dotnet add package pythonnet --version 3.0.3
```

### 3. Generate sample data

```bash
cd SampleData
python generate_sample.py    # creates sales.xlsx (20 rows of sales data)
```

### 4. (Optional) Set up Ollama for LLM inference

```bash
# Install Ollama: https://ollama.com
ollama serve                 # start the server
ollama pull llama3           # download a model (~4 GB)
```

### 5. Set the Python DLL path

pythonnet needs to know where your Python shared library lives:

```bash
# Linux
export PYTHON_DLL=/usr/lib/x86_64-linux-gnu/libpython3.11.so

# macOS (Homebrew)
export PYTHON_DLL=/opt/homebrew/Frameworks/Python.framework/Versions/3.11/lib/libpython3.11.dylib

# Windows (PowerShell)
$env:PYTHON_DLL = "C:\Python311\python311.dll"
```

---

## Running the Application

### With .NET (native)

```bash
cd RagHost

# Data retrieval only (no LLM)
dotnet run -- --file ../SampleData/sales.xlsx --group Category

# With filtering
dotnet run -- --file ../SampleData/sales.xlsx --filter-column Region --filter-value North

# Full RAG pipeline (requires Ollama running)
dotnet run -- --file ../SampleData/sales.xlsx \
    --group Category \
    --query "Which category generated the most revenue?" \
    --model llama3
```

### With Docker

```bash
# Build the image
docker compose build

# Run data retrieval (default command groups by Category)
docker compose up rag-app

# Full RAG with Ollama (starts both containers)
docker compose up

# Custom query
docker compose run --rm rag-app \
    --file /app/SampleData/sales.xlsx \
    -g Region \
    -q "Which region has the most orders?"

# Mount your own Excel file
docker compose run --rm \
    -v /path/to/your/data.xlsx:/app/data.xlsx \
    rag-app --file /app/data.xlsx --group YourColumn
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--file, -f` | Path to the Excel file **(required)** |
| `--group, -g` | Column name for GroupBy summarization |
| `--filter-column` | Column to filter on |
| `--filter-value` | Value to match in the filter column |
| `--query, -q` | Natural-language question for the RAG pipeline |
| `--model, -m` | Ollama model name (default: `llama3`) |

---

## Testing

### Run tests locally

```bash
# Quick — using the helper script
bash scripts/run_tests.sh

# Or directly with pytest
python -m pytest tests/ -v --tb=short

# Run a specific test file
python -m pytest tests/test_data_processor.py -v

# Run a specific test class
python -m pytest tests/test_data_processor.py::TestSummarizeByColumn -v

# Run with coverage (install pytest-cov first)
pip install pytest-cov
python -m pytest tests/ -v --cov=PythonScripts --cov-report=term-missing
```

### Run tests in Docker

```bash
docker compose --profile test run --rm tests
```

### Test Suite Overview

| File | Tests | What it covers |
|------|-------|----------------|
| `test_data_processor.py` | 10 | Excel loading, validation, GroupBy, filtering, schema |
| `test_rag_engine.py` | 6 | Prompt building, embedding shapes, vector search, Ollama error handling |

**Tests that run without extra dependencies:**
- All `data_processor` tests (need only pandas + openpyxl)
- `TestBuildPrompt` and `TestCallOllama` (no ML libraries needed)

**Tests that require sentence-transformers:**
- `TestEmbedding` and `TestSimpleVectorStore` (auto-skipped if not installed)

---

## How It Works

### 1. C# Interop Layer (`Program.cs`)

```
PythonEngine.Initialize()
 └─> Py.GIL()                          // acquire the Global Interpreter Lock
      ├─> import data_processor         // Pandas: load Excel, GroupBy / filter
      │    └─> returns context string
      ├─> import rag_engine             // embed context, retrieve top-k chunks
      │    └─> call Ollama, return answer
      └─> release GIL
PythonEngine.Shutdown()
```

### 2. Pandas Data Processing (`data_processor.py`)

- Loads `.xlsx` via `pd.read_excel()` with openpyxl engine
- `summarize_by_column()` — groups by a column, aggregates numerics (count/mean/sum)
- `filter_rows()` — filters rows where a column matches a value
- Returns plain-text table strings as RAG context

### 3. RAG Engine (`rag_engine.py`)

- Embeds text chunks with `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- Stores vectors in a simple NumPy array (no external vector DB)
- Retrieves top-3 most similar chunks via cosine similarity
- Builds a constrained prompt and sends it to Ollama's `/api/generate` endpoint

---

## Docker Architecture

```
docker-compose.yml
 ├── rag-app      .NET 8 + Python 3.11 (multi-stage build)
 │    ├── Builds C# app in SDK image
 │    └── Runs in runtime image with Python installed
 ├── ollama       Local LLM server (GPU optional)
 │    └── Persists models in named volume
 └── tests        Same image as rag-app, entrypoint = pytest
      └── Activated with --profile test
```

### Dockerfile Stages

| Stage | Base Image | Purpose |
|-------|-----------|---------|
| `build` | `mcr.microsoft.com/dotnet/sdk:8.0` | Compile and publish the C# app |
| `runtime` | `mcr.microsoft.com/dotnet/runtime:8.0` | Run with Python 3.11 + all pip deps |

---

## Memory Management: pythonnet Internals

### How pythonnet bridges managed C# and unmanaged Python memory

pythonnet (Python.Runtime) sits at the boundary between two garbage-collected runtimes that know nothing about each other. Here is how it manages the transition:

#### 1. Reference Counting ↔ Garbage Collection

| Side | Strategy | Mechanism |
|------|----------|-----------|
| **Python** | Reference counting + cycle collector | `Py_INCREF` / `Py_DECREF` |
| **C# (.NET)** | Tracing garbage collector | Finalizers, `IDisposable` |

When C# code holds a Python object (via `PyObject`), pythonnet calls `Py_INCREF` to prevent Python's reference counter from freeing it. When the C# wrapper is disposed or finalized, pythonnet calls `Py_DECREF` to let Python reclaim the memory.

#### 2. The Global Interpreter Lock (GIL)

Python's GIL ensures only one thread executes Python bytecode at a time. pythonnet exposes this via `Py.GIL()`:

```csharp
using (Py.GIL())           // acquires the GIL
{
    dynamic np = Py.Import("numpy");
    // ... safe to call Python here
}                            // GIL released automatically (IDisposable)
```

**Critical rule:** Every Python call from C# must happen inside a `Py.GIL()` block. Forgetting this causes segfaults or data corruption.

#### 3. Object Lifecycle

```
C# code creates PyObject wrapper
  → pythonnet calls Py_INCREF on the underlying CPython object
  → C# uses the object (inside GIL block)
  → C# disposes / GC finalizes the PyObject
  → pythonnet calls Py_DECREF (must re-acquire GIL if called from finalizer)
  → when refcount reaches 0, CPython frees the memory
```

#### 4. Preventing Leaks

- **Use `using` blocks** for `Py.GIL()` — guarantees lock release.
- **Dispose `PyObject` instances** when done, especially in loops.
- **Call `PythonEngine.Shutdown()`** outside the GIL block — it finalizes all remaining Python objects and releases the interpreter.
- **Avoid storing `PyObject` references** beyond the GIL scope — they become dangling pointers once the GIL is released.

#### 5. Data Marshalling

Primitive types (int, float, string, bool) are automatically marshalled between C# and Python. For complex types (DataFrames, numpy arrays), pythonnet uses `dynamic` dispatch, which invokes Python's `__getattr__`/`__setattr__` under the hood via the CPython C-API. The data stays in Python's heap; C# gets a thin proxy, not a copy.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `DllNotFoundException: python3.XX` | Set `PYTHON_DLL` env variable to the full path of your Python shared library |
| `ModuleNotFoundError: No module named 'pandas'` | Run `pip install -r requirements.txt` in the same Python environment |
| `Ollama unreachable` | Start Ollama with `ollama serve`, then pull a model: `ollama pull llama3` |
| `PythonException: column not found` | Check column names in your Excel file — they are case-sensitive |
| Segfault on Python calls | Ensure all Python calls are inside a `Py.GIL()` block |
| Docker build fails on ARM | The Dockerfile targets x86_64; for ARM use `libpython3.11.aarch64.so` |
| Tests skip embedding tests | Install `sentence-transformers`: `pip install sentence-transformers` |

---

## License

This sample project is provided as-is for educational purposes. All dependencies are open-source:

- [pythonnet](https://github.com/pythonnet/pythonnet) — MIT
- [Pandas](https://pandas.pydata.org/) — BSD-3
- [sentence-transformers](https://www.sbert.net/) — Apache 2.0
- [Ollama](https://ollama.com/) — MIT
