import requests
import csv

# 1. API SETTINGS

url = "https://world.openfoodfacts.org/api/v2/search"

headers = {
    "User-Agent": "NutriScan/1.0 (nutriscan-project@example.com)"
}

# Fields that we want from the API
params = {
    "page": 1,
    "page_size": 100,
    "fields": (
        "code,product_name,brands,categories,"
        "nutriments,ingredients_text,nutrition_grades"
    )
}

# 2. SEND REQUEST TO THE API

try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    # Check whether the request was successful
    response.raise_for_status()

    # Convert JSON response into Python data
    data = response.json()

    # Get the list of products
    products = data.get("products", [])

    print("Products received:", len(products))

except requests.RequestException as error:
    print("API request failed:", error)
    raise SystemExit(1)

# 3. EXTRACT REQUIRED INFORMATION

extracted_products = []

for product in products:

    # Nutritional information is stored separately
    nutriments = product.get("nutriments") or {}

    # Create a simpler record for each product
    record = {
        "product_code": product.get("code", ""),
        "product_name": product.get("product_name", ""),
        "brand": product.get("brands", ""),
        "category": product.get("categories", ""),

        "energy_kcal": nutriments.get("energy-kcal_100g"),
        "sugars_g": nutriments.get("sugars_100g"),
        "proteins_g": nutriments.get("proteins_100g"),
        "carbohydrates_g": nutriments.get("carbohydrates_100g"),
        "fat_g": nutriments.get("fat_100g"),
        "saturated_fat_g": nutriments.get("saturated-fat_100g"),
        "salt_g": nutriments.get("salt_100g"),

        "ingredients": product.get("ingredients_text", ""),
        "nutrition_grade": product.get("nutrition_grades", "")
    }

    extracted_products.append(record)

# 4. SAVE DATA TO A CSV FILE

if extracted_products:

    filename = "raw_food_data.csv"

    # Use the keys of the first record as column names
    fieldnames = extracted_products[0].keys()

    with open(filename, "w", newline="", encoding="utf-8-sig") as file:

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write the column headings
        writer.writeheader()

        # Write all product records
        writer.writerows(extracted_products)

    print("Data saved successfully!")
    print("File name:", filename)
    print("Total records saved:", len(extracted_products))

else:
    print("No products were returned. Please check the API response.")