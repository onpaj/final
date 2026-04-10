"""Run once after migration to populate starter categories."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models import CategoryGroup, Category

TAXONOMY = [
    {"name": "Living",    "color": "#4CAF50", "sort_order": 1, "categories": [
        {"name": "Groceries"},
        {"name": "Rent"},
        {"name": "Utilities"},
        {"name": "Household"},
    ]},
    {"name": "Transport", "color": "#2196F3", "sort_order": 2, "categories": [
        {"name": "Fuel"},
        {"name": "Public Transport"},
        {"name": "Car Maintenance"},
        {"name": "Parking"},
    ]},
    {"name": "Leisure",   "color": "#FF9800", "sort_order": 3, "categories": [
        {"name": "Restaurants"},
        {"name": "Entertainment"},
        {"name": "Travel"},
        {"name": "Subscriptions"},
    ]},
    {"name": "Health",    "color": "#E91E63", "sort_order": 4, "categories": [
        {"name": "Pharmacy"},
        {"name": "Doctor"},
        {"name": "Gym"},
    ]},
    {"name": "Income",    "color": "#9C27B0", "sort_order": 5, "categories": [
        {"name": "Salary", "is_income": True},
        {"name": "Freelance", "is_income": True},
        {"name": "Other Income", "is_income": True},
    ]},
    {"name": "Savings",   "color": "#009688", "sort_order": 6, "categories": [
        {"name": "Savings Transfer"},
        {"name": "Investment"},
    ]},
    {"name": "Transfers", "color": "#607D8B", "sort_order": 7, "categories": [
        {"name": "Internal Transfer", "is_system": True},
    ]},
    {"name": "Other",     "color": "#9E9E9E", "sort_order": 8, "categories": [
        {"name": "Fees & Charges"},
        {"name": "Uncategorized"},
    ]},
]

async def seed():
    async with AsyncSessionLocal() as db:
        for group_data in TAXONOMY:
            cats = group_data.pop("categories")
            group = CategoryGroup(**group_data)
            db.add(group)
            await db.flush()
            for cat_data in cats:
                db.add(Category(group_id=group.id, **cat_data))
        await db.commit()
    print("Seed complete.")

if __name__ == "__main__":
    asyncio.run(seed())
