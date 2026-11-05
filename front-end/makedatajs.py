import json
from pathlib import Path

import pandas as pd

CSV_FILE = Path("cleaned_food_data.csv")
OUTPUT_FILE = Path("data.js")

FOOD_GROUP_RULES = [
    ("Waters", ["water"]),
    ("Dairy", ["cheese", "cheddar", "fromage", "yogurt", "skyr", "kefir", "milk", "dairy"]),
    ("Biscuits", ["biscuit", "wafer", "cracker"]),
    ("Breads", ["bread", "rusk", "brioche", "pain"]),
    ("Cereals", ["cereal", "muesli", "oat"]),
    ("Spreads", ["spread", "butter", "margarine", "tartiner"]),
    ("Chocolate", ["chocolate"]),
    ("Drinks", ["beverage", "drink", "juice", "cola"]),
]


def get_food_group(category_text):
    if pd.isna(category_text):
        return "Other"
    text = str(category_text).lower()
    for group_name, keywords in FOOD_GROUP_RULES:
        if any(keyword in text for keyword in keywords):
            return group_name
    return "Other"


def clean_value(value):
    if pd.isna(value):
        return None
    return value


def main():
    df = pd.read_csv(CSV_FILE, dtype={"product_code": str}, encoding="utf-8-sig")
    df["food_group"] = df["category"].apply(get_food_group)

    columns = [
        "product_code",
        "product_name",
        "brand",
        "food_group",
        "category",
        "energy_kcal",
        "sugars_g",
        "proteins_g",
        "carbohydrates_g",
        "fat_g",
        "saturated_fat_g",
        "salt_g",
        "nutrition_grade",
    ]

    records = []
    for row in df[columns].to_dict(orient="records"):
        clean_row = {key: clean_value(value) for key, value in row.items()}
        records.append(clean_row)

    output = (
        "// data.js - made by make_data_js.py from cleaned_food_data.csv\n"
        + "// One object per product. null means the value is missing.\n"
        + "const PRODUCTS = " + json.dumps(records, ensure_ascii=False, indent=1) + ";\n"
    )
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    print(f"Wrote {len(records)} products to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()