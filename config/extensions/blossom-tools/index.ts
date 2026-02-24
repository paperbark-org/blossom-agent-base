/**
 * Blossom Tools – OpenClaw plugin
 *
 * Registers agent tools that proxy requests to the Blossom FastAPI
 * /internal/* endpoints. Each OpenClaw instance is provisioned per-user,
 * so the user identity is fixed via BLOSSOM_USER_ID env var — the LLM
 * never controls identity.
 *
 * Required env vars (set in ~/.openclaw/.env):
 *   BLOSSOM_API_URL        – FastAPI base URL (no trailing slash)
 *   BLOSSOM_INTERNAL_KEY   – shared secret for x-internal-key header
 *   BLOSSOM_USER_ID        – Clerk user ID for this instance's owner
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

/** Shape returned by POST /search (UnapprovedCandidate). */
interface CreatorCard {
  name?: string;
  handle?: string;
  instagramUserId?: string;
  followers?: number;
  engagementRate?: string;
  niche?: string;
  country?: string;
}

// ---------------------------------------------------------------------------
// Config (resolved once at load time)
// ---------------------------------------------------------------------------

interface PluginConfig {
  apiUrl: string;
  internalKey: string;
  userId: string;
  hikerApiKey: string;
}

let _config: PluginConfig | null = null;

const resolveConfig = (): PluginConfig => {
  if (_config) return _config;

  const apiUrl = process.env.BLOSSOM_API_URL;
  const internalKey = process.env.BLOSSOM_INTERNAL_KEY;
  const userId = process.env.BLOSSOM_USER_ID;
  const hikerApiKey = process.env.HIKER_API_KEY;

  if (!apiUrl || !internalKey || !userId) {
    throw new Error(
      "Missing required env vars: BLOSSOM_API_URL, BLOSSOM_INTERNAL_KEY, BLOSSOM_USER_ID",
    );
  }

  if (!hikerApiKey) {
    throw new Error("Missing required env var: HIKER_API_KEY");
  }

  _config = { apiUrl, internalKey, userId, hikerApiKey };
  return _config;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const apiCall = async (
  method: string,
  path: string,
  body?: Record<string, unknown>,
): Promise<unknown> => {
  const { apiUrl, internalKey, userId } = resolveConfig();

  const url = `${apiUrl}/api/v1/internal${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "x-internal-key": internalKey,
    "x-user-id": userId,
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    if (!res.ok) {
      const status = res.status;
      const errBody = await res.text();
      console.error(
        `[blossom-tools] ${method} ${path} → ${status}: ${errBody}`,
      );
      throw new Error(`Request failed (status ${status}). Please try again.`);
    }

    return res.json();
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
};

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

const formatCreatorCard = (c: CreatorCard): string => {
  const lines: string[] = [];
  const name = c.name || c.handle || "Unknown";
  const handle = c.handle ? `@${c.handle}` : "";

  lines.push(`**${name}** ${handle}`);

  if (c.instagramUserId) {
    lines.push(`ID: ${c.instagramUserId}`);
  }

  if (c.followers != null) {
    const formatted =
      c.followers >= 1_000_000
        ? `${(c.followers / 1_000_000).toFixed(1)}M`
        : c.followers >= 1_000
          ? `${(c.followers / 1_000).toFixed(1)}K`
          : `${c.followers}`;
    lines.push(`Followers: ${formatted}`);
  }

  if (c.engagementRate) {
    lines.push(`Engagement: ${c.engagementRate}`);
  }

  if (c.niche) {
    lines.push(`Niche: ${c.niche}`);
  }

  if (c.country) {
    lines.push(`Location: ${c.country}`);
  }

  return lines.join("\n");
};

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
    // creator_search
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "creator_search",
      description:
        "Search for Australian creators/influencers matching a natural language query. " +
        "Returns a list of matching creator profiles with handles, follower counts, and niches. " +
        "Use this for discovery queries like 'fitness influencers in Sydney'. " +
        "This tool ONLY searches the Australian creator database. " +
        "For international/non-AU creators, use web_search instead. " +
        "For looking up a specific Instagram handle, use creator_profile instead.",
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
        const { query, limit, min_followers, max_followers } = params;

        const body: Record<string, unknown> = { query };
        if (limit != null) body.limit = limit;
        if (min_followers != null) body.min_followers = min_followers;
        if (max_followers != null) body.max_followers = max_followers;

        const data: any = await apiCall("POST", "/search", body);
        const candidates: CreatorCard[] = data.candidates ?? [];

        if (candidates.length === 0) {
          return textResult("No creators found matching your search criteria.");
        }

        const cards = candidates.map(formatCreatorCard);
        return textResult(
          `Found ${candidates.length} creator(s):\n` + cards.join("\n---\n"),
        );
      },
    });

    // -----------------------------------------------------------------------
    // creator_get
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "creator_get",
      description:
        "Get the full profile for an Australian creator by their internal ID. " +
        "Use the ID field from creator_search results. " +
        "Returns detailed profile information including followers, niche, age group, and gender. " +
        "Do NOT use this for Instagram usernames — use creator_profile for that.",
      parameters: {
        type: "object",
        properties: {
          influencer_user_id: {
            type: "string",
            description:
              "The creator's ID (from the 'ID:' field in creator_search results)",
          },
        },
        required: ["influencer_user_id"],
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        const { influencer_user_id } = params;

        const data: any = await apiCall(
          "GET",
          `/creator/${encodeURIComponent(influencer_user_id)}`,
        );

        const profile = data.creator;

        const lines: string[] = [];
        lines.push(
          `# ${profile.full_name || profile.username || influencer_user_id}`,
        );

        if (profile.username) lines.push(`Handle: @${profile.username}`);
        if (profile.follower_count != null)
          lines.push(`Followers: ${profile.follower_count.toLocaleString()}`);
        if (profile.niche) lines.push(`Niche: ${profile.niche}`);
        if (profile.age_group) lines.push(`Age Group: ${profile.age_group}`);
        if (profile.gender) lines.push(`Gender: ${profile.gender}`);
        if (profile.occupation) lines.push(`Occupation: ${profile.occupation}`);

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
        // HikerAPI wraps the profile in a "user" key
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

        // Resolve username → user_id if needed
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
