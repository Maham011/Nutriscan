import pandas as pd
from pydantic import BaseModel, Field, ValidationError


# ---------- Validation model ----------
class FoodProduct(BaseModel):
    product_code: str = Field(pattern=r"^\d{8,14}$")
    product_name: str = Field(min_length=1)
    brand: str | None = None
    category: str | None = None
    energy_kcal: float | None = Field(default=None, ge=0, le=1000)
    sugars_g: float | None = Field(default=None, ge=0, le=100)
    proteins_g: float | None = Field(default=None, ge=0, le=100)
    carbohydrates_g: float | None = Field(default=None, ge=0, le=100)
    fat_g: float | None = Field(default=None, ge=0, le=100)
    saturated_fat_g: float | None = Field(default=None, ge=0, le=100)
    salt_g: float | None = Field(default=None, ge=0, le=100)
    ingredients: str | None = None
    nutrition_grade: str | None = Field(default=None, pattern=r"^[a-e]$")


# ---------- Load ----------
df = pd.read_csv("raw_food_data.csv", dtype={"product_code": str}, encoding="utf-8-sig")

# ---------- Standardize column names ----------
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

# ---------- Clean text fields ----------
text_columns = ["product_code", "product_name", "brand", "category", "ingredients", "nutrition_grade"]

for column in text_columns:
    df[column] = (
        df[column]
        .str.replace("&quot;", '"', regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df[column] = df[column].replace("", None)

df["category"] = df["category"].str.replace(r"(^|, )[a-z]{2}:", r"\1", regex=True)

df["nutrition_grade"] = df["nutrition_grade"].str.lower()
df.loc[~df["nutrition_grade"].isin(list("abcde")), "nutrition_grade"] = None

df.loc[df["product_name"] == df["product_code"], "product_name"] = None

# ---------- Convert nutrition values to numbers ----------
nutrition_columns = [
    "energy_kcal", "sugars_g", "proteins_g", "carbohydrates_g",
    "fat_g", "saturated_fat_g", "salt_g",
]

for column in nutrition_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")
    df[column] = df[column].round(6 if column == "salt_g" else 2)

# ---------- Remove duplicates ----------
df = df.drop_duplicates(subset=["product_code"], keep="first")

accents = r"[\u0300-\u036f]"

df["name_key"] = (
    df["product_name"].fillna("")
    .str.lower()
    .str.normalize("NFKD")
    .str.replace(accents, "", regex=True)
    .str.replace(r"\b\d+([.,]\d+)?\s?(cl|ml|l|g|kg)\b", "", regex=True)
    .str.replace(r"[\W_]+", "", regex=True)
)

df["brand_key"] = (
    df["brand"].fillna("")
    .str.lower()
    .str.normalize("NFKD")
    .str.replace(accents, "", regex=True)
    .str.replace(r"[^\w,]+", "", regex=True)
)

# Most complete records first, so the best one is kept
df["filled"] = df.notna().sum(axis=1)
df = df.sort_values("filled", ascending=False)

kept_rows = []
looked_at = []

for _, row in df.iterrows():
    is_duplicate = False

    for other in looked_at:
        same_name = row["name_key"] != "" and row["name_key"] == other["name_key"]
        same_brand = len(
            set(row["brand_key"].split(",")) & set(other["brand_key"].split(",")) - {""}
        ) > 0
        same_numbers = (row[nutrition_columns] == other[nutrition_columns]).all()
        one_is_empty = (
            row[nutrition_columns].isna().all() or other[nutrition_columns].isna().all()
        )

        if (
            (same_name and same_brand)
            or (same_numbers and (same_brand or same_name))
            or (same_name and one_is_empty)
        ):
            is_duplicate = True
            break

    if not is_duplicate:
        kept_rows.append(row)

    looked_at.append(row)

df = pd.DataFrame(kept_rows).sort_index()
df = df.drop(columns=["name_key", "brand_key", "filled"])

# ---------- Validate with Pydantic ----------
valid_records = []
rejected_records = []

for _, row in df.iterrows():
    record = {key: (None if pd.isna(value) else value) for key, value in row.to_dict().items()}

    try:
        valid_records.append(FoodProduct.model_validate(record).model_dump())
    except ValidationError as error:
        first_error = error.errors()[0]
        record["validation_error"] = f"{first_error['loc'][0]}: {first_error['msg']}"
        rejected_records.append(record)

# ---------- Save ----------
pd.DataFrame(valid_records).to_csv("cleaned_food_data.csv", index=False, encoding="utf-8-sig")

if rejected_records:
    pd.DataFrame(rejected_records).to_csv("rejected_food_data.csv", index=False, encoding="utf-8-sig")