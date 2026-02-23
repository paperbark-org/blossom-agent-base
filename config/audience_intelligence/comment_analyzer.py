"""Comment quality analysis using LLM.

Samples comments from sponsored + organic posts, sends to Gemini for
quality classification, returns scores matching the frontend
EngagementQualityAnalysis contract.
"""

import json
import logging
import random
import re
from datetime import UTC, datetime
from typing import Any

from google import genai
from google.genai import types as genai_types
from hikerapi import Client as HikerClient

from api.services.audience_intelligence.roi_calculator import is_sponsored_post

logger = logging.getLogger(__name__)


class CommentAnalyzer:
    """Fetch and analyze Instagram comments for engagement quality."""

    def __init__(self, hiker_client: HikerClient, genai_client: genai.Client):
        self.hiker_client = hiker_client
        self.genai_client = genai_client
        self.model_name = "gemini-2.5-flash"

    # ------------------------------------------------------------------
    # Step 1: Fetch comments for a single post
    # ------------------------------------------------------------------

    def fetch_comments_for_post(self, media_id: str, limit: int = 20) -> list[dict]:
        """Fetch top comments for a single post via HikerAPI.

        Returns list of {text, username, like_count}.
        """
        try:
            response = self.hiker_client.media_comments_chunk_v1(id=media_id)

            # Response is [comments_list, cursor, None]
            if isinstance(response, list) and len(response) >= 1:
                raw_comments = response[0]
            else:
                raw_comments = []

            comments = []
            for c in raw_comments[:limit]:
                text = c.get("text", "").strip()
                if not text:
                    continue
                comments.append({
                    "text": text,
                    "username": c.get("user", {}).get("username", ""),
                    "like_count": c.get("like_count", 0),
                })

            logger.info(f"Fetched {len(comments)} comments for post {media_id}")
            return comments

        except Exception as e:
            logger.warning(f"Failed to fetch comments for post {media_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Step 2: Sample posts (mix of sponsored + organic)
    # ------------------------------------------------------------------

    def sample_posts(self, posts: list[dict], total: int = 5) -> list[dict]:
        """Sample a mix of sponsored and organic posts.

        Targets 2-3 sponsored + 2-3 organic for balanced quality assessment.
        """
        sponsored = [p for p in posts if is_sponsored_post(p)]
        organic = [p for p in posts if not is_sponsored_post(p)]

        # Aim for ~half sponsored, ~half organic
        n_sponsored = min(len(sponsored), total // 2 + 1)  # up to 3
        n_organic = min(len(organic), total - n_sponsored)

        # If one category is short, backfill from the other
        if n_sponsored + n_organic < total:
            n_organic = min(len(organic), total - n_sponsored)
        if n_sponsored + n_organic < total:
            n_sponsored = min(len(sponsored), total - n_organic)

        sampled = []
        if sponsored:
            sampled.extend(random.sample(sponsored, min(n_sponsored, len(sponsored))))
        if organic:
            sampled.extend(random.sample(organic, min(n_organic, len(organic))))

        logger.info(
            f"Sampled {len(sampled)} posts "
            f"({sum(1 for p in sampled if is_sponsored_post(p))} sponsored, "
            f"{sum(1 for p in sampled if not is_sponsored_post(p))} organic)"
        )
        return sampled

    # ------------------------------------------------------------------
    # Step 3: Collect comments from sampled posts
    # ------------------------------------------------------------------

    def collect_comments(
        self,
        posts: list[dict],
        post_ids: list[str] | None = None,
        comments_per_post: int = 20,
    ) -> tuple[list[dict], int]:
        """Fetch comments from posts, return (all_comments, posts_analyzed).

        If post_ids provided, use those specific posts. Otherwise sample.
        """
        if post_ids:
            # Use specific posts requested by frontend
            target_posts = []
            pk_to_post = {str(p.get("pk", "")): p for p in posts}
            id_to_post = {str(p.get("id", "")): p for p in posts}
            for pid in post_ids:
                post = pk_to_post.get(pid) or id_to_post.get(pid)
                if post:
                    target_posts.append(post)
            if not target_posts:
                target_posts = self.sample_posts(posts)
        else:
            target_posts = self.sample_posts(posts)

        all_comments = []
        posts_with_comments = 0

        for post in target_posts:
            media_id = str(post.get("pk") or post.get("id", ""))
            if not media_id:
                continue

            comments = self.fetch_comments_for_post(media_id, limit=comments_per_post)
            if comments:
                posts_with_comments += 1
                all_comments.extend(comments)

        return all_comments, posts_with_comments

    # ------------------------------------------------------------------
    # Step 4: LLM analysis
    # ------------------------------------------------------------------

    def analyze_comment_quality(self, comments: list[dict]) -> dict[str, Any]:
        """Send comments to Gemini for quality classification.

        Returns dict matching EngagementQualityStats contract.
        """
        comment_texts = [c["text"] for c in comments[:50]]
        prompt = self._build_prompt(comment_texts)

        logger.info(f"Sending {len(comment_texts)} comments to Gemini for quality analysis")

        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=[prompt],
            config=genai_types.GenerateContentConfig(
                safety_settings=[
                    genai_types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_ONLY_HIGH",
                    ),
                ],
            ),
        )

        return self._parse_response(response.text, len(comment_texts))

    @staticmethod
    def _sanitize_comment(text: str, max_length: int = 500) -> str:
        """Sanitize a comment for safe LLM input."""
        # Strip control characters (keep newlines and spaces)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text.strip()

    def _build_prompt(self, comments: list[str]) -> str:
        sanitized = [self._sanitize_comment(c) for c in comments if c.strip()]
        comments_block = "\n".join(f"- {c}" for c in sanitized)

        return f"""Analyze these {len(sanitized)} Instagram comments for engagement quality.

COMMENTS:
{comments_block}

Classify each comment into EXACTLY ONE category:
1. **genuine** - Thoughtful, specific, personal reactions (e.g. "Love how you styled this with the boots!", "This recipe changed my dinner routine")
2. **question** - Asking questions about content, products, or the creator (e.g. "Where did you get that?", "What shade is that lipstick?")
3. **buying_intent** - Showing purchase interest (e.g. "Need this!", "Just ordered", "Link?", "How much?", "Where to buy?")
4. **bot** - Generic/spam/single emoji/low-effort (e.g. "🔥", "Nice!", "Beautiful", "👏👏👏", "Check my page")

Return ONLY valid JSON with these exact fields (percentages must sum to 100):
{{
  "genuine_percent": <number 0-100>,
  "question_percent": <number 0-100>,
  "buying_intent_percent": <number 0-100>,
  "bot_percent": <number 0-100>
}}

Return ONLY the JSON object, no markdown fences, no explanation."""

    def _parse_response(self, text: str, total_comments: int) -> dict[str, Any]:
        """Parse Gemini response into EngagementQualityStats fields."""
        cleaned = text.strip()

        # Strip markdown fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Gemini response: {cleaned[:200]}")
            return {
                "genuine_percent": 0,
                "question_percent": 0,
                "buying_intent_percent": 0,
                "bot_percent": 0,
            }

        return {
            "genuine_percent": round(float(data.get("genuine_percent", 0)), 1),
            "question_percent": round(float(data.get("question_percent", 0)), 1),
            "buying_intent_percent": round(float(data.get("buying_intent_percent", 0)), 1),
            "bot_percent": round(float(data.get("bot_percent", 0)), 1),
        }

    # ------------------------------------------------------------------
    # Public API: Full pipeline
    # ------------------------------------------------------------------

    def analyze(
        self,
        posts: list[dict],
        post_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run full engagement quality analysis.

        Returns dict matching frontend EngagementQualityAnalysis type:
        {
            "stats": { ... EngagementQualityStats ... },
            "analyzed_at": "ISO timestamp"
        }
        """
        comments, posts_analyzed = self.collect_comments(posts, post_ids=post_ids)

        if len(comments) < 5:
            logger.warning(f"Insufficient comments ({len(comments)}) for quality analysis")
            return {
                "stats": None,
                "analyzed_at": datetime.now(UTC).isoformat(),
                "insufficient_data": True,
                "message": f"Only {len(comments)} comments available, need at least 5",
            }

        quality_scores = self.analyze_comment_quality(comments)

        return {
            "stats": {
                "posts_analyzed": posts_analyzed,
                "total_comments_sampled": len(comments),
                **quality_scores,
            },
            "analyzed_at": datetime.now(UTC).isoformat(),
        }
