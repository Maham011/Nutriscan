import pandas as pd
from sqlalchemy import create_engine, Column, String, Float, text
from sqlalchemy.orm import declarative_base, Session

# STEP 1: CREATE THE SQLITE DATABASE CONNECTION

# This creates (or opens) the database file nutriscan.db in this folder
engine = create_engine("sqlite:///nutriscan.db")

Base = declarative_base()

# STEP 2: DESIGN THE food_products TABLE

class FoodProduct(Base):

    __tablename__ = "food_products"

    # primary_key=True means every product_code must be UNIQUE,
    # so the same barcode can never be stored twice
    product_code = Column(String, primary_key=True)

    # nullable=False means the name is required
    product_name = Column(String, nullable=False)

    # These can be empty (NULL) because the information may be missing
    brand = Column(String)
    category = Column(String)

    energy_kcal = Column(Float)
    sugars_g = Column(Float)
    proteins_g = Column(Float)
    carbohydrates_g = Column(Float)
    fat_g = Column(Float)
    saturated_fat_g = Column(Float)
    salt_g = Column(Float)

    ingredients = Column(String)
    nutrition_grade = Column(String)


# Create the table in the database (does nothing if it already exists)
Base.metadata.create_all(engine)

print("Database and table created: nutriscan.db -> food_products")

# STEP 3: LOAD THE CLEANED CSV FILE

# dtype keeps the barcode as text so leading zeros are not lost
df = pd.read_csv(
    "cleaned_food_data.csv",
    dtype={"product_code": str},
    encoding="utf-8-sig"
)

print("Rows in cleaned_food_data.csv:", len(df))

# Safety check: every product needs a unique barcode and a name.
# (A correct cleaned file already passes this, so nothing is removed.)
df = df.drop_duplicates(subset="product_code")
df = df.dropna(subset=["product_name"])

print("Rows ready to load:", len(df))

# STEP 4: INSERT THE PRODUCTS INTO THE DATABASE

added = 0
skipped = 0

with Session(engine) as session:

    for _, row in df.iterrows():

        # If this barcode is already in the database, skip it (no duplicates)
        if session.get(FoodProduct, row["product_code"]) is not None:
            skipped += 1
            continue

        # Pandas uses NaN for empty cells. The database needs None (NULL).
        record = {
            column: (None if pd.isna(value) else value)
            for column, value in row.items()
        }

        session.add(FoodProduct(**record))
        added += 1

    # Save all the new products to the database
    session.commit()

print("Products added:", added)
print("Products skipped (already in database):", skipped)

# STEP 5: CHECK THE NUMBER OF RECORDS

with Session(engine) as session:
    total_in_database = session.query(FoodProduct).count()

print("\nRecords in database:", total_in_database)
print("Records expected (from CSV):", len(df))

if total_in_database == len(df):
    print("CHECK PASSED: the numbers match.")
else:
    print("CHECK FAILED: the numbers do not match!")

# STEP 6: RUN BASIC SQL QUERIES

queries = [

    ("1. First 5 products",
     "SELECT product_name, brand, energy_kcal FROM food_products LIMIT 5"),

    ("2. Top 5 products with the most sugar",
     "SELECT product_name, sugars_g FROM food_products "
     "WHERE sugars_g IS NOT NULL ORDER BY sugars_g DESC LIMIT 5"),

    ("3. Number of products for each nutrition grade",
     "SELECT nutrition_grade, COUNT(*) FROM food_products "
     "GROUP BY nutrition_grade ORDER BY nutrition_grade"),

    ("4. Products with high protein (more than 20 g)",
     "SELECT product_name, proteins_g FROM food_products "
     "WHERE proteins_g > 20 ORDER BY proteins_g DESC"),

    ("5. Products with missing sugar information",
     "SELECT COUNT(*) FROM food_products WHERE sugars_g IS NULL"),

    ("6. Search for a product by name (Nutella)",
     "SELECT product_code, product_name, sugars_g, nutrition_grade "
     "FROM food_products WHERE product_name LIKE '%Nutella%'"),
]

with engine.connect() as connection:

    for title, sql in queries:

        print("\n" + title)

        for result_row in connection.execute(text(sql)).fetchall():
            print("  ", result_row)

print("\nDone! The database file is nutriscan.db")
