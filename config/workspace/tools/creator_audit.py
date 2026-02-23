#!/usr/bin/env python3
"""
creator_audit.py — Blossom's standalone creator intelligence tool.

Tiered approach — start cheap, go deeper on request:
  Tier 1 (Quick Scan):   profile + 12 posts, no comments → Low confidence
  Tier 2 (Standard):     36 posts + ~60 comments         → Medium confidence
  Tier 3 (Deep Audit):   100 posts + ~200 comments       → High confidence

Usage:
    python3 tools/creator_audit.py <instagram_handle>           # Tier 1 (default)
    python3 tools/creator_audit.py <instagram_handle> --tier 2
    python3 tools/creator_audit.py <instagram_handle> --tier 3
"""

import json
import math
import os
import re
import statistics
import sys
import urllib.request
from datetime import UTC, datetime

# ─── Config ───────────────────────────────────────────────────────────────────
HIKER_API_KEY = os.environ["HIKER_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HIKER_BASE = "https://api.hikerapi.com"
HIKER_HEADERS = {
    "x-access-key": HIKER_API_KEY,
    "accept": "application/json",
    "User-Agent": "curl/7.88.1",  # HikerAPI blocks Python's default UA
}

# ─── Tier configuration ───────────────────────────────────────────────────────
TIERS = {
    1: {
        "label": "Quick Scan",
        "confidence": "Low",
        "max_posts": 12,
        "comment_posts": 0,       # no comment sampling at tier 1
        "comments_per_post": 0,
        "fetch_account_history": False,
        "caveat": (
            "⚠️  Low confidence — based on {posts} posts only. "
            "Comments not sampled. ROI and Trust scores are indicative, not reliable.\n"
            "   → Run with --tier 2 for a Standard Audit with comment quality data."
        ),
    },
    2: {
        "label": "Standard Audit",
        "confidence": "Medium",
        "max_posts": 36,
        "comment_posts": 3,
        "comments_per_post": 20,
        "fetch_account_history": True,
        "caveat": (
            "ℹ️  Medium confidence — based on {posts} posts and ~{comments} comments "
            "across {comment_posts} posts.\n"
            "   → Run with --tier 3 for a Deep Audit before committing campaign budget."
        ),
    },
    3: {
        "label": "Deep Audit",
        "confidence": "High",
        "max_posts": 100,
        "comment_posts": 8,
        "comments_per_post": 25,
        "fetch_account_history": True,
        "caveat": (
            "✅  High confidence — based on {posts} posts and ~{comments} comments "
            "across {comment_posts} posts."
        ),
    },
}

# ─── HikerAPI helpers ─────────────────────────────────────────────────────────

def hiker_get(path: str, params: dict) -> dict:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{HIKER_BASE}{path}?{query}"
    req = urllib.request.Request(url, headers=HIKER_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_profile(username: str) -> dict:
    """GET /v2/user/by/username"""
    data = hiker_get("/v2/user/by/username", {"username": username})
    return data.get("user", data)


def fetch_posts(user_id: str, max_posts: int = 50) -> list:
    """GET /v1/user/medias/chunk — paginated up to max_posts."""
    all_posts = []
    end_cursor = None
    # Each page gives ~12 posts; cap pages to avoid runaway calls
    max_pages = math.ceil(max_posts / 12) + 1
    for _ in range(max_pages):
        params = {"user_id": user_id}
        if end_cursor:
            params["end_cursor"] = end_cursor
        resp = hiker_get("/v1/user/medias/chunk", params)
        items = resp if isinstance(resp, list) else resp.get("items", [])
        if isinstance(items, list) and items and isinstance(items[0], list):
            end_cursor = items[1] if len(items) > 1 else None
            items = items[0]
        all_posts.extend(items)
        if len(all_posts) >= max_posts or not end_cursor:
            break
    return all_posts[:max_posts]


def fetch_user_about(user_id: str) -> dict:
    """GET /v1/user/about"""
    try:
        return hiker_get("/v1/user/about", {"id": user_id})
    except Exception:
        return {}


def fetch_comments(media_id: str, limit: int = 20) -> list:
    """GET /v1/media/comments/chunk — param is 'id' not 'media_id'"""
    try:
        resp = hiker_get("/v1/media/comments/chunk", {"id": media_id})
        items = resp if isinstance(resp, list) else resp.get("comments", [])
        if isinstance(items, list) and items and isinstance(items[0], list):
            items = items[0]
        return [
            {"text": c.get("text", ""), "username": c.get("user", {}).get("username", "")}
            for c in items[:limit] if c.get("text", "").strip()
        ]
    except Exception:
        return []


# ─── Claude (Anthropic) helper ────────────────────────────────────────────────

def claude(system: str, user: str, model: str = "claude-haiku-4-5") -> str:
    """Call Claude API. Returns raw text — caller parses JSON."""
    payload = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["content"][0]["text"].strip()


# ─── Sponsored detection ──────────────────────────────────────────────────────

SPONSORED_RE = re.compile(
    r"#ad\b|#sponsored\b|#partner\b|#gifted\b|#collab\b|#paidpartnership\b|"
    r"#brandambassador\b|#ambassador\b|paid partnership|sponsored by|in partnership with",
    re.IGNORECASE,
)

def is_sponsored(post: dict) -> bool:
    if post.get("is_paid_partnership"):
        return True
    if post.get("coauthor_producers"):
        return True
    caption = post.get("caption") or ""
    if isinstance(caption, dict):
        caption = caption.get("text", "")
    return bool(SPONSORED_RE.search(caption))

def get_engagement(post: dict) -> float:
    return float((post.get("like_count") or 0) + (post.get("comment_count") or 0))


# ─── ROI Score ────────────────────────────────────────────────────────────────

def calc_roi(posts: list, follower_count: int) -> dict:
    if not posts or follower_count <= 0:
        return {"roi_score": 0.5, "verdict": "Caution", "signals": {}}

    engagements = [get_engagement(p) for p in posts]

    # Engagement rate score
    avg_eng = statistics.mean(engagements)
    rate = (avg_eng / follower_count) * 100
    if rate >= 5:
        er_score = 1.0
    elif rate >= 3:
        er_score = 0.8 + (rate - 3) * 0.1
    elif rate >= 1:
        er_score = 0.5 + (rate - 1) * 0.15
    else:
        er_score = rate * 0.5

    # Consistency score (coefficient of variation)
    if len(engagements) >= 3:
        cv = statistics.stdev(engagements) / avg_eng if avg_eng > 0 else 1
        if cv <= 0.3:
            con_score = 1.0
        elif cv <= 0.5:
            con_score = 1.0 - (cv - 0.3) * 1.5
        elif cv <= 1.0:
            con_score = 0.7 - (cv - 0.5) * 0.6
        else:
            con_score = max(0.2, 0.4 - (cv - 1.0) * 0.2)
    else:
        con_score = 0.5

    # Sponsored delta
    sponsored = [p for p in posts if is_sponsored(p)]
    organic = [p for p in posts if not is_sponsored(p)]
    if sponsored and organic:
        ratio = statistics.mean([get_engagement(p) for p in sponsored]) / max(
            statistics.mean([get_engagement(p) for p in organic]), 1
        )
        spon_score = min(ratio, 1.0)
    else:
        spon_score = 0.5

    roi = 0.45 * er_score + 0.30 * con_score + 0.25 * spon_score
    verdict = "Partner" if roi >= 0.60 else "Caution" if roi >= 0.35 else "Avoid"

    return {
        "roi_score": round(roi, 2),
        "verdict": verdict,
        "signals": {
            "engagement_rate_pct": round(rate, 2),
            "er_score": round(er_score, 2),
            "consistency_score": round(con_score, 2),
            "sponsored_delta_score": round(spon_score, 2),
            "sponsored_post_count": len(sponsored),
            "organic_post_count": len(organic),
        },
    }


# ─── Trust Score ──────────────────────────────────────────────────────────────

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

def calc_trust(profile: dict, posts: list, user_about: dict) -> dict:
    follower_count = int(profile.get("follower_count") or 0)
    following_count = int(profile.get("following_count") or 0)

    # Account age
    date_str = user_about.get("date", "")
    parts = str(date_str).strip().split()
    age_score = 0.5
    if len(parts) == 2:
        month = MONTH_MAP.get(parts[0].lower())
        try:
            year = int(parts[1])
            if month:
                created = datetime(year, month, 1, tzinfo=UTC)
                age_years = (datetime.now(UTC) - created).days / 365.25
                if age_years >= 5:
                    age_score = 1.0
                elif age_years >= 2:
                    age_score = 0.5 + (age_years - 2) * (0.5 / 3)
                elif age_years >= 1:
                    age_score = 0.25 + (age_years - 1) * 0.25
                else:
                    age_score = age_years * 0.25
        except ValueError:
            pass

    # Follower ratio (log scale)
    if following_count > 0:
        ratio = follower_count / following_count
        log_ratio = math.log10(max(ratio, 0.1))
        ratio_score = min(1.0, max(0.0, log_ratio / 3.0))
    else:
        ratio_score = 0.5

    # Posting cadence
    timestamps = sorted(
        [p["taken_at_ts"] for p in posts if p.get("taken_at_ts")], reverse=True
    )
    if len(timestamps) >= 5:
        gaps = [(timestamps[i] - timestamps[i + 1]) / 86400 for i in range(len(timestamps) - 1)]
        avg_gap = statistics.mean(gaps)
        cv = statistics.stdev(gaps) / avg_gap if avg_gap > 0 else 1
        if cv <= 0.5:
            cadence_score = 0.7 + (0.5 - cv) * 0.6
        elif cv <= 1.0:
            cadence_score = 0.4 + (1.0 - cv) * 0.6
        else:
            cadence_score = max(0.1, 0.4 - (cv - 1.0) * 0.15)
    else:
        cadence_score = 0.5

    # Identity stability
    former = user_about.get("former_usernames", "")
    if not former:
        id_score = 1.0
    else:
        count = len(former.split(",")) if isinstance(former, str) else len(former)
        id_score = 1.0 if count == 0 else 0.7 if count <= 2 else 0.4

    trust = 0.25 * age_score + 0.25 * ratio_score + 0.25 * cadence_score + 0.25 * id_score
    verdict = "High Trust" if trust >= 0.70 else "Moderate Trust" if trust >= 0.45 else "Low Trust"

    return {
        "trust_score": round(trust, 2),
        "verdict": verdict,
        "signals": {
            "account_age_score": round(age_score, 2),
            "follower_ratio_score": round(ratio_score, 2),
            "cadence_score": round(cadence_score, 2),
            "identity_stability_score": round(id_score, 2),
        },
    }


# ─── LLM Analysis ─────────────────────────────────────────────────────────────

def llm_profile_analysis(profile: dict, posts: list) -> dict:
    """Use Claude to classify niche, intent scores, audience from HikerAPI data."""

    caption_sample = []
    locations = []
    for p in posts[:15]:
        cap = p.get("caption") or ""
        if isinstance(cap, dict):
            cap = cap.get("text", "")
        if cap:
            caption_sample.append(cap[:300])
        loc = p.get("location")
        if isinstance(loc, dict):
            city = loc.get("name") or loc.get("city")
            if city:
                locations.append(city)

    system = (
        "You are an expert influencer marketing analyst specialising in the Australian market. "
        "Return ONLY valid JSON — no markdown fences, no explanation."
    )

    user = f"""Analyse this Instagram creator and return a JSON profile:

Profile:
- Username: @{profile.get("username")}
- Full name: {profile.get("full_name", "")}
- Bio: {profile.get("biography", "")}
- Followers: {profile.get("follower_count", 0):,}
- Following: {profile.get("following_count", 0):,}
- Posts: {profile.get("media_count", 0)}
- Verified: {profile.get("is_verified", False)}
- Business account: {profile.get("is_business", False)}
{f"- Post locations: {', '.join(set(locations))}" if locations else ""}

Recent captions:
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(caption_sample[:10]))}

Return this exact JSON schema (all fields required):
{{
  "niche": "single primary niche (fitness/food/fashion/beauty/lifestyle/parenting/travel/wellness/education/entertainment/sports/tech/business/other)",
  "sub_niche": ["specific tag 1", "specific tag 2", "specific tag 3"],
  "age_group": "18-24 or 25-34 or 35-44 or 45-54 or Unknown",
  "gender": "Male or Female or Unknown",
  "country": "Full country name. Infer from: AU/AUS mentions, Australian slang (arvo/servo/maccas), spelling (colour/favourite), AUD currency, known AU cities, brands (Coles/Woolworths/ANZ). Default to Australia if unclear.",
  "city": "City name if determinable from bio/locations, else empty string",
  "customer_story": "2-sentence description of who follows them and why",
  "is_ugc_creator": true or false,
  "intent_scores": {{
    "product_discovery": 0.0,
    "education": 0.0,
    "entertainment": 0.0,
    "lifestyle_aspiration": 0.0,
    "community": 0.0
  }},
  "value_system": ["value1", "value2", "value3"],
  "brand_fit": "1 sentence on what product categories suit this creator"
}}"""

    try:
        raw = claude(system, user, model="claude-haiku-4-5")
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(cleaned)
    except Exception as e:
        return {"error": str(e), "raw": raw if "raw" in dir() else ""}


def llm_comment_analysis(comments: list) -> dict:
    """Classify comments into genuine/question/buying_intent/bot using Claude."""
    if len(comments) < 5:
        return {"insufficient_data": True, "total": len(comments)}

    texts = [c["text"] for c in comments[:50]]

    system = (
        "You are an Instagram engagement quality analyst. "
        "Return ONLY valid JSON — no markdown, no explanation."
    )
    user = f"""Classify these {len(texts)} Instagram comments into 4 categories.
Count how many fall into each, then calculate percentages (must sum to 100).

Categories:
- genuine: Thoughtful, specific reactions ("Love how you styled this!", "This changed my routine")
- question: Asking about products, location, price, where to buy ("Where is that from?", "What shade?", "Link?")
- buying_intent: Direct purchase signals ("Need this!", "Just ordered", "Adding to cart", "How much?")
- bot: Generic/spam/single emoji ("🔥", "Nice!", "Beautiful 😍", "Check my page", repetitive emoji strings)

Note: question and buying_intent are separate — "where can I buy?" is buying_intent, "what is this?" is question.

Comments to classify:
{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(texts))}

Return JSON:
{{
  "genuine_percent": <integer 0-100>,
  "question_percent": <integer 0-100>,
  "buying_intent_percent": <integer 0-100>,
  "bot_percent": <integer 0-100>,
  "total_classified": {len(texts)}
}}"""

    try:
        raw = claude(system, user, model="claude-haiku-4-5")
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(cleaned)
        keys = ["genuine_percent", "question_percent", "buying_intent_percent", "bot_percent"]
        total = sum(data.get(k, 0) for k in keys)
        if total > 0 and total != 100:
            for k in keys:
                data[k] = round(data.get(k, 0) * 100 / total)
        return data
    except Exception as e:
        return {"error": str(e)}


# ─── Brand detection ──────────────────────────────────────────────────────────

def extract_brands(posts: list) -> list:
    brands = set()
    for post in posts:
        if not is_sponsored(post):
            continue
        for sponsor in post.get("sponsor_tags", []):
            if isinstance(sponsor, dict):
                name = sponsor.get("username") or sponsor.get("full_name")
                if name:
                    brands.add(name)
        caption = post.get("caption") or ""
        if isinstance(caption, dict):
            caption = caption.get("text", "")
        mentions = re.findall(r"@(\w+)", caption)
        skip = {"instagram", "instagr", "link", "shop", "bio"}
        brands.update(m for m in mentions if m.lower() not in skip)
    return sorted(brands)[:10]


# ─── Main audit ───────────────────────────────────────────────────────────────

def run_audit(username: str, tier: int = 1) -> dict:
    cfg = TIERS[tier]
    print(f"\n🔍 Auditing @{username} [{cfg['label']} / {cfg['confidence']} Confidence]...\n")

    step = 1
    total_steps = 4 + (1 if cfg["fetch_account_history"] else 0) + (1 if cfg["comment_posts"] > 0 else 0)

    print(f"  [{step}/{total_steps}] Fetching profile...")
    profile = fetch_profile(username)
    user_id = str(profile.get("pk") or profile.get("id", ""))
    step += 1

    print(f"  [{step}/{total_steps}] Fetching up to {cfg['max_posts']} posts...")
    posts = fetch_posts(user_id, max_posts=cfg["max_posts"])
    print(f"        → {len(posts)} posts fetched")
    step += 1

    user_about = {}
    if cfg["fetch_account_history"]:
        print(f"  [{step}/{total_steps}] Fetching account history...")
        user_about = fetch_user_about(user_id)
        step += 1

    print(f"  [{step}/{total_steps}] Running LLM profile analysis...")
    analysis = llm_profile_analysis(profile, posts)
    step += 1

    # Comment sampling
    all_comments = []
    comment_posts_sampled = 0
    if cfg["comment_posts"] > 0:
        print(f"  [{step}/{total_steps}] Sampling comments ({cfg['comment_posts']} posts × {cfg['comments_per_post']} comments)...")
        for post in posts[:cfg["comment_posts"] * 2]:  # try more posts in case some have no comments
            if comment_posts_sampled >= cfg["comment_posts"]:
                break
            mid = str(post.get("pk") or post.get("id", ""))
            if mid:
                comments = fetch_comments(mid, limit=cfg["comments_per_post"])
                if comments:
                    all_comments.extend(comments)
                    comment_posts_sampled += 1
        print(f"        → {len(all_comments)} comments from {comment_posts_sampled} posts")
        step += 1

    print(f"  [{step}/{total_steps}] Calculating ROI + Trust scores...")
    follower_count = int(profile.get("follower_count") or 0)
    roi = calc_roi(posts, follower_count)
    trust = calc_trust(profile, posts, user_about)
    brands = extract_brands(posts)

    comment_quality = llm_comment_analysis(all_comments) if all_comments else {"not_sampled": True}

    return {
        "handle": username,
        "tier": tier,
        "tier_label": cfg["label"],
        "confidence": cfg["confidence"],
        "sample": {
            "posts_fetched": len(posts),
            "comment_posts_sampled": comment_posts_sampled,
            "comments_sampled": len(all_comments),
        },
        "profile": {
            "full_name": profile.get("full_name"),
            "followers": follower_count,
            "following": int(profile.get("following_count") or 0),
            "posts": int(profile.get("media_count") or 0),
            "verified": profile.get("is_verified", False),
            "bio": profile.get("biography", ""),
        },
        "analysis": analysis,
        "roi": roi,
        "trust": trust,
        "comment_quality": comment_quality,
        "brands_detected": brands,
    }


def print_report(audit: dict) -> None:
    p = audit["profile"]
    a = audit["analysis"]
    roi = audit["roi"]
    trust = audit["trust"]
    cq = audit["comment_quality"]
    s = audit["sample"]
    tier = audit["tier"]
    cfg = TIERS[tier]

    print(f"\n{'═'*60}")
    print(f"  🌸 CREATOR AUDIT: @{audit['handle']}")
    print(f"  {audit['tier_label'].upper()} | {audit['confidence'].upper()} CONFIDENCE")
    print(f"{'═'*60}")
    print(f"  {p['full_name']} | {p['followers']:,} followers | {'✓ Verified' if p['verified'] else 'Unverified'}")
    print(f"  Bio: {p['bio'][:80]}...")

    # Sample sizes — always visible
    print(f"\n📐 SAMPLE SIZES")
    print(f"  Posts analysed:     {s['posts_fetched']} of {p['posts']} total")
    if s['comment_posts_sampled'] > 0:
        print(f"  Comments sampled:   {s['comments_sampled']} across {s['comment_posts_sampled']} posts")
    else:
        print(f"  Comments sampled:   0 — not sampled at Tier {tier}")
    print(f"  Account history:    {'Yes' if cfg['fetch_account_history'] else 'No — not fetched at Tier ' + str(tier)}")

    print(f"\n📊 PROFILE INTELLIGENCE")
    print(f"  Niche: {a.get('niche', '?')} → {', '.join(a.get('sub_niche', []))}")
    print(f"  Demographics: {a.get('gender', '?')} | {a.get('age_group', '?')} | {a.get('country', '?')}")
    print(f"  Audience: {a.get('customer_story', '?')}")
    if a.get("brand_fit"):
        print(f"  Brand fit: {a['brand_fit']}")

    print(f"\n📈 INTENT SCORES  (based on {s['posts_fetched']} posts)")
    for k, v in (a.get("intent_scores") or {}).items():
        bar = "█" * int(v * 10) + "░" * (10 - int(v * 10))
        print(f"  {k:<25} {bar} {v:.2f}")

    print(f"\n💰 ROI SCORE: {roi['roi_score']} → {roi['verdict']}  [{audit['confidence']} confidence]")
    rs = roi["signals"]
    print(f"  Posts used:      {s['posts_fetched']}")
    print(f"  Engagement rate: {rs.get('engagement_rate_pct', 0):.2f}%  (score: {rs.get('er_score', 0):.2f})")
    print(f"  Consistency:     score {rs.get('consistency_score', 0):.2f}  (more posts = more reliable)")
    spon_note = "" if rs.get('sponsored_post_count', 0) > 0 else "  ← no sponsored posts detected"
    print(f"  Sponsored delta: score {rs.get('sponsored_delta_score', 0):.2f}{spon_note}")
    print(f"  Sponsored posts: {rs.get('sponsored_post_count', 0)} | Organic: {rs.get('organic_post_count', 0)}")

    print(f"\n🔒 TRUST SCORE: {trust['trust_score']} → {trust['verdict']}  [{audit['confidence']} confidence]")
    ts = trust["signals"]
    print(f"  Account age:         {ts.get('account_age_score', 0):.2f}  {'← not fetched at Tier 1' if not cfg['fetch_account_history'] else ''}")
    print(f"  Follower ratio:      {ts.get('follower_ratio_score', 0):.2f}")
    print(f"  Posting cadence:     {ts.get('cadence_score', 0):.2f}  (based on {s['posts_fetched']} posts)")
    print(f"  Identity stability:  {ts.get('identity_stability_score', 0):.2f}  {'← not fetched at Tier 1' if not cfg['fetch_account_history'] else ''}")

    print(f"\n💬 COMMENT QUALITY")
    if cq.get("not_sampled"):
        print(f"  Not sampled at Tier {tier} — run --tier 2 to see bot %, buying intent, and genuine engagement rates.")
    elif cq.get("insufficient_data"):
        print(f"  Insufficient comments ({cq.get('total', 0)} found — need 5+ to classify)")
    elif cq.get("error"):
        print(f"  Error: {cq['error']}")
    else:
        total_c = cq.get("total_classified", s["comments_sampled"])
        print(f"  Based on {total_c} comments across {s['comment_posts_sampled']} posts:")
        print(f"  Genuine:       {cq.get('genuine_percent', 0):.0f}%")
        print(f"  Questions:     {cq.get('question_percent', 0):.0f}%")
        print(f"  Buying intent: {cq.get('buying_intent_percent', 0):.0f}%  ← 'where's your hat from?'")
        print(f"  Bot/spam:      {cq.get('bot_percent', 0):.0f}%")
        if cq.get("bot_percent", 0) >= 25 and tier < 3:
            print(f"  ⚠️  Bot % is elevated — run --tier 3 to confirm with a larger sample.")

    if audit["brands_detected"]:
        print(f"\n🏷️  BRANDS DETECTED: {', '.join(audit['brands_detected'])}")

    # Confidence caveat — always last
    print(f"\n{'─'*60}")
    caveat = cfg["caveat"].format(
        posts=s["posts_fetched"],
        comments=s["comments_sampled"],
        comment_posts=s["comment_posts_sampled"],
    )
    print(f"  {caveat}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/creator_audit.py <instagram_handle> [--tier 1|2|3]")
        sys.exit(1)

    handle = sys.argv[1].lstrip("@")

    tier = 1
    if "--tier" in sys.argv:
        idx = sys.argv.index("--tier")
        if idx + 1 < len(sys.argv):
            try:
                tier = int(sys.argv[idx + 1])
                if tier not in TIERS:
                    raise ValueError
            except ValueError:
                print("Error: --tier must be 1, 2, or 3")
                sys.exit(1)

    audit = run_audit(handle, tier=tier)
    print_report(audit)

    out_path = f"/tmp/audit_{handle}_tier{tier}.json"
    with open(out_path, "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"Full JSON saved to: {out_path}")
