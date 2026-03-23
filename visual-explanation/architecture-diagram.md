# Architecture Diagram — RAG System with Office Auditor

## High-Level System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER / CLI INPUT                             │
│                                                                     │
│  Single-File Mode:                                                  │
│    dotnet run -- --file sales.xlsx --group Category -q "..."        │
│                                                                     │
│  Audit Mode:                                                        │
│    dotnet run -- --audit --staff staff.xlsx --tasks logs.xlsx -q "." │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   C# HOST (Program.cs)                              │
│                   .NET 8 + pythonnet 3.0.3                          │
│                                                                     │
│  ┌─────────────────────────────────────────┐                        │
│  │  1. ResolvePythonDll()                  │                        │
│  │  2. PythonEngine.Initialize()           │                        │
│  │  3. Py.GIL() — acquire lock             │                        │
│  │  4. sys.path.append(PythonScripts/)     │                        │
│  └────────────────┬────────────────────────┘                        │
│                   │                                                  │
│  ┌────────────────▼────────────────────────┐                        │
│  │  Route to mode:                         │                        │
│  │   ├── RunSingleFileMode()               │                        │
│  │   │    → import data_processor          │                        │
│  │   │    → import rag_engine              │                        │
│  │   └── RunAuditMode()                    │                        │
│  │        → import analysis_engine         │                        │
│  │        → GetAIResponse()                │                        │
│  │        → import rag_engine              │                        │
│  └────────────────┬────────────────────────┘                        │
│                   │                                                  │
│  ┌────────────────▼────────────────────────┐                        │
│  │  5. PythonEngine.Shutdown()             │                        │
│  └─────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│data_processor│ │analysis_     │ │   rag_engine     │
│    .py       │ │ engine.py    │ │     .py          │
│              │ │              │ │                  │
│ •load_and_  │ │ •load_and_   │ │ •embed_texts()   │
│  validate() │ │  merge()     │ │ •SimpleVector    │
│ •summarize_ │ │ •calculate_  │ │  Store           │
│  by_column()│ │  productivity│ │ •build_prompt()  │
│ •filter_    │ │ •format_top_ │ │ •build_auditor_  │
│  rows()     │ │  bottom()    │ │  prompt()        │
│ •get_schema │ │ •format_     │ │ •call_ollama()   │
│  ()         │ │  summary_    │ │ •ask()           │
│              │ │  stats()     │ │ •ask_auditor()   │
│  [Pandas]   │ │ •build_audit │ │                  │
│              │ │  _context()  │ │  [sentence-      │
│              │ │              │ │   transformers]  │
│              │ │  [Pandas     │ │  [NumPy]         │
│              │ │   + merge]   │ │  [Ollama HTTP]   │
└──────────────┘ └──────────────┘ └──────────────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │   OLLAMA (LLM)   │
                                  │   localhost:11434 │
                                  │                  │
                                  │  Models:         │
                                  │  • llama3        │
                                  │  • mistral       │
                                  │  • phi3          │
                                  └──────────────────┘
```

## Audit Mode Data Flow (Detailed)

```
  staff_list.xlsx              task_logs.xlsx
  ┌────────────────┐           ┌─────────────────────┐
  │EmployeeID      │           │EmployeeID           │
  │EmployeeName    │           │Week                  │
  │Department      │           │TasksCompleted        │
  │Role            │           │HoursWorked           │
  │HourlyRate      │           │                     │
  └───────┬────────┘           └──────────┬──────────┘
          │                               │
          └──────────┬────────────────────┘
                     │
                     ▼  pd.merge(on="EmployeeID")
          ┌──────────────────────┐
          │   MERGED DataFrame   │
          │                      │
          │  EmployeeID          │
          │  EmployeeName        │
          │  Department          │
          │  Role                │
          │  HourlyRate          │
          │  Week                │
          │  TasksCompleted      │
          │  HoursWorked         │
          │                      │
          │  (60 rows = 15       │
          │   employees × 4 wks) │
          └──────────┬───────────┘
                     │
                     ▼  GroupBy(EmployeeName).agg(sum)
          ┌──────────────────────┐
          │  PRODUCTIVITY DF     │
          │                      │
          │  EmployeeName        │
          │  total_hours         │  ← sum(HoursWorked)
          │  total_tasks         │  ← sum(TasksCompleted)
          │  tasks_per_hour      │  ← total_tasks / total_hours
          │  workload_pct        │  ← hours / team_total × 100
          │                      │
          │  Sorted by           │
          │  tasks_per_hour DESC │
          └──────────┬───────────┘
                     │
          ┌──────────┼──────────────┐
          ▼          ▼              ▼
   ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │ Top 5    │ │ Bottom 5 │ │ Summary      │
   │Performers│ │Performers│ │ Statistics   │
   │          │ │          │ │              │
   │ Markdown │ │ Markdown │ │ • Headcount  │
   │ table    │ │ table    │ │ • Total hrs  │
   └──────┬───┘ └────┬─────┘ │ • Avg TPH   │
          │          │        │ • Most hrs   │
          └────┬─────┘        │ • Least eff  │
               │              └──────┬───────┘
               └──────┬──────────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │  MARKDOWN CONTEXT    │  ← Full audit report string
           │  (RAG input)         │
           └──────────┬───────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │  RAG PIPELINE        │
           │                      │
           │  1. Chunk context    │
           │  2. Embed chunks     │  ← sentence-transformers
           │  3. Embed query      │
           │  4. Cosine search    │  ← top-5 chunks
           │  5. Build auditor    │
           │     prompt           │
           │  6. Call Ollama      │
           └──────────┬───────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │  LLM ANSWER          │
           │                      │
           │  "Based on the data, │
           │   Leo Martinez has   │
           │   the lowest tasks/  │
           │   hour ratio..."     │
           └──────────────────────┘
```

## Docker Architecture

```
  docker-compose.yml
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
  │  │  rag-app     │  │  rag-audit   │  │  ollama   │  │
  │  │              │  │              │  │           │  │
  │  │ Single-file  │  │ Audit mode   │  │ LLM srv  │  │
  │  │ mode         │  │ (two files)  │  │ :11434   │  │
  │  │              │  │              │  │           │  │
  │  │ .NET 8 +     │  │ .NET 8 +     │  │ llama3   │  │
  │  │ Python 3.11  │  │ Python 3.11  │  │ mistral  │  │
  │  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  │
  │         │                 │                │         │
  │         └─────────────────┼────────────────┘         │
  │                           │                          │
  │  ┌──────────────┐   ┌─────┴─────┐                    │
  │  │  tests       │   │  volumes  │                    │
  │  │  (profile:   │   │           │                    │
  │  │   test)      │   │ ollama_   │                    │
  │  │  pytest      │   │  data     │                    │
  │  └──────────────┘   └───────────┘                    │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

## Memory Management Flow (pythonnet)

```
  C# (.NET GC)                          Python (RefCount + Cycle GC)
  ─────────────                          ──────────────────────────────

  ┌─────────────────┐
  │ Py.GIL()        │ ──── acquires ──── ┌─────────────────┐
  │ (IDisposable)   │                    │ GIL lock held   │
  └────────┬────────┘                    └────────┬────────┘
           │                                      │
           ▼                                      ▼
  ┌─────────────────┐    Py_INCREF()     ┌─────────────────┐
  │ PyObject wrapper│ ────────────────── │ CPython object   │
  │ (C# heap)       │                    │ (Python heap)    │
  │                 │                    │ refcount: 2      │
  └────────┬────────┘                    └────────┬────────┘
           │                                      │
           │ C# uses dynamic                      │
           │ dispatch (getattr)                    │
           │                                      │
           ▼                                      ▼
  ┌─────────────────┐    Py_DECREF()     ┌─────────────────┐
  │ Dispose() or    │ ────────────────── │ refcount: 1      │
  │ GC finalizer    │                    │ (Python still    │
  │                 │                    │  owns it)        │
  └────────┬────────┘                    └─────────────────┘
           │
           ▼
  ┌─────────────────┐
  │ } // GIL block  │ ──── releases ──── GIL lock freed
  │ ends            │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ PythonEngine.   │ ──── finalises ─── All remaining Python objects
  │ Shutdown()      │                    freed, interpreter released
  └─────────────────┘
```
