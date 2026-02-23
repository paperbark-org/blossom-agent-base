# Known Limitations

Platform constraints, data gaps, and confidence ceilings that affect what Blossom can build with HikerAPI data.

---

## Platform-Level Limitations (Shared by All Competitors)

These are Instagram platform restrictions. No third-party tool can work around them.

### 1. Save Count is Invisible

**Impact: CRITICAL**

Instagram does not expose save counts to third-party APIs. Saves are arguably the strongest purchase intent signal — a user saving a product post is bookmarking it for later action.

The `save_count` field exists in **two** endpoints — `/v1/media/insight` and `/gql/user/medias` (on every media object in `stream_rows`) — but always returns `null`/`None`. Additionally, `/gql/user/medias` exposes `can_viewer_save` (boolean, always `true`) and `has_viewer_saved` (always `None` without auth). Exhaustive testing across 38 posts from 3 account types (creator, business with Shop) confirmed zero non-null values. See [critical-discoveries.md](./critical-discoveries.md) Section 1 for the full verification matrix.

**Workaround:** None. We infer intent from comments (much weaker signal) and engagement patterns (indirect).

### 2. Shopping Click Data is Invisible

**Impact: CRITICAL**

`shopping_outbound_click_count` and `shopping_product_click_count` are always `null` via third-party access. These would be direct conversion indicators — users clicking through to shop from a post.

**Workaround:** None. We can detect whether a post has product tags (`has_product_tags`) and whether the creator's account has a shop (`show_shoppable_feed`), but we cannot see click-through rates.

### 3. Share Count / DM Shares are Invisible

**Impact: HIGH**

We cannot see how many times a post was shared via DM. `reshare_count` is available on reels (v2 only) but this counts story reshares, not DM shares. DM shares would indicate private advocacy — "look at this product" messages to friends.

**Workaround:** `reshare_count` on reels is the closest proxy. `media_repost_count` captures public reposts across all formats.

### 4. Story Engagement is Invisible

**Impact: HIGH**

Stories are ephemeral and the API cannot access:
- Story poll responses
- Story question replies
- Story reaction counts
- Swipe-up / link sticker click rates
- Story view completion rates

We can see current live stories (`/v2/user/stories`) but not historical engagement on past stories.

**Workaround:** None for historical data. Current stories provide limited content analysis opportunity.

### 5. Video Completion Rate is Unavailable

**Impact: MEDIUM-HIGH**

For Reels/video, we get `play_count` but not average watch time or completion rate. A video with 100K plays and 10% completion is fundamentally different from one with 100K plays and 80% completion. Both look identical in our data.

**Workaround:** None. `play_count` is the only video performance metric available.

### 6. Audience Demographics are Hidden

**Impact: HIGH**

We cannot see audience demographics (age, gender, location distribution) from the API. This data is only available to the account owner via Instagram Insights.

**Workaround:** Sample follower profiles (`/v2/user/followers`) to infer demographics from follower bios, locations, and profile characteristics. This is a biased sample (public profiles only, relevance-sorted).

---

## HikerAPI-Specific Limitations

### 7. Comment Page Size is Fixed at 15

**Impact: MEDIUM**

All comment endpoints return exactly 15 comments per request. There is no parameter to increase this. For a post with 1,000 comments, we sample <2% per page.

**Mitigation:**
- Paginate to collect more comments (costs more API requests)
- Comments are sorted by Instagram's relevance algorithm, so early pages contain the highest-quality comments
- Practical ceiling: ~100-200 comments per post before quality degrades
- Always report sample sizes alongside any comment-derived metrics

### 8. `is_paid_partnership` Has False Negatives

**Impact: MEDIUM**

This field is `false` on many clearly sponsored posts because creators don't always use Instagram's native Paid Partnership label.

**Mitigation:** Use composite detection — see [field-investment-verification-map.md](./field-investment-verification-map.md) Section A for the recommended composite signal.

### 9. Commerce Fields Are Account-Type Dependent

**Impact: LOW-MEDIUM**

Commerce fields (`merchant_checkout_style`, `show_shoppable_feed`, etc.) only populate for business accounts with Instagram Shop. Creator accounts always show `none`/`false` regardless of their commercial activity.

**Mitigation:** Use these fields for brand verification, not creator assessment. For creators, assess commercial relevance through content analysis and comment intent.

### 10. `commerce_integrity_review_decision` is Inconsistent

**Impact: LOW**

This field appears on media objects but its population is inconsistent across accounts and post types. Observed empty on many posts where we'd expect it to have a value.

**Mitigation:** Don't rely on this field as a primary signal. Treat as supplementary when available.

### 11. `/v1/user/about` Has Limited Historical Data

**Impact: LOW**

The `former_usernames` field is often empty even for accounts that have changed names. Instagram may only expose very recent name changes.

**Mitigation:** Use as a bonus signal when available. Don't rely on absence as evidence of no name changes.

### 12. Some v2 Endpoints Don't Exist

**Impact: LOW**

Not all v1 endpoints have v2 equivalents:
- `/v1/user/about` — v1 only (no v2)
- `/v1/media/insight` — v1 only (no v2)
- `/v1/user/guides` — deprecated, no replacement
- `/v1/user/medias/pinned` — v1 only

**Mitigation:** Use the available version. These are supplementary endpoints.

---

## Data Confidence Ceilings

Even with optimal use of all available endpoints, these confidence ceilings apply:

| Analysis Type | Maximum Confidence | Limiting Factor |
|---|---|---|
| Engagement metrics | **High** | Directly observed, full population |
| Content classification | **Medium** | AI-inferred from multimodal input |
| Sponsorship detection | **Medium-High** | Composite signal, but false negatives persist |
| Comment intent analysis | **Low-Medium** | 15-comment sample, vocal minority bias |
| Audience motivation ("why they follow") | **Medium** | Inference from multiple signals, no ground truth |
| Purchase intent | **Low-Medium** | Saves invisible, shopping clicks invisible, comments are proxy |
| ROI prediction | **Low** | No outcome data, no conversion tracking |
| Audience demographics | **Low-Medium** | Follower sampling bias, public profiles only |

---

## Competitive Parity

These limitations are shared by all competitors:

| Competitor | Same Limitations? |
|---|---|
| CreatorIQ | Yes — same API constraints. They supplement with first-party data from opted-in creators |
| HypeAuditor | Yes — they focus on fraud detection (where public data suffices) |
| Upfluence/Grin | Yes — they push creators to connect accounts for first-party data |
| Lefty | Yes — they supplement with forecasting models trained on historical outcomes |

**Blossom's differentiation cannot come from having better raw data** (everyone has the same constraints). It comes from:
1. **Better analysis** of available data (multi-signal synthesis, post performance matrix)
2. **Better presentation** (enterprise scorecard, comparative benchmarks)
3. **AI-native multimodal analysis** (Gemini for content understanding)
4. **Unique metrics** (Sponsored Receptivity Score, Content-Intent Alignment Map)
