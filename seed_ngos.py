"""
seed_ngos.py
------------
Inserts five fictional demo NGO profiles into the SharePlate database.

These are ENTIRELY FICTIONAL organisations created for the IBM Bobathon
hackathon demonstration. They do not represent real organisations.
They cover different areas of Bengaluru and different food preferences
so the matching logic can be demonstrated.

Safe to run multiple times — it checks whether NGOs already exist first.
Run with: python seed_ngos.py
"""

import sqlite3
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DB_PATH = os.environ.get("SHAREPLATE_DB_PATH", os.path.join(os.path.dirname(__file__), "shareplate.db"))
try:
    APP_TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "Asia/Kolkata"))
except ZoneInfoNotFoundError:
    APP_TIMEZONE = None

DEMO_NGOS = [
    {
        "name":            "Aahar Bengaluru",
        "contact_name":    "Demo Contact A",
        "phone":           "9900000001",
        "email":           "demo.a@example.com",
        "service_area":    "Indiranagar, Koramangala, HSR Layout, Bengaluru",
        "food_preference": "any",
        "min_quantity":    10,
    },
    {
        "name":            "Nourish Whitefield",
        "contact_name":    "Demo Contact B",
        "phone":           "9900000002",
        "email":           "demo.b@example.com",
        "service_area":    "Whitefield, Marathahalli, Bellandur, Bengaluru",
        "food_preference": "prepared_meals",
        "min_quantity":    20,
    },
    {
        "name":            "Fresh Harvest Trust",
        "contact_name":    "Demo Contact C",
        "phone":           "9900000003",
        "email":           "demo.c@example.com",
        "service_area":    "Jayanagar, JP Nagar, Bannerghatta Road, Bengaluru",
        "food_preference": "fruits",
        "min_quantity":    5,
    },
    {
        "name":            "City Bread Network",
        "contact_name":    "Demo Contact D",
        "phone":           "9900000004",
        "email":           "demo.d@example.com",
        "service_area":    "MG Road, Shivajinagar, Yelahanka, Bengaluru",
        "food_preference": "bakery",
        "min_quantity":    15,
    },
    {
        "name":            "Green Plate Collective",
        "contact_name":    "Demo Contact E",
        "phone":           "9900000005",
        "email":           "demo.e@example.com",
        "service_area":    "Rajajinagar, Vijayanagar, Malleswaram, Bengaluru",
        "food_preference": "vegetables",
        "min_quantity":    8,
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    # Serialize concurrent web-worker startup so demo records are not duplicated.
    conn.execute("BEGIN IMMEDIATE")
    inserted = 0
    skipped  = 0

    for ngo in DEMO_NGOS:
        exists = conn.execute(
            "SELECT id FROM ngos WHERE name = ?", (ngo["name"],)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        conn.execute(
            """
            INSERT INTO ngos
                (name, contact_name, phone, email,
                 service_area, food_preference, min_quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ngo["name"], ngo["contact_name"], ngo["phone"], ngo["email"],
                ngo["service_area"], ngo["food_preference"], ngo["min_quantity"],
            )
        )
        inserted += 1

    # Add clearly labelled fictional sample donations so the Browse page
    # demonstrates real database-backed cards on a fresh deployment.
    demo_donations = [
        ("Demo College Cafeteria", "Vegetable Biryani", "prepared_meals", 3, 30,
         "Whitefield, Bengaluru", "Freshly prepared demo listing", "Fictional sample donation for demonstration only."),
        ("Demo Bakery", "Assorted Bread & Buns", "bakery", 2, 20,
         "Indiranagar, Bengaluru", "Packed in clean food-grade bags", "Fictional sample donation for demonstration only."),
        ("Demo Community Kitchen", "Fresh Seasonal Fruits", "fruits", 4, 40,
         "Jayanagar, Bengaluru", "Washed and sorted demo listing", "Fictional sample donation for demonstration only."),
        ("Demo Event Organiser", "Fresh Vegetable Packs", "vegetables", 5, 50,
         "Koramangala, Bengaluru", "Sorted seasonal vegetables", "Fictional sample donation for demonstration only."),
        ("Demo Office Pantry", "Packaged Snack Boxes", "packaged_food", 6, 60,
         "HSR Layout, Bengaluru", "Sealed packaged snack boxes", "Fictional sample donation for demonstration only."),
        ("Demo Fruit Market", "Banana & Apple Boxes", "fruits", 4, 40,
         "Marathahalli, Bengaluru", "Fresh fruit boxes for collection", "Fictional sample donation for demonstration only."),
    ]
    demo_now = datetime.now(APP_TIMEZONE).replace(second=0, microsecond=0) if APP_TIMEZONE else datetime.now(timezone.utc).replace(second=0, microsecond=0)
    demo_inserted = 0
    for donor, food, category, quantity, servings, location, storage, note in demo_donations:
        exists = conn.execute(
            "SELECT id FROM donations WHERE donor_name = ? AND food_name = ?",
            (donor, food)
        ).fetchone()
        ready = (demo_now + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
        deadline = (demo_now + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M")
        if exists:
            # Refresh only these known demo records so their pickup windows
            # remain valid on a restarted demo instance.
            conn.execute(
                """UPDATE donations
                   SET available_from = ?, available_until = ?
                   WHERE id = ? AND status = 'pending'""",
                (ready, deadline, exists[0])
            )
            continue
        conn.execute(
            """INSERT INTO donations
               (donor_name, food_name, food_type, quantity, servings, location,
                available_from, available_until, storage_info, notes, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (donor, food, category, quantity, servings, location,
             ready, deadline, storage, note)
        )
        demo_inserted += 1

    conn.commit()
    conn.close()
    print(f"[OK] NGO seed complete: {inserted} NGOs inserted, {skipped} already existed.")
    print(f"[OK] Demo donations inserted: {demo_inserted}. These are fictional sample records.")


if __name__ == "__main__":
    seed()
