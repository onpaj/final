"""Run once after migration to populate starter categories."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models import CategoryGroup, Category

TAXONOMY = [
    {"name": "Bydlení",    "slug": "living",     "color": "#4CAF50", "sort_order": 1, "categories": [
        {"name": "Potraviny",        "slug": "groceries"},
        {"name": "Nájem",            "slug": "rent"},
        {"name": "Energie a služby", "slug": "utilities"},
        {"name": "Domácnost",        "slug": "household"},
    ]},
    {"name": "Doprava",    "slug": "transport",  "color": "#2196F3", "sort_order": 2, "categories": [
        {"name": "Pohonné hmoty",    "slug": "fuel"},
        {"name": "Veřejná doprava",  "slug": "public_transport"},
        {"name": "Údržba auta",      "slug": "car_maintenance"},
        {"name": "Parkování",        "slug": "parking"},
    ]},
    {"name": "Volný čas",  "slug": "leisure",    "color": "#FF9800", "sort_order": 3, "categories": [
        {"name": "Restaurace",       "slug": "restaurants"},
        {"name": "Zábava",           "slug": "entertainment"},
        {"name": "Cestování",        "slug": "travel"},
        {"name": "Předplatné",       "slug": "subscriptions"},
    ]},
    {"name": "Zdraví",     "slug": "health",     "color": "#E91E63", "sort_order": 4, "categories": [
        {"name": "Lékárna",          "slug": "pharmacy"},
        {"name": "Lékař",            "slug": "doctor"},
        {"name": "Fitness",          "slug": "gym"},
    ]},
    {"name": "Příjmy",     "slug": "income",     "color": "#009688", "sort_order": 5, "categories": [
        {"name": "Plat",             "slug": "salary", "is_income": True},
        {"name": "Freelance",        "slug": "freelance", "is_income": True},
        {"name": "Ostatní příjmy",   "slug": "other_income", "is_income": True},
    ]},
    {"name": "Úspory",     "slug": "savings",    "color": "#3F51B5", "sort_order": 6, "categories": [
        {"name": "Převod do úspor",  "slug": "savings_transfer"},
        {"name": "Investice",        "slug": "investment"},
    ]},
    {"name": "Převody",    "slug": "transfers",  "color": "#9C27B0", "sort_order": 7, "categories": [
        {"name": "Interní převod",   "slug": "internal_transfer", "is_system": True},
    ]},
    {"name": "Ostatní",    "slug": "other",      "color": "#607D8B", "sort_order": 8, "categories": [
        {"name": "Poplatky",         "slug": "fees_charges"},
        {"name": "Nezařazeno",       "slug": "uncategorized"},
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
