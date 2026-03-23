# Data Flow Diagrams

## Single-File Mode Flow

```
                ┌───────────┐
                │ sales.xlsx│
                └─────┬─────┘
                      │
                      ▼
               ┌──────────────┐
               │ pd.read_excel│
               │ (openpyxl)   │
               └──────┬───────┘
                      │
              ┌───────┼───────┐
              ▼       ▼       ▼
         ┌────────┐ ┌─────┐ ┌──────┐
         │GroupBy  │ │Filtr│ │Schema│
         │ agg    │ │  er │ │      │
         └───┬────┘ └──┬──┘ └──┬───┘
             │         │       │
             └────┬────┘       │
                  ▼            ▼
         ┌──────────────┐  (printed
         │ Context str  │   to user)
         │ (text table) │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Chunk text   │
         │  into blocks  │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Embed each   │  ← all-MiniLM-L6-v2
         │  chunk (384d)  │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ Cosine search │  ← top-3 chunks
         │ vs query vec  │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ build_prompt  │  ← generic data analyst
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Ollama LLM   │  → answer string
         └──────────────┘
```

## Audit Mode Flow (Two-File Merge)

```
  ┌──────────────┐    ┌──────────────┐
  │ staff_list   │    │ task_logs    │
  │   .xlsx      │    │   .xlsx      │
  │              │    │              │
  │ EmployeeID   │    │ EmployeeID   │
  │ EmployeeName │    │ Week         │
  │ Department   │    │ TasksDone    │
  │ Role         │    │ HoursWorked  │
  │ HourlyRate   │    │              │
  └──────┬───────┘    └──────┬───────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
          ┌────────────────┐
          │  pd.merge()     │
          │  on=EmployeeID  │
          │  how="inner"    │
          └────────┬───────┘
                   │
                   ▼
          ┌────────────────┐
          │ 60 rows        │  (15 employees × 4 weeks)
          │ 8 columns      │
          └────────┬───────┘
                   │
                   ▼
          ┌────────────────────────────────┐
          │  GroupBy(EmployeeName).agg()    │
          │                                │
          │  total_hours  = sum(Hours)      │
          │  total_tasks  = sum(Tasks)      │
          │  tasks_per_hr = tasks/hours     │
          │  workload_pct = hrs/team × 100  │
          └────────┬───────────────────────┘
                   │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
    ┌─────────┐ ┌────────┐ ┌─────────────┐
    │ Top 5   │ │Bottom 5│ │ Summary     │
    │ by TPH  │ │by TPH  │ │ Stats       │
    │         │ │        │ │             │
    │ Grace   │ │ Leo    │ │ Headcount:15│
    │ Alice   │ │ Bob    │ │ AvgTPH:0.20 │
    │ Jack    │ │ Henry  │ │ MostHrs:    │
    │ Frank   │ │ Noah   │ │  Karen 196h │
    │ Olivia  │ │ Eve    │ │ LeastEff:   │
    │         │ │        │ │  Leo 0.071  │
    └────┬────┘ └───┬────┘ └──────┬──────┘
         │         │              │
         └────┬────┘              │
              │                   │
              ▼                   ▼
    ┌─────────────────────────────────────┐
    │       MARKDOWN CONTEXT STRING        │
    │                                     │
    │  ## Office Audit — Productivity...  │
    │  #### Team Summary Statistics        │
    │  | Metric | Value |                 │
    │  | --- | --- |                      │
    │  | Headcount | 15 |                 │
    │  ...                                │
    │  #### Top 5 Performers              │
    │  ...                                │
    │  #### Bottom 5 Performers           │
    │  ...                                │
    │  #### Full Ranking                  │
    │  ...                                │
    └────────────────┬────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────┐
    │           RAG PIPELINE               │
    │                                      │
    │  1. Split into chunks (by \\n\\n)      │
    │  2. Embed chunks → 384-dim vectors   │
    │  3. Embed user query                 │
    │  4. Cosine similarity → top 5        │
    │  5. Build AUDITOR prompt:            │
    │     ┌──────────────────────────────┐ │
    │     │ "You are an expert Office    │ │
    │     │  Productivity Auditor..."    │ │
    │     │                              │ │
    │     │  Mandatory analysis:         │ │
    │     │  1. Least performing member  │ │
    │     │  2. Most time-allotted       │ │
    │     │  3. Productivity trends      │ │
    │     │  4. Numbers-backed claims    │ │
    │     └──────────────────────────────┘ │
    │  6. Send to Ollama                   │
    └────────────────┬─────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────┐
    │            LLM RESPONSE              │
    │                                      │
    │  "Based on the productivity data:    │
    │                                      │
    │   1. LEAST PERFORMING: Leo Martinez  │
    │      with 0.071 tasks/hour...        │
    │                                      │
    │   2. MOST HOURS: Karen Thomas        │
    │      logged 196.0 hours (8.5% of     │
    │      team total)...                  │
    │                                      │
    │   3. TRENDS: The team shows a wide   │
    │      spread in efficiency (std dev   │
    │      0.082). Engineering tends to    │
    │      outperform Sales and Marketing  │
    │      in tasks/hour..."               │
    └──────────────────────────────────────┘
```

## C# ↔ Python Interop Flow

```
   C# (.NET 8)                                    Python 3.11
   ════════════                                    ══════════

   Runtime.PythonDLL = "libpython3.11.so"
         │
         ▼
   PythonEngine.Initialize()  ────────────────►  Py_Initialize()
         │
         ▼
   using (Py.GIL())  ────────────────────────►  PyGILState_Ensure()
         │                                           │
         ├── dynamic sys = Py.Import("sys")          │
         │        │                                  │
         │        └── sys.path.append(scripts_dir)   │
         │                                           │
         ├── dynamic engine = Py.Import(             │
         │       "analysis_engine")                  │
         │        │                                  │
         │        └── string ctx = engine             │
         │              .build_audit_context(         │
         │                  staffPath,               │
         │                  tasksPath,               │
         │                  mergeKey                 │
         │              ).ToString()                 │
         │                    │                      │
         │                    └────── returns ◄──── pd.merge()
         │                              Markdown     pd.groupby()
         │                              string       .agg()
         │                                           │
         ├── dynamic rag = Py.Import(                │
         │       "rag_engine")                       │
         │        │                                  │
         │        └── string answer = rag             │
         │              .ask_auditor(                 │
         │                  query,                   │
         │                  ctx,                     │
         │                  model                    │
         │              ).ToString()                 │
         │                    │                      │
         │                    └────── returns ◄──── embed()
         │                              LLM          search()
         │                              answer       call_ollama()
         │                                           │
   } // GIL released  ──────────────────────────►  PyGILState_Release()
         │
         ▼
   PythonEngine.Shutdown()  ─────────────────►  Py_Finalize()
```
