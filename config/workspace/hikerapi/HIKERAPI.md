# HikerAPI Knowledge Base

## Overview
HikerAPI is a fault-tolerant Instagram data API. Base URL: `https://api.hikerapi.com`
Auth: header `x-access-key: <token>`
Default headers: `x-access-key: <token>`, `accept: application/json`

## Endpoint Map (by intent)

### 👤 User / Profile
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get profile by username | GET /v1/user/by/username | `?username=` |
| Get profile by ID | GET /v1/user/by/id | `?id=` |
| Get profile by URL | GET /v1/user/by/url | `?url=` |
| Get extended profile info | GET /v2/user/by/username | `?username=` |
| Get user "about" info | GET /v1/user/about | `?id=` |
| Get web profile info | GET /v1/user/web/profile/info | `?username=` |
| Search users | GET /v2/search/accounts | `?query=` |
| Get suggested/similar accounts | GET /v2/user/suggested/profiles | `?user_id=` |
| Get related business accounts | GET /v2/user/explore/businesses/by/id | `?user_id=` |

### 📸 Media / Posts
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get post by ID | GET /v1/media/by/id | `?id=` |
| Get post by shortcode/code | GET /v1/media/by/code | `?code=` |
| Get post by URL | GET /v1/media/by/url | `?url=` (use /p/ URLs) |
| Get post details (v2) | GET /v2/media/by/id | `?id=` |
| Get post author | GET /v1/media/user | `?media_id=` |
| Get post insights/engagement | GET /v1/media/insight | `?media_id=` |
| Get post likers | GET /v1/media/likers | `?id=` |
| Get post comments | GET /v1/media/comments/chunk | `?id=` (NOT media_id), `?end_cursor=` — returns [[comments], cursor, None] |
| Get embed info from URL | GET /v1/media/oembed | `?url=` |
| Get users tagged in post | GQL /gql/media/usertags | `?media_ids=` (up to 10) |

### 🎬 Reels / Clips
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get user reels | GET /v2/user/clips | `?user_id=`, `?page_id=` |
| Get user reels (GQL) | GET /gql/user/clips | `?user_id=`, `?max_id=` |
| Get reels for hashtag | GET /v1/hashtag/medias/clips | `?name=` |
| Get reels for hashtag (chunk) | GET /v1/hashtag/medias/clips/chunk | `?name=`, `?max_id=` |
| Get user reposts | GET /gql/user/reposts | `?user_id=` |

### 📰 User Feed / Posts
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get user posts | GET /gql/user/medias | `?user_id=` |
| Get user posts (chunk/paginated) | GET /v1/user/medias/chunk | `?user_id=`, `?end_cursor=` |
| Get user pinned posts | GET /v1/user/medias/pinned | `?user_id=` |
| Get posts user is tagged in | GET /v2/user/tag/medias | `?user_id=`, `?page_id=` |

### 👥 Followers / Following
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get followers (paginated, GQL) | GET /gql/user/followers/chunk | `?user_id=`, `?end_cursor=` |
| Get followers (v1) | GET /v1/user/followers/chunk | `?user_id=`, `?max_id=` |
| Get followers (v2) | GET /v2/user/followers | `?user_id=`, `?page_id=` |
| Get following (GQL) | GET /gql/user/following/chunk | `?user_id=`, `?end_cursor=` |
| Get following (v1) | GET /v1/user/following/chunk | `?user_id=`, `?max_id=` |
| Get following (v2) | GET /v2/user/following | `?user_id=`, `?page_id=` |
| Search within followers | GET /v1/user/search/followers | `?user_id=`, `?query=` |
| Search within following | GET /v1/user/search/following | `?user_id=`, `?query=` |

### 📖 Stories & Highlights
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get stories by user ID | GET /v1/user/stories | `?user_id=` |
| Get stories by username | GET /v1/user/stories/by/username | `?username=` |
| Get highlights by user ID | GET /v1/user/highlights | `?user_id=` |
| Get highlights by username | GET /v1/user/highlights/by/username | `?username=` |
| Get story by ID | GET /v1/story/by/id | `?id=` |
| Get highlight by ID | GET /v2/highlight/by/id | `?id=` |

### #️⃣ Hashtags
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get hashtag info | GET /v1/hashtag/by/name | `?name=` |
| Get top posts for hashtag | GET /v1/hashtag/medias/top | `?name=` |
| Get recent posts for hashtag | GET /v2/hashtag/medias/recent | `?name=`, `?page_id=` |
| Search hashtags | GET /v2/search/hashtags | `?query=` |

### 📍 Locations
| Intent | Endpoint | Params |
|--------|----------|--------|
| Get location by ID | GET /v1/location/by/id | `?id=` |
| Get top posts at location | GET /v1/location/medias/top | `?location_pk=` |
| Get recent posts at location | GET /v1/location/medias/recent | `?location_pk=` |
| Search locations by name | GET /v1/fbsearch/places | `?query=`, `?lat=`, `?lng=` (optional) |
| Search locations by lat/lng | GET /v1/location/search | `?lat=`, `?lng=` |

### 🎵 Music / Audio
| Intent | Endpoint | Params |
|--------|----------|--------|
| Search music/audio | GET /v2/search/music | `?query=` |
| Get track by ID | GET /v2/track/by/id | `?track_id=` |

### 🔍 General Search
| Intent | Endpoint | Params |
|--------|----------|--------|
| Top search (users, hashtags, places) | GET /v1/fbsearch/topsearch | `?query=` |
| Search accounts | GET /v2/search/accounts | `?query=` |

## Key Notes

- **Always prefer v2 endpoints** over v1 where available — more reliable
- **Username → ID resolution**: Some endpoints need user_id not username. Use `/v1/user/by/username` first to get `pk` field
- **Pagination**: Use `end_cursor` or `page_id` from response to get next page
- **Request costs**: Highlights and stories cost 2-3 requests per call; use `force=on` to skip privacy checks and save 1 req
- **403** = private account; **404** = account not found/deleted
- **Rate limit**: 429 = slow down

## Common Workflows

### "Tell me about @username"
1. GET /v1/user/by/username → full profile (followers, following, bio, post count, verified, business)

### "Show me recent posts from @username"  
1. GET /v1/user/by/username → get `pk`
2. GET /v1/user/medias/chunk?user_id={pk} → posts

### "Who are @username's followers?"
1. GET /v1/user/by/username → get `pk`
2. GET /gql/user/followers/chunk?user_id={pk} → paginate with end_cursor

### "What's trending under #hashtag?"
1. GET /v1/hashtag/medias/top?name={hashtag}
2. GET /v2/hashtag/medias/recent?name={hashtag}

### "Analyze this post: [URL]"
1. GET /v1/media/by/url?url={url} → post details
2. GET /v1/media/insight?media_id={id} → engagement metrics
3. GET /v1/media/likers?id={id} → who liked it
4. GET /v1/media/comments/chunk?media_id={id} → comments

### "Find posts near [location]"
1. GET /v1/fbsearch/places?query={location} → get location_pk
2. GET /v1/location/medias/recent?location_pk={pk} → recent posts there
