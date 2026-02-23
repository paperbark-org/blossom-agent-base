# API Reference

## Authentication

All endpoints require the `access_key` query parameter:

```
GET https://api.hikerapi.com/v2/user/by/id?user_id=292236837&access_key=YOUR_KEY
```

## Account Balance

```
GET /sys/balance
```

Returns remaining request credits and dollar amount:

```json
{
  "requests": 598130,
  "rate": 15,
  "currency": "USD",
  "amount": 358.93
}
```

Rate is $15 per 1,000 requests.

## Parameter Conventions

This is one of the most important sections — parameter naming is **inconsistent** across endpoint families, and incorrect params return 422 errors.

| Endpoint Family | ID Parameter | Example |
|---|---|---|
| User endpoints | `user_id` | `/v2/user/by/id?user_id=292236837` |
| Media endpoints (v1/v2) | `id` | `/v2/media/info/by/id?id=3685810725207115695` |
| Media endpoints (by code) | `code` | `/v2/media/info/by/code?code=DFxyz123` |
| Comment endpoints (v1/v2) | `id` | `/v2/media/comments?id=3685810725207115695` |
| Comment endpoints (gql) | `media_id` | `/gql/comments/chunk?media_id=3685810725207115695` |
| Liker endpoints (v1/v2) | `id` | `/v2/media/likers?id=3685810725207115695` |
| Search endpoints | `query` | `/v2/fbsearch/accounts?query=emma` |
| Hashtag endpoints | `name` | `/v2/hashtag/by/name?name=fitness` |
| Comment reply endpoint | `id`, `comment_id` | `/v2/media/comments/replies?id=MEDIA_ID&comment_id=COMMENT_ID` |
| Comment offensive check | `media_id`, `comment_text` | `/v2/media/comment/offensive?media_id=ID&comment_text=TEXT` |

**Critical gotcha:** Media and comment endpoints use `id` (NOT `media_id`). Using `media_id` returns `422: {"type":"missing","loc":["query","id"],"msg":"Field required"}`. The only exception is gql endpoints which use `media_id`.

## Pagination Patterns

### Chunk Endpoints (Recommended)

Most list endpoints have a `/chunk` variant that returns one page at a time:

```
GET /v2/media/comments?id=MEDIA_ID                    # First page
GET /v2/media/comments?id=MEDIA_ID&end_cursor=CURSOR   # Next page
```

Response includes pagination info:

```json
{
  "response": { ... },
  "next_page_id": "QVFBejN..."  // null when no more pages
}
```

Use `next_page_id` as the `end_cursor` for the next request.

### Chunk vs Non-Chunk

| Pattern | Returns | Cost |
|---|---|---|
| `/v1/media/comments` (deprecated) | All comments, paginated internally | 1 request per ~20 comments |
| `/v1/media/comments/chunk` | 15 comments per request | 1 request per page |
| `/v2/media/comments` | 15 comments per request | 1 request per page |

**Prefer chunk endpoints** — they give more control over pagination and cost.

### Comment Limits

- **15 comments per request** (both v1/chunk and v2)
- No way to increase page size
- Comments sorted by relevance (not chronological)
- **No deep pagination available** — practical limit is ~100-200 comments before quality degrades

### User Media Pagination

```
GET /gql/user/medias?user_id=USER_ID                    # First page (12 posts)
GET /gql/user/medias?user_id=USER_ID&end_cursor=CURSOR  # Next pages
```

The preferred endpoint for user media is `/gql/user/medias` (per deprecation warnings on `/v2/user/medias`).

### Follower/Following Pagination

```
GET /v2/user/followers?user_id=USER_ID                    # First page
GET /v2/user/followers?user_id=USER_ID&end_cursor=CURSOR  # Next pages
```

Returns ~46 followers per request per the API description.

## Response Structure

### Standard Response Wrapper

Most v2 endpoints wrap responses:

```json
{
  "response": {
    // actual data here
  },
  "next_page_id": "..." // or null
}
```

### User Response Wrapper

```json
{
  "user": {
    // user fields
  },
  "status": "ok"
}
```

### Media Response Wrapper (v2/media/info)

```json
{
  "response": {
    "items": [
      {
        "media_or_ad": {
          // media fields
        }
      }
    ]
  },
  "next_page_id": null
}
```

Note the `media_or_ad` wrapper — this is specific to `/v2/media/info/*` endpoints.

## Error Responses

| Status | Meaning |
|---|---|
| 200 | Success |
| 404 | Not found (deleted post, private account, invalid endpoint) |
| 422 | Validation error (missing/wrong parameter name) |
| 429 | Rate limited |

422 errors include helpful detail:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "id"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

## Version Priority

Based on our testing and deprecation warnings in the OpenAPI spec:

| Use Case | Preferred Endpoint | Fallback |
|---|---|---|
| User by username | `/v2/user/by/username` | `/v1/user/by/username` |
| User by ID | `/v2/user/by/id` | `/v1/user/by/id` |
| User medias | `/gql/user/medias` | `/v1/user/medias/chunk` |
| Media detail (by code) | `/v2/media/info/by/code` | `/v1/media/by/code` |
| Media detail (by ID) | `/v2/media/info/by/id` | `/v1/media/by/id` |
| Comments | `/v2/media/comments` | `/v1/media/comments/chunk` |
| Comment replies | `/v2/media/comments/replies` | none |
| Likers | `/v2/media/likers` | `/v1/media/likers` |
| Followers | `/v2/user/followers` | `/v1/user/followers/chunk` |
| Following | `/v2/user/following` | `/v1/user/following/chunk` |
| Clips/Reels | `/v2/user/clips` | `/gql/user/clips` |
| Search accounts | `/v2/fbsearch/accounts` | `/v1/search/users` (deprecated) |
| Search places | `/v3/fbsearch/places` | `/v2/fbsearch/places` |
| Search top | `/v3/fbsearch/topsearch` | `/v2/fbsearch/topsearch` |
| Reposts | `/gql/user/reposts` | none |
| Tagged media | `/v2/user/tag/medias` | `/v1/user/tag/medias/chunk` |
| User about | `/v1/user/about` | none (v1 only) |
| Media insight | `/v1/media/insight` | none (v1 only, data mostly null) |
| Stories | `/v2/user/stories` | `/v1/user/stories` |
| Highlights | `/v2/user/highlights` | `/v1/user/highlights` |

## Endpoint Naming Conventions

- `/v1/`, `/v2/`, `/v3/` — REST API versions (higher = newer, richer data)
- `/gql/` — GraphQL-backed endpoints (often richest data, different param conventions)
- `/a2/` — Alternative GraphQL user endpoint (very rich, 148KB response)
- `/sys/` — System endpoints (balance only)
- `/chunk` suffix — Paginated variant, returns one page per request
- `fbsearch` — Facebook/Meta search infrastructure endpoints
