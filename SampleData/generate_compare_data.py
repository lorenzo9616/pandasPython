"""
generate_compare_data.py
------------------------
Creates 3 quarterly sales Excel files for multi-file comparison testing.
Each file has the same schema but different data to simulate Q1/Q2/Q3 reports.

Run:  python generate_compare_data.py
"""

import pandas as pd

# Shared structure: same columns across all three files
products = ["Laptop", "Mouse", "Keyboard", "Monitor", "Webcam",
            "Headset", "Tablet", "Printer"]
regions = ["North", "South", "East", "West"]

# ---------- Q1 ----------
q1_data = {
    "ProductID": [f"P{i:03d}" for i in range(1, 9)],
    "Product": products,
    "Region": ["North", "South", "East", "West", "North", "South", "East", "West"],
    "UnitsSold": [120, 450, 280, 65, 95, 180, 40, 30],
    "Revenue": [119880, 13455, 22372, 22749, 5699, 26998, 15996, 8997],
    "ReturnRate": [2.1, 1.5, 0.8, 3.2, 1.0, 2.5, 1.8, 4.0],
    "Quarter": ["Q1"] * 8,
}
q1 = pd.DataFrame(q1_data)
q1.to_excel("sales_q1.xlsx", index=False, engine="openpyxl")
print(f"Created sales_q1.xlsx with {len(q1)} rows.")

# ---------- Q2 (growth in most products, new product added) ----------
q2_data = {
    "ProductID": [f"P{i:03d}" for i in range(1, 10)],  # 9 products (Dock added)
    "Product": products + ["Docking Station"],
    "Region": ["North", "South", "East", "West", "North", "South", "East", "West", "North"],
    "UnitsSold": [135, 510, 260, 72, 110, 200, 55, 28, 45],
    "Revenue": [134865, 15249, 20774, 25192, 6599, 29998, 21995, 8397, 8995],
    "ReturnRate": [1.8, 1.2, 1.0, 2.8, 0.9, 2.0, 1.5, 4.5, 0.5],
    "Quarter": ["Q2"] * 9,
}
q2 = pd.DataFrame(q2_data)
q2.to_excel("sales_q2.xlsx", index=False, engine="openpyxl")
print(f"Created sales_q2.xlsx with {len(q2)} rows.")

# ---------- Q3 (decline in some, Printer dropped) ----------
q3_data = {
    "ProductID": [f"P{i:03d}" for i in [1, 2, 3, 4, 5, 6, 7, 9]],  # no P008 (Printer)
    "Product": [p for p in products if p != "Printer"] + ["Docking Station"],
    "Region": ["North", "South", "East", "West", "North", "South", "East", "North"],
    "UnitsSold": [110, 480, 300, 80, 130, 170, 60, 70],
    "Revenue": [109890, 14352, 23970, 27992, 7799, 25498, 23994, 13993],
    "ReturnRate": [2.5, 1.8, 0.7, 2.5, 1.2, 3.0, 1.2, 0.3],
    "Quarter": ["Q3"] * 8,
}
q3 = pd.DataFrame(q3_data)
q3.to_excel("sales_q3.xlsx", index=False, engine="openpyxl")
print(f"Created sales_q3.xlsx with {len(q3)} rows.")
