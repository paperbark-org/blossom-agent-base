"""ROI Calculator for Influencer Analysis.

Calculates a composite ROI score from measurable engagement signals.
No ML required - just math on HikerAPI data.
"""

import re
import statistics
from typing import Any


# Sponsored content indicators — caption patterns
SPONSORED_PATTERNS = [
    # Hashtag indicators
    r"#ad\b",
    r"#sponsored\b",
    r"#partner\b",
    r"#partnership\b",
    r"#gifted\b",
    r"#collab\b",
    r"#brandpartner\b",
    r"#brandambassador\b",
    r"#ambassador\b",
    r"#paidpartnership\b",
    r"#spon\b",
    r"#promo\b",
    r"#advertisement\b",
    # Phrase indicators
    r"paid partnership",
    r"sponsored by",
    r"in partnership with",
    r"partnered with",
    r"\bad\b:",
    r"advertisement",
    r"presents\b",
    r"powered by",
]

SPONSORED_REGEX = re.compile("|".join(SPONSORED_PATTERNS), re.IGNORECASE)


def _get_caption_text(post: dict) -> str:
    """Safely extract caption text from a post, handling dict or string formats."""
    caption = post.get("caption")
    if isinstance(caption, dict):
        return caption.get("text", "")
    if isinstance(caption, str):
        return caption
    caption_text = post.get("caption_text")
    if isinstance(caption_text, str):
        return caption_text
    return ""


def is_sponsored_post(post: dict) -> bool:
    """Check if a post is sponsored based on API flags, metadata, or caption content."""
    # Check API-level flag first (most reliable)
    if post.get("is_paid_partnership"):
        return True

    # Check branded_content_tag_info (Instagram's native branded content tag)
    branded_info = post.get("branded_content_tag_info")
    if isinstance(branded_info, dict) and branded_info:
        if branded_info.get("name") or branded_info.get("username"):
            return True

    # Check coauthor_producers (collaboration indicator)
    coauthors = post.get("coauthor_producers")
    if isinstance(coauthors, list) and coauthors:
        return True

    # Check sponsor_tags
    sponsor_tags = post.get("sponsor_tags")
    if isinstance(sponsor_tags, list) and sponsor_tags:
        return True

    # Fall back to caption regex
    caption = _get_caption_text(post)
    return bool(SPONSORED_REGEX.search(caption))


def get_engagement(post: dict) -> float:
    """Get total engagement for a post (likes + comments)."""
    likes = post.get("like_count", 0) or 0
    comments = post.get("comment_count", 0) or 0
    return float(likes + comments)


def calc_sponsored_delta(posts: list[dict]) -> tuple[float, str]:
    """Calculate sponsored post performance vs organic.

    Returns:
        (score, explanation) where score is 0-1
    """
    sponsored = [p for p in posts if is_sponsored_post(p)]
    organic = [p for p in posts if not is_sponsored_post(p)]

    if not sponsored:
        return 0.5, "No sponsored posts found to analyze"

    if not organic:
        return 0.5, "No organic posts to compare against"

    avg_sponsored = statistics.mean([get_engagement(p) for p in sponsored])
    avg_organic = statistics.mean([get_engagement(p) for p in organic])

    if avg_organic == 0:
        return 0.5, "Insufficient engagement data"

    ratio = avg_sponsored / avg_organic

    # Normalize to 0-1 scale
    # ratio >= 1.0 means sponsored performs as well or better = 1.0
    # ratio = 0.5 means sponsored gets half the engagement = 0.5
    # ratio = 0 means no engagement on sponsored = 0
    score = min(ratio, 1.0)

    if ratio >= 0.8:
        explanation = f"Sponsored posts retain {ratio:.0%} of organic engagement - audience accepts branded content well"
    elif ratio >= 0.5:
        explanation = f"Sponsored posts get {ratio:.0%} of organic engagement - moderate audience tolerance"
    else:
        explanation = f"Sponsored posts only get {ratio:.0%} of organic engagement - audience may resist branded content"

    return score, explanation


def calc_engagement_rate(posts: list[dict], follower_count: int) -> tuple[float, str]:
    """Calculate average engagement rate.

    Returns:
        (score, explanation) where score is 0-1
    """
    if not posts or follower_count <= 0:
        return 0.5, "Insufficient data for engagement rate"

    total_engagement = sum(get_engagement(p) for p in posts)
    avg_engagement = total_engagement / len(posts)
    rate = (avg_engagement / follower_count) * 100

    # Normalize to 0-1 scale
    # >= 5% = 1.0 (exceptional)
    # 3% = 0.8 (great)
    # 1% = 0.5 (average)
    # 0.5% = 0.25 (below average)
    if rate >= 5:
        score = 1.0
    elif rate >= 3:
        score = 0.8 + (rate - 3) * 0.1  # 3-5% maps to 0.8-1.0
    elif rate >= 1:
        score = 0.5 + (rate - 1) * 0.15  # 1-3% maps to 0.5-0.8
    else:
        score = rate * 0.5  # 0-1% maps to 0-0.5

    score = max(0, min(1, score))

    if rate >= 3:
        explanation = f"{rate:.1f}% engagement rate - excellent audience responsiveness"
    elif rate >= 1:
        explanation = f"{rate:.1f}% engagement rate - healthy audience engagement"
    else:
        explanation = f"{rate:.1f}% engagement rate - below average, possible fake followers"

    return score, explanation


def calc_consistency(posts: list[dict]) -> tuple[float, str]:
    """Calculate engagement consistency (low variance = reliable performer).

    Returns:
        (score, explanation) where score is 0-1
    """
    if len(posts) < 3:
        return 0.5, "Not enough posts to measure consistency"

    engagements = [get_engagement(p) for p in posts]

    if not any(engagements):
        return 0.5, "No engagement data available"

    mean_eng = statistics.mean(engagements)
    if mean_eng == 0:
        return 0.5, "No engagement data available"

    stdev = statistics.stdev(engagements)
    cv = stdev / mean_eng  # Coefficient of variation

    # Lower CV = more consistent
    # CV of 0.3 or less = very consistent = 1.0
    # CV of 0.5 = moderate = 0.7
    # CV of 1.0 = high variance = 0.4
    # CV > 1.5 = very unpredictable = 0.2
    if cv <= 0.3:
        score = 1.0
    elif cv <= 0.5:
        score = 1.0 - (cv - 0.3) * 1.5  # 0.3-0.5 maps to 1.0-0.7
    elif cv <= 1.0:
        score = 0.7 - (cv - 0.5) * 0.6  # 0.5-1.0 maps to 0.7-0.4
    else:
        score = max(0.2, 0.4 - (cv - 1.0) * 0.2)  # >1.0 maps down from 0.4

    score = max(0, min(1, score))

    if cv <= 0.3:
        explanation = "Highly consistent engagement - predictable campaign performance"
    elif cv <= 0.5:
        explanation = "Moderately consistent engagement - generally reliable"
    elif cv <= 1.0:
        explanation = "Variable engagement - performance may be unpredictable"
    else:
        explanation = "Highly variable engagement - campaign results could swing widely"

    return score, explanation


def calculate_roi_score(posts: list[dict], user_data: dict[str, Any]) -> dict[str, Any]:
    """Calculate composite ROI score from engagement signals.

    Args:
        posts: List of post data from HikerAPI
        user_data: User profile data including follower_count

    Returns:
        Dictionary with roi_score, verdict, signals, and narrative
    """
    follower_count = user_data.get("follower_count", 0) or 0

    # Calculate individual signals
    sponsored_delta, sponsored_explanation = calc_sponsored_delta(posts)
    engagement_rate, engagement_explanation = calc_engagement_rate(posts, follower_count)
    consistency, consistency_explanation = calc_consistency(posts)

    # Composite score with calibrated weights.
    # Engagement is the primary signal (always available). Sponsored delta is
    # secondary because it defaults to 0.5 when no sponsored posts exist.
    roi_score = (
        0.45 * engagement_rate +
        0.30 * consistency +
        0.25 * sponsored_delta
    )

    # Calibrated verdict thresholds.
    # From real data: P50=0.50, P75=0.55. Shifted down so ~20% Partner,
    # ~60% Caution, ~20% Avoid across a diverse creator set.
    if roi_score >= 0.60:
        verdict = "Partner"
        verdict_narrative = "Strong ROI potential - recommended for campaigns"
    elif roi_score >= 0.35:
        verdict = "Caution"
        verdict_narrative = "Moderate ROI potential - review signals before committing"
    else:
        verdict = "Avoid"
        verdict_narrative = "Low ROI potential - significant risk factors present"

    return {
        "roi_score": round(roi_score, 2),
        "verdict": verdict,
        "verdict_narrative": verdict_narrative,
        "signals": {
            "engagement_rate": {
                "score": round(engagement_rate, 2),
                "weight": 0.45,
                "explanation": engagement_explanation,
            },
            "consistency": {
                "score": round(consistency, 2),
                "weight": 0.30,
                "explanation": consistency_explanation,
            },
            "sponsored_delta": {
                "score": round(sponsored_delta, 2),
                "weight": 0.25,
                "explanation": sponsored_explanation,
            },
        },
    }
