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

const API_TIMEOUT_MS = 10_000;

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
        const shortlisted = data.is_shortlisted ? " (shortlisted)" : "";

        const lines: string[] = [];
        lines.push(
          `# ${profile.full_name || profile.username || influencer_user_id}${shortlisted}`,
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
    // shortlist_list
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "shortlist_list",
      description:
        "Get the current user's shortlisted creators. " +
        "Returns all creators the user has saved to their shortlist with profile details.",
      parameters: {
        type: "object",
        properties: {},
      },

      async execute(_id: string, _params: any): Promise<ToolResult> {
        const data: any = await apiCall("GET", "/shortlist");
        const entries: any[] = data.entries ?? [];

        if (entries.length === 0) {
          return textResult(
            "Your shortlist is empty. Use creator_search to find creators and shortlist_add to save them.",
          );
        }

        const lines: string[] = [
          `You have ${entries.length} creator(s) shortlisted:\n`,
        ];

        for (const entry of entries) {
          const inf = entry.influencer;
          if (inf) {
            const name =
              inf.full_name || inf.username || entry.influencer_user_id;
            const handle = inf.username ? ` (@${inf.username})` : "";
            const followers = inf.follower_count
              ? ` – ${inf.follower_count.toLocaleString()} followers`
              : "";
            lines.push(`- **${name}**${handle}${followers}`);
          } else {
            lines.push(`- ${entry.influencer_user_id}`);
          }

          if (entry.notes) {
            lines.push(`  Notes: ${entry.notes}`);
          }
        }

        return textResult(lines.join("\n"));
      },
    });

    // -----------------------------------------------------------------------
    // shortlist_add
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "shortlist_add",
      description:
        "Add a creator to the current user's shortlist. " +
        "Use the ID field from creator_search results as the influencer_user_id. " +
        "Optionally include notes about why they were shortlisted.",
      parameters: {
        type: "object",
        properties: {
          influencer_user_id: {
            type: "string",
            description:
              "The creator's ID (from the 'ID:' field in creator_search results)",
          },
          notes: {
            type: "string",
            description:
              "Optional notes about why this creator was shortlisted",
          },
        },
        required: ["influencer_user_id"],
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        const { influencer_user_id, notes } = params;

        const body: Record<string, unknown> = { influencer_user_id };
        if (notes) body.notes = notes;

        const data: any = await apiCall("POST", "/shortlist", body);

        const name =
          data.influencer?.full_name ||
          data.influencer?.username ||
          influencer_user_id;

        return textResult(`Added **${name}** to your shortlist.`);
      },
    });

    // -----------------------------------------------------------------------
    // shortlist_remove
    // -----------------------------------------------------------------------
    api.registerTool({
      name: "shortlist_remove",
      description:
        "Remove a creator from the current user's shortlist. " +
        "Use the ID field from creator_search or shortlist_list results.",
      parameters: {
        type: "object",
        properties: {
          influencer_user_id: {
            type: "string",
            description:
              "The creator's ID (from the 'ID:' field in search or shortlist results)",
          },
        },
        required: ["influencer_user_id"],
      },

      async execute(_id: string, params: any): Promise<ToolResult> {
        const { influencer_user_id } = params;

        await apiCall(
          "DELETE",
          `/shortlist/${encodeURIComponent(influencer_user_id)}`,
        );

        return textResult(`Removed from your shortlist.`);
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

    api.logger.info("Blossom Tools plugin registered (6 tools)");
  },
};
