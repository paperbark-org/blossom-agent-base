# v1 vs v2 Endpoint Comparison

Detailed field-level comparison showing why v2 endpoints should be preferred for investment verification.

---

## User Endpoints

### Summary

| Metric | v1 `/v1/user/by/id` | v2 `/v2/user/by/id` |
|---|---|---|
| Total fields | **30** | **223** |
| Response size | 1.4KB | 14.3KB |
| Unique fields | 3 | 196 |
| Shared fields | 27 | 27 |

### v1-Only Fields (3)

These are available in v1 but NOT in v2:

| Field | Type | Notes |
|---|---|---|
| `hd_profile_pic_url_info` (structure) | object | Different structure in v2 |
| `profile_pic_url` (format) | string | Present in both but different URL format |
| `edge_*` fields | numbers | v1 uses `edge_followed_by` etc; v2 uses `follower_count` |

### v2-Only Fields by Investment Verification Category

#### A. Commerce / Shopping (12 fields)

| Field | Type | Sample Value | Investment Relevance |
|---|---|---|---|
| `merchant_checkout_style` | string | `"none"` (creator), `"multi_item_checkout"` (brand) | Whether account has Instagram Shop |
| `show_shoppable_feed` | boolean | `false` (creator), `true` (brand) | Shoppable feed active |
| `seller_shoppable_feed_type` | string | `"none"`, `"mini_shop_wave_2"` | Shop tier level |
| `creator_shopping_info` | object | `{"linked_merchant_accounts": []}` | Creator-to-brand commerce links |
| `is_eligible_for_creator_product_links` | boolean | varies | Can tag products in posts |
| `current_catalog_id` | string/null | `null` | Active product catalog |
| `mini_shop_seller_onboarding_status` | string/null | `null` | Shop setup progress |
| `shopping_post_onboard_nux_type` | string/null | `null` | Shopping onboarding state |
| `disable_profile_shop_cta` | boolean | varies | Shop CTA visibility |
| `can_use_affiliate_partnership_messaging_as_creator` | boolean | `false` | Affiliate commerce capability |
| `can_use_affiliate_partnership_messaging_as_brand` | boolean | `false` | Brand affiliate capability |
| `is_eligible_for_creator_product_links` | boolean | varies | Product linking capability |

#### B. Partnership / Branded Content (6 fields)

| Field | Type | Sample Value | Investment Relevance |
|---|---|---|---|
| `can_use_branded_content_discovery_as_creator` | boolean | `false` | On Instagram's branded content marketplace |
| `can_use_branded_content_discovery_as_brand` | boolean | `false` | Brand-side marketplace access |
| `can_use_paid_partnership_messaging_as_creator` | boolean | `false` | Can use paid partnership label |
| `is_open_to_collab` | boolean | `false` | Self-declared collaboration openness |
| `has_collab_collections` | boolean | `false` | Has collaboration content collections |
| `is_recon_ad_cta_on_profile_eligible_with_viewer` | boolean | varies | Ad CTA eligibility |

#### C. Meta Verification / Trust (12 fields)

| Field | Type | Sample Value | Investment Relevance |
|---|---|---|---|
| `is_eligible_for_meta_verified_label` | boolean | `true` | Meta Verified eligibility |
| `meta_verified_benefits_info` | object | `{active_meta_verified_benefits: [], ...}` | Active verification benefits |
| `is_eligible_for_ig_meta_verified_label` | boolean | varies | IG-specific verification |
| `is_eligible_for_meta_verified_content_protection` | boolean | `false` | Content protection tier |
| `is_eligible_for_meta_verified_links_in_reels` | boolean | `false` | Premium link features |
| `is_eligible_for_meta_verified_links_in_post` | boolean | `false` | Premium post links |
| `is_eligible_for_meta_verified_enhanced_link_sheet` | boolean | `false` | Enhanced link features |
| `is_eligible_for_meta_verified_related_accounts` | boolean | `false` | Related accounts feature |
| `is_eligible_for_meta_verified_multiple_addresses_creation` | boolean | `false` | Multi-address capability |
| `show_account_transparency_details` | boolean | `true` | Transparency page available |
| `transparency_product_enabled` | boolean | `false` | Full transparency product |
| `show_blue_badge_on_main_profile` | boolean | `true` | Blue badge visibility |

#### D. Fan / Subscription (8 fields)

| Field | Type | Sample Value | Investment Relevance |
|---|---|---|---|
| `fan_club_info` | object | `{fan_club_id: null, subscriber_count: null, ...}` | Fan club/subscription setup |
| `has_fan_club_subscriptions` | boolean | `false` | Active subscription offering |
| `has_exclusive_feed_content` | boolean | `false` | Gated content available |
| `is_fan_club_gifting_eligible` | boolean | null | Gifting feature eligible |
| `fan_consideration_page_revamp_eligiblity` | boolean | null | Fan page feature |
| `has_enough_subscribers_for_ssc` | boolean | null | Subscriber scale |
| `is_fan_club_referral_eligible` | boolean | null | Referral program |
| `is_free_trial_eligible` | boolean | null | Free trial offering |

#### E. Content / Engagement Signals (15+ fields)

| Field | Type | Sample Value | Investment Relevance |
|---|---|---|---|
| `account_type` | integer | `1` (personal), `2` (business), `3` (creator) | Account classification |
| `bio_links` | array | Full link objects with titles, URLs, types | External link ecosystem |
| `total_clips_count` | integer | `1` | Reels production volume |
| `has_guides` | boolean | `false` | Content curation investment |
| `has_videos` | boolean | `true` | Video content presence |
| `has_highlight_reels` | boolean | `false` | Highlight curation |
| `is_interest_account` | boolean | `true` | Instagram's interest classification |
| `is_potential_business` | boolean | `false` | Business conversion potential |
| `feed_post_reshare_disabled` | boolean | `false` | Reshare permissions |
| `is_remix_setting_enabled_for_posts` | boolean | `true` | Remix/collab permissions |
| `is_remix_setting_enabled_for_reels` | boolean | `true` | Reel remix permissions |
| `profile_type` | integer | `0` | Profile type classification |
| `has_music_on_profile` | boolean | `false` | Music content feature |
| `has_public_tab_threads` | boolean | `true` | Threads integration |
| `is_active_on_text_post_app` | boolean | `false` | Threads activity |

#### F. Account Meta / System (20+ fields)

| Field | Type | Investment Relevance |
|---|---|---|
| `pk_id` / `instagram_pk` | string | Stable identifier |
| `fbid_v2` | integer | Meta/Facebook ID cross-reference |
| `interop_messaging_user_fbid` | integer | Messaging platform ID |
| `third_party_downloads_enabled` | integer | Content download permissions |
| `nametag` | object | Profile customisation data |
| `avatar_status` | object | Avatar/metaverse presence |
| `broadcast_chat_preference_status` | object | Broadcast channel info |
| `pinned_channels_info` | object | Channel pinning behaviour |

---

## Comment Endpoints

### Summary

| Metric | v1 `/v1/media/comments/chunk` | v2 `/v2/media/comments` |
|---|---|---|
| Fields per comment | **8** | **32** |
| Response size (15 comments) | 14KB | 31.9KB |
| Comments per page | 15 | 15 |

### v1 Comment Fields (8)

```
pk, text, user (basic), created_at, comment_like_count,
child_comment_count, has_liked_comment, did_report_as_spam
```

### v2 Additional Comment Fields (24 extra)

| Field | Type | Investment Relevance |
|---|---|---|
| `content_type` | string | Comment content classification |
| `status` | string | Comment moderation status |
| `share_enabled` | boolean | Whether comment can be shared |
| `is_covered` | boolean | Whether comment is hidden/filtered |
| `has_translation` | boolean | Multi-language indicator |
| `is_ranked_comment` | boolean | Instagram's comment quality signal |
| `media_id` | string | Parent media reference |
| `parent_comment_id` | string | Thread parent (for nested replies) |
| `comment_index` | integer | Position in comment list |
| `giphy_media_info` | object | GIF response data |
| `private_reply_status` | integer | DM reply status |
| `user.is_verified` | boolean | Commenter verification status |
| `user.is_private` | boolean | Commenter privacy status |
| `user.account_badges` | array | Commenter badges |
| `user.latest_reel_media` | integer | Commenter activity level |
| `user.fan_club_info` | object | Commenter subscription status |
| `inline_composer_display_condition` | string | UI display condition |
| `preview_child_comments` | array | Preview of threaded replies |
| + additional UI/rendering fields | various | Limited investment value |

**Key takeaway for investment verification:** v2 comments give us `is_ranked_comment` (Instagram's own quality signal), richer commenter profiles (verified status, activity level), and thread structure (`parent_comment_id`, `preview_child_comments`). The commenter's `is_verified` status is useful — verified accounts leaving genuine comments is a strong quality signal.

---

## Media Endpoints

### Summary

| Metric | v1 `/v1/media/by/code` | v2 `/v2/media/info/by/code` |
|---|---|---|
| Response wrapper | Direct media object | `media_or_ad` wrapper |
| Response size | ~15KB | ~39.6KB |
| Reels-specific fields | Limited | `reshare_count`, `play_count` |

### Key v2-Only Media Fields

| Field | Type | Investment Relevance |
|---|---|---|
| `reshare_count` | integer | **HIGH** — audience advocacy (reels only) |
| `media_repost_count` | integer | Formal reposts (all post types) |
| `coauthor_producers` | array | **HIGH** — brand collaboration partners |
| `sponsor_tags` | array | **HIGH** — explicit sponsor tagging |
| `invited_coauthor_producers` | array | Pending collabs |
| `commerce_integrity_review_decision` | string | Commerce compliance status |
| `ig_media_sharing_disabled` | boolean | Sharing restrictions |
| `is_open_to_public_submission` | boolean | UGC/submission status |
| `organic_tracking_token` | string | Tracking identifier |
| `featured_products` | array | Tagged products (usually empty for non-shop posts) |
| `product_suggestions` | array | Suggested products |
| `shop_routing_user_id` | string/null | Shopping routing |

---

## Recommendation

**Always use v2 endpoints when available.** The data richness difference is substantial:
- User: 7x more fields
- Comments: 4x more fields
- Media: ~2.5x larger response with critical fields (`reshare_count`, `coauthor_producers`)

The additional API response size cost is negligible compared to the analytical value gained.
