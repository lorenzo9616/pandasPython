# Sample Scenarios — Office Auditor Commands & Expected Output

This document shows practical examples of how to use the Office Auditor
to answer real workforce management questions.

---

## Prerequisites

```bash
# Generate the sample data first
cd SampleData
python generate_sample.py
python generate_audit_data.py
cd ..
```

---

## Scenario 1: Comparing Working Hours of Employees

**Question:** "Who worked the most hours this month, and how are hours distributed?"

### Command (with .NET)

```bash
cd RagHost
dotnet run -- --audit \
    --staff ../SampleData/staff_list.xlsx \
    --tasks ../SampleData/task_logs.xlsx \
    -q "Who worked the most hours this month? Show the distribution of hours across all employees."
```

### Command (with Docker)

```bash
docker compose run --rm rag-audit \
    --audit \
    --staff /app/SampleData/staff_list.xlsx \
    --tasks /app/SampleData/task_logs.xlsx \
    -q "Who worked the most hours this month? Show the distribution of hours across all employees."
```

### Command (context only — no LLM needed)

```bash
cd RagHost
dotnet run -- --audit \
    --staff ../SampleData/staff_list.xlsx \
    --tasks ../SampleData/task_logs.xlsx
```

### Expected Output (Context)

```
--- Productivity Report ---

## Office Audit — Productivity Report

#### Team Summary Statistics

| Metric | Value |
| --- | --- |
| Headcount | 15 |
| Total team hours | 2299.0 |
| Most hours worked | Karen Thomas (196.0 hrs) |
| ...

#### Top 5 Performers (highest tasks/hour)

| EmployeeName | total_hours | total_tasks | tasks_per_hour | workload_pct |
| --- | --- | --- | --- | --- |
| Grace Wilson | 158.0 | 52 | 0.329 | 6.9 |
| Alice Johnson | 156.0 | 52 | 0.333 | 6.8 |
| ...

#### Bottom 5 Performers (lowest tasks/hour)

| EmployeeName | total_hours | total_tasks | tasks_per_hour | workload_pct |
| --- | --- | --- | --- | --- |
| Leo Martinez | 156.0 | 11 | 0.071 | 6.8 |
| Bob Smith | 161.0 | 12 | 0.075 | 7.0 |
| ...
```

### Visual: Hours Distribution

```
                    Monthly Hours Worked by Employee
                    ════════════════════════════════

Karen Thomas    ████████████████████████████████████████ 196 hrs  (8.5%)
David Brown     ████████████████████████████████████     178 hrs  (7.7%)
Jack Anderson   ████████████████████████████████         162 hrs  (7.0%)
Henry Moore     ████████████████████████████████         162 hrs  (7.0%)
Bob Smith       ████████████████████████████████         161 hrs  (7.0%)
Grace Wilson    ███████████████████████████████          158 hrs  (6.9%)
Alice Johnson   ███████████████████████████████          156 hrs  (6.8%)
Olivia Lewis    ███████████████████████████████          156 hrs  (6.8%)
Leo Martinez    ███████████████████████████████          156 hrs  (6.8%)
Frank Miller    ██████████████████████████████           149 hrs  (6.5%)
Mia Robinson    ██████████████████████████████           148 hrs  (6.4%)
Noah Clark      █████████████████████████████            140 hrs  (6.1%)
Irene Taylor    █████████████████████████████            134 hrs  (5.8%)
Carol Williams  █████████████████████████████            142 hrs  (6.2%)
Eve Davis       █████████████████████████                129 hrs  (5.6%)
                └───┴───┴───┴───┴───┴───┴───┴───┴───┘
                0  25  50  75 100 125 150 175 200
```

---

## Scenario 2: Comparing Performance / Delivery Efficiency

**Question:** "Who delivers the most tasks per hour? Rank all employees by efficiency."

### Command

```bash
cd RagHost
dotnet run -- --audit \
    --staff ../SampleData/staff_list.xlsx \
    --tasks ../SampleData/task_logs.xlsx \
    -q "Rank all employees by tasks per hour efficiency. Who is the most and least efficient?"
```

### Expected Analysis

```
                    Tasks Per Hour — Efficiency Ranking
                    ═══════════════════════════════════

 RANK  EMPLOYEE          TASKS/HR   ASSESSMENT
 ────  ────────────────  ────────   ──────────────────────
  1.   Grace Wilson       0.329     ★ Top performer
  2.   Alice Johnson      0.333     ★ Top performer
  3.   Jack Anderson      0.284     ● Above average
  4.   Frank Miller       0.255     ● Above average
  5.   David Brown        0.236     ● Above average
  6.   Olivia Lewis       0.244     ● Average
  7.   Carol Williams     0.225     ● Average
  8.   Mia Robinson       0.203     ● Average
  9.   Irene Taylor       0.209     ● Average
 10.   Eve Davis          0.186     ▽ Below average
 11.   Karen Thomas       0.173     ▽ Below average
 12.   Noah Clark         0.164     ▽ Below average
 13.   Henry Moore        0.099     ▼ Low performer
 14.   Bob Smith          0.075     ▼ Low performer
 15.   Leo Martinez       0.071     ▼ Lowest — needs review

       TEAM AVERAGE:      0.201 tasks/hr
       TEAM MEDIAN:       0.203 tasks/hr
       STD DEVIATION:     0.082
```

---

## Scenario 3: Comparing Tardiness / Missed Hours

**Question:** "Who has the lowest hours relative to expected? Are there employees
who might be missing activity?"

### Command

```bash
cd RagHost
dotnet run -- --audit \
    --staff ../SampleData/staff_list.xlsx \
    --tasks ../SampleData/task_logs.xlsx \
    -q "Assuming a standard 160-hour month, which employees worked fewer hours than expected? Who appears to have missed the most activity time?"
```

### Expected Analysis

```
                    Hours vs. Expected (160 hrs/month)
                    ══════════════════════════════════

                                      ACTUAL   DELTA   STATUS
Employee          Dept          Role  HOURS    vs 160
──────────────    ────────────  ────  ──────   ──────  ────────────
Karen Thomas      Sales         Mgr   196.0    +36.0   ● Overtime
David Brown       Engineering   Lead  178.0    +18.0   ● Overtime
Jack Anderson     Engineering   Sr    162.0     +2.0   ● On target
Henry Moore       Sales         Exec  162.0     +2.0   ● On target
Bob Smith         Engineering   Jr    161.0     +1.0   ● On target
Grace Wilson      Engineering   Mid   158.0     -2.0   ● On target
Alice Johnson     Engineering   Sr    156.0     -4.0   ● On target
Olivia Lewis      Engineering   Mid   156.0     -4.0   ● On target
Leo Martinez      Engineering   Jr    156.0     -4.0   ● On target
Frank Miller      Sales         Exec  149.0    -11.0   ▽ Under
Mia Robinson      Sales         Exec  148.0    -12.0   ▽ Under
Carol Williams    Marketing     Lead  142.0    -18.0   ▽ Under
Noah Clark        Marketing     Anl   140.0    -20.0   ▽ Under
Irene Taylor      Marketing     Dsgn  134.0    -26.0   ▼ Missed 26h
Eve Davis         Marketing     Anl   129.0    -31.0   ▼ Missed 31h

Employees below 140 hours:  3  (Eve Davis, Irene Taylor, Noah Clark)
Average hours across team:  153.3 hrs
```

---

## Scenario 4: Department-Level Comparison

**Question:** "How does Engineering compare to Sales and Marketing?"

### Command

```bash
cd RagHost
dotnet run -- --audit \
    --staff ../SampleData/staff_list.xlsx \
    --tasks ../SampleData/task_logs.xlsx \
    -q "Compare productivity across departments. Which department is most efficient?"
```

### Expected Analysis

```
                    Department Comparison
                    ═════════════════════

Department      Headcount  Avg Hrs  Avg Tasks/Hr  Total Output
──────────────  ─────────  ───────  ────────────  ────────────
Engineering         6       158.2      0.222         211 tasks
Sales               4       163.8      0.183         117 tasks
Marketing           5       137.0      0.196         119 tasks

Key Findings:
 • Engineering has the highest headcount AND best efficiency
 • Sales works the most hours but mid-range efficiency
 • Marketing works the fewest hours and delivers moderate output
```

---

## Scenario 5: Identify Employees Needing Support

**Question:** "Which employees should be flagged for a performance review?"

### Command

```bash
cd RagHost
dotnet run -- --audit \
    --staff ../SampleData/staff_list.xlsx \
    --tasks ../SampleData/task_logs.xlsx \
    -q "Which employees should be flagged for performance review? Consider both efficiency and total output."
```

---

## Python-Only Execution (No .NET Required)

You can also run the analysis engine directly from Python:

```bash
cd /path/to/pandasPython
python -c "
import sys; sys.path.insert(0, 'PythonScripts')
from analysis_engine import build_audit_context

context = build_audit_context(
    'SampleData/staff_list.xlsx',
    'SampleData/task_logs.xlsx'
)
print(context)
"
```

### Filter by merge key (custom column name)

```bash
python -c "
import sys; sys.path.insert(0, 'PythonScripts')
from analysis_engine import build_audit_context

# If your files use 'EmpID' instead of 'EmployeeID':
context = build_audit_context(
    'staff.xlsx', 'logs.xlsx',
    merge_key='EmpID',
    employee_col='FullName',
    hours_col='Hours',
    tasks_col='Completed'
)
print(context)
"
```

---

## Quick Reference — All Commands

```bash
# ─── SINGLE-FILE MODE ───────────────────────────────────────────────
# Group sales by category
dotnet run -- --file sales.xlsx --group Category

# Filter sales by region
dotnet run -- --file sales.xlsx --filter-column Region --filter-value North

# Ask a question about sales
dotnet run -- --file sales.xlsx -g Category -q "Which category sells most?"


# ─── AUDIT MODE ─────────────────────────────────────────────────────
# Generate productivity report (no LLM)
dotnet run -- --audit --staff staff_list.xlsx --tasks task_logs.xlsx

# Who worked the most hours?
dotnet run -- --audit --staff staff_list.xlsx --tasks task_logs.xlsx \
    -q "Who worked the most hours?"

# Who is least efficient?
dotnet run -- --audit --staff staff_list.xlsx --tasks task_logs.xlsx \
    -q "Who has the lowest tasks per hour?"

# Missing hours analysis
dotnet run -- --audit --staff staff_list.xlsx --tasks task_logs.xlsx \
    -q "Who worked fewer than 150 hours?"

# Department comparison
dotnet run -- --audit --staff staff_list.xlsx --tasks task_logs.xlsx \
    -q "Compare department productivity"

# Custom merge key
dotnet run -- --audit --staff staff.xlsx --tasks logs.xlsx \
    --merge-key EmpID -q "Productivity trends?"


# ─── DOCKER ─────────────────────────────────────────────────────────
# Build
docker compose build

# Run audit mode
docker compose up rag-audit

# Run with custom query
docker compose run --rm rag-audit --audit \
    --staff /app/SampleData/staff_list.xlsx \
    --tasks /app/SampleData/task_logs.xlsx \
    -q "Who needs a performance review?"

# Run tests
docker compose --profile test run --rm tests
```
