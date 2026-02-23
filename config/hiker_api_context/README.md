# HikerAPI Endpoint Documentation

> Research conducted January 2026 for Blossom (Paperbark) — "Verification Layer of Creator Investments"

## Purpose

This documentation captures a comprehensive audit of HikerAPI's Instagram data endpoints, with a specific focus on **which data fields can be used to verify creator investment decisions**. It was produced through hands-on endpoint testing (not from official docs — HikerAPI has no public documentation beyond an OpenAPI spec).

## API Overview

| Property | Value |
|---|---|
| Base URL | `https://api.hikerapi.com` |
| Auth | Query parameter: `access_key` |
| API Version | HikerAPI REST v1.7.6 |
| Total Endpoints | **143** (discovered via `/openapi.json`) |
| Endpoint Versions | v1, v2, v3, gql, a2, sys |
| Rate/Pricing | ~$0.86 AUD per 1,000 requests ($0.0006 USD/request, converted at ~1.44 USD/AUD) |

## File Index

| File | Description |
|---|---|
| [endpoint-priority-matrix.md](./endpoint-priority-matrix.md) | Tiered endpoint ranking by investment verification value |
| [critical-discoveries.md](./critical-discoveries.md) | Key findings — media insight nulls, commerce gaps, partnership detection |
| [v1-vs-v2-comparison.md](./v1-vs-v2-comparison.md) | Field-level comparison across API versions |
| [field-investment-verification-map.md](./field-investment-verification-map.md) | Every relevant field mapped to investment verification use cases |
| [api-reference.md](./api-reference.md) | Auth, pagination patterns, parameter conventions, error handling |
| [endpoint-catalog.md](./endpoint-catalog.md) | Full catalog of all 143 endpoints from OpenAPI spec |
| [known-limitations.md](./known-limitations.md) | Platform constraints, data gaps, confidence ceilings |
| [testing-methodology.md](./testing-methodology.md) | Users sampled, post types tested, confidence framework |

## Key Findings (TL;DR)

1. **v2 endpoints return dramatically richer data** — User: 30 fields (v1) vs 223 fields (v2). Comments: 8 vs 32 fields. Always prefer v2.

2. **Media insight data is inaccessible** — `/v1/media/insight` exposes `save_count`, `shopping_outbound_click_count`, `shopping_product_click_count` but ALL return **null** via third-party API access. Requires account owner authentication.

3. **`is_paid_partnership` is unreliable** — Often `false` on clearly sponsored content. Use `coauthor_producers` + caption analysis for partnership detection.

4. **`reshare_count` is v2-only, reels-only** — Strong audience advocacy signal but limited to reel format. `media_repost_count` is available on all post types.

5. **Commerce fields exist but are account-type dependent** — `merchant_checkout_style`, `show_shoppable_feed` etc. populate for brand accounts (e.g., Glossier) but not for creators.

6. **Comment sampling is limited** — 15 comments per request, no deep pagination. This is a hard ceiling on comment-based analysis.

## How to Use This Research

**For pipeline engineers:** Start with [api-reference.md](./api-reference.md) for integration patterns, then [endpoint-priority-matrix.md](./endpoint-priority-matrix.md) to know which endpoints to call.

**For product/strategy:** Start with [critical-discoveries.md](./critical-discoveries.md) to understand what's possible and what isn't, then [field-investment-verification-map.md](./field-investment-verification-map.md) for specific field-to-feature mapping.

**For AI/ML engineers:** See [v1-vs-v2-comparison.md](./v1-vs-v2-comparison.md) for the richest data sources, and [known-limitations.md](./known-limitations.md) for confidence ceilings on any model inputs.

## Raw API Responses

Raw JSON responses from all tested endpoints are stored in the scratchpad directory used during research. Key files include full v1/v2 user profiles for emmachamberlain, garyvee, glossier, zoella, and kayla_itsines, plus media detail comparisons across carousel, reel, and photo post types.
