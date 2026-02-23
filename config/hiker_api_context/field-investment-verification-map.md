# Field-Level Investment Verification Map

Every field relevant to Blossom's mission — "Verification Layer of Creator Investments" — mapped by verification category and confidence level.

---

## A. Partnership & Sponsorship Detection

**Use case:** Identify which posts are sponsored, which brands the creator works with, and how transparent they are about partnerships.

### High Confidence Fields

| Field | Source Endpoint | Type | How to Use | Confidence |
|---|---|---|---|---|
| `coauthor_producers` | v2 media info | array of user objects | Non-empty = official brand collaboration. Contains brand's user object. **Most reliable** partnership signal. | **High** |
| `sponsor_tags` | v2 media info | array | Explicit sponsor tag applied by creator. Less common than coauthor but very reliable when present. | **High** |
| `usertags` | v2 media info | array of user objects with coordinates | Brands tagged in photos. Check against known brand account list. | **High** (when matched) |
| `is_paid_partnership` | media objects | boolean | Instagram's native paid partnership label. **Unreliable as sole signal** — often `false` on sponsored content. | **Medium** (false negatives) |

### Medium Confidence Fields

| Field | Source Endpoint | Type | How to Use | Confidence |
|---|---|---|---|---|
| `caption.text` | media objects | string | Parse for #ad, #sponsored, #gifted, #partner, #collab, brand @mentions. Requires NLP/regex. | **Medium** |
| `can_use_paid_partnership_messaging_as_creator` | v2 user | boolean | Whether the creator has partnership tools enabled. Indicates partnership readiness, not actual partnerships. | **Medium** |
| `can_use_branded_content_discovery_as_creator` | v2 user | boolean | On Instagram's branded content marketplace. Indicates professional creator status. | **Medium** |
| `is_open_to_collab` | v2 user | boolean | Self-declared collaboration openness. | **Low-Medium** |
| `has_collab_collections` | v2 user | boolean | Has curated collaboration content. | **Low-Medium** |

### Composite Sponsorship Detection (Recommended)

```
sponsored =
  is_paid_partnership == true
  OR coauthor_producers is non-empty
  OR sponsor_tags is non-empty
  OR caption matches /\b(#ad|#sponsored|#gifted|#partner|paid partnership)\b/i
  OR usertags intersect known_brand_accounts
```

**Estimated detection improvement:** This composite catches ~2-3x more sponsored posts than `is_paid_partnership` alone.

---

## B. Engagement & Audience Quality

**Use case:** Assess whether engagement is genuine, what drives it, and whether the audience is commercially receptive.

### Directly Observed (High Confidence)

| Field | Source Endpoint | Type | How to Use | Confidence |
|---|---|---|---|---|
| `like_count` | media objects | integer | Base engagement metric. Compare to follower count for engagement rate. | **High** |
| `comment_count` | media objects | integer | Interaction depth. High comment-to-like ratio suggests engaged community. | **High** |
| `play_count` | media objects (reels) | integer | Video view count. Compare to follower count for reach rate. | **High** |
| `reshare_count` | v2 media info (reels only) | integer | **Audience advocacy** — reshare-to-like ratio. Above 5% is strong. | **High** (reels only) |
| `media_repost_count` | v2 media info | integer | Formal reposts. Less common than reshares but available on all post types. | **High** |
| `comment_like_count` | comment objects | integer | Comment quality — high-liked comments indicate community consensus. | **High** |
| `follower_count` | user objects | integer | Audience size baseline. | **High** |
| `following_count` | user objects | integer | Follow ratio (followers:following). Extreme ratios can indicate follow-unfollow tactics. | **High** |
| `media_count` | user objects | integer | Content volume and posting consistency. | **High** |

### AI-Derived (Medium Confidence)

| Signal | Source | How to Derive | Confidence |
|---|---|---|---|
| Engagement rate | `like_count + comment_count / follower_count` | Standard calculation per post, then average | **High** (calculation), **Medium** (as quality indicator) |
| Sponsored vs organic delta | Compare engagement on `sponsored=true` vs `sponsored=false` posts | Ratio of avg engagement. >70% retention = audience tolerates ads | **Medium-High** (depends on sample size) |
| Comment quality breakdown | Comment text via NLP | Classify: genuine, buying intent, question, generic/bot | **Low-Medium** (15 comment sample) |
| Reshare-to-like ratio | `reshare_count / like_count` (reels only) | Benchmark within niche | **High** (reels), **N/A** (other formats) |
| Content-engagement correlation | Group posts by content theme × media type, compare metrics | Per-theme performance matrix | **Medium** |

### Comment-Derived Intent Signals (Low-Medium Confidence)

| Signal | Detection Method | Confidence |
|---|---|---|
| Buying intent | Comments containing "where", "link", "how much", "need this", product-specific questions | **Low-Medium** |
| Question intent | Comments containing "?", "how do you", "what is", "can you" | **Medium** |
| Generic/bot | Short comments (<3 words), emoji-only, repetitive patterns | **Medium** |
| Genuine engagement | Substantive comments referencing specific content | **Medium** |
| Language distribution | `text_language` from `/v2/media/comment/offensive` or NLP detection | **Medium** |

---

## C. Commerce & Shopping Capability

**Use case:** Determine whether a creator/brand has commerce infrastructure and whether their audience engages with shopping features.

### Account-Level Commerce (v2 User)

| Field | Type | What It Tells Us | Populated For |
|---|---|---|---|
| `is_business` | boolean | Business vs creator account | All accounts |
| `merchant_checkout_style` | string | `"none"`, `"multi_item_checkout"` | **Brands only** |
| `show_shoppable_feed` | boolean | Instagram Shop active on profile | **Brands only** |
| `seller_shoppable_feed_type` | string | `"none"`, `"mini_shop_wave_2"` | **Brands only** |
| `creator_shopping_info` | object | `linked_merchant_accounts` array | All (usually empty for creators) |
| `is_eligible_for_creator_product_links` | boolean | Can tag products in posts | Creator accounts |
| `current_catalog_id` | string/null | Active product catalog | Brands with Shop |
| `mini_shop_seller_onboarding_status` | string/null | Shop setup progress | Brands |

### Post-Level Commerce (v2 Media)

| Field | Type | What It Tells Us | Confidence |
|---|---|---|---|
| `has_product_tags` | boolean | Post has tagged products | **High** |
| `featured_products` | array | Tagged product objects | **High** (when populated) |
| `product_suggestions` | array | Suggested products | **Low** (usually empty) |
| `shop_routing_user_id` | string/null | Shopping redirect target | **Medium** |
| `commerce_integrity_review_decision` | string | Commerce compliance status | **Medium** (inconsistent) |

### Inaccessible Commerce Data (CRITICAL GAP)

| Field | Endpoint | Status | What It Would Tell Us |
|---|---|---|---|
| `save_count` | `/v1/media/insight` | **Always null** | Purchase intent (bookmarking to buy) |
| `shopping_outbound_click_count` | `/v1/media/insight` | **Always null** | Direct shopping clicks |
| `shopping_product_click_count` | `/v1/media/insight` | **Always null** | Product page visits |
| `shopping_product_by_tag_click_count` | `/v1/media/insight` | **Always empty** | Per-product click attribution |

These require account owner authentication. No third-party tool has access.

---

## D. Creator Trust & Authenticity

**Use case:** Verify that a creator is legitimate, trustworthy, and operates transparently.

### Identity & Verification

| Field | Source Endpoint | Type | What It Tells Us | Confidence |
|---|---|---|---|---|
| `is_verified` | user objects | boolean | Instagram blue badge verification | **High** |
| `is_eligible_for_meta_verified_label` | v2 user | boolean | Meta Verified subscription eligibility | **High** |
| `meta_verified_benefits_info` | v2 user | object | Active Meta Verified features | **High** |
| `show_blue_badge_on_main_profile` | v2 user | boolean | Badge display status | **High** |
| `show_account_transparency_details` | v2 user | boolean | Transparency page available | **High** |
| `transparency_product_enabled` | v2 user | boolean | Full transparency product active | **High** |

### Account Provenance

| Field | Source Endpoint | Type | What It Tells Us | Confidence |
|---|---|---|---|---|
| `country` | `/v1/user/about` | string | Account's declared country | **High** |
| `date` | `/v1/user/about` | string (e.g. "May 2015") | Account creation date | **High** |
| `former_usernames` | `/v1/user/about` | string | Previous usernames (rebrands/pivots) | **Medium** (often empty) |
| `account_type` | v2 user | integer | 1=personal, 2=business, 3=creator | **High** |
| `is_private` | user objects | boolean | Public vs private account | **High** |
| `is_memorialized` | v2 user | boolean | Deceased/memorial account | **High** |

### Content Authenticity

| Field | Source Endpoint | Type | What It Tells Us | Confidence |
|---|---|---|---|---|
| `is_remix_setting_enabled_for_posts` | v2 user | boolean | Allows content remixing (open creator) | **Medium** |
| `is_remix_setting_enabled_for_reels` | v2 user | boolean | Allows reel remixing | **Medium** |
| `feed_post_reshare_disabled` | v2 user | boolean | Blocks resharing (defensive posture) | **Medium** |
| `third_party_downloads_enabled` | v2 user | integer | Content download permissions | **Medium** |
| `has_anonymous_profile_picture` | v2 user | boolean | Default/placeholder profile pic | **High** (red flag if true) |

### Network Signals

| Field | Source Endpoint | Type | What It Tells Us | Confidence |
|---|---|---|---|---|
| Follower/following ratio | Derived from user object | float | Extreme ratios indicate manipulation | **Medium-High** |
| `mutual_followers_count` | v2 user | integer | Shared followers with viewer | **Low** (viewer-specific) |
| `is_interest_account` | v2 user | boolean | Instagram's interest classification | **Medium** |
| `is_potential_business` | v2 user | boolean | Business conversion potential | **Medium** |

---

## E. Content & Format Analysis

**Use case:** Understand what content a creator produces, in what formats, and how consistently.

| Field | Source | Type | What It Tells Us | Confidence |
|---|---|---|---|---|
| `media_type` | media objects | integer | 1=photo, 2=video, 8=carousel | **High** |
| `product_type` | media objects | string | `"feed"`, `"clips"` (reels), `"igtv"` | **High** |
| `carousel_media_count` | media objects | integer | Number of slides in carousel | **High** |
| `caption.text` | media objects | string | Full caption text for NLP analysis | **High** |
| `caption.hashtags` | media objects | array | Hashtag strategy | **High** |
| `taken_at` | media objects | timestamp | Posting schedule/cadence | **High** |
| `location` | media objects | object | Geo-location of post | **Medium** (not all posts geotagged) |
| `total_clips_count` | v2 user | integer | Reels production volume | **High** |
| `has_guides` | v2 user | boolean | Has created Guide content | **High** |
| `has_videos` | v2 user | boolean | Produces video content | **High** |
| `bio_links` | v2 user | array | External link ecosystem (YouTube, podcast, shop, etc.) | **High** |
| `biography` | user objects | string | Bio text for NLP analysis | **High** |

---

## Confidence Level Definitions

| Level | Meaning | Data Source |
|---|---|---|
| **High** | Directly observed from Instagram. Full population data. Minimal inference. | API metadata, counts, booleans |
| **Medium-High** | Directly observed but sample-size dependent or context-dependent. | Derived metrics with sufficient data |
| **Medium** | AI-inferred from rich signal, or directly observed but with known gaps. | Gemini analysis, composite detection |
| **Low-Medium** | AI-inferred from limited sample or indirect signal. Directional only. | Comment classification, intent inference |
| **Low** | Speculative or highly sample-dependent. Use with explicit caveats. | Small sample extrapolation |
| **UNUSABLE** | Data exists in schema but never populates via API. | `/v1/media/insight` null fields |
