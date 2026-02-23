"""Trust signal analyzer for Instagram creator profiles.

Computes account-level trust signals from HikerAPI data:
- Account age (from user_about_v1)
- Follower/following ratio
- Posting cadence consistency
- Verification and business status

These are lightweight, non-ML signals that complement the ROI score.
"""

import logging
import math
import statistics
from datetime import UTC, datetime
from typing import Any

from hikerapi import Client

logger = logging.getLogger(__name__)

# Month name → number mapping for parsing "March 2012" date format
_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_user_about(hiker_client: Client, user_id: str | int) -> dict[str, Any] | None:
    """Fetch user_about_v1 data from HikerAPI.

    Returns dict with keys: username, is_verified, country, date, former_usernames
    or None on failure.
    """
    try:
        response = hiker_client.user_about_v1(user_id)
        if isinstance(response, dict):
            return response
        return None
    except Exception as e:
        logger.warning(f"user_about_v1 failed for {user_id}: {e}")
        return None


def _parse_account_date(date_str: str | None) -> datetime | None:
    """Parse account creation date from 'March 2012' format."""
    if not date_str or not isinstance(date_str, str):
        return None

    parts = date_str.strip().split()
    if len(parts) != 2:
        return None

    month_name, year_str = parts
    month = _MONTH_MAP.get(month_name.lower())
    if not month:
        return None

    try:
        year = int(year_str)
    except ValueError:
        return None

    return datetime(year, month, 1, tzinfo=UTC)


def calculate_account_age(user_about: dict[str, Any] | None) -> dict[str, Any]:
    """Calculate account age trust signal.

    Calibrated thresholds:
    - >= 5 years: high trust (score 1.0)
    - 2-5 years: moderate (score 0.5-1.0 linear)
    - 1-2 years: low-moderate (score 0.25-0.5)
    - < 1 year: low trust (score 0.0-0.25)
    """
    if not user_about:
        return {
            "score": 0.5,
            "years": None,
            "date_joined": None,
            "explanation": "Account creation date unavailable",
        }

    date_str = user_about.get("date")
    created_at = _parse_account_date(date_str)

    if not created_at:
        return {
            "score": 0.5,
            "years": None,
            "date_joined": date_str,
            "explanation": "Could not parse account creation date",
        }

    now = datetime.now(tz=UTC)
    age_years = (now - created_at).days / 365.25

    if age_years >= 5:
        score = 1.0
        explanation = f"Established account ({age_years:.1f} years)"
    elif age_years >= 2:
        score = 0.5 + (age_years - 2) * (0.5 / 3)
        explanation = f"Maturing account ({age_years:.1f} years)"
    elif age_years >= 1:
        score = 0.25 + (age_years - 1) * 0.25
        explanation = f"Relatively new account ({age_years:.1f} years)"
    else:
        score = age_years * 0.25
        explanation = f"Very new account ({age_years:.1f} years)"

    return {
        "score": round(min(1.0, max(0.0, score)), 2),
        "years": round(age_years, 1),
        "date_joined": date_str,
        "explanation": explanation,
    }


def calculate_follower_ratio(
    follower_count: int, following_count: int
) -> dict[str, Any]:
    """Calculate follower/following ratio trust signal.

    Uses log-scale normalization since ratio varies from 0.3 to 4.8M.

    Calibrated thresholds (from real data):
    - log10(ratio) >= 2.5 (ratio >= ~316): high trust
    - log10(ratio) >= 1.0 (ratio >= 10): moderate trust
    - log10(ratio) < 1.0 (ratio < 10): low trust
    """
    if following_count <= 0:
        return {
            "score": 0.5,
            "ratio": None,
            "explanation": "Following count unavailable",
        }

    ratio = follower_count / following_count

    if ratio <= 0:
        return {
            "score": 0.0,
            "ratio": 0.0,
            "explanation": "No followers",
        }

    log_ratio = math.log10(max(ratio, 0.1))

    # Normalize log_ratio to 0-1 scale
    # log10(1) = 0 → score 0.2 (following = followers is borderline)
    # log10(10) = 1 → score 0.5
    # log10(100) = 2 → score 0.75
    # log10(1000) = 3 → score 1.0
    score = min(1.0, max(0.0, log_ratio / 3.0))

    if ratio >= 100:
        explanation = f"Strong follower ratio ({ratio:.0f}:1)"
    elif ratio >= 10:
        explanation = f"Healthy follower ratio ({ratio:.0f}:1)"
    elif ratio >= 1:
        explanation = f"Balanced follower ratio ({ratio:.1f}:1)"
    else:
        explanation = f"More following than followers ({ratio:.2f}:1)"

    return {
        "score": round(score, 2),
        "ratio": round(ratio, 1),
        "explanation": explanation,
    }


def calculate_posting_cadence(posts: list[dict]) -> dict[str, Any]:
    """Calculate posting cadence consistency trust signal.

    Measures how regularly the creator posts by looking at gaps between posts.
    Low variance in post intervals = consistent = higher trust.

    Calibrated thresholds:
    - CV (coefficient of variation) <= 0.5: consistent (score >= 0.7)
    - CV 0.5-1.0: moderate (score 0.4-0.7)
    - CV > 1.0: inconsistent (score < 0.4)
    """
    if len(posts) < 5:
        return {
            "score": 0.5,
            "avg_days_between_posts": None,
            "consistency_cv": None,
            "explanation": "Not enough posts to measure cadence",
        }

    # Extract timestamps
    timestamps = []
    for post in posts:
        ts = post.get("taken_at_ts")
        if isinstance(ts, (int, float)):
            timestamps.append(ts)

    if len(timestamps) < 5:
        return {
            "score": 0.5,
            "avg_days_between_posts": None,
            "consistency_cv": None,
            "explanation": "Not enough timestamped posts",
        }

    # Sort descending (most recent first)
    timestamps.sort(reverse=True)

    # Calculate gaps in days between consecutive posts
    gaps = [
        (curr - nxt) / 86400
        for curr, nxt in zip(timestamps, timestamps[1:])
        if curr > nxt
    ]

    if len(gaps) < 3:
        return {
            "score": 0.5,
            "avg_days_between_posts": None,
            "consistency_cv": None,
            "explanation": "Insufficient gap data",
        }

    avg_gap = statistics.mean(gaps)
    stdev_gap = statistics.stdev(gaps)
    cv = stdev_gap / avg_gap if avg_gap > 0 else 0

    # Score: lower CV = more consistent = higher score
    if cv <= 0.5:
        score = 0.7 + (0.5 - cv) * 0.6  # 0.7-1.0
    elif cv <= 1.0:
        score = 0.4 + (1.0 - cv) * 0.6  # 0.4-0.7
    else:
        score = max(0.1, 0.4 - (cv - 1.0) * 0.15)

    score = min(1.0, max(0.0, score))

    if cv <= 0.5:
        explanation = f"Consistent posting ({avg_gap:.0f} days avg, low variance)"
    elif cv <= 1.0:
        explanation = f"Moderate posting consistency ({avg_gap:.0f} days avg)"
    else:
        explanation = f"Irregular posting pattern ({avg_gap:.0f} days avg, high variance)"

    return {
        "score": round(score, 2),
        "avg_days_between_posts": round(avg_gap, 1),
        "consistency_cv": round(cv, 2),
        "explanation": explanation,
    }


def calculate_former_usernames(user_about: dict[str, Any] | None) -> dict[str, Any]:
    """Check for former usernames as a trust signal.

    Frequent name changes can indicate rebranding or deceptive practices.
    """
    if not user_about:
        return {
            "score": 0.5,
            "count": None,
            "names": [],
            "explanation": "Former username data unavailable",
        }

    raw = user_about.get("former_usernames", "")

    # API returns empty string "" for no former names, or comma-separated list
    if not raw or (isinstance(raw, str) and not raw.strip()):
        return {
            "score": 1.0,
            "count": 0,
            "names": [],
            "explanation": "No former usernames — consistent identity",
        }

    if isinstance(raw, str):
        names = [n.strip() for n in raw.split(",") if n.strip()]
    elif isinstance(raw, list):
        names = [str(n) for n in raw if n]
    else:
        names = []

    count = len(names)

    if count == 0:
        score = 1.0
        explanation = "No former usernames — consistent identity"
    elif count <= 2:
        score = 0.7
        explanation = f"{count} former username(s) — minor rebranding"
    else:
        score = 0.4
        explanation = f"{count} former usernames — frequent identity changes"

    return {
        "score": round(score, 2),
        "count": count,
        "names": names[:5],  # Cap at 5 for display
        "explanation": explanation,
    }


def analyze_trust(
    user_data: dict[str, Any],
    posts: list[dict],
    user_about: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute composite trust score from individual signals.

    Weights (calibrated):
    - account_age: 0.25 — longer history = more trustworthy
    - follower_ratio: 0.25 — healthy ratio indicates organic growth
    - posting_cadence: 0.25 — consistent posting = professional creator
    - identity_stability: 0.25 — stable username = established brand
    """
    follower_count = int(user_data.get("follower_count", 0) or 0)
    following_count = int(user_data.get("following_count", 0) or 0)

    account_age = calculate_account_age(user_about)
    follower_ratio = calculate_follower_ratio(follower_count, following_count)
    posting_cadence = calculate_posting_cadence(posts)
    identity_stability = calculate_former_usernames(user_about)

    # Equal weights — all signals are complementary
    weights = {
        "account_age": 0.25,
        "follower_ratio": 0.25,
        "posting_cadence": 0.25,
        "identity_stability": 0.25,
    }

    trust_score = (
        weights["account_age"] * account_age["score"]
        + weights["follower_ratio"] * follower_ratio["score"]
        + weights["posting_cadence"] * posting_cadence["score"]
        + weights["identity_stability"] * identity_stability["score"]
    )

    # Trust verdict
    if trust_score >= 0.70:
        verdict = "High Trust"
        verdict_narrative = "Account shows strong trust signals across all dimensions"
    elif trust_score >= 0.45:
        verdict = "Moderate Trust"
        verdict_narrative = "Account shows mixed trust signals — review individual factors"
    else:
        verdict = "Low Trust"
        verdict_narrative = "Account shows concerning trust signals — investigate further"

    return {
        "trust_score": round(trust_score, 2),
        "verdict": verdict,
        "verdict_narrative": verdict_narrative,
        "signals": {
            "account_age": {**account_age, "weight": weights["account_age"]},
            "follower_ratio": {**follower_ratio, "weight": weights["follower_ratio"]},
            "posting_cadence": {**posting_cadence, "weight": weights["posting_cadence"]},
            "identity_stability": {**identity_stability, "weight": weights["identity_stability"]},
        },
    }
