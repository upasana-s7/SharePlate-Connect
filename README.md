# SharePlate Connect

**IBM Bobathon: Build for Bengaluru — Hackathon Project**

SharePlate Connect is a surplus food donation and NGO coordination platform. It connects food donors — college cafeterias, restaurants, and event organisers — with NGOs and community organisations that can collect and distribute surplus food across Bengaluru.

**Live Demo:** https://shareplate-connect.onrender.com
**GitHub Repo:** https://github.com/upasana-s7/SharePlate-Connect

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
| 7 | Impact Dashboard with status, collection-rate, completed-servings, and food-category metrics |
| 8 | Donation browsing controls: status filter, sorting, live result count, and empty states |
| 9 | Local-time-aware donation deadline validation and CSRF protection for form submissions |
| 10 | Configurable database location, SQLite indexes, and baseline security headers |
| 11 | Donor and NGO registration, password hashing, sign-in and sign-out |
| 12 | Role-based workspaces for donors, NGOs and coordinators |
| 13 | Coordinator-only NGO verification and match confirmation |
| 14 | Assigned NGO collection confirmation with ownership checks |

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
├── seed_ngos.py        # Inserts fictional demo NGOs and six demo donations
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
    ├── dashboard.html      # Impact Dashboard
    ├── auth.html           # Donor / NGO registration and sign-in
    └── portal.html         # Role-based workspace
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

The application uses Flask and `tzdata` (for consistent IANA time-zone support on platforms such as Windows). Everything else (`sqlite3`, `os`, `datetime`, `re`, `zoneinfo`) is part of the Python standard library.

---

## Running the Application

```bash
python app.py
```

The Flask development server starts on **http://127.0.0.1:5000** with auto-reload enabled.

The SQLite database (`shareplate.db`) is created automatically in the project directory on first run. No separate database setup step is needed.

### Recommended environment configuration

Set a strong, private `SECRET_KEY` in your deployment environment. Do not commit it to GitHub.

Optional settings:

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs Flask sessions and CSRF tokens | Development-only fallback |
| `APP_TIMEZONE` | Time zone used for pickup deadlines and expiry | `Asia/Kolkata` |
| `COOKIE_SECURE` | Sends session cookies only over HTTPS | Enabled on Render; disabled locally |
| `SHAREPLATE_DB_PATH` | Full path to the SQLite database file | Project directory |
| `COORDINATOR_EMAIL` | Email address that receives coordinator permissions when registering as a donor | Not set |
| `SEED_DEMO_DATA` | Inserts fictional demo NGOs and donation cards at startup when set to `true` | `false` |

For a Render demo deployment, set `SEED_DEMO_DATA=true` to automatically insert the clearly labelled fictional showcase NGOs and donation cards when the service starts. Leave it `false` (or unset) when you only want real user-submitted donations. For a Render deployment, add `SECRET_KEY` as a private environment variable. Set `COORDINATOR_EMAIL` to the email address you will use for the coordinator account, then register on the website using that email and choose **Food donor** as the account type. That account receives coordinator permissions; coordinator registration is not offered publicly. If you attach a persistent disk, set `SHAREPLATE_DB_PATH` to a file path on that disk. The default Render free filesystem is ephemeral, so SQLite records may be lost when the service restarts or is replaced.

---

## Seeding Demo Data

To populate the database manually with five fictional demo NGO profiles and six fictional donation listings for the Browse Donations page (or set `SEED_DEMO_DATA=true` to do this at app startup):

```bash
python seed_ngos.py
```

This inserts five NGO profiles and six donation cards. It is safe to run multiple times: existing demo profiles are skipped, and the pickup windows on the six known demo donations are refreshed so they remain visible during a demonstration.

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
| GET/POST | `/register` | Create donor or NGO account |
| GET/POST | `/login` | Sign in |
| POST | `/logout` | Sign out |
| GET | `/portal` | Role-based workspace |
| POST | `/coordinator/verify-ngo/<id>` | Coordinator verifies an NGO |

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

- **Prototype account controls.** Donor and NGO accounts use password hashing and role checks, but there is no email verification, password reset, multi-factor authentication, or production-grade account recovery. Coordinator access depends on the private `COORDINATOR_EMAIL` environment variable. Do not use this prototype for real personal or sensitive data.
- **Expiry is display-only.** Pending donations past their deadline show as "Expired" in the UI but their database `status` field is not automatically updated. A scheduled cleanup job would be needed in production.
- **Location matching is text-based.** The matcher compares location keywords as plain text. No geocoding or distance-based matching is implemented.
- **Demo data only.** The five seeded NGO profiles and six seeded donation listings are fictional. Newly registered NGO profiles remain hidden from matching until a coordinator verifies them. Verification is an internal workflow step, not an independent legal or charity-status check.
- **Single NGO per donation.** Once a match is confirmed, no second NGO can be assigned to the same donation.
- **No notifications.** Coordinators must check the platform manually. Email or SMS notification is not implemented.
- **SQLite only.** Suitable for a single-server prototype. A persistent disk is required to retain SQLite data across supported host restarts; a production deployment should use managed PostgreSQL or another durable database.

---

## Demo Notes for Judges

1. Run `python seed_ngos.py` before demonstrating NGO matching.
2. Submit a donation at `/donate` using a Bengaluru location (e.g. "Indiranagar, Bengaluru") to get the best matching results.
3. Click "Find NGOs →" on a donation card to see the matching recommendations.
4. Register a coordinator account using the email configured in `COORDINATOR_EMAIL`. Register an NGO account to test the pending-verification flow; the coordinator can verify it from the workspace.
5. As coordinator, use "Confirm Match" after simulating external NGO contact. Sign in as the assigned NGO to mark the pickup collected.
5. The Impact Dashboard at `/dashboard` reflects all actions in real time.

---

## Licence

This project was built for the **IBM Bobathon: Build for Bengaluru** hackathon. All NGO profiles are fictional and created solely for demonstration purposes.
