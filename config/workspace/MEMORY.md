# MEMORY.md — Blossom's Long-Term Memory

## About Me
- Name: Blossom 🌸
- Role: Proactive social media assistant & influencer discovery strategist
- Trainer: Oreo (AI expert, building platform for enterprise marketing teams)

---

## 🗄️ Qdrant Creator Database — Critical Facts

**Connection env vars:** `$QDRANT_URL`, `$QDRANT_API_KEY`, `$QDRANT_COLLECTION_NAME` (= `instagram_influencers`)

**Scale:** 56,579 Australian Instagram creators | Mega (1M+): ~170 | Micro-Macro (10K-100K): ~14,936

### ⚠️ EMBEDDING MODEL: `text-embedding-3-small` (OpenAI)
- **DO NOT use `text-embedding-ada-002`** — scores come out ~0.04 (garbage results)
- **USE `text-embedding-3-small`** — scores come out ~0.63+ (correct, relevant results)
- Both are 1536-dim but the DB was indexed with `text-embedding-3-small`
- Confirmed via score comparison test on 2026-02-19

### Rich payload fields per creator
`username`, `full_name`, `user_id`, `biography`, `follower_count`, `following_count`, `media_count`,
`is_private`, `is_verified`, `is_business`, `city_name`, `country`, `niche`, `sub_niche[]`,
`visual_aesthetic`, `content_details`, `customer_story`, `age_group`, `gender`, `occupation`,
`inferred_value_system[]`, `text_representation`, `analysis_updated_at`

### Indexed/filterable fields
- `follower_count` (int range)
- `is_business` (bool)
- `username` (keyword)
- `age_group` (keyword: "18-24", "25-34", "35-44", etc.)

---

## 🔀 Discovery Platform — Three-Source Strategy

| Source | Role |
|---|---|
| **Qdrant** (our DB) | Primary: semantic search + payload filters. Best for rich profiling. |
| **Hiker API** (`creator_search`/`creator_get`) | Cross-reference, fill gaps |
| **`creator_profile`** | Live Instagram verification (current followers, bio, active?) |
| **`web_search`** | Brand safety, press, controversies, trends |

### Recommended Flow
1. Embed query with `text-embedding-3-small`
2. Qdrant semantic search + payload filters (follower range, gender, age_group, etc.)
3. Cross-check interesting results via Hiker (`creator_search` / `creator_get`)
4. Verify live via `creator_profile` before pitching
5. `web_search` for brand safety on shortlisted creators

---

## 🧠 Audience Intelligence Pipeline — ~/.openclaw/audience_intelligence/

Full codebase lives locally. Full reference in memory/audience-intelligence-pipeline.md.

### Key files
- `analyzer.py` — AudienceIntelligenceAnalyzer: 3 HikerAPI calls + Gemini 2.5 Flash multimodal
- `comment_analyzer.py` — CommentAnalyzer: `media_comments_chunk_v1` + Gemini → genuine/question/buying_intent/bot %
- `roi_calculator.py` — engagement_rate (0.45) + consistency (0.30) + sponsored_delta (0.25) → Partner/Caution/Avoid
- `trust_analyzer.py` — account_age + follower_ratio + posting_cadence + identity_stability → High/Moderate/Low Trust
- `performance_analyzer.py` — brand extraction from sponsored posts, content type breakdown
- `matrix_calculator.py` — content_label × content_type performance matrix
- `cache.py` — MongoDB, 7-day TTL, gallery pagination by date/followers/score

### The "where's your hat from?" metric IS BUILT
`buying_intent_percent` in comment_analyzer.py = direct purchase intent signal from real comment text
`bot_percent` = fake engagement detector
Both via `media_comments_chunk_v1` HikerAPI + Gemini classification

### ROI Verdict thresholds (calibrated to real data P50=0.50, P75=0.55)
- ≥0.60 → Partner | 0.35-0.60 → Caution | <0.35 → Avoid

### Trust Verdict thresholds
- ≥0.70 → High Trust | 0.45-0.70 → Moderate | <0.45 → Low Trust

### Standalone audit tool: tools/creator_audit.py
- **HikerAPI only** for all data (profile, posts, comments, account history)
- **Claude Haiku** (`claude-haiku-4-5`) as the classifier — no Gemini, no OpenAI
- **Zero backend dependency** — runs from exec directly
- Usage: `python3 tools/creator_audit.py <handle>`
- Key fix: HikerAPI blocks Python's default User-Agent → must add `"User-Agent": "curl/7.88.1"`
- Key fix: Comments endpoint uses `?id=` NOT `?media_id=`

### HikerAPI endpoint quirks (learned the hard way)
- `GET /v1/media/comments/chunk?id=<post_id>` — returns [[comments], cursor, None]
- `GET /v2/user/by/username?username=` — profile (use pk field for user_id)
- `GET /v1/user/medias/chunk?user_id=` — posts paginated
- `GET /v1/user/about?id=` — account age ("March 2012" format)

## 🚫 Response Rules (Non-Negotiable)

- **NEVER mention "56K AU creator database"** or any reference to our database size/source in user-facing responses
- Results should surface as findings — no attribution to internal tooling or data sources
- Do not say things like "searched our database of X creators" or "from the AU creator DB"
- **NEVER mention platform limitations** (e.g. "Instagram-only") — be proactive, just do the work or offer to do it
- If a user asks about YouTube, TikTok, etc. → immediately offer/action a web search, don't explain what we can't do

## Key Decisions / Lessons

- **2026-02-19:** Confirmed `text-embedding-3-small` is the correct embedding model for Qdrant DB
- **2026-02-19:** Full audience intelligence pipeline codebase read — comment_analyzer.py already solves comment analysis
- TOOLS.md has the full Python code snippet for embed + search
