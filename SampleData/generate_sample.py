"""
generate_sample.py
------------------
Run this once to create a sample sales.xlsx file for testing.

    python generate_sample.py
"""

import pandas as pd

data = {
    "OrderID": list(range(1001, 1021)),
    "Product": [
        "Laptop", "Mouse", "Keyboard", "Monitor", "Laptop",
        "Webcam", "Mouse", "Headset", "Monitor", "Keyboard",
        "Laptop", "Webcam", "Headset", "Mouse", "Monitor",
        "Keyboard", "Laptop", "Headset", "Webcam", "Mouse",
    ],
    "Category": [
        "Electronics", "Accessories", "Accessories", "Electronics", "Electronics",
        "Accessories", "Accessories", "Audio", "Electronics", "Accessories",
        "Electronics", "Accessories", "Audio", "Accessories", "Electronics",
        "Accessories", "Electronics", "Audio", "Accessories", "Accessories",
    ],
    "Region": [
        "North", "South", "East", "West", "North",
        "South", "East", "West", "North", "South",
        "East", "West", "North", "South", "East",
        "West", "North", "South", "East", "West",
    ],
    "Quantity": [
        2, 10, 5, 1, 3,
        8, 15, 4, 2, 7,
        1, 6, 3, 12, 1,
        9, 2, 5, 4, 20,
    ],
    "UnitPrice": [
        999.99, 29.99, 79.99, 349.99, 1099.99,
        59.99, 24.99, 149.99, 399.99, 89.99,
        1199.99, 49.99, 129.99, 19.99, 449.99,
        69.99, 949.99, 139.99, 54.99, 22.99,
    ],
    "Revenue": [
        2000.0, 300.0, 400.0, 350.0, 3300.0,
        480.0, 375.0, 600.0, 800.0, 630.0,
        1200.0, 300.0, 390.0, 240.0, 450.0,
        630.0, 1900.0, 700.0, 220.0, 460.0,
    ],
}

df = pd.DataFrame(data)
df.to_excel("sales.xlsx", index=False, engine="openpyxl")
print(f"Created sales.xlsx with {len(df)} rows.")
