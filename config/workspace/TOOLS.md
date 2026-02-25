# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Qdrant Database — Australian Creator DB

> ⚠️ **CRITICAL: This database contains ONLY Australian creators.**
> If a user asks about creators in the US, UK, Europe, Asia, or any non-Australian market — Qdrant has nothing for them. Use HikerAPI instead.
> For Australian searches, ALWAYS use Qdrant / Blossom Backend API first — they are fast (< 2s) and have 56K AU creators.

**Connection**
- URL: `$QDRANT_URL`
- API Key: `$QDRANT_API_KEY`
- Collection: `$QDRANT_COLLECTION_NAME` → `instagram_influencers`

**Scale**
- **56,579** Australian Instagram creators
- Mega (1M+): ~170 creators
- Macro/Micro (10K–100K): ~14,936 creators
- Vectors: 1536-dim, cosine similarity (OpenAI-style embeddings)

**Rich AI-enriched payload per creator**
| Field | Description |
|---|---|
| `username`, `full_name`, `user_id` | Identity |
| `biography`, `media_count` | Profile basics |
| `follower_count`, `following_count` | Reach |
| `is_verified`, `is_business`, `is_private` | Account flags |
| `country`, `city_name` | Location |
| `niche`, `sub_niche[]` | Topic categories |
| `visual_aesthetic` | AI description of visual style |
| `content_details` | AI analysis of recent posts |
| `customer_story` | AI-inferred target audience |
| `age_group`, `gender`, `occupation` | Creator demographics |
| `inferred_value_system[]` | Values driving their content |
| `text_representation` | Full text blob used for embedding |
| `analysis_updated_at` | When the AI analysis was last run |

**Indexed for fast filtering**
- `follower_count` (integer range)
- `is_business` (bool)
- `username` (keyword exact match)
- `age_group` (keyword)

**Embedding Model (CRITICAL)**
- **Model:** `text-embedding-3-small` (OpenAI) ← confirmed via score testing
- **Dims:** 1536 | **Distance:** Cosine
- `text-embedding-ada-002` gives scores ~0.04 (wrong) — `text-embedding-3-small` gives scores ~0.63 (correct)
- Always use `$OPENAI_API_KEY` to embed queries before searching

**How to query**
```python
import urllib.request, json, os

def embed(text):
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": "text-embedding-3-small", "input": text}).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read())["data"][0]["embedding"]

def qdrant_search(vector, limit=10, filters=None):
    payload = {"vector": vector, "limit": limit, "with_payload": True, "with_vector": False}
    if filters:
        payload["filter"] = filters
    req = urllib.request.Request(
        f"{os.environ['QDRANT_URL']}/collections/{os.environ['QDRANT_COLLECTION_NAME']}/points/search",
        data=json.dumps(payload).encode(),
        headers={"api-key": os.environ["QDRANT_API_KEY"], "Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read())["result"]

# Example: semantic + payload filter
vector = embed("fitness influencers in Sydney who post about healthy eating")
results = qdrant_search(vector, limit=10, filters={
    "must": [{"key": "follower_count", "range": {"gte": 5000, "lte": 100000}}]
})
```

**Filter fields available**
- `follower_count` → range: `{"gte": 10000, "lte": 500000}`
- `is_business` → match: `{"value": true}`
- `age_group` → match: `{"value": "25-34"}`
- `username` → match: `{"value": "somehandle"}`
- `city_name` → match: `{"value": "Sydney"}` (but see WARNING below)

### ⚠️ CITY DATA IS SPARSE — DO NOT filter on city_name alone!

**Problem:** Most creators (~70%) have empty or missing `city_name`. An enrichment pipeline fills this field using Gemini vision + post locations + captions, but it hasn't processed all 56K creators yet.

**What to do instead:**
1. **Include the city name in your semantic query text** — e.g. "beauty creators in Sydney" → the `text_representation` field already contains biography text, which often mentions "Sydney", "Bondi", etc.
2. **Only use `city_name` filter as an ADDITIONAL filter**, not the primary one. Always rely on semantic search first.
3. **Post-filter results** by checking the `biography`, `text_representation`, and `city_name` payload fields for location keywords.

**Enrichment fields added by the pipeline:**
- `city_name` — inferred Australian city (or "Unknown")
- `ethnicity` — inferred from profile picture + name
- `clothing_style` — one-sentence description of fashion aesthetic
- `engagement_rate` — calculated from recent posts (e.g. "3.2%")
- `post_thumbnails` — array of {url, width, height, code, like_count, comment_count, taken_at}
- `no_longer_found` — boolean, true if 404'd on HikerAPI (skip these!)

**Australian city values used in enrichment (exact strings):**
Sydney, Melbourne, Brisbane, Perth, Adelaide, Gold Coast, Newcastle, Canberra, Sunshine Coast, Central Coast, Wollongong, Geelong, Hobart, Townsville, Cairns, Darwin, Ballarat, Bendigo, Byron Bay, etc.

**Recommended search pattern for city-specific queries:**
```python
# Embed with city context in the query
vector = embed("beauty and skincare creators based in Sydney, Australia")
results = qdrant_search(vector, limit=20, filters={
    "must": [
        {"key": "follower_count", "range": {"gte": 10000, "lte": 50000}}
    ]
})
# Then post-filter: check each result's biography, city_name, text_representation for "Sydney"/"Bondi"/etc
```

---

## Discovery Platform Strategy

### Source 1: Qdrant — Primary for AU creators (fast, semantic)

**For all Australian creator searches, use Qdrant directly.** It's fast (< 2s), semantically rich, and has 56K AU profiles with AI-enriched fields including `engagement_rate`, `visual_aesthetic`, `niche`, `customer_story`, and more.

See the **Qdrant Database** section above for the full query pattern.

Fields returned per creator: `username`, `full_name`, `user_id`, `follower_count`, `niche`, `engagement_rate`, `visual_aesthetic`, `customer_story`, `age_group`, `gender`, `occupation`, `inferred_value_system`, `post_thumbnails` (sparse), `biography`, `city_name`

**After getting Qdrant results:**
- Assign a `blossomScore` (0–100) per creator based on fit against the user's brief
- Include 1–2 sentence `reasoning` per row
- Render a `:::table` block immediately

### Source 2: HikerAPI — AU Enrichment / Non-AU Discovery + Enrichment (SLOW)
- `creator_search` → keyword/niche discovery
- `creator_get` → full profile by internal Hiker ID (recent posts, CDN thumbnails, live stats)
- `creator_posts` → recent post grid with engagement data
- **Strength:** Live data Qdrant doesn't have — recent post thumbnails, CDN image links, real-time engagement, story views
- ⚠️ **WARNING: HikerAPI is slow (~5–15s per call, 45s+ for multi-step flows).** Always warn the user before making multiple calls.
- **For AU creators — enrichment only:** Use Qdrant for discovery. Use `creator_get` AFTER to fetch live post thumbnails and engagement for shortlisted/top candidates.
- **For non-AU creators — discovery + enrichment:** Use `creator_search` to find creators, then `creator_get` to enrich each with full profile data.
- **DO NOT** use `creator_search` for Australian creator discovery — Qdrant is faster and semantically richer.
- **DO** tell the user when pulling live data: "Fetching live post data — this'll take a moment."

### Source 3: creator_profile (Instagram Live) — Verification
- `creator_profile(username)` → real-time Instagram lookup
- **Use for:** Confirming a creator is still active, current follower count, before pitching

### Source 4: web_search — Context & Brand Safety
- **Use for:** Recent press, brand safety checks, campaign history, trend research, competitor analysis

### Discovery Flow (recommended)

**For Australian creators (the common case — fast path):**
1. **Qdrant semantic search** → embed query, search collection, apply follower filters
2. **Score each result** → assign `blossomScore` (0–100) based on brief fit, include `reasoning`
3. **Render `:::table` block** → show results immediately
4. **(Optional enrichment)** Call HikerAPI `creator_get` on top candidates to fetch live post thumbnails — tell the user you're doing this

**For non-Australian creators (HikerAPI — warn about latency):**
1. Tell the user: "Searching live Instagram data — this takes a moment..."
2. **HikerAPI `creator_search`** → discovery by keyword/niche
3. **HikerAPI `creator_get`** → enrich each result with full profile, posts, CDN images
4. **Score candidates** → assign `blossomScore` manually
5. **Render `:::table` block** → show results

**Never** run multiple sequential HikerAPI calls silently — always set user expectations upfront.
**Never** use Qdrant for non-Australian creators — they're not in the database.

---

Add whatever helps you do your job. This is your cheat sheet.
