# Endpoint Priority Matrix

Endpoints ranked by value to Blossom's mission: **"Verification Layer of Creator Investments"**

## Tier 1 — Must Use (Core Investment Signals)

These endpoints provide the data backbone for creator verification.

| Endpoint | Investment Value | Key Fields | Confidence |
|---|---|---|---|
| `/v2/user/by/id` | Creator profile depth — 223 fields including commerce, partnership capability, transparency | `is_paid_partnership`, `merchant_checkout_style`, `show_shoppable_feed`, `creator_shopping_info`, `fan_club_info`, `is_eligible_for_meta_verified_*`, `account_type`, `bio_links` | **High** |
| `/gql/user/medias` | Post history — content mix, posting cadence, engagement patterns. **Richest media endpoint** — `stream_rows[2+]` contain ~160+ fields per post including `save_count` (always null), `reshare_count`, `fb_comment_count`, `fb_like_count`, `ig_play_count`, `has_reshares`, `creator_viewer_insights` | Full post objects with `like_count`, `comment_count`, `play_count`, `save_count` (null), `media_type`, `product_type`, `caption`, `is_paid_partnership`, `coauthor_producers`, `usertags` | **High** |
| `/v2/media/info/by/code` | Individual post deep-dive — richest media detail available | `media_or_ad` wrapper, `reshare_count` (reels), `media_repost_count`, `sponsor_tags`, `coauthor_producers`, `usertags`, `carousel_media` | **High** |
| `/v2/media/comments` | Comment quality analysis — intent signals, audience sentiment | 32 fields per comment including `text`, `comment_like_count`, `has_liked_comment`, `is_covered`, `share_enabled`, user info | **Medium** (15 per request) |
| `/v1/media/comments/chunk` | Alternative comment source (v1) — same 15-per-page limit | 8 fields per comment — leaner but sufficient for text analysis | **Medium** |

## Tier 2 — High Value (Enrichment Signals)

These endpoints add significant context to investment decisions.

| Endpoint | Investment Value | Key Fields | Confidence |
|---|---|---|---|
| `/v2/media/comments/replies` | Threaded conversation depth — reply quality indicates engaged community | Reply text, reply count, parent comment context | **Medium** |
| `/v2/user/clips` | Reels/short video performance — format-specific engagement | `play_count`, `reshare_count`, `media_repost_count` (reels-specific metrics) | **High** |
| `/gql/user/reposts` | Audience advocacy — what content the creator amplifies | Reposted media objects with full metadata | **High** |
| `/v2/user/tag/medias` | Brand collaboration history — who tags this creator | Tagged posts reveal past/current brand partnerships | **High** |
| `/v1/media/insight` | **THEORETICALLY** the most valuable — saves, shopping clicks | `save_count`, `shopping_outbound_click_count`, `shopping_product_click_count` | **UNUSABLE** (all null) |
| `/v1/user/about` | Account provenance — country, creation date, former usernames | `country`, `date` (account creation), `former_usernames` | **High** |
| `/v2/user/explore/businesses/by/id` | Category-adjacent brand accounts — competitive intelligence | Recommended businesses in creator's niche | **Medium** |
| `/v2/media/likers` | Liker demographics — who engages (limited to public profiles) | Full user objects for each liker | **Medium-High** |
| `/gql/media/usertags` | Batch usertag lookup — efficiency for multi-post analysis | Accepts up to 10 media IDs per request | **High** |

## Tier 3 — Supplementary (Context Signals)

Lower priority but useful for specific analyses.

| Endpoint | Investment Value | Key Fields | Confidence |
|---|---|---|---|
| `/v2/user/followers` | Follower sampling — audience quality assessment | Full user objects (but only samples, not full audience) | **Low-Medium** |
| `/v2/user/following` | Creator's network — brand affinities, peer relationships | Who the creator follows (brands, competitors, peers) | **Medium** |
| `/v2/user/suggested/profiles` | Instagram's own creator similarity graph | Similar accounts by Instagram's algorithm | **Medium** |
| `/v1/user/web_profile_info` | Alternative user profile (62 fields) — some unique data | Web-specific profile fields | **Medium** |
| `/a2/user` | GraphQL full user (148KB response) — most complete single endpoint | Every possible user field | **High** (but expensive/verbose) |
| `/v2/userstream/by/username` | Combined user + recent media in one call | Efficient for initial creator scan | **Medium** |
| `/v2/media/comment/offensive` | Toxicity screening for specific comment text | `is_offensive`, `text_language` | **Medium** |
| `/v1/user/highlights` | Highlight reels — curated content themes | Highlight covers and titles | **Low** |
| `/v2/user/stories` | Current stories (ephemeral) | Story media if currently active | **Low** (ephemeral) |
| `/v2/fbsearch/accounts` | Account search — discovery pipeline | Search results with basic profile info | **High** (for discovery) |
| `/v2/hashtag/medias/top` | Hashtag content — niche analysis | Top posts for a hashtag | **Medium** |
| `/v1/user/medias/pinned` | Pinned posts — creator's own content curation priorities | Posts the creator chose to pin | **Medium** |

## Tier 4 — Low Priority / Deprecated

| Endpoint | Status | Notes |
|---|---|---|
| `/v1/user/by/username` | Use `/v2/user/by/username` instead | v1 returns 30 fields vs v2's 223 |
| `/v1/media/by/code` | Use `/v2/media/info/by/code` instead | v2 has `media_or_ad` wrapper, richer data |
| `/v2/media/by/code` | **Deprecated** | Use `/v2/media/info/by/code` |
| `/v1/user/medias` | **Deprecated** | Use `/gql/user/medias` |
| `/v2/user/medias` | **Deprecated** | Use `/gql/user/medias` |
| `/v1/media/comments` | **Deprecated** | Use `/v1/media/comments/chunk` or `/v2/media/comments` |
| `/v1/user/followers` | **Deprecated** | Use `/v2/user/followers` |
| `/v1/user/following` | **Deprecated** | Use `/v2/user/following` |
| `/v1/search/users` | **Deprecated** | Use `/v2/fbsearch/accounts` |
| `/v1/user/videos` | **Deprecated** | Use `/v2/user/clips` |
| `/v2/search/accounts` | **Deprecated** | Use `/v2/fbsearch/accounts` |
| `/v2/search/places` | **Deprecated** | Use `/v3/fbsearch/places` |
| `/gql/user/related/profiles` | **Deprecated** | Use `/v2/user/suggested/profiles` |

## Cost-Optimised Call Sequence

For a standard creator evaluation, the recommended call sequence:

```
1. /v2/user/by/username          → Creator profile (1 request)
2. /gql/user/medias              → Latest posts, paginate for ~100 posts (~9 requests)
3. /v2/media/info/by/code        → Detailed media for key posts (~10-20 requests)
4. /v2/media/comments            → Comments per post, 15 per page (~50-100 requests)
5. /v1/user/about                → Account provenance (1 request)
6. /v2/user/tag/medias           → Brand collaboration history (1-5 requests)
7. /v2/user/clips                → Reel performance (1-5 requests)
8. /gql/user/reposts             → Repost behaviour (1 request)

Total: ~75-145 requests per creator evaluation
Cost: ~$1.10-$2.20 per creator at $15/1K requests
```
