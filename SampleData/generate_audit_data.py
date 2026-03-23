"""
generate_audit_data.py
----------------------
Creates two sample Excel files for the Office Auditor feature:
  - staff_list.xlsx  (15 employees with department and role info)
  - task_logs.xlsx   (multiple task log entries per employee)

Run:  python generate_audit_data.py
"""

import pandas as pd

# ---------- Staff List ----------

staff_data = {
    "EmployeeID": [f"E{i:03d}" for i in range(1, 16)],
    "EmployeeName": [
        "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
        "Eve Davis", "Frank Miller", "Grace Wilson", "Henry Moore",
        "Irene Taylor", "Jack Anderson", "Karen Thomas", "Leo Martinez",
        "Mia Robinson", "Noah Clark", "Olivia Lewis",
    ],
    "Department": [
        "Engineering", "Engineering", "Marketing", "Engineering", "Marketing",
        "Sales", "Engineering", "Sales", "Marketing", "Engineering",
        "Sales", "Engineering", "Sales", "Marketing", "Engineering",
    ],
    "Role": [
        "Senior Dev", "Junior Dev", "Content Lead", "Tech Lead", "Analyst",
        "Account Exec", "Mid Dev", "Account Exec", "Designer", "Senior Dev",
        "Sales Manager", "Junior Dev", "Account Exec", "Analyst", "Mid Dev",
    ],
    "HourlyRate": [
        75.0, 45.0, 60.0, 90.0, 55.0,
        50.0, 65.0, 50.0, 58.0, 75.0,
        70.0, 45.0, 50.0, 55.0, 65.0,
    ],
}

staff_df = pd.DataFrame(staff_data)
staff_df.to_excel("staff_list.xlsx", index=False, engine="openpyxl")
print(f"Created staff_list.xlsx with {len(staff_df)} employees.")

# ---------- Task Logs ----------
# Multiple entries per employee to simulate a month of work

task_entries = []
# (EmployeeID, Week, TasksCompleted, HoursWorked)
raw_logs = [
    # Alice — high performer
    ("E001", "Week1", 12, 38), ("E001", "Week2", 14, 40),
    ("E001", "Week3", 11, 36), ("E001", "Week4", 15, 42),
    # Bob — low efficiency
    ("E002", "Week1", 3, 40), ("E002", "Week2", 4, 42),
    ("E002", "Week3", 2, 38), ("E002", "Week4", 3, 41),
    # Carol — moderate
    ("E003", "Week1", 8, 35), ("E003", "Week2", 7, 34),
    ("E003", "Week3", 9, 37), ("E003", "Week4", 8, 36),
    # David — tech lead, solid
    ("E004", "Week1", 10, 45), ("E004", "Week2", 11, 44),
    ("E004", "Week3", 9, 43), ("E004", "Week4", 12, 46),
    # Eve — moderate
    ("E005", "Week1", 6, 32), ("E005", "Week2", 7, 34),
    ("E005", "Week3", 5, 30), ("E005", "Week4", 6, 33),
    # Frank — sales, good
    ("E006", "Week1", 9, 36), ("E006", "Week2", 10, 38),
    ("E006", "Week3", 8, 35), ("E006", "Week4", 11, 40),
    # Grace — high performer
    ("E007", "Week1", 13, 39), ("E007", "Week2", 12, 38),
    ("E007", "Week3", 14, 41), ("E007", "Week4", 13, 40),
    # Henry — low efficiency
    ("E008", "Week1", 4, 40), ("E008", "Week2", 3, 39),
    ("E008", "Week3", 5, 42), ("E008", "Week4", 4, 41),
    # Irene — moderate
    ("E009", "Week1", 7, 33), ("E009", "Week2", 8, 35),
    ("E009", "Week3", 6, 32), ("E009", "Week4", 7, 34),
    # Jack — strong performer
    ("E010", "Week1", 11, 40), ("E010", "Week2", 12, 41),
    ("E010", "Week3", 10, 39), ("E010", "Week4", 13, 42),
    # Karen — sales manager, most hours
    ("E011", "Week1", 8, 48), ("E011", "Week2", 9, 50),
    ("E011", "Week3", 7, 47), ("E011", "Week4", 10, 51),
    # Leo — junior, struggling
    ("E012", "Week1", 2, 38), ("E012", "Week2", 3, 40),
    ("E012", "Week3", 2, 37), ("E012", "Week4", 4, 41),
    # Mia — sales, decent
    ("E013", "Week1", 7, 36), ("E013", "Week2", 8, 38),
    ("E013", "Week3", 6, 35), ("E013", "Week4", 9, 39),
    # Noah — moderate
    ("E014", "Week1", 5, 34), ("E014", "Week2", 6, 36),
    ("E014", "Week3", 5, 33), ("E014", "Week4", 7, 37),
    # Olivia — solid mid-level
    ("E015", "Week1", 9, 38), ("E015", "Week2", 10, 40),
    ("E015", "Week3", 8, 37), ("E015", "Week4", 11, 41),
]

tasks_df = pd.DataFrame(
    raw_logs,
    columns=["EmployeeID", "Week", "TasksCompleted", "HoursWorked"],
)
tasks_df.to_excel("task_logs.xlsx", index=False, engine="openpyxl")
print(f"Created task_logs.xlsx with {len(tasks_df)} log entries.")
