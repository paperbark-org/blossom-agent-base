"""Performance analysis from Instagram posts."""

import re
from typing import Any

from api.services.audience_intelligence.roi_calculator import _get_caption_text, is_sponsored_post


def calculate_engagement_metrics(posts: list[dict], follower_count: int = 0) -> dict[str, Any]:
    """Calculate average engagement metrics from posts."""
    if not posts:
        return {
            "avg_engagement_rate": 0.0,
            "avg_likes": 0.0,
            "avg_comments": 0.0,
            "total_posts_analyzed": 0,
        }

    total_likes = sum(p.get("like_count", 0) for p in posts)
    total_comments = sum(p.get("comment_count", 0) for p in posts)
    post_count = len(posts)

    avg_likes = total_likes / post_count if post_count > 0 else 0
    avg_comments = total_comments / post_count if post_count > 0 else 0

    # Calculate engagement rate
    if follower_count > 0:
        avg_engagement_rate = ((total_likes + total_comments) / post_count / follower_count) * 100
    else:
        avg_engagement_rate = 0.0

    return {
        "avg_engagement_rate": round(avg_engagement_rate, 2),
        "avg_likes": round(avg_likes, 1),
        "avg_comments": round(avg_comments, 1),
        "total_posts_analyzed": post_count,
    }


def _extract_brands(post: dict, caption: str) -> set[str]:
    """Extract brand names from a sponsored post's metadata and caption."""
    brands: set[str] = set()

    # Official sponsor tags
    for sponsor in post.get("sponsor_tags", []):
        if isinstance(sponsor, dict):
            name = sponsor.get("username") or sponsor.get("full_name")
            if name:
                brands.add(name)

    # Branded content tags
    branded_info = post.get("branded_content_tag_info", {})
    if isinstance(branded_info, dict):
        name = branded_info.get("name") or branded_info.get("username")
        if name:
            brands.add(name)

    # Co-author/collaboration
    for coauthor in post.get("coauthor_producers", []):
        if isinstance(coauthor, dict):
            name = coauthor.get("username") or coauthor.get("full_name")
            if name:
                brands.add(name)

    # @mentions in caption
    if caption:
        mentions = re.findall(r"@(\w+)", caption)
        generic = {"instagram", "instagr", "link", "code", "shop", "bio"}
        brands.update(m for m in mentions if m.lower() not in generic)

    return brands


def detect_sponsored_content(posts: list[dict]) -> dict[str, Any]:
    """Detect sponsored posts and extract brand mentions."""
    sponsored_posts = []
    brands: set[str] = set()

    for post in posts:
        if is_sponsored_post(post):
            sponsored_posts.append(post)
            caption = _get_caption_text(post).lower()
            brands.update(_extract_brands(post, caption))

    # Calculate sponsored vs organic delta
    delta = None
    if len(posts) >= 2 and sponsored_posts:
        organic_posts = [p for p in posts if not is_sponsored_post(p)]
        sponsored_engagement = sum(
            p.get("like_count", 0) + p.get("comment_count", 0) for p in sponsored_posts
        ) / len(sponsored_posts)
        organic_engagement = (
            sum(p.get("like_count", 0) + p.get("comment_count", 0) for p in organic_posts)
            / len(organic_posts)
            if organic_posts
            else 0
        )
        if organic_engagement > 0:
            delta = ((sponsored_engagement - organic_engagement) / organic_engagement) * 100

    return {
        "total_partnerships": len(sponsored_posts),
        "brands_worked_with": sorted(brands)[:10],
        "sponsored_vs_organic_delta": round(delta, 2) if delta is not None else None,
        "sponsored_post_count": len(sponsored_posts),
    }


def analyze_content_types(posts: list[dict], follower_count: int = 0) -> dict[str, Any]:
    """Breakdown posts by content type (reel, image, carousel)."""
    from api.services.audience_intelligence.matrix_calculator import infer_content_type

    content_breakdown = {}

    for post in posts:
        content_type = infer_content_type(post)

        if content_type not in content_breakdown:
            content_breakdown[content_type] = {
                "post_count": 0,
                "total_engagement": 0,
                "posts": [],
            }

        engagement = post.get("like_count", 0) + post.get("comment_count", 0)
        content_breakdown[content_type]["post_count"] += 1
        content_breakdown[content_type]["total_engagement"] += engagement
        content_breakdown[content_type]["posts"].append(post)

    # Calculate averages
    result = {}
    for content_type, data in content_breakdown.items():
        post_count = data["post_count"]
        avg_engagement = data["total_engagement"] / post_count if post_count > 0 else 0

        # Engagement rate = (avg_engagement / follower_count) * 100
        if follower_count > 0:
            avg_er = (avg_engagement / follower_count) * 100
        else:
            avg_er = 0

        result[content_type] = {
            "post_count": post_count,
            "avg_engagement": round(avg_engagement, 1),
            "avg_engagement_rate": round(avg_er, 2),
        }

    return result


def calculate_performance(
    posts: list[dict],
    user_data: dict[str, Any],
) -> dict[str, Any]:
    """Calculate comprehensive performance metrics."""
    follower_count = user_data.get("follower_count", 0) or 0

    engagement_metrics = calculate_engagement_metrics(posts, follower_count)
    sponsored_metrics = detect_sponsored_content(posts)
    content_breakdown = analyze_content_types(posts, follower_count)

    return {
        "engagement_metrics": engagement_metrics,
        "sponsored_metrics": sponsored_metrics,
        "content_breakdown": content_breakdown,
    }
