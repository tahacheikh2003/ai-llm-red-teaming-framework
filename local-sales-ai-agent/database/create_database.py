"""Create the demo database and CSV using only Python's standard library.

Run from the project root: python -m database.create_database
All names, transactions, and employee identifiers are fictional.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import random
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "sales.db"
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "sales_seed.csv"
DATA_YEAR = 2025
RANDOM_SEED = 2026
ORDERS_PER_MONTH = 200

# product: (category, reference retail price in USD, cost fraction)
PRODUCT_CATALOG = {
    "Laptop": ("Computers", 1199.00, 0.72),
    "Smartphone": ("Mobile Devices", 749.00, 0.66),
    "Tablet": ("Mobile Devices", 449.00, 0.65),
    "Monitor": ("Accessories", 279.00, 0.61),
    "Headphones": ("Accessories", 99.00, 0.45),
    "Keyboard": ("Accessories", 79.00, 0.42),
    "Mouse": ("Accessories", 39.00, 0.38),
}
PRODUCTS = tuple(PRODUCT_CATALOG)
CATEGORIES = tuple(sorted({item[0] for item in PRODUCT_CATALOG.values()}))
REGIONS = ("North", "South", "East", "West")
FIELD_NAMES = (
    "id", "date", "month", "product", "category", "region", "quantity",
    "unit_price", "revenue", "cost", "profit", "salesperson",
)


def generate_sales_rows() -> list[dict]:
    """Return the same 2,400 synthetic orders every time."""
    rng = random.Random(RANDOM_SEED)
    rows = []
    for month in range(1, 13):
        # Larger baskets in the autumn and holiday period create visible trends.
        weights = [17, 23, 12, 13, 15, 10, 10]
        if month in (8, 9):
            weights = [25, 18, 18, 12, 9, 10, 8]
        elif month in (11, 12):
            weights = [15, 25, 10, 10, 23, 9, 8]
        for _ in range(ORDERS_PER_MONTH):
            product = rng.choices(PRODUCTS, weights=weights, k=1)[0]
            category, price, cost_fraction = PRODUCT_CATALOG[product]
            quantity = rng.randint(1, 5 if month < 10 else 7)
            discount = rng.choice([0, 0, 0.05, 0.10, 0.15])
            unit_price = round(price * (1 - discount), 2)
            revenue = round(quantity * unit_price, 2)
            unit_cost = round(price * cost_fraction, 2)
            cost = round(quantity * unit_cost, 2)
            day = rng.randint(1, calendar.monthrange(DATA_YEAR, month)[1])
            rows.append({
                "date": f"{DATA_YEAR}-{month:02d}-{day:02d}",
                "month": f"{DATA_YEAR}-{month:02d}",
                "product": product,
                "category": category,
                "region": rng.choices(REGIONS, weights=[30, 22, 20, 28], k=1)[0],
                "quantity": quantity,
                "unit_price": unit_price,
                "revenue": revenue,
                "cost": cost,
                "profit": round(revenue - cost, 2),
                "salesperson": f"SYNTH-REP-{rng.randint(1, 12):02d}",
            })
    rows.sort(key=lambda row: row["date"])
    for index, row in enumerate(rows, start=1):
        row["id"] = index
    return rows


def create_database(
    db_path: str | Path = DEFAULT_DB_PATH,
    csv_path: str | Path | None = DEFAULT_CSV_PATH,
    *,
    force: bool = False,
) -> dict:
    """Create the synthetic fixtures; replacing an existing DB requires force."""
    db_path = Path(db_path).resolve()
    if db_path.exists() and not force:
        raise FileExistsError(
            f"Database already exists: {db_path}. Use --force to regenerate synthetic data."
        )
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_sales_rows()
    # Write to a sibling file first, so a failed build cannot damage an old DB.
    temporary_path = db_path.with_suffix(".building.db")
    if temporary_path.exists():
        raise FileExistsError(f"Remove the stale build file before retrying: {temporary_path}")
    try:
        with sqlite3.connect(temporary_path) as connection:
            connection.executescript("""
                CREATE TABLE sales (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    month TEXT NOT NULL,
                    product TEXT NOT NULL,
                    category TEXT NOT NULL,
                    region TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    unit_price REAL NOT NULL CHECK(unit_price >= 0),
                    revenue REAL NOT NULL CHECK(revenue >= 0),
                    cost REAL NOT NULL CHECK(cost >= 0),
                    profit REAL NOT NULL,
                    salesperson TEXT NOT NULL
                );
                CREATE INDEX idx_sales_month ON sales(month);
                CREATE INDEX idx_sales_product ON sales(product);
                CREATE INDEX idx_sales_region ON sales(region);
                CREATE INDEX idx_sales_category ON sales(category);
            """)
            connection.executemany(
                """INSERT INTO sales
                (id, date, month, product, category, region, quantity,
                 unit_price, revenue, cost, profit, salesperson)
                VALUES (:id, :date, :month, :product, :category, :region, :quantity,
                        :unit_price, :revenue, :cost, :profit, :salesperson)""",
                rows,
            )
        # sqlite3 context managers commit but do not close connections on Windows.
        connection.close()
        temporary_path.replace(db_path)
    except Exception:
        if "connection" in locals():
            connection.close()
        if temporary_path.exists():
            temporary_path.unlink()
        raise

    if csv_path is not None:
        csv_path = Path(csv_path).resolve()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELD_NAMES)
            writer.writeheader()
            writer.writerows(rows)
    return {"rows": len(rows), "months": 12, "year": DATA_YEAR, "database": str(db_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace the synthetic database")
    args = parser.parse_args()
    if DEFAULT_DB_PATH.exists() and not args.force:
        print(f"Database already exists: {DEFAULT_DB_PATH}")
        print("To regenerate the synthetic dataset: python -m database.create_database --force")
        return
    result = create_database(force=args.force)
    print(f"Created {result['rows']:,} synthetic orders across 12 months of {DATA_YEAR}.")
    print(f"Database: {DEFAULT_DB_PATH}")
    print(f"CSV: {DEFAULT_CSV_PATH}")


if __name__ == "__main__":
    main()
