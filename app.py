"""
app.py
------
Main Flask application for SharePlate Connect.
Stage 7: adds the Impact Dashboard.
"""

import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import Flask, render_template, request, redirect, url_for, abort, flash
from database import init_db, get_connection
from matcher import find_matches
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "true" if os.environ.get("RENDER") else "false").lower() == "true"

try:
    APP_TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "Asia/Kolkata"))
except ZoneInfoNotFoundError:
    APP_TIMEZONE = timezone.utc

if app.config["SECRET_KEY"] == "dev-only-change-this-secret" and os.environ.get("RENDER"):
    app.logger.warning("Set a strong SECRET_KEY environment variable in the deployment environment.")

@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


# ---------------------------------------------------------------------------
# Initialise the database on startup — safe, never overwrites data.
# ---------------------------------------------------------------------------
with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Food type human-readable labels
# ---------------------------------------------------------------------------
FOOD_TYPE_LABELS = {
    "prepared_meals": "Prepared Meals",
    "bakery":         "Bakery & Bread",
    "fruits":         "Fruits",
    "vegetables":     "Vegetables",
    "packaged_food":  "Packaged Food",
    "other":          "Other",
}

VALID_FOOD_TYPES = set(FOOD_TYPE_LABELS.keys())


# ---------------------------------------------------------------------------
# Status workflow helpers
# ---------------------------------------------------------------------------

def is_expired(donation):
    """
    Return True if a pending donation's pickup deadline has passed.
    Uses UTC now vs the available_until string stored in the DB
    (format: YYYY-MM-DDTHH:MM, ISO 8601 — lexicographically comparable).
    A donation that is already 'matched' or 'collected' is never expired.
    """
    if donation["status"] in ("matched", "collected"):
        return False
    now_str = datetime.now(APP_TIMEZONE).strftime("%Y-%m-%dT%H:%M")
    return donation["available_until"] < now_str


def effective_status(donation):
    """
    Return the status to display, accounting for expiry.
    If the donation is pending but its deadline has passed, return 'expired'.
    Does NOT write to the database — purely for display/guard purposes.
    """
    if is_expired(donation):
        return "expired"
    return donation["status"]


# ---------------------------------------------------------------------------
# Donation form validation helper
# ---------------------------------------------------------------------------

def validate_donation(form):
    """
    Validate all required fields from a donation POST request.
    Returns (errors, field_errors, data_dict).
    """
    errors = []
    field_errors = {}

    def require(field, label):
        val = form.get(field, "").strip()
        if not val:
            msg = f"{label} is required."
            errors.append(msg)
            field_errors[field] = msg
        return val

    donor_name      = require("donor_name",     "Donor name")
    food_name       = require("food_name",      "Food name")
    food_type       = require("food_type",      "Food category")
    location        = require("location",       "Pickup location")
    available_from  = require("available_from", "Food ready from time")
    available_until = require("available_until","Pickup deadline")

    if food_type and food_type not in VALID_FOOD_TYPES:
        msg = "Please select a valid food category."
        errors.append(msg)
        field_errors["food_type"] = msg

    quantity_raw = form.get("quantity", "").strip()
    quantity = None
    if not quantity_raw:
        msg = "Quantity is required."
        errors.append(msg)
        field_errors["quantity"] = msg
    else:
        try:
            quantity = int(quantity_raw)
            if quantity < 1:
                raise ValueError
        except ValueError:
            msg = "Quantity must be a whole number of at least 1."
            errors.append(msg)
            field_errors["quantity"] = msg

    servings_raw = form.get("servings", "").strip()
    servings = None
    if not servings_raw:
        msg = "Estimated servings is required."
        errors.append(msg)
        field_errors["servings"] = msg
    else:
        try:
            servings = int(servings_raw)
            if servings < 1:
                raise ValueError
        except ValueError:
            msg = "Estimated servings must be a whole number of at least 1."
            errors.append(msg)
            field_errors["servings"] = msg

    if available_from and available_until:
        try:
            ready_dt = datetime.strptime(available_from, "%Y-%m-%dT%H:%M")
            deadline_dt = datetime.strptime(available_until, "%Y-%m-%dT%H:%M")
            if deadline_dt <= ready_dt:
                raise ValueError
        except ValueError:
            msg = "Choose a valid pickup deadline later than the food ready time."
            errors.append(msg)
            field_errors["available_until"] = msg

    for field, value, limit, label in (
        ("donor_name", donor_name, 200, "Donor name"),
        ("food_name", food_name, 200, "Food name"),
        ("location", location, 300, "Pickup location"),
        ("storage_info", form.get("storage_info", "").strip(), 1000, "Storage information"),
        ("notes", form.get("notes", "").strip(), 1500, "Additional notes"),
    ):
        if len(value) > limit:
            msg = f"{label} must be {limit} characters or fewer."
            errors.append(msg)
            field_errors[field] = msg

    return errors, field_errors, {
        "donor_name":     donor_name,
        "food_name":      food_name,
        "food_type":      food_type,
        "quantity":       quantity,
        "servings":       servings,
        "location":       location,
        "available_from": available_from,
        "available_until":available_until,
        "storage_info":   form.get("storage_info", "").strip(),
        "notes":          form.get("notes", "").strip(),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/donate", methods=["GET", "POST"])
def donate():
    """Donation submission form — GET shows form, POST validates and saves."""
    if request.method == "GET":
        return render_template("donate.html", errors=[], field_errors={}, form_data={})

    errors, field_errors, data = validate_donation(request.form)
    if errors:
        return render_template(
            "donate.html",
            errors=errors,
            field_errors=field_errors,
            form_data=request.form,
        ), 422

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO donations
                (donor_name, food_name, food_type, quantity, servings,
                 location, available_from, available_until,
                 storage_info, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                data["donor_name"], data["food_name"], data["food_type"],
                data["quantity"],   data["servings"],  data["location"],
                data["available_from"], data["available_until"],
                data["storage_info"],   data["notes"],
            )
        )
        conn.commit()
        donation_id = cursor.lastrowid
    finally:
        conn.close()

    return render_template(
        "donate_success.html",
        donation_id=donation_id,
        donor_name=data["donor_name"],
        food_name=data["food_name"],
        food_type_label=FOOD_TYPE_LABELS.get(data["food_type"], data["food_type"]),
        servings=data["servings"],
        location=data["location"],
        available_from=data["available_from"],
        available_until=data["available_until"],
    )


@app.route("/donations")
def donations():
    """Browse donations with optional search and category filter."""
    search_query    = request.args.get("q", "").strip()
    active_category = request.args.get("category", "").strip()

    sql    = "SELECT * FROM donations"
    params = []
    conditions = []

    if search_query:
        conditions.append("(LOWER(food_name) LIKE ? OR LOWER(location) LIKE ?)")
        pattern = "%" + search_query.lower() + "%"
        params.extend([pattern, pattern])

    if active_category and active_category in VALID_FOOD_TYPES:
        conditions.append("food_type = ?")
        params.append(active_category)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC"

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    # Attach effective status (may differ from DB status if expired)
    # We convert rows to dicts so we can add the computed field
    donations_list = []
    for row in rows:
        d = dict(row)
        d["display_status"] = effective_status(row)
        donations_list.append(d)

    return render_template(
        "donations.html",
        donations=donations_list,
        food_type_labels=FOOD_TYPE_LABELS,
        categories=sorted(FOOD_TYPE_LABELS.items()),
        search_query=search_query,
        active_category=active_category,
    )


@app.route("/donations/<int:donation_id>/match")
def match_donation(donation_id):
    """
    Show rule-based NGO match recommendations for a single donation.
    Read-only — no automatic assignment happens here.
    """
    conn = get_connection()
    try:
        donation = conn.execute(
            "SELECT * FROM donations WHERE id = ?", (donation_id,)
        ).fetchone()

        if donation is None:
            abort(404)

        ngos = conn.execute("SELECT * FROM ngos ORDER BY name").fetchall()

        existing_match = conn.execute(
            """SELECT m.*, n.name AS ngo_name, n.contact_name, n.phone,
                      n.service_area, n.food_preference, n.min_quantity
               FROM matches m
               JOIN ngos n ON m.ngo_id = n.id
               WHERE m.donation_id = ?
               LIMIT 1""",
            (donation_id,)
        ).fetchone()

        already_matched_ids = set()
        if existing_match:
            already_matched_ids.add(existing_match["ngo_id"])

    finally:
        conn.close()

    donation_status = effective_status(donation)
    can_match = (donation_status == "pending")

    if ngos and can_match:
        recommendations = find_matches(donation, ngos)
    else:
        recommendations = []

    return render_template(
        "match.html",
        donation=donation,
        donation_status=donation_status,
        recommendations=recommendations,
        food_type_labels=FOOD_TYPE_LABELS,
        already_matched_ids=already_matched_ids,
        ngo_count=len(ngos),
        existing_match=existing_match,
        can_match=can_match,
    )


@app.route("/donations/<int:donation_id>/confirm_match", methods=["POST"])
def confirm_match(donation_id):
    """
    POST — coordinator records that an NGO has agreed to collect this donation.

    Guards:
      - Donation must exist.
      - Donation must be in 'pending' status.
      - Donation must not be expired.
      - A match record must not already exist for this donation.
      - The selected NGO must exist.

    On success:
      - Inserts a row into the matches table.
      - Updates donation status to 'matched'.
      - Redirects to the match page with a flash message.

    This action does NOT claim the NGO accepted via the website.
    It records a coordinator's manual confirmation after external contact.
    """
    ngo_id = request.form.get("ngo_id", "").strip()
    if not ngo_id:
        flash("No NGO selected.", "error")
        return redirect(url_for("match_donation", donation_id=donation_id))

    try:
        ngo_id = int(ngo_id)
    except ValueError:
        flash("Invalid NGO selection.", "error")
        return redirect(url_for("match_donation", donation_id=donation_id))

    conn = get_connection()
    try:
        donation = conn.execute(
            "SELECT * FROM donations WHERE id = ?", (donation_id,)
        ).fetchone()

        if donation is None:
            abort(404)

        # Guard: must be pending
        if donation["status"] != "pending":
            flash(
                f"Cannot confirm a match for a donation with status "
                f"'{donation['status']}'. Only pending donations can be matched.",
                "error"
            )
            return redirect(url_for("match_donation", donation_id=donation_id))

        # Guard: must not be expired
        if is_expired(donation):
            flash(
                "This donation's pickup deadline has passed. "
                "It cannot be matched.",
                "error"
            )
            return redirect(url_for("match_donation", donation_id=donation_id))

        # Guard: no existing match record
        existing = conn.execute(
            "SELECT id FROM matches WHERE donation_id = ?", (donation_id,)
        ).fetchone()
        if existing:
            flash(
                "A match for this donation has already been recorded.",
                "warning"
            )
            return redirect(url_for("match_donation", donation_id=donation_id))

        # Guard: NGO must exist
        ngo = conn.execute("SELECT * FROM ngos WHERE id = ?", (ngo_id,)).fetchone()
        if ngo is None:
            flash("The selected NGO does not exist.", "error")
            return redirect(url_for("match_donation", donation_id=donation_id))

        # --- Save the match and update donation status ---
        matched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "INSERT INTO matches (donation_id, ngo_id, matched_at) VALUES (?, ?, ?)",
            (donation_id, ngo_id, matched_at)
        )
        conn.execute(
            "UPDATE donations SET status = 'matched' WHERE id = ?",
            (donation_id,)
        )
        conn.commit()

    finally:
        conn.close()

    flash(
        f"Match confirmed: {ngo['name']} has been recorded as the assigned NGO "
        f"for Donation #{donation_id}. Contact them to arrange the pickup.",
        "success"
    )
    return redirect(url_for("match_donation", donation_id=donation_id))


@app.route("/donations/<int:donation_id>/mark_collected", methods=["POST"])
def mark_collected(donation_id):
    """
    POST — coordinator records that the food has been collected by the NGO.

    Guards:
      - Donation must exist.
      - Donation must be in 'matched' status (not pending, not already collected).
      - A confirmed match record must exist.

    On success:
      - Sets collected_at on the match record.
      - Updates donation status to 'collected'.
      - Redirects to the match page with a flash message.
    """
    conn = get_connection()
    try:
        donation = conn.execute(
            "SELECT * FROM donations WHERE id = ?", (donation_id,)
        ).fetchone()

        if donation is None:
            abort(404)

        # Guard: must be matched (not pending, not collected)
        if donation["status"] != "matched":
            flash(
                f"Cannot mark collection for a donation with status "
                f"'{donation['status']}'. Only matched donations can be collected.",
                "error"
            )
            return redirect(url_for("match_donation", donation_id=donation_id))

        # Guard: match record must exist
        match_record = conn.execute(
            "SELECT * FROM matches WHERE donation_id = ?", (donation_id,)
        ).fetchone()
        if match_record is None:
            flash("No match record found for this donation.", "error")
            return redirect(url_for("match_donation", donation_id=donation_id))

        # Guard: not already collected
        if match_record["collected_at"] is not None:
            flash("This donation has already been marked as collected.", "warning")
            return redirect(url_for("match_donation", donation_id=donation_id))

        # --- Save collection timestamp and update status ---
        collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "UPDATE matches SET collected_at = ? WHERE donation_id = ?",
            (collected_at, donation_id)
        )
        conn.execute(
            "UPDATE donations SET status = 'collected' WHERE id = ?",
            (donation_id,)
        )
        conn.commit()

    finally:
        conn.close()

    flash(
        f"Donation #{donation_id} marked as collected. Thank you for reducing food waste!",
        "success"
    )
    return redirect(url_for("match_donation", donation_id=donation_id))


@app.route("/dashboard")
def dashboard():
    """
    Impact Dashboard — displays real metrics computed from the SQLite database.
    All numbers come from actual records; no figures are invented or estimated.
    """
    now_str = datetime.now(APP_TIMEZONE).strftime("%Y-%m-%dT%H:%M")

    conn = get_connection()
    try:
        # ---- Metric queries ----

        # 1. Total donations ever submitted
        total_donations = conn.execute(
            "SELECT COUNT(*) FROM donations"
        ).fetchone()[0]

        # 2. Successful matches (donation status = 'matched')
        matched_count = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'matched'"
        ).fetchone()[0]

        # 3. Completed pickups (donation status = 'collected')
        collected_count = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'collected'"
        ).fetchone()[0]

        # 4. Pending (active): status = 'pending' AND deadline not yet passed
        pending_count = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'pending' AND available_until >= ?",
            (now_str,)
        ).fetchone()[0]

        # 5. Expired: status = 'pending' AND deadline has passed
        expired_count = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'pending' AND available_until < ?",
            (now_str,)
        ).fetchone()[0]

        # 6. Servings available: only from active pending donations
        servings_available = conn.execute(
            "SELECT COALESCE(SUM(servings), 0) FROM donations "
            "WHERE status = 'pending' AND available_until >= ?",
            (now_str,)
        ).fetchone()[0]

        # ---- Status breakdown for the bar chart ----
        status_breakdown = {
            "pending":   pending_count,
            "expired":   expired_count,
            "matched":   matched_count,
            "collected": collected_count,
        }

        # ---- Recent activity (last 10 donations, newest first) ----
        recent_rows = conn.execute(
            "SELECT id, food_name, food_type, donor_name, location, "
            "       servings, available_until, status, created_at "
            "FROM donations ORDER BY id DESC LIMIT 10"
        ).fetchall()

        # Attach effective display status (pending-but-expired shows as 'expired')
        recent_activity = []
        for row in recent_rows:
            d = dict(row)
            d["display_status"] = effective_status(row)
            recent_activity.append(d)

        # ---- NGO count ----
        ngo_count = conn.execute("SELECT COUNT(*) FROM ngos").fetchone()[0]

    finally:
        conn.close()

    return render_template(
        "dashboard.html",
        total_donations=total_donations,
        matched_count=matched_count,
        collected_count=collected_count,
        pending_count=pending_count,
        expired_count=expired_count,
        servings_available=servings_available,
        status_breakdown=status_breakdown,
        recent_activity=recent_activity,
        food_type_labels=FOOD_TYPE_LABELS,
        ngo_count=ngo_count,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
