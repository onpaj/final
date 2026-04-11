"""add_slug_to_categories

Revision ID: a1b2c3d4e5f6
Revises: 5ad90b2eac19
Create Date: 2026-04-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5ad90b2eac19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GROUP_MAP = {
    "Living":    ("Bydlení",   "living"),
    "Transport": ("Doprava",   "transport"),
    "Leisure":   ("Volný čas", "leisure"),
    "Health":    ("Zdraví",    "health"),
    "Income":    ("Příjmy",    "income"),
    "Savings":   ("Úspory",    "savings"),
    "Transfers": ("Převody",   "transfers"),
    "Other":     ("Ostatní",   "other"),
}

CATEGORY_MAP = {
    "Groceries":         ("Potraviny",           "groceries"),
    "Rent":              ("Nájem",               "rent"),
    "Utilities":         ("Energie a služby",    "utilities"),
    "Household":         ("Domácnost",           "household"),
    "Fuel":              ("Pohonné hmoty",        "fuel"),
    "Public Transport":  ("Veřejná doprava",      "public_transport"),
    "Car Maintenance":   ("Údržba auta",          "car_maintenance"),
    "Parking":           ("Parkování",            "parking"),
    "Restaurants":       ("Restaurace",           "restaurants"),
    "Entertainment":     ("Zábava",               "entertainment"),
    "Travel":            ("Cestování",            "travel"),
    "Subscriptions":     ("Předplatné",           "subscriptions"),
    "Pharmacy":          ("Lékárna",              "pharmacy"),
    "Doctor":            ("Lékař",                "doctor"),
    "Gym":               ("Fitness",              "gym"),
    "Salary":            ("Plat",                 "salary"),
    "Freelance":         ("Freelance",            "freelance"),
    "Other Income":      ("Ostatní příjmy",       "other_income"),
    "Savings Transfer":  ("Převod do úspor",      "savings_transfer"),
    "Investment":        ("Investice",            "investment"),
    "Internal Transfer": ("Interní převod",       "internal_transfer"),
    "Fees & Charges":    ("Poplatky",             "fees_charges"),
    "Uncategorized":     ("Nezařazeno",           "uncategorized"),
}


def upgrade() -> None:
    op.add_column('category_groups', sa.Column('slug', sa.String(), nullable=True))
    op.add_column('categories', sa.Column('slug', sa.String(), nullable=True))

    conn = op.get_bind()

    for eng_name, (czech_name, slug) in GROUP_MAP.items():
        conn.execute(
            sa.text(
                "UPDATE category_groups SET name = :czech_name, slug = :slug WHERE name = :eng_name"
            ),
            {"czech_name": czech_name, "slug": slug, "eng_name": eng_name},
        )

    for eng_name, (czech_name, slug) in CATEGORY_MAP.items():
        conn.execute(
            sa.text(
                "UPDATE categories SET name = :czech_name, slug = :slug WHERE name = :eng_name"
            ),
            {"czech_name": czech_name, "slug": slug, "eng_name": eng_name},
        )


def downgrade() -> None:
    op.drop_column('categories', 'slug')
    op.drop_column('category_groups', 'slug')
