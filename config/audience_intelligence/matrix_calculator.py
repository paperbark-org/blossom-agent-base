"""Calculate performance matrix from posts grouped by content_label x content_type."""

from collections import defaultdict
from typing import Any

# Map HikerAPI media_type to frontend content_type
MEDIA_TYPE_MAP = {
    1: "image",
    2: "video",
    8: "carousel",
}


def infer_content_type(post: dict) -> str:
    """Infer content type from post's media_type field."""
    media_type = post.get("media_type", 1)

    # Check if it's a reel (video with specific product_type)
    if media_type == 2:
        product_type = post.get("product_type", "")
        if product_type == "clips" or post.get("is_reel"):
            return "reel"
        return "video"

    return MEDIA_TYPE_MAP.get(media_type, "image")


def extract_thumbnail(post: dict) -> str | None:
    """Extract thumbnail URL from post data."""
    # Try image_versions2 first
    if post.get("image_versions2"):
        candidates = post["image_versions2"].get("candidates", [])
        if candidates:
            return candidates[0].get("url")

    # Try thumbnail_url
    if post.get("thumbnail_url"):
        return post["thumbnail_url"]

    # Try display_url
    if post.get("display_url"):
        return post["display_url"]

    return None


def calculate_performance_matrix(
    posts: list[dict],
    content_labels: list[dict],
    follower_count: int = 0,
) -> list[dict]:
    """
    Build performance matrix from posts grouped by content_label x content_type.

    Args:
        posts: Raw posts from HikerAPI
        content_labels: Gemini-generated labels [{"post_id": "...", "content_label": "...", "confidence": ...}]
        follower_count: User's follower count for engagement rate calculation

    Returns:
        List of MatrixCell dicts matching frontend interface
    """
    # Build lookup of post_id -> content_label
    label_lookup: dict[str, str] = {}
    for label_item in content_labels:
        post_id = str(label_item.get("post_id", ""))
        content_label = label_item.get("content_label", "other")
        if post_id:
            label_lookup[post_id] = content_label

    # Group posts by (content_label, content_type)
    matrix_cells: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "posts": [],
            "total_likes": 0,
            "total_comments": 0,
            "total_views": 0,
            "thumbnails": [],
        }
    )

    # Also build a code-based lookup for fallback matching
    code_lookup: dict[str, str] = {}
    for label_item in content_labels:
        post_id = str(label_item.get("post_id", ""))
        content_label = label_item.get("content_label", "other")
        if post_id:
            code_lookup[post_id] = content_label

    for post in posts:
        post_id = str(post.get("id", ""))
        post_code = str(post.get("code", ""))
        # Try matching by ID first, then by code (shortcode), then fallback to "other"
        content_label = label_lookup.get(post_id) or code_lookup.get(post_code) or "other"
        content_type = infer_content_type(post)

        key = (content_label, content_type)
        cell = matrix_cells[key]

        cell["posts"].append(post)
        cell["total_likes"] += post.get("like_count", 0)
        cell["total_comments"] += post.get("comment_count", 0)
        cell["total_views"] += post.get("view_count", 0) or post.get("play_count", 0)

        # Collect thumbnails (max 3 per cell)
        if len(cell["thumbnails"]) < 3:
            thumbnail = extract_thumbnail(post)
            if thumbnail:
                cell["thumbnails"].append(thumbnail)

    # Build output matrix
    result: list[dict] = []

    for (content_label, content_type), cell in matrix_cells.items():
        post_count = len(cell["posts"])
        if post_count == 0:
            continue

        avg_likes = cell["total_likes"] / post_count
        avg_comments = cell["total_comments"] / post_count
        avg_views = cell["total_views"] / post_count

        # Calculate engagement rate if follower count is available
        if follower_count > 0:
            avg_engagement_rate = (avg_likes + avg_comments) / follower_count
        else:
            avg_engagement_rate = 0.0

        result.append({
            "content_label": content_label,
            "content_type": content_type,
            "post_count": post_count,
            "avg_engagement_rate": round(avg_engagement_rate, 4),
            "avg_likes": round(avg_likes, 1),
            "avg_comments": round(avg_comments, 1),
            "avg_views": round(avg_views, 1),
            "example_post_ids": [str(p.get("id", "")) for p in cell["posts"][:3]],
            "example_thumbnails": cell["thumbnails"],
        })

    # Sort by engagement rate descending
    result.sort(key=lambda x: x["avg_engagement_rate"], reverse=True)

    return result
