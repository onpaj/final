# Category i18n Design — Czech Names + Slug-Based Translation

**Date:** 2026-04-11
**Status:** Approved

## Goal

Localize category group and category names to Czech. Unlike UI strings (which are hardcoded in the frontend), these names come from the database. The solution uses a stable `slug` field as the i18n lookup key, while the DB `name` field becomes Czech. English translations are added to both `cs/translation.json` and `en/translation.json` under a `cat.*` namespace.

---

## Approach: Slug-Based Translation

Add a `slug` column (nullable `VARCHAR`) to both `category_groups` and `categories` tables. The slug is a stable English snake_case identifier (e.g., `"groceries"`, `"public_transport"`). The DB `name` field becomes Czech. The frontend calls:

```ts
t("cat." + slug, { defaultValue: name })
```

If `slug` is null (user-created categories), it falls back gracefully to the raw `name` from the DB.

**Why slugs instead of using the name as key:** DB names will become Czech, making them unsuitable as JSON keys. A slug is immutable regardless of label changes.

---

## Database Changes

### Schema (`backend/app/db/models.py`)

Add `slug` to both models:

```python
class CategoryGroup(Base):
    # existing fields...
    slug: Mapped[str | None] = mapped_column(String, nullable=True)

class Category(Base):
    # existing fields...
    slug: Mapped[str | None] = mapped_column(String, nullable=True)
```

### Alembic Migration

One migration does two things:
1. Adds `slug` column to both tables
2. Data-migrates: renames existing English `name` values to Czech and populates `slug`

```python
# Data migration mapping
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
```

### Seed (`backend/app/db/seed.py`)

Updated to Czech names with slugs:

```python
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
        {"name": "Plat",             "slug": "salary"},
        {"name": "Freelance",        "slug": "freelance"},
        {"name": "Ostatní příjmy",   "slug": "other_income"},
    ]},
    {"name": "Úspory",     "slug": "savings",    "color": "#3F51B5", "sort_order": 6, "categories": [
        {"name": "Převod do úspor",  "slug": "savings_transfer"},
        {"name": "Investice",        "slug": "investment"},
    ]},
    {"name": "Převody",    "slug": "transfers",  "color": "#9C27B0", "sort_order": 7, "categories": [
        {"name": "Interní převod",   "slug": "internal_transfer"},
    ]},
    {"name": "Ostatní",    "slug": "other",      "color": "#607D8B", "sort_order": 8, "categories": [
        {"name": "Poplatky",         "slug": "fees_charges"},
        {"name": "Nezařazeno",       "slug": "uncategorized"},
    ]},
]
```

---

## Backend API Changes

### `backend/app/api/categories.py`

Add `slug` to both Pydantic response models:

```python
class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str | None = None
    color: str | None = None

class GroupOut(BaseModel):
    id: str
    name: str
    slug: str | None = None
    color: str | None = None
    sort_order: int
    categories: list[CategoryOut]
```

### `backend/app/services/analytics_service.py`

Add `slug` columns to both raw SQL queries:

**Monthly summary query** — add to SELECT:
```sql
cg.slug AS group_slug,
c.slug  AS category_slug
```
And include in returned dicts:
```python
"group_slug":    row.group_slug,
"category_slug": row.category_slug,
```

**Trends query** — add `cg.slug AS group_slug` to SELECT and include in returned data structure.

---

## Frontend Translation JSON

Both `cs/translation.json` and `en/translation.json` gain a `cat` namespace.

### `cs/translation.json` additions
```json
"cat": {
  "living":           "Bydlení",
  "transport":        "Doprava",
  "leisure":          "Volný čas",
  "health":           "Zdraví",
  "income":           "Příjmy",
  "savings":          "Úspory",
  "transfers":        "Převody",
  "other":            "Ostatní",
  "groceries":        "Potraviny",
  "rent":             "Nájem",
  "utilities":        "Energie a služby",
  "household":        "Domácnost",
  "fuel":             "Pohonné hmoty",
  "public_transport": "Veřejná doprava",
  "car_maintenance":  "Údržba auta",
  "parking":          "Parkování",
  "restaurants":      "Restaurace",
  "entertainment":    "Zábava",
  "travel":           "Cestování",
  "subscriptions":    "Předplatné",
  "pharmacy":         "Lékárna",
  "doctor":           "Lékař",
  "gym":              "Fitness",
  "salary":           "Plat",
  "freelance":        "Freelance",
  "other_income":     "Ostatní příjmy",
  "savings_transfer": "Převod do úspor",
  "investment":       "Investice",
  "internal_transfer":"Interní převod",
  "fees_charges":     "Poplatky",
  "uncategorized":    "Nezařazeno"
}
```

### `en/translation.json` additions
```json
"cat": {
  "living":           "Living",
  "transport":        "Transport",
  "leisure":          "Leisure",
  "health":           "Health",
  "income":           "Income",
  "savings":          "Savings",
  "transfers":        "Transfers",
  "other":            "Other",
  "groceries":        "Groceries",
  "rent":             "Rent",
  "utilities":        "Utilities",
  "household":        "Household",
  "fuel":             "Fuel",
  "public_transport": "Public Transport",
  "car_maintenance":  "Car Maintenance",
  "parking":          "Parking",
  "restaurants":      "Restaurants",
  "entertainment":    "Entertainment",
  "travel":           "Travel",
  "subscriptions":    "Subscriptions",
  "pharmacy":         "Pharmacy",
  "doctor":           "Doctor",
  "gym":              "Gym",
  "salary":           "Salary",
  "freelance":        "Freelance",
  "other_income":     "Other Income",
  "savings_transfer": "Savings Transfer",
  "investment":       "Investment",
  "internal_transfer":"Internal Transfer",
  "fees_charges":     "Fees & Charges",
  "uncategorized":    "Uncategorized"
}
```

---

## Frontend TypeScript Changes

### `frontend/src/api/categories.ts`

```ts
export interface Category {
  id: string;
  name: string;
  slug?: string;
  color?: string;
}

export interface CategoryGroup {
  id: string;
  name: string;
  slug?: string;
  color?: string;
  sort_order: number;
  categories: Category[];
}
```

### `frontend/src/api/analytics.ts`

Add `slug` fields to `CategorySummary`, `GroupSummary`, and the trends data structure:

```ts
export interface CategorySummary {
  category_id: string;
  category_name: string;
  category_slug?: string;
  total: number;
}

export interface GroupSummary {
  group_id: string;
  group_name: string;
  group_slug?: string;
  total: number;
  categories: CategorySummary[];
}
```

---

## Frontend Component Changes

All components that display category/group names use the pattern:

```ts
t("cat." + (item.slug ?? ""), { defaultValue: item.name })
```

This resolves to the translated string when a slug is known, and falls back to the raw DB name when `slug` is null (e.g., user-created categories).

### Files to modify

1. `src/pages/Analytics/MonthSummary.tsx` — group names in spending chart and table
2. `src/pages/Analytics/GroupDetail.tsx` — group name in heading, category names in table
3. `src/pages/Analytics/CategoryDetail.tsx` — category name in heading; `categorySlug` prop added for heading translation
4. `src/pages/Analytics/TrendsView.tsx` — group names as Recharts `dataKey` values and Legend labels

### Navigation state extension (`Analytics/index.tsx`)

The `Level` type gains optional slug fields so slugs are carried through click navigation:

```ts
type Level =
  | { view: "overview" }
  | { view: "group"; groupId: string; groupName: string; groupSlug?: string }
  | { view: "category"; groupId: string; groupName: string; groupSlug?: string; categoryId: string; categoryName: string; categorySlug?: string };
```

### TrendsView special case

Recharts uses `dataKey` for pivot columns. After migration, those keys are Czech group names from the DB. The `groupSlug` from analytics data is used in a Legend `formatter` to translate labels:

```ts
<Legend formatter={(value) => {
  const slug = groupSlugMap[value]; // map built from group_slug in response
  return slug ? t("cat." + slug, { defaultValue: value }) : value;
}} />
```

---

## Out of Scope

- Translating user-created category names (no slug → raw name displayed)
- Backend error messages
- Category names in rule definitions (shown as-is from DB)
- Any language switcher UI
