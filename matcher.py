"""
matcher.py
----------
Rule-based NGO matching for SharePlate Connect.

This module is pure Python — no Flask imports, no database access.
It receives a donation and a list of NGOs as plain dictionaries and
returns a ranked list of match recommendations with explanations.

MATCHING RULES
--------------
Each NGO candidate is evaluated against three rules:

  Rule A — Category compatibility  (3 points)
      The NGO's food_preference is 'any', OR it matches the donation's food_type.
      An NGO that cannot accept this food category is excluded entirely.

  Rule B — Capacity compatibility  (2 points)
      The donation's servings value meets or exceeds the NGO's min_quantity.
      If servings is 0 or unknown, we still include the NGO but note the gap.

  Rule C — Location overlap         (0–2 points)
      We tokenise both the donation location and the NGO service_area into
      lowercase words and count how many words they share.
      Up to 2 points are awarded (1 per shared word, capped at 2).
      This is an approximate text match — no geocoding is used.

Maximum possible score: 7 points.

An NGO is recommended only if it passes Rule A (category).
Rules B and C affect score and explanation, but do not exclude an NGO.
"""


def _location_overlap(location_a, location_b):
    """
    Count shared significant words between two location strings.
    Ignores common short words (connectives, prepositions).
    Returns an integer word-overlap count.
    """
    # Short words that carry no location meaning
    stopwords = {
        "road", "rd", "street", "st", "nagar", "layout", "main",
        "cross", "near", "and", "the", "of", "in", "at", "by",
        "1st", "2nd", "3rd", "4th", "5th", "no", "no.",
    }

    def tokenise(text):
        # Split on whitespace and common punctuation; lowercase; strip short filler
        import re
        words = re.split(r"[\s,./\-]+", text.lower())
        return {w for w in words if len(w) > 2 and w not in stopwords}

    words_a = tokenise(location_a)
    words_b = tokenise(location_b)
    return len(words_a & words_b)


def find_matches(donation, ngos):
    """
    Evaluate all NGOs against a single donation and return a ranked list
    of match recommendations.

    Parameters
    ----------
    donation : dict-like
        A donation row from the database (supports dict-style access).
        Required keys: food_type, servings, location, available_until
        Optional keys: food_name

    ngos : list of dict-like
        All NGO rows from the database.
        Required keys: id, name, contact_name, phone, service_area,
                       food_preference, min_quantity

    Returns
    -------
    list of dict
        Each item in the list is a recommendation dict with keys:
          ngo       — the original NGO row
          score     — integer 0–7
          reasons   — list of human-readable reason strings (why it matched)
          warnings  — list of human-readable caveats (limitations)
          excluded  — bool, True if the NGO was excluded (category mismatch)
          reason_for_exclusion — str, only set when excluded=True
    """
    recommendations = []

    donation_food_type  = (donation["food_type"]     or "").strip().lower()
    donation_servings   = int(donation["servings"] or 0)
    donation_location   = (donation["location"]      or "").strip()

    for ngo in ngos:
        ngo_food_pref   = (ngo["food_preference"] or "any").strip().lower()
        ngo_min_qty     = int(ngo["min_quantity"]  or 1)
        ngo_service     = (ngo["service_area"]     or "").strip()

        reasons  = []
        warnings = []
        score    = 0

        # ------------------------------------------------------------------
        # Rule A — Category compatibility (MANDATORY — exclusion if failed)
        # ------------------------------------------------------------------
        if ngo_food_pref == "any":
            score += 3
            reasons.append("Accepts all food categories")
        elif ngo_food_pref == donation_food_type:
            score += 3
            reasons.append(
                f"Specialises in {ngo_food_pref.replace('_', ' ').title()}"
            )
        else:
            # Category mismatch — exclude this NGO
            recommendations.append({
                "ngo":                   ngo,
                "score":                 0,
                "reasons":               [],
                "warnings":              [],
                "excluded":              True,
                "reason_for_exclusion":  (
                    f"Does not accept {donation_food_type.replace('_', ' ').title()} "
                    f"(only accepts {ngo_food_pref.replace('_', ' ').title()})"
                ),
            })
            continue

        # ------------------------------------------------------------------
        # Rule B — Capacity compatibility
        # ------------------------------------------------------------------
        if donation_servings == 0:
            warnings.append(
                "Donation servings not specified — capacity compatibility unknown"
            )
        elif donation_servings >= ngo_min_qty:
            score += 2
            reasons.append(
                f"Quantity sufficient (donation ~{donation_servings} servings, "
                f"NGO minimum {ngo_min_qty})"
            )
        else:
            # Below minimum — still include but flag it
            warnings.append(
                f"Donation may be below this NGO's minimum of {ngo_min_qty} servings "
                f"(donation has ~{donation_servings})"
            )

        # ------------------------------------------------------------------
        # Rule C — Location overlap
        # ------------------------------------------------------------------
        overlap = _location_overlap(donation_location, ngo_service)
        location_points = min(overlap, 2)
        score += location_points

        if overlap == 0:
            warnings.append(
                "No location keywords matched — verify pickup area manually "
                f"(NGO serves: {ngo_service})"
            )
        elif overlap == 1:
            reasons.append(f"Partial location match with service area: {ngo_service}")
        else:
            reasons.append(f"Good location match with service area: {ngo_service}")

        recommendations.append({
            "ngo":                  ngo,
            "score":                score,
            "reasons":              reasons,
            "warnings":             warnings,
            "excluded":             False,
            "reason_for_exclusion": "",
        })

    # Sort non-excluded matches by score descending, excluded ones at the end
    included  = [r for r in recommendations if not r["excluded"]]
    excluded  = [r for r in recommendations if r["excluded"]]
    included.sort(key=lambda r: r["score"], reverse=True)

    return included + excluded
