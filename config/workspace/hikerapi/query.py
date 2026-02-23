#!/usr/bin/env python3
"""
HikerAPI query helper for Blossom.
Usage: python query.py "<natural language query>" [--username X] [--user_id X] [--url X] [--hashtag X] [--location X]
"""

import os
import sys
import json
import argparse
import requests

API_BASE = "https://api.hikerapi.com"
TOKEN = os.environ.get("HIKERAPI_TOKEN", "")

def headers():
    return {
        "x-access-key": TOKEN,
        "accept": "application/json"
    }

def get(path, params=None):
    url = f"{API_BASE}{path}"
    resp = requests.get(url, headers=headers(), params=params)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"error": resp.text}

def resolve_username(username):
    """Get user_id (pk) from username."""
    status, data = get("/v1/user/by/username", {"username": username})
    if status == 200:
        return data.get("pk") or data.get("id"), data
    return None, data

def user_profile(username=None, user_id=None):
    if username and not user_id:
        uid, data = resolve_username(username)
        return data
    if user_id:
        _, data = get("/v1/user/by/id", {"id": user_id})
        return data

def user_posts(username=None, user_id=None, limit=12):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/v1/user/medias/chunk", {"user_id": user_id})
    return data

def user_reels(username=None, user_id=None):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/v2/user/clips", {"user_id": user_id})
    return data

def user_followers(username=None, user_id=None):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/gql/user/followers/chunk", {"user_id": user_id})
    return data

def user_following(username=None, user_id=None):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/gql/user/following/chunk", {"user_id": user_id})
    return data

def user_stories(username=None, user_id=None):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/v1/user/stories", {"user_id": user_id})
    return data

def user_highlights(username=None, user_id=None):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/v1/user/highlights", {"user_id": user_id})
    return data

def user_tagged_posts(username=None, user_id=None):
    if username and not user_id:
        user_id, _ = resolve_username(username)
    _, data = get("/v2/user/tag/medias", {"user_id": user_id})
    return data

def media_by_url(url):
    _, data = get("/v1/media/by/url", {"url": url})
    return data

def media_insight(media_id):
    _, data = get("/v1/media/insight", {"media_id": media_id})
    return data

def media_likers(media_id):
    _, data = get("/v1/media/likers", {"id": media_id})
    return data

def media_comments(media_id):
    _, data = get("/v1/media/comments/chunk", {"media_id": media_id})
    return data

def hashtag_info(name):
    _, data = get("/v1/hashtag/by/name", {"name": name})
    return data

def hashtag_top(name):
    _, data = get("/v1/hashtag/medias/top", {"name": name})
    return data

def hashtag_recent(name):
    _, data = get("/v2/hashtag/medias/recent", {"name": name})
    return data

def hashtag_reels(name):
    _, data = get("/v1/hashtag/medias/clips", {"name": name})
    return data

def search_accounts(query):
    _, data = get("/v2/search/accounts", {"query": query})
    return data

def search_hashtags(query):
    _, data = get("/v2/search/hashtags", {"query": query})
    return data

def location_search(query):
    _, data = get("/v1/fbsearch/places", {"query": query})
    return data

def location_posts(location_pk):
    _, data = get("/v1/location/medias/recent", {"location_pk": location_pk})
    return data

def suggested_accounts(user_id):
    _, data = get("/v2/user/suggested/profiles", {"user_id": user_id})
    return data

# ─── Natural Language Router ───────────────────────────────────────────────

def route(query: str, username=None, user_id=None, url=None, hashtag=None, location=None):
    q = query.lower()

    # Post/URL analysis
    if url:
        result = {"media": media_by_url(url)}
        mid = result["media"].get("pk") or result["media"].get("id")
        if mid:
            result["insight"] = media_insight(mid)
            result["comments"] = media_comments(mid)
        return result

    # Hashtag queries
    if hashtag or any(w in q for w in ["hashtag", "trending", "#"]):
        tag = hashtag or extract_hashtag(query)
        if tag:
            return {
                "hashtag_info": hashtag_info(tag),
                "top_posts": hashtag_top(tag),
                "recent_posts": hashtag_recent(tag),
            }

    # Location queries
    if location or "location" in q or "near" in q or "at " in q:
        loc = location or extract_location(query)
        loc_data = location_search(loc)
        pks = loc_data.get("items", [])
        result = {"locations": loc_data}
        if pks:
            pk = pks[0].get("location", {}).get("pk")
            if pk:
                result["recent_posts"] = location_posts(pk)
        return result

    # Account search
    if not username and not user_id and ("find" in q or "search" in q or "who is" in q):
        term = query.replace("find","").replace("search","").replace("who is","").strip()
        return {"search_results": search_accounts(term)}

    # User-specific queries
    if username or user_id:
        if any(w in q for w in ["follower", "who follows"]):
            return {"followers": user_followers(username=username, user_id=user_id)}
        if any(w in q for w in ["following", "who they follow"]):
            return {"following": user_following(username=username, user_id=user_id)}
        if any(w in q for w in ["reel", "clip", "video"]):
            return {"reels": user_reels(username=username, user_id=user_id)}
        if any(w in q for w in ["stor"]):
            return {"stories": user_stories(username=username, user_id=user_id)}
        if any(w in q for w in ["highlight"]):
            return {"highlights": user_highlights(username=username, user_id=user_id)}
        if any(w in q for w in ["tag", "mentioned"]):
            return {"tagged_posts": user_tagged_posts(username=username, user_id=user_id)}
        if any(w in q for w in ["post", "feed", "content", "media"]):
            return {"posts": user_posts(username=username, user_id=user_id)}
        # Default: full profile overview
        profile = user_profile(username=username, user_id=user_id)
        uid = profile.get("pk") or profile.get("id") or user_id
        return {
            "profile": profile,
            "recent_posts": user_posts(user_id=uid),
        }

    return {"error": "Couldn't determine what to query. Try passing --username, --hashtag, or --url."}


def extract_hashtag(query):
    import re
    match = re.search(r"#(\w+)|hashtag[:\s]+(\w+)", query, re.I)
    if match:
        return match.group(1) or match.group(2)
    words = query.split()
    for w in words:
        if w.startswith("#"):
            return w[1:]
    return None

def extract_location(query):
    # Simple heuristic: everything after "near" or "in" or "at"
    import re
    match = re.search(r"(?:near|in|at)\s+(.+)", query, re.I)
    return match.group(1).strip() if match else query.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HikerAPI natural language query")
    parser.add_argument("query", nargs="?", default="", help="Natural language query")
    parser.add_argument("--username", "-u", help="Instagram username")
    parser.add_argument("--user_id", help="Instagram user ID")
    parser.add_argument("--url", help="Instagram post/profile URL")
    parser.add_argument("--hashtag", help="Hashtag (without #)")
    parser.add_argument("--location", help="Location name")
    args = parser.parse_args()

    if not TOKEN:
        print("ERROR: HIKERAPI_TOKEN not set. Export it first: export HIKERAPI_TOKEN=your_key")
        sys.exit(1)

    result = route(
        args.query,
        username=args.username,
        user_id=args.user_id,
        url=args.url,
        hashtag=args.hashtag,
        location=args.location,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
