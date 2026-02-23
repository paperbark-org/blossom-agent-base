# Complete Endpoint Catalog

All 143 endpoints from HikerAPI REST v1.7.6 OpenAPI spec (`/openapi.json`).

Organised by API version and functional group. Deprecated endpoints are marked.

---

## a2 — Alternative GraphQL (1 endpoint)

| Method | Path | Summary | Key Params |
|---|---|---|---|
| GET | `/a2/user` | User (full GraphQL — 148KB response) | `user_id` |

---

## gql — GraphQL Endpoints (18 endpoints)

### Comments

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/gql/comment/likers` | Comment Likers | `comment_id` | **DEPRECATED** → use `/gql/comment/likers/chunk` |
| GET | `/gql/comment/likers/chunk` | Comment Likers Chunk | `comment_id`, `end_cursor` | Active |
| GET | `/gql/comments` | Media Comments | `media_id` | **DEPRECATED** → use `/gql/comments/chunk` |
| GET | `/gql/comments/chunk` | Media Comments Chunk | `media_id`, `sort_order`, `end_cursor` | Active |
| GET | `/gql/comments/threaded` | Media Comments Threaded | `media_id` | **DEPRECATED** → use `/gql/comments/chunk` |
| GET | `/gql/comments/threaded/chunk` | Media Comments Threaded Chunk | `media_id`, `end_cursor` | Active |

### Media

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/gql/media/likers` | Media Likers | `media_id` | Active |
| GET | `/gql/media/usertags` | Users tagged in video (batch, up to 10 IDs) | `media_ids` | Active |

### User

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/gql/user/by/id` | User By Id | `user_id` | **DEPRECATED** |
| GET | `/gql/user/by/username` | User By Username | `username` | **DEPRECATED** |
| GET | `/gql/user/clips` | User Clips (reels) | `user_id`, `end_cursor` | Active |
| GET | `/gql/user/followers` | User Followers | `user_id` | **DEPRECATED** → use `/v2/user/followers` |
| GET | `/gql/user/followers/chunk` | User Followers Chunk | `user_id`, `end_cursor` | Active |
| GET | `/gql/user/following` | User Following | `user_id` | **DEPRECATED** → use `/v2/user/following` |
| GET | `/gql/user/following/chunk` | User Following Chunk | `user_id`, `end_cursor` | Active |
| GET | `/gql/user/medias` | User Medias (preferred for user feed) | `user_id`, `end_cursor` | Active |
| GET | `/gql/user/related/profiles` | Related Profiles | `user_id` | **DEPRECATED** → use `/v2/user/suggested/profiles` |
| GET | `/gql/user/reposts` | User Reposted Content | `user_id`, `end_cursor` | Active |

---

## sys — System (1 endpoint)

| Method | Path | Summary | Key Params |
|---|---|---|---|
| GET | `/sys/balance` | Account Balance | (none — uses access_key only) |

---

## v1 — Version 1 (72 endpoints)

### Search

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/fbsearch/places` | Facebook Search Places | `query` | Active |
| GET | `/v1/fbsearch/topsearch` | Facebook Top Search | `query` | Active |
| GET | `/v1/fbsearch/topsearch/hashtags` | Web Search Top Hashtags | `query` | Active |
| GET | `/v1/search/hashtags` | Search Hashtags | `query` | Active |
| GET | `/v1/search/music` | Search Music | `query` | Active |
| GET | `/v1/search/users` | Search Users | `query` | **Deprecating** → use `/v2/fbsearch/accounts` |

### Hashtag

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/hashtag/by/name` | Hashtag By Name | `name` | Active |
| GET | `/v1/hashtag/medias/clips` | Hashtag Media Clips | `name` | Active |
| GET | `/v1/hashtag/medias/clips/chunk` | Hashtag Media Clips Chunk | `name`, `end_cursor` | Active |
| GET | `/v1/hashtag/medias/recent` | Hashtag Recent Medias | `name` | **DEPRECATED** |
| GET | `/v1/hashtag/medias/recent/chunk` | Hashtag Recent Chunk | `name`, `end_cursor` | **DEPRECATED** |
| GET | `/v1/hashtag/medias/top` | Hashtag Top Medias | `name` | Active |
| GET | `/v1/hashtag/medias/top/chunk` | Hashtag Top Chunk | `name`, `end_cursor` | Active |
| GET | `/v1/hashtag/medias/top/recent/chunk` | Hashtag Top Recent Chunk | `name`, `end_cursor` | Active |

### Highlight

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/highlight/by/id` | Highlight By Id | `id` | **DEPRECATED** |
| GET | `/v1/highlight/by/url` | Highlight By URL | `url` | Active (use `/v1/share/by/url` for /s/ links) |

### Location

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/location/by/id` | Location By Id | `id` | Active |
| GET | `/v1/location/guides` | Location Guides | `id` | Active |
| GET | `/v1/location/medias/recent` | Location Recent Medias | `id` | Active |
| GET | `/v1/location/medias/recent/chunk` | Location Recent Chunk | `id`, `end_cursor` | Active |
| GET | `/v1/location/medias/top` | Location Top Medias | `id` | Active |
| GET | `/v1/location/medias/top/chunk` | Location Top Chunk | `id`, `end_cursor` | Active |
| GET | `/v1/location/search` | Location Search | `query` | Active |

### Media

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/media/by/code` | Media By Code | `code` | Active |
| GET | `/v1/media/by/id` | Media By Id | `id` | Active |
| GET | `/v1/media/by/url` | Media By URL | `url` | Active |
| GET | `/v1/media/code/from/pk` | Media Code From PK | `pk` | Active |
| GET | `/v1/media/comments` | Media Comments (all) | `id` | **DEPRECATED** → use chunk |
| GET | `/v1/media/comments/chunk` | Media Comments Chunk (15/page) | `id`, `end_cursor` | Active |
| GET | `/v1/media/download/photo` | Photo Download | `id` | **DEPRECATED** |
| GET | `/v1/media/download/photo/by/url` | Photo Download By URL | `url` | **DEPRECATED** |
| GET | `/v1/media/download/video` | Video Download | `id` | **DEPRECATED** |
| GET | `/v1/media/download/video/by/url` | Video Download By URL | `url` | **DEPRECATED** |
| GET | `/v1/media/insight` | Media Insights | `id` | Active (**but save/shopping fields always null**) |
| GET | `/v1/media/likers` | Media Likers | `id` | Active |
| GET | `/v1/media/oembed` | Media OEmbed | `url` | Active |
| GET | `/v1/media/pk/from/code` | Media PK From Code | `code` | Active |
| GET | `/v1/media/pk/from/url` | Media PK From URL | `url` | Active |
| GET | `/v1/media/user` | Media Owner User | `id` | Active |

### Share

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/share/by/code` | Share By Code (stories/highlights) | `code` | Active |
| GET | `/v1/share/by/url` | Share By URL (for /s/ links) | `url` | Active |
| GET | `/v1/share/reel/by/url` | Share Reel By URL | `url` | Active |

### Story

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/story/by/id` | Story By Id | `id` | Active |
| GET | `/v1/story/by/url` | Story By URL | `url` | Active |
| GET | `/v1/story/download` | Story Download | `id` | Active |
| GET | `/v1/story/download/by/story/url` | Story Download By Story URL | `url` | Active |
| GET | `/v1/story/download/by/url` | Story Download By File URL | `url` | Active |

### User

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v1/user/about` | User About (country, creation date) | `user_id` | Active (v1 only) |
| GET | `/v1/user/by/id` | User By Id | `user_id` | Active |
| GET | `/v1/user/by/url` | User By URL | `url` | Active |
| GET | `/v1/user/by/username` | User By Username | `username` | Active |
| GET | `/v1/user/clips` | User Clips (first page) | `user_id` | **DEPRECATED** → use `/v1/user/clips/chunk` |
| GET | `/v1/user/clips/chunk` | User Clips Chunk | `user_id`, `end_cursor` | Active |
| GET | `/v1/user/followers` | User Followers (first page) | `user_id` | **DEPRECATED** → use `/v2/user/followers` |
| GET | `/v1/user/followers/chunk` | User Followers Chunk | `user_id`, `end_cursor` | Active |
| GET | `/v1/user/following` | User Following (first page) | `user_id` | **DEPRECATED** → use `/v2/user/following` |
| GET | `/v1/user/following/chunk` | User Following Chunk | `user_id`, `end_cursor` | Active |
| GET | `/v1/user/guides` | User Guides | `user_id` | **DEPRECATED** |
| GET | `/v1/user/highlights` | User Highlights | `user_id` | Active |
| GET | `/v1/user/highlights/by/username` | User Highlights By Username | `username` | Active |
| GET | `/v1/user/medias` | User Medias (first page) | `user_id` | **DEPRECATED** → use `/gql/user/medias` |
| GET | `/v1/user/medias/chunk` | User Medias Chunk | `user_id`, `end_cursor` | Active |
| GET | `/v1/user/medias/pinned` | Pinned Medias | `user_id` | Active |
| GET | `/v1/user/search/followers` | Search Followers | `user_id`, `query` | Active |
| GET | `/v1/user/search/following` | Search Following | `user_id`, `query` | Active |
| GET | `/v1/user/stories` | User Stories | `user_id` | Active |
| GET | `/v1/user/stories/by/username` | User Stories By Username | `username` | Active |
| GET | `/v1/user/tag/medias` | User Tagged Medias | `user_id` | **DEPRECATED** |
| GET | `/v1/user/tag/medias/chunk` | User Tagged Medias Chunk | `user_id`, `end_cursor` | Active |
| GET | `/v1/user/videos` | User Videos | `user_id` | **DEPRECATED** → use `/v2/user/clips` |
| GET | `/v1/user/videos/chunk` | User Videos Chunk | `user_id`, `end_cursor` | **DEPRECATED** |
| GET | `/v1/user/web_profile_info` | Web Profile Info (62 fields) | `username` | Active |

---

## v2 — Version 2 (47 endpoints)

### Search

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/fbsearch/accounts` | Account Search | `query` | Active |
| GET | `/v2/fbsearch/places` | Place Search | `query` | Active |
| GET | `/v2/fbsearch/reels` | Reel Search | `query` | Active |
| GET | `/v2/fbsearch/topsearch` | Top Search | `query` | Active |
| GET | `/v2/search/accounts` | Account Search (no paging) | `query` | **DEPRECATED** → use `/v2/fbsearch/accounts` |
| GET | `/v2/search/hashtags` | Hashtag Search | `query` | Active |
| GET | `/v2/search/music` | Music Search | `query` | Active |
| GET | `/v2/search/places` | Place Search | `query` | **DEPRECATED** → use `/v3/fbsearch/places` |
| GET | `/v2/search/reels` | Reel Search | `query` | **DEPRECATED** → use `/v3/fbsearch/reels` |
| GET | `/v2/search/topsearch` | Top Search | `query` | **DEPRECATED** → use `/v3/fbsearch/topsearch` |

### Hashtag

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/hashtag/by/name` | Hashtag By Name | `name` | Active |
| GET | `/v2/hashtag/medias/clips` | Hashtag Clips | `name` | **DEPRECATED** → use `/v2/fbsearch/reels` |
| GET | `/v2/hashtag/medias/recent` | Hashtag Recent Medias | `name`, `end_cursor` | Active |
| GET | `/v2/hashtag/medias/top` | Hashtag Top Medias | `name`, `end_cursor` | Active |

### Highlight

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/highlight/by/id` | Highlight By Id | `id` | Active |

### Media

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/media/by/code` | Media By Code | `code` | **DEPRECATED** → use `/v2/media/info/by/code` |
| GET | `/v2/media/by/id` | Media By Id | `id` | **DEPRECATED** → use `/v2/media/info/by/id` |
| GET | `/v2/media/by/url` | Media By URL | `url` | **DEPRECATED** → use `/v2/media/info/by/url` |
| GET | `/v2/media/comment/offensive` | Check Offensive Comment | `media_id`, `comment_text` | Active |
| GET | `/v2/media/comments` | Media Comments (15/page) | `id`, `end_cursor` | Active |
| GET | `/v2/media/comments/replies` | Comment Replies | `id`, `comment_id` | Active |
| GET | `/v2/media/info/by/code` | Media Info By Code (**preferred**) | `code` | Active |
| GET | `/v2/media/info/by/id` | Media Info By Id | `id` | Active |
| GET | `/v2/media/info/by/url` | Media Info By URL | `url` | Active |
| GET | `/v2/media/likers` | Media Likers | `id` | Active |
| GET | `/v2/media/template` | Media Template | `id` | Active |

### Story

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/story/by/id` | Story By Id | `id` | Active |
| GET | `/v2/story/by/url` | Story By URL | `url` | Active |

### Track (Music)

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/track/by/canonical/id` | Track By Canonical Id | `id` | Active |
| GET | `/v2/track/by/id` | Track By Id | `id` | Active |
| GET | `/v2/track/stream/by/id` | Track Stream By Id | `id` | Active |

### User

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v2/user/by/id` | User By Id (**preferred**) | `user_id` | Active |
| GET | `/v2/user/by/username` | User By Username | `username` | Active |
| GET | `/v2/user/clips` | User Clips (reels) | `user_id`, `end_cursor` | Active |
| GET | `/v2/user/explore/businesses/by/id` | Explore Businesses | `user_id` | Active |
| GET | `/v2/user/followers` | User Followers | `user_id`, `end_cursor` | Active |
| GET | `/v2/user/following` | User Following | `user_id`, `end_cursor` | Active |
| GET | `/v2/user/highlights` | User Highlights | `user_id` | Active |
| GET | `/v2/user/highlights/by/username` | User Highlights By Username | `username` | Active |
| GET | `/v2/user/medias` | User Medias | `user_id` | **DEPRECATED** → use `/gql/user/medias` |
| GET | `/v2/user/stories` | User Stories | `user_id` | Active |
| GET | `/v2/user/stories/by/username` | User Stories By Username | `username` | Active |
| GET | `/v2/user/suggested/profiles` | Suggested Profiles | `user_id` | Active |
| GET | `/v2/user/tag/medias` | User Tagged Medias | `user_id`, `end_cursor` | Active |
| GET | `/v2/user/videos` | User Videos | `user_id` | **DEPRECATED** → use `/v2/user/clips` |
| GET | `/v2/userstream/by/id` | User Stream By Id | `user_id` | Active |
| GET | `/v2/userstream/by/username` | User Stream By Username | `username` | Active |

---

## v3 — Version 3 (4 endpoints)

| Method | Path | Summary | Key Params | Status |
|---|---|---|---|---|
| GET | `/v3/fbsearch/accounts` | Account Search | `query` | Active |
| GET | `/v3/fbsearch/places` | Place Search | `query` | Active |
| GET | `/v3/fbsearch/reels` | Reel Search | `query` | Active |
| GET | `/v3/fbsearch/topsearch` | Top Search | `query` | Active |

---

## Endpoint Count Summary

| Version | Total | Active | Deprecated |
|---|---|---|---|
| a2 | 1 | 1 | 0 |
| gql | 18 | 10 | 8 |
| sys | 1 | 1 | 0 |
| v1 | 72 | 52 | 20 |
| v2 | 47 | 33 | 14 |
| v3 | 4 | 4 | 0 |
| **Total** | **143** | **101** | **42** |

---

## Notes

- All endpoints require `access_key` query parameter (omitted from Key Params columns above)
- `end_cursor` is the standard pagination parameter for chunk/paginated endpoints
- Parameter naming differs between endpoint families — see [api-reference.md](./api-reference.md) for details
- Deprecated endpoints may still work but should not be used in new code
- v3 endpoints are currently search-only (4 endpoints)
- The OpenAPI spec at `/openapi.json` is the authoritative source and may be updated by HikerAPI
