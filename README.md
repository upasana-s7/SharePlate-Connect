# SharePlate Connect

**IBM Bobathon: Build for Bengaluru — Hackathon Project**

SharePlate Connect is a surplus food donation and NGO coordination platform. It connects food donors — college cafeterias, restaurants, and event organisers — with NGOs and community organisations that can collect and distribute surplus food across Bengaluru.

The goal is to reduce food waste and make donation coordination faster and simpler through a lightweight, human-in-the-loop web application.

---

## Problem Statement

A significant proportion of food prepared in Bengaluru's restaurants, tech campuses, and large-scale events goes to waste every day — not because of shortage, but because of a coordination gap between those with surplus and those who need it. SharePlate Connect addresses this gap with a simple digital platform that makes donation as easy as filling out a short form.

---

## Features

| Stage | Feature |
|---|---|
| 1 | Flask application skeleton, SQLite database initialisation |
| 2 | Professional landing page with hero, How It Works, mission, and CTA sections |
| 3 | Food donation submission form with server-side validation |
| 4 | Browse Donations page with search and category filter |
| 5 | Rule-based NGO matching recommendations with scoring and explanations |
| 6 | Coordinator-confirmed NGO assignment and collection tracking |
| 7 | Impact Dashboard showing live metrics from the database |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3.1 |
| Database | SQLite (via Python `sqlite3` standard library) |
| Templating | Jinja2 (bundled with Flask) |
| Frontend | HTML5, CSS3 (custom design system), Vanilla JavaScript |
| Matching | Pure Python rule-based logic (`matcher.py`) |

No external CSS frameworks, JavaScript libraries, or cloud databases are required.

---

## Project Structure

```
SharePlate/
├── app.py              # Flask application, all routes
├── database.py         # DB connection, schema initialisation
├── matcher.py          # Rule-based NGO matching logic
├── seed_ngos.py        # Inserts fictional demo NGO profiles
├── requirements.txt
├── static/
│   ├── css/style.css   # Full design system (no Bootstrap)
│   └── js/main.js      # Mobile nav toggle
└── templates/
    ├── base.html           # Shared layout and navigation
    ├── index.html          # Landing page
    ├── donate.html         # Donation submission form
    ├── donate_success.html # Submission confirmation
    ├── donations.html      # Browse Donations with search/filter
    ├── match.html          # NGO recommendations and status tracking
    └── dashboard.html      # Impact Dashboard
```

---

## Setup and Installation

### Prerequisites

- Python 3.10 or later
- pip

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd SharePlate
```

### 2. Create and activate a virtual environment (recommended)

```bash
# macOS / Linux
python -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The only third-party dependency is Flask. Everything else (`sqlite3`, `os`, `datetime`, `re`) is part of the Python standard library.

---

## Running the Application

```bash
python app.py
```

The Flask development server starts on **http://127.0.0.1:5000** with auto-reload enabled.

The SQLite database (`shareplate.db`) is created automatically in the project directory on first run. No separate database setup step is needed.

---

## Seeding Demo NGO Profiles

The NGO table is empty by default. To populate it with fictional demo profiles for testing:

```bash
python seed_ngos.py
```

This inserts 5 NGO profiles and is safe to run multiple times (it skips profiles that already exist).

> **Important:** These NGO profiles are **entirely fictional** and were created for demonstration purposes only. They do not represent real organisations.

---

## Application Routes

| Method | Route | Description |
|---|---|---|
| GET | `/` | Landing page |
| GET/POST | `/donate` | Donation submission form |
| GET | `/donations` | Browse all donations (search + filter) |
| GET | `/donations/<id>/match` | NGO recommendations for a donation |
| POST | `/donations/<id>/confirm_match` | Coordinator confirms an NGO match |
| POST | `/donations/<id>/mark_collected` | Coordinator marks food as collected |
| GET | `/dashboard` | Impact Dashboard |

---

## Donation Status Workflow

```
pending  -->  matched  -->  collected
   |
   +-- (deadline passed, display only) --> expired
```

- **pending**: Submitted, awaiting NGO confirmation.
- **matched**: A coordinator has manually confirmed an NGO after external contact.
- **collected**: The NGO has collected the food (coordinator-recorded).
- **expired**: Pending donation whose pickup deadline has passed. Display-only — no automatic write occurs.

NGO matching is a recommendation system, not automated assignment. A human coordinator must confirm every match after contacting the NGO externally.

---

## NGO Matching Logic

The matching algorithm in `matcher.py` evaluates each registered NGO against three rules:

| Rule | Points | Criteria |
|---|---|---|
| Category | 3 | NGO accepts `any` food, or specifically accepts the donation's food type |
| Capacity | 2 | Donation servings meet the NGO's minimum quantity |
| Location overlap | 0–2 | Shared significant keywords between donation location and NGO service area |

Maximum score: 7. NGOs that fail the category rule are excluded entirely and listed separately. No geocoding or distance calculation is used.

---

## Known Limitations

- **No authentication.** Any user can confirm matches or record collection. An authentication layer would be needed for production deployment.
- **Expiry is display-only.** Pending donations past their deadline show as "Expired" in the UI but their database `status` field is not automatically updated. A scheduled cleanup job would be needed in production.
- **Location matching is text-based.** The matcher compares location keywords as plain text. No geocoding or distance-based matching is implemented.
- **Demo NGOs only.** The five seeded NGO profiles are fictional. Real NGO onboarding and verification is out of scope for this prototype.
- **Single NGO per donation.** Once a match is confirmed, no second NGO can be assigned to the same donation.
- **No notifications.** Coordinators must check the platform manually. Email or SMS notification is not implemented.
- **SQLite only.** Suitable for a single-server prototype. A production deployment would need a more robust database.

---

## Demo Notes for Judges

1. Run `python seed_ngos.py` before demonstrating NGO matching.
2. Submit a donation at `/donate` using a Bengaluru location (e.g. "Indiranagar, Bengaluru") to get the best matching results.
3. Click "Find NGOs →" on a donation card to see the matching recommendations.
4. Use "Confirm Match" (after simulating external NGO contact) and then "Mark as Collected" to walk through the full workflow.
5. The Impact Dashboard at `/dashboard` reflects all actions in real time.

---

## Licence

This project was built for the **IBM Bobathon: Build for Bengaluru** hackathon. All NGO profiles are fictional and created solely for demonstration purposes.
