/**
 * Blossom Tools – OpenClaw plugin
 *
 * AU creator discovery via Qdrant (semantic vector search) + OpenAI embeddings.
 * HikerAPI for live profile lookups and post media (global Instagram data).
 *
 * Required env vars (set in ~/.openclaw/.env):
 *   QDRANT_URL             – Qdrant cluster URL
 *   QDRANT_API_KEY         – Qdrant API key
 *   QDRANT_COLLECTION_NAME – collection name (default: instagram_influencers)
 *   OPENAI_API_KEY         – for text-embedding-3-small embeddings
 *   HIKER_API_KEY          – HikerAPI access key for Instagram data
 */

const API_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ToolContent {
  type: "text";
  text: string;
}

interface ToolResult {
  content: ToolContent[];
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

interface PluginConfig {
  qdrantUrl: string;
  qdrantApiKey: string;
  qdrantCollection: string;
  openaiApiKey: string;
  hikerApiKey: string;
}

let _config: PluginConfig | null = null;

const resolveConfig = (): PluginConfig => {
  if (_config) return _config;

  const hikerApiKey = process.env.HIKER_API_KEY;
  if (!hikerApiKey) {
    throw new Error("Missing required env var: HIKER_API_KEY");
  }

  _config = {
    qdrantUrl: process.env.QDRANT_URL ?? "",
    qdrantApiKey: process.env.QDRANT_API_KEY ?? "",
    qdrantCollection:
      process.env.QDRANT_COLLECTION_NAME ?? "instagram_influencers",
    openaiApiKey: process.env.OPENAI_API_KEY ?? "",
    hikerApiKey,
  };
  return _config;
};

const requireQdrant = (): {
  qdrantUrl: string;
  qdrantApiKey: string;
  qdrantCollection: string;
  openaiApiKey: string;
} => {
  const c = resolveConfig();
  if (!c.qdrantUrl || !c.qdrantApiKey) {
    throw new Error(
      "Australian creator search is unavailable — QDRANT_URL and QDRANT_API_KEY are not configured on this instance.",
    );
  }
  if (!c.openaiApiKey) {
    throw new Error(
      "Australian creator search is unavailable — OPENAI_API_KEY is not configured on this instance.",
    );
  }
  return c;
};

// ---------------------------------------------------------------------------
// Qdrant helpers
// ---------------------------------------------------------------------------

const embedQuery = async (text: string): Promise<number[]> => {
  const { openaiApiKey } = requireQdrant();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch("https://api.openai.com/v1/embeddings", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${openaiApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ model: "text-embedding-3-small", input: text }),
      signal: controller.signal,
    });

    if (!res.ok) throw new Error(`OpenAI embeddings failed: ${res.status}`);
    const data: any = await res.json();
    return data.data[0].embedding;
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Embedding request timed out.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
};

const qdrantSearch = async (
  vector: number[],
  limit: number,
  filter?: Record<string, unknown>,
): Promise<any[]> => {
  const { qdrantUrl, qdrantApiKey, qdrantCollection } = requireQdrant();

  const body: Record<string, unknown> = {
    vector,
    limit,
    with_payload: true,
    with_vector: false,
  };
  if (filter) body.filter = filter;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch(
      `${qdrantUrl}/collections/${qdrantCollection}/points/search`,
      {
        method: "POST",
        headers: {
          "api-key": qdrantApiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      },
    );

    if (!res.ok) throw new Error(`Qdrant search failed: ${res.status}`);
    const data: any = await res.json();
    return data.result ?? [];
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Qdrant search timed out.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
};

const qdrantScrollByUserId = async (userId: string): Promise<any | null> => {
  const { qdrantUrl, qdrantApiKey, qdrantCollection } = requireQdrant();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch(
      `${qdrantUrl}/collections/${qdrantCollection}/points/scroll`,
      {
        method: "POST",
        headers: {
          "api-key": qdrantApiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filter: {
            must: [{ key: "user_id", match: { value: userId } }],
          },
          limit: 1,
          with_payload: true,
          with_vector: false,
        }),
        signal: controller.signal,
      },
    );

    if (!res.ok) throw new Error(`Qdrant scroll failed: ${res.status}`);
    const data: any = await res.json();
    const points = data.result?.points ?? [];
    return points[0]?.payload ?? null;
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Qdrant lookup timed out.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
};

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

const formatFollowers = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
};

const formatQdrantCreator = (result: any): string => {
  const p = result.payload ?? result;
  const lines: string[] = [];

  const name = p.full_name || p.username || "Unknown";
  const handle = p.username ? `@${p.username}` : "";
  lines.push(`**${name}** ${handle}`.trim());

  if (p.user_id) lines.push(`ID: ${p.user_id}`);
  if (p.follower_count != null)
    lines.push(`Followers: ${formatFollowers(p.follower_count)}`);
  if (p.engagement_rate) lines.push(`Engagement: ${p.engagement_rate}`);
  if (p.niche) lines.push(`Niche: ${p.niche}`);
  if (p.age_group) lines.push(`Age Group: ${p.age_group}`);
  if (p.gender) lines.push(`Gender: ${p.gender}`);
  if (p.occupation) lines.push(`Occupation: ${p.occupation}`);
  if (p.city_name && p.city_name !== "Unknown")
    lines.push(`City: ${p.city_name}`);
  if (p.visual_aesthetic) lines.push(`Visual Style: ${p.visual_aesthetic}`);
  if (p.customer_story) lines.push(`Audience: ${p.customer_story}`);
  if (p.inferred_value_system?.length) {
    lines.push(`Values: ${(p.inferred_value_system as string[]).join(", ")}`);
  }

  return lines.join("\n");
};

// ---------------------------------------------------------------------------
// HikerAPI helper
// ---------------------------------------------------------------------------

const HIKER_API_BASE = "https://api.hikerapi.com";

const hikerCall = async (
  path: string,
  params?: Record<string, string>,
): Promise<unknown> => {
  const { hikerApiKey } = resolveConfig();

  const url = new URL(path, HIKER_API_BASE);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch(url.toString(), {
      method: "GET",
      headers: { "x-access-key": hikerApiKey },
      signal: controller.signal,
    });

    if (!res.ok) {
      const status = res.status;
      const errBody = await res.text();
      console.error(
        `[blossom-tools] HIKER GET ${path} → ${status}: ${errBody}`,
      );

      if (status === 404) {
        throw new Error(
          "Instagram user not found. Check the username and try again.",
        );
      }
      throw new Error(
        `HikerAPI request failed (status ${status}). Please try again.`,
      );
    }

    return res.json();
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("HikerAPI request timed out. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
};

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

const textResult = (text: string): ToolResult => ({
  content: [{ type: "text", text }],
});

// ---------------------------------------------------------------------------
// Plugin registration
// ---------------------------------------------------------------------------

export default {
  id: "blossom-tools",
  name: "Blossom Tools",

  register(api: any) {
    // -----------------------------------------------------------------------
    // creator_search — AU creator discovery via Qdrant
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "creator_search",
      description:
        "Search the Australian Instagram creator database (56,000+ creators) using semantic search. " +
        "Returns rich profiles including engagement_rate, niche, visual_aesthetic, customer_story, age_group, gender, and occupation. " +
        "Use for all Australian creator discovery queries. " +
        "This database ONLY contains Australian creators — for non-AU searches use web_search. " +
        "For a specific Instagram handle lookup, use creator_profile instead.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description:
              "Natural language search query (e.g. 'fitness influencers in Sydney with 50k+ followers')",
          },
          limit: {
            type: "number",
            description:
              "Maximum number of results to return (default 10, max 50)",
          },
          min_followers: {
            type: "number",
            description: "Minimum follower count filter",
          },
          max_followers: {
            type: "number",
            description: "Maximum follower count filter",
          },
        },
        required: ["query"],
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        const { query, limit = 10, min_followers, max_followers } = params;

        const vector = await embedQuery(query);

        const mustClauses: any[] = [
          // Exclude creators that have been marked as no longer found
          { key: "no_longer_found", match: { value: false } },
        ];

        if (min_followers != null || max_followers != null) {
          const range: Record<string, number> = {};
          if (min_followers != null) range.gte = min_followers;
          if (max_followers != null) range.lte = max_followers;
          mustClauses.push({ key: "follower_count", range });
        }

        const filter = { must: mustClauses };
        const results = await qdrantSearch(vector, Math.min(limit, 50), filter);

        if (results.length === 0) {
          return textResult("No creators found matching your search criteria.");
        }

        const cards = results.map(formatQdrantCreator);
        return textResult(
          `Found ${results.length} Australian creator(s):\n\n` +
            cards.join("\n---\n"),
        );
      },
    });

    // -----------------------------------------------------------------------
    // creator_get — fetch full profile from Qdrant by Instagram user ID
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "creator_get",
      description:
        "Get the full Qdrant profile for an Australian creator by their Instagram user ID. " +
        "Use the ID field from creator_search results. " +
        "Returns all available data: followers, engagement_rate, niche, visual_aesthetic, customer_story, demographics, values, and post_thumbnails. " +
        "Do NOT use this for Instagram username lookups — use creator_profile for that.",
      parameters: {
        type: "object",
        properties: {
          influencer_user_id: {
            type: "string",
            description:
              "The creator's Instagram user ID (from the 'ID:' field in creator_search results)",
          },
        },
        required: ["influencer_user_id"],
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        const { influencer_user_id } = params;

        const payload = await qdrantScrollByUserId(influencer_user_id);

        if (!payload) {
          return textResult(
            `Creator with ID ${influencer_user_id} not found in the Australian creator database.`,
          );
        }

        const lines = [formatQdrantCreator({ payload })];

        if (payload.biography) {
          lines.push(`\nBio: ${payload.biography}`);
        }

        const thumbnails: any[] = payload.post_thumbnails ?? [];
        if (thumbnails.length > 0) {
          lines.push(`\nPost thumbnails available: ${thumbnails.length} posts`);
          thumbnails.slice(0, 3).forEach((t: any, i: number) => {
            if (t.url)
              lines.push(`  ${i + 1}. ${t.url} (${t.like_count ?? 0} likes)`);
          });
        }

        return textResult(lines.join("\n"));
      },
    });

    // -----------------------------------------------------------------------
    // creator_profile (HikerAPI – global Instagram data)
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "creator_profile",
      description:
        "Look up a specific Instagram user's profile by their exact username. " +
        "Returns follower count, bio, post count, and verification status. " +
        "Use this when the user asks about a SPECIFIC Instagram account (e.g., '@therock', '50cent'). " +
        "Do NOT use this for discovering or searching for creators — use creator_search (Australian creators) " +
        "or web_search (international creators) instead. " +
        "The username should NOT include the '@' symbol.",
      parameters: {
        type: "object",
        properties: {
          username: {
            type: "string",
            description:
              "Instagram username without the @ symbol (e.g., 'therock', not '@therock')",
          },
        },
        required: ["username"],
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        const rawUsername: string = params.username;
        const username = rawUsername.replace(/^@/, "");

        const raw: any = await hikerCall("/v2/user/by/username", { username });
        const data: any = raw?.user ?? raw;

        if (!data || (!data.pk && !data.username)) {
          return textResult(
            `Could not find an Instagram account with username "${username}".`,
          );
        }

        if (data.is_private) {
          const lines: string[] = [
            `# @${data.username} (Private Account)`,
            "",
            `**${data.full_name || data.username}** has a private account.`,
          ];
          if (data.follower_count != null) {
            lines.push(`Followers: ${data.follower_count.toLocaleString()}`);
          }
          if (data.following_count != null) {
            lines.push(`Following: ${data.following_count.toLocaleString()}`);
          }
          lines.push(
            "",
            "Their posts and detailed metrics are not publicly available.",
          );
          return textResult(lines.join("\n"));
        }

        const lines: string[] = [];
        lines.push(`# @${data.username}`);
        lines.push("");

        if (data.full_name) lines.push(`**${data.full_name}**`);
        if (data.is_verified) lines.push("Verified ✓");
        if (data.biography) lines.push(`\n${data.biography}`);
        if (data.external_url) lines.push(`Link: ${data.external_url}`);

        lines.push("");
        if (data.follower_count != null)
          lines.push(`Followers: ${data.follower_count.toLocaleString()}`);
        if (data.following_count != null)
          lines.push(`Following: ${data.following_count.toLocaleString()}`);
        if (data.media_count != null)
          lines.push(`Posts: ${data.media_count.toLocaleString()}`);

        if (data.category_name) lines.push(`Category: ${data.category_name}`);
        if (data.is_business != null)
          lines.push(`Business Account: ${data.is_business ? "Yes" : "No"}`);

        return textResult(lines.join("\n"));
      },
    });

    // -----------------------------------------------------------------------
    // creator_media (HikerAPI – recent posts for an Instagram user)
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "creator_media",
      description:
        "Fetch recent Instagram posts/media for a creator. " +
        "Accepts EITHER a username OR an Instagram user ID (numeric pk). " +
        "Returns up to 12 recent posts with captions, likes, comments, media type, and timestamps. " +
        "Use this to analyse a creator's content style, posting frequency, engagement, and sponsorship activity. " +
        "If you only have a username, this tool will resolve the user ID automatically. " +
        "Do NOT scrape Instagram via web_fetch — always use this tool instead.",
      parameters: {
        type: "object",
        properties: {
          username: {
            type: "string",
            description:
              "Instagram username without @ (e.g., 'therock'). Provide this OR user_id.",
          },
          user_id: {
            type: "string",
            description:
              "Instagram numeric user ID (pk). Provide this OR username.",
          },
        },
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        let userId: string = params.user_id;

        if (!userId && params.username) {
          const username = (params.username as string).replace(/^@/, "");
          const profile: any = await hikerCall("/v2/user/by/username", {
            username,
          });
          const user = profile?.user ?? profile;
          if (!user?.pk) {
            return textResult(
              `Could not find Instagram user "${username}". Check the spelling.`,
            );
          }
          userId = String(user.pk);
        }

        if (!userId) {
          return textResult(
            "Please provide either a username or user_id parameter.",
          );
        }

        const data: any = await hikerCall("/gql/user/medias", {
          user_id: userId,
        });

        const items: any[] = data?.response?.items ?? data?.items ?? [];

        if (items.length === 0) {
          return textResult("No recent posts found for this user.");
        }

        const posts = items.slice(0, 12).map((item: any, i: number) => {
          const lines: string[] = [];
          const num = i + 1;
          const date = item.taken_at
            ? new Date(item.taken_at * 1000).toISOString().split("T")[0]
            : "unknown date";

          const mediaType =
            item.product_type === "clips"
              ? "Reel"
              : item.media_type === 8
                ? "Carousel"
                : item.media_type === 2
                  ? "Video"
                  : "Photo";

          const sponsored = item.is_paid_partnership ? " [SPONSORED]" : "";
          lines.push(`### ${num}. ${mediaType}${sponsored} — ${date}`);

          const caption = item.caption?.text;
          if (caption) {
            const truncated =
              caption.length > 200 ? caption.slice(0, 200) + "…" : caption;
            lines.push(truncated);
          }

          const metrics: string[] = [];
          if (item.like_count != null)
            metrics.push(`Likes: ${item.like_count.toLocaleString()}`);
          if (item.comment_count != null)
            metrics.push(`Comments: ${item.comment_count.toLocaleString()}`);
          if (item.play_count != null)
            metrics.push(`Views: ${item.play_count.toLocaleString()}`);
          if (item.reshare_count != null)
            metrics.push(`Shares: ${item.reshare_count.toLocaleString()}`);

          if (metrics.length > 0) lines.push(metrics.join(" | "));

          if (item.coauthor_producers?.length > 0) {
            const collabs = item.coauthor_producers
              .map((c: any) => `@${c.username}`)
              .join(", ");
            lines.push(`Collab: ${collabs}`);
          }

          if (item.usertags?.in?.length > 0) {
            const tags = item.usertags.in
              .slice(0, 5)
              .map((t: any) => `@${t.user?.username}`)
              .filter(Boolean)
              .join(", ");
            if (tags) lines.push(`Tagged: ${tags}`);
          }

          return lines.join("\n");
        });

        return textResult(
          `Recent posts (${items.length} returned):\n\n` +
            posts.join("\n---\n"),
        );
      },
    });

    api.logger.info("Blossom Tools plugin registered (4 tools)");
  },
};
