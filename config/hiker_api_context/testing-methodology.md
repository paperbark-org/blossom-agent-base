# Testing Methodology

How this research was conducted, which accounts were tested, and how confidence levels were assigned.

---

## Research Approach

This documentation was produced through **hands-on endpoint testing**, not from official documentation (HikerAPI has no public docs beyond an OpenAPI spec at `/openapi.json`).

### Discovery Process

1. **Manual endpoint testing** — Tested 28+ endpoint URL patterns with various parameter combinations
2. **OpenAPI spec discovery** — Found `/openapi.json` (177KB) revealing all 143 endpoints with summaries, parameter names, and deprecation warnings
3. **Parameter trial-and-error** — Discovered parameter naming inconsistencies (e.g., media endpoints use `id`, not `media_id`) through 422 error messages
4. **Cross-account comparison** — Tested identical endpoints across different account types to identify population patterns
5. **Cross-format comparison** — Tested identical endpoints across different post types (carousel, reel, photo) to identify format-specific fields

---

## Test Accounts

### Primary Test Accounts (v2 User Profiles Captured)

| Account | Followers | `is_business` | `account_type` | Category | Why Selected |
|---|---|---|---|---|---|
| emmachamberlain | 14.5M | `false` | 3 (creator) | Lifestyle/creator | Large creator, diverse content types |
| garyvee | 11.2M | `false` | 3 (creator) | Business/motivational | High-volume poster, business-adjacent |
| glossier | 3.2M | `true` | 2 (business) | Beauty/DTC brand | **Business account with Instagram Shop** |
| zoella | — | `false` | 3 (creator) | Lifestyle/beauty | UK-based creator, long-established |
| kayla_itsines | — | `false` | 3 (creator) | Fitness/wellness | Fitness ambassador, commercial partnerships |

### Additional Test Accounts

| Account | Purpose |
|---|---|
| jaime.chapman | `/v1/user/about` testing (Australian, verified, account creation date) |
| sephora | Commerce field testing (retail brand with Instagram Shop) |

### Account Type Coverage

| Account Type | Value | Accounts Tested |
|---|---|---|
| Personal | 1 | (none — rare for our use case) |
| Business | 2 | glossier, sephora |
| Creator | 3 | emmachamberlain, garyvee, zoella, kayla_itsines |

---

## Post Types Tested

### Media Format Matrix

| Format | `media_type` | `product_type` | Test Account | Key Finding |
|---|---|---|---|---|
| Photo | 1 | `"feed"` | emmachamberlain | No `play_count`, no `reshare_count` |
| Video/Reel | 2 | `"clips"` | kayla_itsines, emmachamberlain | Has `play_count`, `reshare_count` (v2 only) |
| Carousel | 8 | `"feed"` | kayla_itsines | `carousel_media_count`, no `reshare_count` |

### Fields Tested Across Formats

| Field | Photo | Reel | Carousel | Notes |
|---|---|---|---|---|
| `like_count` | Present | Present | Present | Universal |
| `comment_count` | Present | Present | Present | Universal |
| `play_count` | Absent | **Present** | Absent | Reel-exclusive |
| `reshare_count` | Absent | **Present** (v2) | Absent | Reel-exclusive, v2 only |
| `media_repost_count` | Present (v2) | Present (v2) | Present (v2) | Universal in v2 |
| `is_paid_partnership` | Present | Present | Present | Universal |
| `coauthor_producers` | Present | Present | Present | Universal |
| `carousel_media_count` | Absent | Absent | **Present** | Carousel-exclusive |
| `commerce_integrity_review_decision` | Inconsistent | Inconsistent | Inconsistent | Varies by account |

---

## Endpoint Testing Results

### Endpoints Tested Directly (with HTTP status and response size)

| Endpoint | Status | Response Size | Notes |
|---|---|---|---|
| `/v1/user/by/username` | 200 | 1.4KB | v1 user (30 fields) |
| `/v2/user/by/id` | 200 | 14.3KB | v2 user (223 fields) |
| `/v1/user/by/id` | 200 | 1.4KB | v1 user |
| `/v2/user/by/username` | 200 | 14.3KB | v2 user |
| `/gql/user/medias` | 200 | varies | User media feed |
| `/v1/media/comments` | 200 | 14.3KB | v1 comments (deprecated) |
| `/v2/media/comments` | 200 | 31.9KB | v2 comments (32 fields/comment) |
| `/v1/media/comments/chunk` | 200 | 14KB | v1 chunked comments |
| `/v1/media/likers` | 200 | 718KB | v1 media likers |
| `/v2/media/likers` | 200 | 805KB | v2 media likers |
| `/v1/user/followers/chunk` | 200 | 35.6KB | Follower page |
| `/v1/user/following/chunk` | 200 | 17.9KB | Following page |
| `/v2/user/suggested/profiles` | 200 | 45.8KB | Similar accounts |
| `/v1/search/users` | 200 | 7.4KB | User search |
| `/v1/search/hashtags` | 200 | 6.5KB | Hashtag search |
| `/v1/user/clips` | 200 | 170KB | v1 reels (deprecated) |
| `/v2/user/clips` | 200 | 218KB | v2 reels |
| `/v1/media/insight` | 200 | 1.2KB | **All commercial fields null** |
| `/v2/media/info/by/code` | 200 | 39.6KB | Richest media detail |
| `/v1/user/about` | 200 | 109B | Country, creation date |
| `/v2/media/comments/replies` | 200 | 1.8KB | Threaded replies |
| `/gql/user/reposts` | 200 | 501KB | Reposted content |
| `/v2/user/tag/medias` | 200 | 1.3MB | Tagged media (large) |
| `/sys/balance` | 200 | 64B | Account balance |
| `/a2/user` | 200 | 148KB | Full GraphQL user |
| `/v2/userstream/by/username` | 200 | 17.8KB | User + recent media |
| `/v2/user/explore/businesses/by/id` | 200 | 96KB | Business recommendations |
| `/gql/media/usertags` | 200 | 4KB | Batch usertag lookup |
| `/v2/media/comment/offensive` | 200 | 90B | Toxicity check |
| `/v1/user/web_profile_info` | 200 | 4.2KB | Web profile (62 fields) |
| `/v1/media/user` | 200 | 715B | Media owner info |
| `/v1/user/guides` | 200 | varies | Creator guides (deprecated) |
| `/openapi.json` | 200 | 177KB | Full API specification |

### Endpoints That Failed

| Endpoint | Status | Reason |
|---|---|---|
| `/v2/user/medias/chunk` | 404 | Doesn't exist (use `/gql/user/medias`) |
| `/v2/user/followers/chunk` | 404 | Doesn't exist (use `/v2/user/followers`) |
| `/v2/user/following/chunk` | 404 | Doesn't exist (use `/v2/user/following`) |
| `/v2/search/users` | 404 | Doesn't exist (use `/v2/fbsearch/accounts`) |
| `/v1/hashtag/medias/chunk` | 404 | Doesn't exist |
| `/v1/user/tagged/medias` | 404 | Wrong path (use `/v1/user/tag/medias`) |
| `/v1/user/reels` | 404 | Doesn't exist (use `/v1/user/clips`) |
| `/v2/user/reels` | 404 | Doesn't exist (use `/v2/user/clips`) |
| `/v1/media/by/id` | 404 | Different behaviour than expected |
| `/v2/media/by/id` | 404 | Deprecated (use `/v2/media/info/by/id`) |
| `/v2/media/comments/chunk` | 404 | Doesn't exist (use `/v2/media/comments`) |
| `/gql/comments/chunk` | 422 | Different param names needed (`media_id`, `sort_order`, `end_cursor`) |

---

## Confidence Level Methodology

Confidence ratings were assigned based on:

### High Confidence
- Data comes directly from Instagram's database (not inferred)
- Field consistently populated across all tested accounts
- Field meaning is unambiguous
- Full population data (not sampled)

### Medium-High Confidence
- Directly observed but sample-size dependent
- OR directly observed but context matters (e.g., `is_paid_partnership` — true when populated, but false negatives exist)

### Medium Confidence
- AI-inferred from rich signal (multimodal content analysis)
- OR directly observed but with known gaps in population
- OR derived metric with sufficient data points

### Low-Medium Confidence
- Small sample (comments: 15 per page)
- Vocal minority bias (comment authors ≠ audience)
- AI classification of informal text
- Multiple inference steps from raw data

### Low Confidence
- Speculative extrapolation from limited data
- Ephemeral data (stories)
- Highly viewer-specific data (mutual followers)

### Unusable
- Schema exists but data never populates (media insight null fields)
- Deprecated with no replacement

---

## Research Date

- **Conducted:** January 2026
- **API Version:** HikerAPI REST v1.7.6
- **Account Balance at Test Time:** 598,130 requests (~$358.93)
- **Estimated Requests Used:** ~200-300 for full research

---

## Reproducibility

All raw API responses were saved to scratchpad during research. To reproduce any finding:

1. Use the OpenAPI spec (`/openapi.json`) as the authoritative endpoint reference
2. Ensure `access_key` is valid and account has sufficient balance
3. Note parameter naming: `user_id` for user endpoints, `id` for media/comment endpoints, `media_id` for gql endpoints
4. v2 endpoints may add or deprecate fields over time — re-test periodically
