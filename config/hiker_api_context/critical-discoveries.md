# Critical Discoveries

Findings from hands-on API testing that fundamentally affect what Blossom can and cannot build.

---

## 1. Save Count & Shopping Clicks are Inaccessible (CRITICAL)

**The field exists in MORE places than originally documented — but is ALWAYS null.**

### Where `save_count` appears in the API

| Endpoint | Field Present? | Value | Notes |
|---|---|---|---|
| `/v1/media/insight` | Yes | **Always `null`** | Dedicated insight endpoint |
| `/gql/user/medias` | Yes (on every media object in `stream_rows[2+]`) | **Always `None`** | Richest media endpoint — also has `can_viewer_save` and `has_viewer_saved` |
| `/v2/media/info/by/code` | `can_viewer_save` only | `true` (boolean permission, not count) | No `save_count` field |
| `/v1/media/by/code` | No | — | No save fields at all |
| `/a2/user` | No | — | No save fields in 148KB GraphQL response |

### `/v1/media/insight` response

```json
{
  "id": "17852764359500678",
  "instagram_media_type": "VIDEO",
  "comment_count": 65,
  "like_count": 8849,
  "save_count": null,
  "shopping_outbound_click_count": null,
  "shopping_product_click_count": null,
  "shopping_product_insights": {
    "shopping_product_by_tag_click_count": [],
    "shopping_product_by_tag_outbound_click_count": []
  }
}
```

### `/gql/user/medias` save fields (per media object)

```json
{
  "save_count": null,
  "can_viewer_save": true,
  "has_viewer_saved": null
}
```

### Exhaustive cross-account verification

| Account | Type | Endpoint | Posts Tested | `save_count` Result |
|---|---|---|---|---|
| emmachamberlain | Creator (14.5M) | `/gql/user/medias` | 12 | ALL `None` |
| glossier | Business (Instagram Shop) | `/gql/user/medias` | 12 | ALL `None` |
| garyvee | Creator (11.2M) | `/gql/user/medias` | 12 | ALL `None` |
| jaime.chapman | Creator | `/v1/media/insight` | 1 | `null` |
| emmachamberlain | Creator | `/v1/media/insight` | 1 | `null` |
| glossier | Business | `/v1/media/insight` | 1 | `null` |

**38 total posts tested across 3 account types. Zero non-null save counts.**

### Verdict

`save_count` exists in the API schema on at least 2 endpoints (`/v1/media/insight` and `/gql/user/medias`) but is **always null/None** via third-party API access. This requires **account owner authentication** (Instagram Professional Dashboard / Creator Studio). No third-party tool — HikerAPI, CreatorIQ, HypeAuditor, or any other — has access to save counts.

The companion fields `can_viewer_save` (boolean permission — always `true`) and `has_viewer_saved` (viewer-specific — always `None` without auth) provide no useful data.

**Impact on Blossom:**
- **Save count** would be the strongest purchase intent signal — a user saving a product post is effectively bookmarking to buy. We cannot access this.
- **Shopping clicks** (`shopping_outbound_click_count`, `shopping_product_click_count`) would be direct conversion indicators. Also always null.
- This is a platform-level restriction, not an account-type issue or an API limitation.

**Mitigation:** Build the Post Performance Matrix on available high-confidence metrics (likes, comments count, views, plays, reshares) and layer comment-derived intent signals on top. See the Audience Intent Analysis evaluation for the full approach.

---

## 2. `is_paid_partnership` is Unreliable

**Field:** `is_paid_partnership` (boolean on media objects)

**Problem:** This field is `false` on many posts that are clearly sponsored content. It only reflects whether the creator used Instagram's native "Paid Partnership" label feature.

**Why it's unreliable:**
- Many creators don't use the native label (especially for gifted/affiliate content)
- Some brands prefer creators NOT use the paid partnership label
- Micro/mid-tier creators often skip it entirely
- The field reflects self-reporting, not actual sponsorship status

**Better alternatives for sponsorship detection:**

| Signal | Field | Reliability |
|---|---|---|
| Coauthor producers | `coauthor_producers` array on media | **High** — indicates official brand collaboration |
| Sponsor tags | `sponsor_tags` on media | **High** — explicitly tagged brands |
| Caption analysis | `caption.text` | **Medium** — detect #ad, #sponsored, #gifted, #partner, brand @mentions |
| User tags in media | `usertags` on media | **Medium** — brands tagged in photos |
| Bio brand mentions | `biography` on user profile | **Low** — "ambassador for @brand" etc |

**Recommendation:** Use a composite signal: `is_paid_partnership` OR `coauthor_producers` is non-empty OR `sponsor_tags` is non-empty OR caption contains sponsorship keywords. This catches significantly more sponsored content than `is_paid_partnership` alone.

---

## 3. v2 Returns 7x More Data Than v1

**User endpoint comparison:**
- v1 (`/v1/user/by/id`): **30 fields**, 1.4KB response
- v2 (`/v2/user/by/id`): **223 fields**, 14.3KB response

**Of the 223 v2 fields:**
- 27 shared with v1
- 196 v2-only fields
- 3 v1-only fields

The v2-only fields include categories critical for investment verification:
- **Commerce/Shopping:** `merchant_checkout_style`, `show_shoppable_feed`, `seller_shoppable_feed_type`, `creator_shopping_info`, `is_eligible_for_creator_product_links`
- **Partnership:** `can_use_branded_content_discovery_as_brand`, `can_use_branded_content_discovery_as_creator`, `can_use_paid_partnership_messaging_as_creator`, `can_use_affiliate_partnership_messaging_as_creator`
- **Verification/Trust:** `is_eligible_for_meta_verified_label`, `meta_verified_benefits_info`, `show_account_transparency_details`, `transparency_product_enabled`
- **Fan/Subscription:** `fan_club_info`, `has_fan_club_subscriptions`

See [v1-vs-v2-comparison.md](./v1-vs-v2-comparison.md) for the full field-level breakdown.

---

## 4. Commerce Fields Are Account-Type Dependent

**Finding:** Commerce-related fields populate differently based on account type:

| Account | `is_business` | `merchant_checkout_style` | `show_shoppable_feed` | `seller_shoppable_feed_type` |
|---|---|---|---|---|
| emmachamberlain (creator, 14.5M) | `false` | `none` | `false` | `none` |
| garyvee (creator, 11.2M) | `false` | `none` | `false` | (not present) |
| glossier (brand, 3.2M) | `true` | **`multi_item_checkout`** | **`true`** | **`mini_shop_wave_2`** |
| kayla_itsines (creator) | `false` | `none` | `false` | `none` |

**Implication:** These fields tell us whether a brand has Instagram Shopping set up, but they don't tell us whether a creator's audience is shopping-oriented. Creator accounts universally show `none`/`false` for commerce fields regardless of how commercial their content is.

**For Blossom:** Commerce fields are useful for **brand verification** (does this brand actually sell on Instagram?) but NOT for **creator investment verification** (is this creator's audience likely to convert?).

---

## 5. `reshare_count` is Valuable but Reels-Only

**Field:** `reshare_count` (on media objects, v2 only)

**What it measures:** How many times users shared this post via DM or to their stories. This is a direct **audience advocacy** signal — people sharing content indicates they find it valuable enough to pass on.

**Example from testing:**
- Reel by kayla_itsines: `reshare_count: 659`, `like_count: 8,849` → 7.4% reshare-to-like ratio
- Non-reel posts: `reshare_count` is not present

**Limitation:** Only available on Reels/clips. Photos and carousels don't expose this.

**Related field:** `media_repost_count` — available on ALL post types in v2. This counts formal "reposts" (a newer Instagram feature). Less common than reshares but available universally.

**For Blossom:**
- Reshare-to-like ratio on reels is a strong signal of audience advocacy
- Compare across creators: high reshare ratio = audience actively amplifies content
- Can benchmark within niches (fitness creators average X% reshare rate)
- Combine with repost data for a composite "audience amplification" metric

---

## 6. Comment Sampling Has a Hard Ceiling

**All comment endpoints return 15 comments per request.**

- `/v1/media/comments/chunk`: 15 per page
- `/v2/media/comments`: 15 per page
- `/gql/comments/chunk`: 15 per page (different params)

**Practical implications:**
- For a post with 500 comments, we get ~3% sample per page
- Comments are sorted by Instagram's relevance algorithm (not chronological)
- The "top" comments skew toward popular/engaging comments
- Pagination is available but quality degrades past the first few pages
- Practical limit: ~100-200 comments per post before diminishing returns

**For Blossom:** Comment-based analysis (intent classification, buying signals, question detection) operates on a vocal minority. Any metrics derived from comments should be clearly labelled with sample size and treated as **directional, not precise**.

---

## 7. Account Creation Date Available via `/v1/user/about`

**Endpoint:** `/v1/user/about` (v1 only, no v2 equivalent)

```json
{
  "username": "jaime.chapman",
  "is_verified": true,
  "country": "Australia",
  "date": "May 2015",
  "former_usernames": ""
}
```

**Investment value:**
- **Account age** is a trust signal (accounts created recently may be suspicious)
- **Country** reveals market/geography without relying on audience inference
- **Former usernames** can reveal rebrands or pivots
- `is_verified` confirms Instagram's own trust assessment

**Limitation:** `date` is month + year only, not exact date. `former_usernames` is often empty even for accounts that have changed names (Instagram may only expose recent changes).

---

## 8. Comment Toxicity Check Available

**Endpoint:** `/v2/media/comment/offensive`

```json
{
  "response": {
    "is_offensive": false,
    "text_language": "en",
    "status": "ok"
  }
}
```

**How it works:** Pass `media_id` + `comment_text` and Instagram's own moderation system tells you if the text is offensive + detects the language.

**For Blossom:**
- Could be used to flag problematic comments before including them in analysis
- Language detection is useful for audience geo-inference
- However, this is a per-comment call — expensive at scale
- Better to run our own toxicity detection in-pipeline and reserve this for validation

---

## 9. Full GraphQL User (`/a2/user`) is the Most Complete Single Endpoint

**Response size:** 148KB per user — the largest single-endpoint response available.

Contains every possible user field in a single call, but at significant response size cost. Useful when you need maximum data in minimum requests, but typically `/v2/user/by/id` (14KB) provides sufficient data for investment verification.

---

## 10. Business Exploration Endpoint for Competitive Intelligence

**Endpoint:** `/v2/user/explore/businesses/by/id`

Returns recommended business accounts in the same category as the queried user. This is Instagram's own categorisation graph — valuable for:
- Understanding which niche Instagram places a creator in
- Finding competing/adjacent brand accounts
- Validating our own niche classification against Instagram's internal model

Response size: ~96KB, containing full user objects for recommended businesses.
