import os
import sqlite3

import pandas as pd
import matplotlib

matplotlib.use("Agg")  # lets us save graphs as files without opening a window
import matplotlib.pyplot as plt

# SETTINGS (you can change these)

CSV_FILE = "cleaned_food_data.csv"   # made by Person 2
DATABASE_FILE = "nutriscan.db"       # made by Person 3
OUTPUT_FOLDER = "eda_outputs"        # graphs and tables are saved here

# The nutrient columns we will analyse (same names the whole team agreed on)
NUTRIENTS = [
    "energy_kcal",
    "sugars_g",
    "proteins_g",
    "carbohydrates_g",
    "fat_g",
    "saturated_fat_g",
    "salt_g",
]

# Colours for the graphs (one calm blue, dark grey text)
BAR_COLOUR = "#2a78d6"
TEXT_COLOUR = "#52514e"

# Show wide tables fully in the terminal (instead of "...")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

# Create the output folder if it does not exist yet
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# STEP 1: LOAD THE CLEANED DATA

if os.path.exists(DATABASE_FILE):
    connection = sqlite3.connect(DATABASE_FILE)
    df = pd.read_sql("SELECT * FROM food_products", connection)
    connection.close()
    print("Data loaded from the database:", DATABASE_FILE)
else:
    # dtype keeps the barcode as text so leading zeros are not lost
    df = pd.read_csv(CSV_FILE, dtype={"product_code": str}, encoding="utf-8-sig")
    print("Data loaded from the CSV file:", CSV_FILE)

print("Number of products:", len(df))
print("Number of columns:", len(df.columns))
print("\nFirst 5 products:")
print(df[["product_name", "brand", "energy_kcal", "sugars_g"]].head())

# STEP 2: MAKE A SIMPLE FOOD GROUP FOR EACH PRODUCT

FOOD_GROUP_RULES = [
    ("Waters",             ["water"]),
    ("Dairy",              ["cheese", "cheddar", "fromage", "yogurt", "skyr", "kefir",
                            "milk", "dairy"]),
    ("Biscuits",           ["biscuit", "wafer", "cracker"]),
    ("Breads",             ["bread", "rusk", "brioche", "pain"]),
    ("Cereals",            ["cereal", "muesli", "oat"]),
    ("Spreads",            ["spread", "butter", "margarine", "tartiner"]),
    ("Chocolate",          ["chocolate"]),
    ("Drinks",             ["beverage", "drink", "juice", "cola"]),
]


def get_food_group(category_text):
    """Return one simple food group for a messy category text."""
    if pd.isna(category_text):
        return "Other"
    text = category_text.lower()          # make it lowercase so "Water" = "water"
    for group_name, keywords in FOOD_GROUP_RULES:
        for word in keywords:
            if word in text:
                return group_name
    return "Other"                        # sauces, salt, almonds, etc.


# .apply() runs our function on every row of the category column
df["food_group"] = df["category"].apply(get_food_group)

print("\nNumber of products in each food group:")
print(df["food_group"].value_counts())

# STEP 3: DESCRIPTIVE STATISTICS

# For each nutrient: how many values we have, mean (average),
# median (middle value), minimum and maximum.

stats = df[NUTRIENTS].agg(["count", "mean", "median", "min", "max"])
stats = stats.T.round(2)   # .T turns the table so nutrients are rows
stats.columns = ["Products with value", "Mean", "Median", "Minimum", "Maximum"]

print("\n=== Descriptive statistics (per 100 g) ===")
print(stats)
stats.to_csv(os.path.join(OUTPUT_FOLDER, "descriptive_statistics.csv"))

# STEP 4: COMPARE SUGAR, CALORIES AND PROTEIN BY FOOD GROUP

# groupby("food_group") puts products of the same group together,
# then .mean() calculates the average of each group.

by_group = df.groupby("food_group").agg(
    products=("product_name", "count"),
    avg_sugar_g=("sugars_g", "mean"),
    avg_calories_kcal=("energy_kcal", "mean"),
    avg_protein_g=("proteins_g", "mean"),
).round(1)

by_group = by_group.sort_values("avg_sugar_g", ascending=False)

print("\n=== Average values by food group (per 100 g) ===")
print(by_group)
by_group.to_csv(os.path.join(OUTPUT_FOLDER, "averages_by_food_group.csv"))

# STEP 5: ARE SUGAR AND CALORIES RELATED?


correlation = df["sugars_g"].corr(df["energy_kcal"])
print("\n=== Sugar vs calories ===")
print("Correlation (r) between sugar and calories:", round(correlation, 2))

if correlation > 0.7:
    print("This is a STRONG positive relation.")
elif correlation > 0.3:
    print("This is a MODERATE positive relation.")
else:
    print("This is a WEAK relation.")

# STEP 6: PRODUCTS WITH THE HIGHEST VALUES

# nlargest(5, column) gives the 5 rows with the biggest values.
# Products with a missing value are skipped automatically.

top_tables = []

for nutrient in ["sugars_g", "energy_kcal", "fat_g", "salt_g", "proteins_g"]:
    top5 = df.nlargest(5, nutrient)[["product_name", "food_group", nutrient]]
    print("\n=== Top 5 products by", nutrient, "===")
    print(top5.to_string(index=False))

    # keep a copy for the CSV file
    top5 = top5.rename(columns={nutrient: "value"})
    top5.insert(0, "nutrient", nutrient)
    top_tables.append(top5)

pd.concat(top_tables).to_csv(
    os.path.join(OUTPUT_FOLDER, "top_products.csv"), index=False
)

# STEP 7: MISSING NUTRITION INFORMATION

# .isna() gives True where a value is missing, .sum() counts the Trues.

missing = df[NUTRIENTS].isna().sum().sort_values(ascending=False)
missing_percent = (missing / len(df) * 100).round(1)

missing_table = pd.DataFrame({
    "missing_products": missing,
    "missing_percent": missing_percent,
})
print("\n=== Missing values per nutrient ===")
print(missing_table)
missing_table.to_csv(os.path.join(OUTPUT_FOLDER, "missing_values.csv"))

# How many products miss at least one nutrient?
rows_with_missing = df[NUTRIENTS].isna().any(axis=1).sum()
print("Products with at least one missing nutrient:", rows_with_missing,
      "out of", len(df))
print("Products with no nutrition grade:", df["nutrition_grade"].isna().sum())

# STEP 8: GRAPHS

# A small helper so all 5 graphs have the same clean style.

def style_graph(ax, title, x_label, y_label):
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=12)
    ax.set_xlabel(x_label, color=TEXT_COLOUR)
    ax.set_ylabel(y_label, color=TEXT_COLOUR)
    ax.spines["top"].set_visible(False)      # remove the box lines on top
    ax.spines["right"].set_visible(False)    # and on the right
    ax.tick_params(colors=TEXT_COLOUR)
    ax.grid(axis="y", color="#e5e5e5")       # light helper lines
    ax.set_axisbelow(True)                   # helper lines behind the bars


def save_graph(fig, file_name):
    path = os.path.join(OUTPUT_FOLDER, file_name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("Saved graph:", path)


def add_numbers_on_bars(ax, bars):
    """Write the value on top of each bar so the reader sees exact numbers."""
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height,
                f"{height:.0f}", ha="center", va="bottom",
                fontsize=9, color=TEXT_COLOUR)


print("\n=== Creating graphs ===")

# ---------- Graph 1: Average sugar by food group (bar chart) ----------
sugar = by_group["avg_sugar_g"].sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(sugar.index, sugar.values, color=BAR_COLOUR, width=0.6)
add_numbers_on_bars(ax, bars)
style_graph(ax, "1. Average sugar by food group",
            "Food group", "Average sugar (g per 100 g)")
plt.xticks(rotation=30, ha="right")
save_graph(fig, "1_avg_sugar_by_group.png")

# ---------- Graph 2: Average calories by food group (bar chart) ----------
calories = by_group["avg_calories_kcal"].sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(calories.index, calories.values, color=BAR_COLOUR, width=0.6)
add_numbers_on_bars(ax, bars)
style_graph(ax, "2. Average calories by food group",
            "Food group", "Average energy (kcal per 100 g)")
plt.xticks(rotation=30, ha="right")
save_graph(fig, "2_avg_calories_by_group.png")

# ---------- Graph 3: Distribution of sugar (histogram) ----------
# A histogram puts the sugar values into "bins" (ranges, e.g. 0-5 g, 5-10 g)
# and shows how many products fall into each range.
# dropna() removes missing values (we cannot place "unknown" in a range).

fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(df["sugars_g"].dropna(), bins=range(0, 65, 5),
        color=BAR_COLOUR, edgecolor="white", linewidth=2)
style_graph(ax, "3. Distribution of sugar content",
            "Sugar (g per 100 g)", "Number of products")
save_graph(fig, "3_sugar_distribution.png")

# ---------- Graph 4: Sugar vs calories (scatter plot) ----------
# Each dot is one product. Only products that have BOTH values are used.

both = df.dropna(subset=["sugars_g", "energy_kcal"])

fig, ax = plt.subplots(figsize=(9, 6))
ax.scatter(both["sugars_g"], both["energy_kcal"], s=50,
           color=BAR_COLOUR, alpha=0.8, edgecolors="white", linewidths=1.5)
style_graph(ax, f"4. Sugar vs calories  (r = {correlation:.2f})",
            "Sugar (g per 100 g)", "Energy (kcal per 100 g)")
ax.grid(axis="x", color="#e5e5e5")

# Write the names of a few interesting products next to their dots
for name in ["Nutella", "Coca-Cola Original Taste", "Menguy's Peanut 100%"]:
    row = both[both["product_name"] == name]
    if not row.empty:
        ax.annotate(name, (row["sugars_g"].iloc[0], row["energy_kcal"].iloc[0]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=9, color=TEXT_COLOUR)
save_graph(fig, "4_sugar_vs_calories.png")

# ---------- Graph 5: Missing nutrition information (bar chart) ----------
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(missing.index, missing.values, color=BAR_COLOUR, width=0.6)
add_numbers_on_bars(ax, bars)
style_graph(ax, "5. Products with missing nutrition information",
            "Nutrient", "Number of products with no value")
ax.set_ylim(0, max(missing.max() + 1, 5))
ax.yaxis.get_major_locator().set_params(integer=True)  # whole numbers only
plt.xticks(rotation=30, ha="right")
save_graph(fig, "5_missing_values.png")

# DONE

print("\nEDA finished! Open the folder", OUTPUT_FOLDER,
      "to see the 5 graphs and the CSV tables.")
