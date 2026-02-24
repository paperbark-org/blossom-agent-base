# FRONTEND.md — Blossom Frontend Integration

## Block Format for Chat Responses

When responding via HTTP chat completions (to the blossom-frontend), use **triple-colon fence blocks** to embed structured data in your responses. The frontend parses these blocks and renders them as interactive UI components.

### Format

```
:::block-type
{"key": "value", ...}
:::
```

The JSON must be valid and on a single logical block (can be multiline). Blocks MUST be surrounded by newlines.

### Available Block Types

#### `creator-table` — Grid of creator results
Use after searching for creators. The frontend renders an interactive table with shortlist buttons.

```
:::creator-table
{"creators": [
  {"handle": "glowbyjess", "name": "Jess Park", "instagramUserId": "12345", "followers": 45200, "engagement": "3.2%", "niche": "Beauty", "blossomScore": 87, "reasoning": "High engagement, authentic audience, strong beauty niche fit"},
  {"handle": "skincaresyd", "name": "Sarah Chen", "instagramUserId": "67890", "followers": 92000, "engagement": "2.8%", "niche": "Skincare", "blossomScore": 72, "reasoning": "Good reach but some bot activity"}
]}
:::
```

**Required fields:** `handle`, `name`, `followers`
**Recommended fields:** `instagramUserId`, `engagement`, `niche`, `blossomScore` (1-100), `reasoning`
**Optional fields:** `platform`, `profileUrl`, `visualAesthetic`, `customerStory`, `ageGroup`, `gender`, `occupation`, `inferredValueSystem` (string[])

#### `creator-card` — Single creator highlight
Use when focusing on one creator in detail.

```
:::creator-card
{"handle": "glowbyjess", "name": "Jess Park", "followers": "45.2K", "engagement": "3.2%", "niche": "Beauty", "avatar_url": "https://..."}
:::
```

#### `analysis-report` — Audience intelligence results
Use when showing engagement quality or audience analysis.

```
:::analysis-report
{"handle": "glowbyjess", "investment_score": 0.72, "engagement_quality": "High", "summary": "Strong organic engagement with genuine purchase intent in comments"}
:::
```

#### `shortlist-summary` — Current shortlist overview
Use when the user asks about their shortlist. Read `shortlist.csv` first, then render this block.

```
:::shortlist-summary
{"candidates": [{"name": "Jess Park", "handle": "glowbyjess"}, {"name": "Sarah Chen", "handle": "skincaresyd"}], "count": 2}
:::
```

### Best Practices

1. **Always include prose** around blocks — explain what you found, why these creators match, what to do next
2. **Use `instagramUserId`** (the `user_id` field from Qdrant) — include it when available for frontend display
3. **blossomScore** should be 1-100, where 100 = perfect match for the brief
4. **Followers** in blocks should be raw numbers (45200) not formatted strings — frontend handles formatting
5. **Don't use markdown tables** for creator results — always use `:::creator-table` blocks instead
6. **Keep reasoning concise** — 1-2 sentences explaining why this creator matches the brief

### Shortlist

Shortlisting is managed entirely by you via `shortlist.csv` in your workspace (see SOUL.md for instructions). There is no backend API for shortlisting. When users ask to add, remove, or view their shortlist, handle it yourself — do not wait for the frontend to do it.

### Scoring Creators

When returning search results, score each creator against the user's brief:
- **blossomScore 80-100:** Strong match (niche alignment + good engagement + right audience size)
- **blossomScore 60-79:** Decent match (partial niche overlap or engagement concerns)
- **blossomScore 40-59:** Weak match (tangential niche or red flags)
- **blossomScore <40:** Poor match (include only if explicitly broadening search)

Provide a 1-2 sentence `reasoning` explaining the score. Be honest about concerns (bot activity, niche drift, etc).
