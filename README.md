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
├── requirements.txt            # Python dependencies
├── RagHost.sln
└── README.md
```

---

## Setup Guide

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| .NET SDK | 8.0+ | Build & run the C# host |
| Python | 3.10 – 3.12 | Runtime for Pandas + embeddings |
| Ollama | latest | Local LLM server (optional for RAG step) |

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

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
python generate_sample.py    # creates sales.xlsx
```

### 4. (Optional) Set up Ollama for LLM inference

```bash
# Install Ollama: https://ollama.com
ollama pull llama3           # or any model you prefer
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

---

## License

This sample project is provided as-is for educational purposes. All dependencies are open-source:

- [pythonnet](https://github.com/pythonnet/pythonnet) — MIT
- [Pandas](https://pandas.pydata.org/) — BSD-3
- [sentence-transformers](https://www.sbert.net/) — Apache 2.0
- [Ollama](https://ollama.com/) — MIT
