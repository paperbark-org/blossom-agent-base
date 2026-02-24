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

---

## CRITICAL — Read This First

**ANY list of structured data goes in a `:::table` block. No exceptions.**

❌ NEVER output markdown tables (`| col | col |`)
❌ NEVER output bullet lists of results (`- @handle: 45K followers`)
✅ ALWAYS use `:::table` — for creators, competitors, posts, accounts, anything with rows

**Why:** The frontend can only extract data from `:::table` blocks. Markdown tables are invisible to the assets system — users can't export them, save them, or act on them.

---

## Available Block Types

### `:::table` — Any structured list

Use for **any list of rows**: creator results, competitor accounts, post rankings, audience data — anything tabular.

```
:::table
{"rows": [
  {"handle": "glowbyjess", "name": "Jess Park", "followers": 45200, "engagement": "3.2%", "niche": "Beauty", "blossomScore": 87, "reasoning": "High engagement, authentic audience"},
  {"handle": "skincaresyd", "name": "Sarah Chen", "followers": 92000, "engagement": "2.8%", "niche": "Skincare", "blossomScore": 72, "reasoning": "Good reach but some bot activity"}
]}
:::
```

**The frontend auto-renders based on field names:**
- `handle` / `username` → shown as `@handle` with avatar
- `name` → shown as display name
- `followers` → formatted as `45.2K` / `1.2M`
- `blossomScore` → colored badge (green ≥80, amber ≥60, red <60)
- `imageUrl` / `avatar_url` / `thumbnailUrl` → shown as image thumbnail
- `profileUrl` → link on the handle
- Everything else → plain text column

**Optional top-level fields:**
- `title` — heading shown above the table (e.g. `"title": "Top Food Creators in Sydney"`)

**Array key:** use `rows` (preferred), `creators`, or `items` — all accepted.

**Scoring creators:**
- blossomScore 80–100: Strong match
- blossomScore 60–79: Decent match
- blossomScore 40–59: Weak match
- blossomScore <40: Poor match (only include if broadening search)

Include a 1–2 sentence `reasoning` per row explaining the score or why this result is relevant.

---

### `:::bar-chart` — Bar chart

Use for comparing values across categories (e.g. engagement by account, post performance over time).

```
:::bar-chart
{"title": "Engagement by Account", "bars": [
  {"label": "HexClad AU", "value": 8.4},
  {"label": "Le Creuset", "value": 2.1},
  {"label": "Lodge", "value": 3.7}
]}
:::
```

---

### `:::shortlist-summary` — Current shortlist

Use when the user asks about their shortlist. Read `shortlist.csv` first, then render this block.

```
:::shortlist-summary
{"candidates": [{"name": "Jess Park", "handle": "glowbyjess"}, {"name": "Sarah Chen", "handle": "skincaresyd"}], "count": 2}
:::
```

---

## Best Practices

1. **Always include prose** around blocks — explain what you found, why these results match, what to do next
2. **Use `instagramUserId`** when available — the `user_id` field from Qdrant/HikerAPI
3. **Followers should be raw numbers** (45200 not "45.2K") — the frontend handles formatting
4. **Keep reasoning concise** — 1–2 sentences per row

## Shortlist

Shortlisting is managed entirely by you via `shortlist.csv` in your workspace (see SOUL.md for instructions). There is no backend API for shortlisting. When users ask to add, remove, or view their shortlist, handle it yourself.
