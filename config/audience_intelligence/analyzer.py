"""Instagram audience intelligence analyzer using Google Gemini."""

import asyncio
import json
import logging
import os
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
import httpx
from hikerapi import Client
from PIL import Image, UnidentifiedImageError

from agent.config import settings
from api.services.audience_intelligence.image_store import persist_profile_pic, persist_thumbnails
from api.services.audience_intelligence.roi_calculator import calculate_roi_score
from api.services.audience_intelligence.trust_analyzer import analyze_trust, fetch_user_about

logger = logging.getLogger(__name__)

# Instagram media type constants
MEDIA_TYPE_IMAGE = 1
MEDIA_TYPE_VIDEO = 2
MEDIA_TYPE_CAROUSEL = 8

# Default configuration values
DEFAULT_MAX_IMAGE_SIZE = (512, 512)
DEFAULT_IMAGE_QUALITY = 75
DEFAULT_VIDEO_MAX_DURATION = 10
DEFAULT_VIDEO_FPS = 1
DEFAULT_USER_INACTIVE_DAYS = 30
DEFAULT_RATE_DELAY = 0.09


class UserNotFoundError(Exception):
    """Raised when an Instagram user is not found or cannot be accessed."""


class UserInactiveError(Exception):
    """Raised when a user has not posted recently (inactive account)."""


class APITimeoutError(Exception):
    """Raised when the API request times out."""


class AudienceIntelligenceAnalyzer:
    """Fetch Instagram posts and analyze with Gemini for audience intelligence."""

    def __init__(self, hikerapi_token: str | None = None, gemini_api_key: str | None = None):
        """Initialize the analyzer."""
        token = hikerapi_token or settings.HIKER_API_KEY
        if not token:
            raise ValueError("HIKER_API_KEY is required")

        self.hiker_client = Client(token=token)

        api_key = gemini_api_key or getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")

        # Initialize the new google-genai client
        self.genai_client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"

        # Configure safety settings to be less restrictive for demographic analysis
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_ONLY_HIGH",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_MEDIUM_AND_ABOVE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ]

        self.rate_delay = DEFAULT_RATE_DELAY
        self.max_image_size = DEFAULT_MAX_IMAGE_SIZE
        self.image_quality = DEFAULT_IMAGE_QUALITY
        self.video_max_duration = DEFAULT_VIDEO_MAX_DURATION
        self.video_fps = DEFAULT_VIDEO_FPS

    def fetch_user_data(self, username: str) -> dict:
        """Fetch user profile data by username."""
        try:
            response = self.hiker_client.user_by_username_v2(username)

            if not response:
                raise UserNotFoundError(f"User {username} not found - empty response")

            if isinstance(response, dict) and "user" not in response:
                if "error" in response or "message" in response:
                    error_msg = response.get("error") or response.get("message", "Unknown error")
                    raise UserNotFoundError(f"User {username} not found - {error_msg}")
                raise UserNotFoundError(f"User {username} not found")

            return response["user"]

        except UserNotFoundError:
            raise
        except (TimeoutError, httpx.TimeoutException, httpx.ReadTimeout) as e:
            raise APITimeoutError(f"API request timed out for user {username}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "timed out" in error_msg:
                raise APITimeoutError(f"API request timed out for user {username}") from e
            raise UserNotFoundError(f"User {username} not found - API error: {e}") from e

    def _has_posted_recently(self, posts: list[dict], days: int | None = None) -> bool:
        """Check if user has posted within the last X days."""
        if not posts:
            return False

        if days is None:
            days = DEFAULT_USER_INACTIVE_DAYS

        now = datetime.now(tz=UTC)
        x_days_ago = now.timestamp() - (days * 24 * 60 * 60)

        for post in posts:
            taken_at_ts = post.get("taken_at_ts")
            if taken_at_ts and taken_at_ts >= x_days_ago:
                return True

        return False

    def fetch_posts(self, user_id: str, count: int = 100) -> list[dict]:
        """Fetch user posts with pagination support."""
        try:
            all_posts: list[dict] = []
            end_cursor = None
            max_pages = 5  # Safety limit to avoid infinite loops

            for _ in range(max_pages):
                response = self.hiker_client.user_medias_chunk_v1(
                    user_id=user_id, end_cursor=end_cursor
                )

                items: Sequence[dict] = []

                if isinstance(response, list):
                    items = response[0] if response and isinstance(response[0], list) else response
                    # Check for cursor in tuple response
                    if len(response) > 1:
                        end_cursor = response[1] if response[1] else None
                elif isinstance(response, dict):
                    items = response.get("items", [])
                    end_cursor = response.get("end_cursor") or response.get("next_max_id")

                if not items:
                    break

                all_posts.extend(items)

                # Stop if we have enough posts or no more pages
                if len(all_posts) >= count or not end_cursor:
                    break

            if not all_posts:
                return []

            posts_list = list(all_posts[:count])
            if not self._has_posted_recently(posts_list):
                raise UserInactiveError(
                    f"User has not posted in the last {DEFAULT_USER_INACTIVE_DAYS} days"
                )

            logger.info(f"Fetched {len(posts_list)} posts for user {user_id}")
            return posts_list
        except UserInactiveError:
            raise
        except (TimeoutError, httpx.TimeoutException, httpx.ReadTimeout) as e:
            raise APITimeoutError(f"API timeout fetching posts for user {user_id}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                raise APITimeoutError(f"API timeout fetching posts for user {user_id}") from e
            logger.error(f"Error fetching posts for user_id {user_id}: {e}")
            return []

    def _parse_timestamp(self, post: dict) -> datetime | None:
        """Convert timestamp fields into a timezone-aware datetime."""
        ts = post.get("taken_at_ts")
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=UTC)

        raw = post.get("taken_at")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                pass

        return None

    def _resolve_caption(self, post: dict) -> str:
        """Return the best available caption text."""
        caption_dict = post.get("caption")
        if isinstance(caption_dict, dict):
            text = caption_dict.get("text")
            if text:
                return self._sanitize_caption(text)

        text = post.get("caption_text")
        if isinstance(text, str) and text.strip():
            return self._sanitize_caption(text)

        text = post.get("title")
        if isinstance(text, str) and text.strip():
            return self._sanitize_caption(text)

        return "No caption"

    def _sanitize_caption(self, caption: str) -> str:
        """Sanitize caption text."""
        if not caption:
            return "No caption"

        import re

        max_length = 2000
        if len(caption) > max_length:
            caption = caption[:max_length] + "..."

        caption = re.sub(r"([!?@#$%^&*])\1{3,}", r"\1\1", caption)
        return caption.strip()

    def _resolve_media_url(self, post: dict, media_type: int) -> str | None:
        """Find the first playable/viewable URL."""
        source: dict = post.get("_resource", post)

        if media_type == MEDIA_TYPE_IMAGE:
            candidates = source.get("image_versions2", {}).get("candidates")
            if candidates:
                return candidates[0].get("url")
            image_versions = source.get("image_versions", [])
            if image_versions and isinstance(image_versions, list):
                return image_versions[0].get("url")

        elif media_type == MEDIA_TYPE_VIDEO:
            versions = source.get("video_versions", [])
            if versions:
                return versions[0].get("url")

        thumbnail = source.get("thumbnail_url")
        if isinstance(thumbnail, str):
            return thumbnail

        return None

    def format_post_data(self, post: dict | None, media_type_name: str) -> dict | None:
        """Normalize post data for downstream processing."""
        if not post:
            return None

        resource = post.get("_resource")
        media_type = (resource or post).get("media_type")

        post_date = self._parse_timestamp(post)
        media_url = self._resolve_media_url(post, media_type)

        location = post.get("location")
        location_name = None
        if location and isinstance(location, dict):
            location_name = location.get("name") or location.get("city")

        caption = self._resolve_caption(post)

        formatted_data = {
            "type": media_type_name,
            "media_type": media_type,
            "post_id": post.get("id"),
            "code": post.get("code"),
            "taken_at": post_date.isoformat() if post_date else "Unknown",
            "caption": caption,
            "like_count": post.get("like_count", 0),
            "comment_count": post.get("comment_count", 0),
            "play_count": post.get("play_count", 0),
            "view_count": post.get("view_count", 0),
            "media_url": media_url,
        }

        if location_name:
            formatted_data["location"] = location_name

        return formatted_data

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image to max dimensions while maintaining aspect ratio."""
        image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
        return image

    def _compress_image(self, image: Image.Image) -> bytes:
        """Compress image to JPEG with specified quality."""
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(
                image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None
            )
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=self.image_quality, optimize=True)
        return buffer.getvalue()

    def download_image(self, url: str) -> tuple[bytes | None, str | None, Image.Image | None]:
        """Download and compress an image to reduce token usage."""
        if not url:
            return None, None, None

        try:
            response = httpx.get(url, timeout=60.0, follow_redirects=True)
            response.raise_for_status()

            data = response.content
            image = Image.open(BytesIO(data))
            image = self._resize_image(image)
            compressed_data = self._compress_image(image)
            return compressed_data, "image/jpeg", image
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None, None, None

    def _extract_video_frames(self, video_path: str) -> list[Image.Image]:
        """Extract frames from video at specified FPS."""
        try:
            import cv2
        except ImportError as e:
            raise ImportError("opencv-python is required for video processing") from e

        frames = []
        cap = cv2.VideoCapture(video_path)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            max_frames = min(
                int(self.video_max_duration * self.video_fps), int(duration * self.video_fps)
            )
            frame_interval = int(fps / self.video_fps) if self.video_fps > 0 else int(fps)

            frame_count = 0
            extracted = 0

            while extracted < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    frames.append(pil_image)
                    extracted += 1

                frame_count += 1
        finally:
            cap.release()

        return frames

    def download_video(self, url: str) -> tuple[bytes | None, str | None]:
        """Download video and extract representative frames."""
        if not url:
            return None, None

        tmp_path = None
        try:
            with httpx.Client(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()
                video_data = response.content

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(video_data)
                tmp_path = tmp_file.name

            frames = self._extract_video_frames(tmp_path)

            if not frames:
                return None, None

            middle_frame = frames[len(frames) // 2]
            middle_frame = self._resize_image(middle_frame)
            compressed_data = self._compress_image(middle_frame)

            return compressed_data, "image/jpeg"
        except Exception as e:
            logger.error(f"Error processing video from {url}: {e}")
            return None, None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def _build_prompt(
        self,
        user_data: dict,
        image_post: dict | None,
        video_post: dict | None,
        all_image_posts: list[dict] | None = None,
        all_video_posts: list[dict] | None = None,
    ) -> str:
        """Create a single prompt for Gemini with structured instructions."""

        def format_post(post: dict | None) -> str:
            if not post:
                return "null"

            post_data = {
                "post_id": post.get("post_id") or post.get("code", ""),
                "type": post["type"],
                "taken_at": post["taken_at"],
                "media_type": post["media_type"],
                "caption": post["caption"],
                "like_count": post["like_count"],
                "comment_count": post["comment_count"],
            }

            if post.get("play_count"):
                post_data["play_count"] = post["play_count"]
            if post.get("view_count"):
                post_data["view_count"] = post["view_count"]
            if post.get("location"):
                post_data["location"] = post["location"]

            return json.dumps(post_data, ensure_ascii=False, indent=2)

        follower_count = user_data.get("follower_count", 0)
        avg_engagement = 0
        post_count = 0

        all_posts = (all_image_posts or []) + (all_video_posts or [])
        if all_posts and follower_count > 0:
            for post in all_posts:
                if post:
                    avg_engagement += post.get("like_count", 0) + post.get("comment_count", 0)
                    post_count += 1

            if post_count > 0:
                avg_engagement = (avg_engagement / post_count / follower_count) * 100
                engagement_context = (
                    f"Average engagement rate from {post_count} recent posts: {avg_engagement:.2f}%"
                )
            else:
                engagement_context = "Insufficient data to calculate engagement rate."
        else:
            engagement_context = "Insufficient data to calculate engagement rate."

        additional_context = ""
        if all_image_posts and len(all_image_posts) > 1:
            additional_context += "\n\nAdditional recent image posts (for pattern analysis):\n"
            for i, post in enumerate(all_image_posts[1:], start=2):
                if post:
                    additional_context += f"Image Post {i}: {format_post(post)}\n"

        if all_video_posts and len(all_video_posts) > 1:
            additional_context += "\n\nAdditional recent video posts (for pattern analysis):\n"
            for i, post in enumerate(all_video_posts[1:], start=2):
                if post:
                    additional_context += f"Video Post {i}: {format_post(post)}\n"

        prompt = f"""
You are given Instagram account data of an influencer for demographic and marketing analysis.

Here is their profile details:
{json.dumps({
    "id": user_data.get("id"),
    "username": user_data.get("username"),
    "full_name": user_data.get("full_name"),
    "biography": user_data.get("biography"),
    "follower_count": user_data.get("follower_count"),
    "following_count": user_data.get("following_count"),
    "media_count": user_data.get("media_count"),
    "is_private": user_data.get("is_private"),
    "is_verified": user_data.get("is_verified"),
}, ensure_ascii=False, indent=2)}

Here is their most recent image post with engagement metrics:
{format_post(image_post)}

Here is their most recent video post with engagement metrics:
{format_post(video_post)}
{additional_context}

ENGAGEMENT CONTEXT:
{engagement_context}

TASK:
Analyze the influencer's profile, post content (both visual and captions), engagement metrics, and location data to provide a comprehensive demographic and marketing analysis.

Pay special attention to:
- Engagement rates (likes, comments, views, plays) relative to follower count
- Themes, topics, hashtags, and tone in captions
- Visual style, aesthetic, and content quality of posts
- Biography, how they position themselves, and any business indicators
- Location tags which may indicate their geographic base
- Posting frequency and consistency (if inferable from timestamps)
- UGC (User-Generated Content) indicators: Do they create authentic, relatable content that brands might use? Look for natural product features, unboxing, reviews, testimonials, or lifestyle content.

Provide your analysis strictly in valid JSON with this schema:

{{
  "UserAccountAnalysis": {{
    "instagram_account_type": "personal" | "influencer" | "business",
    "visual_aesthetic": "detailed description of visual aesthetic based on posts",
    "niche": "main niche (single value): fitness, travel, food, fashion, beauty, lifestyle, parenting, tech, etc.",
    "sub_niche": ["sub-niche1", "sub-niche2", "..."],
    "customer_story": "narrative of their target customer/audience based on content and positioning",
    "age_group": "<18" | "18-24" | "25-34" | "35-44" | "45-54" | "55-64" | "65+" | "Unknown",
    "gender": "Male" | "Female" | "Non-binary" | "Unknown",
    "occupation": "inferred occupation from bio and content",
    "inferred_value_system": ["value1", "value2", "..."],
    "country": "Full country name (e.g., 'Australia', 'United States', 'United Kingdom')",
    "content_details": "detailed description of content type, style, and format. Add what the image and video post had in detail too when available, describe the post.",
    "engagement_rate": "estimated engagement rate as percentage (e.g., '4.5%')",
    "description_of_influencer": "comprehensive description of the influencer's brand, persona, how they look, and their content style",
    "description_of_audience": "detailed description of their audience demographics and psychographics",
    "is_au": true | false,
    "is_ugc_creator": true | false,
    "additional_context": "any other relevant context or observations"
  }},
  "IntentAnalysis": {{
    "intent_scores": [
      {{ "category": "product_discovery", "score": 0.0, "reasoning": "Why followers come for product recommendations" }},
      {{ "category": "education_learning", "score": 0.0, "reasoning": "Why followers come to learn" }},
      {{ "category": "entertainment", "score": 0.0, "reasoning": "Why followers come for entertainment" }},
      {{ "category": "lifestyle_aspiration", "score": 0.0, "reasoning": "Why followers aspire to this lifestyle" }},
      {{ "category": "community_identity", "score": 0.0, "reasoning": "Why followers identify with this community" }},
      {{ "category": "news_updates", "score": 0.0, "reasoning": "Why followers come for news/updates" }}
    ],
    "content_labels": [
      {{ "post_id": "post_id_here", "content_label": "product_review|tutorial|lifestyle_ootd|brand_partnership|personal_vlog|entertainment|educational|behind_the_scenes|giveaway_promo|other", "confidence": 0.0 }}
    ],
    "content_intent_alignments": [
      {{ "content_label": "label", "dominant_intent": "category", "intent_score": 0.0, "insight": "How this content type drives this intent" }}
    ]
  }}
}}

IMPORTANT INSTRUCTIONS:
- Output ONLY valid JSON. No markdown fences, explanatory text, or backticks.
- ALL fields must be present. Use null for undeterminable optional fields, empty arrays [] for lists, empty string "" for required strings.
- Base analysis on provided data: profile, bio, posts, captions, engagement metrics, visual content, and location tags.
- For engagement_rate: Calculate as (average likes + comments) / followers * 100, or estimate from provided metrics.
- For is_ugc_creator: Determine if they create authentic, brand-friendly content that companies could use in marketing.
- For country/is_au: Use bio text, location tags, content references, language/slang, and visual cues.

INTENT ANALYSIS INSTRUCTIONS:
- intent_scores: Score each category 0.0-1.0 based on WHY followers engage. All 6 categories must be present:
  * product_discovery: Do followers come for product recommendations, reviews, or shopping inspiration?
  * education_learning: Do followers come to learn skills, tips, or knowledge?
  * entertainment: Do followers come purely for entertainment, humor, or fun?
  * lifestyle_aspiration: Do followers aspire to this creator's lifestyle, aesthetic, or status?
  * community_identity: Do followers feel part of a community or identity group?
  * news_updates: Do followers come for news, updates, or timely information?
- content_labels: Label EACH post provided using its post_id field. Use the EXACT post_id value from the post data. One of: product_review, tutorial, lifestyle_ootd, brand_partnership, personal_vlog, entertainment, educational, behind_the_scenes, giveaway_promo, other
- content_intent_alignments: For each unique content_label used, specify which intent category it primarily drives
"""
        return prompt.strip()

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove optional ``` ``` wrappers from the model output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.lstrip("`\n")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.lstrip("\n")
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].rstrip()
        return cleaned

    def _parse_json_response(self, text: str) -> dict:
        if not text or not text.strip():
            return {}

        cleaned = self._strip_markdown_fences(text)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.exception(f"Gemini response was not valid JSON: {cleaned[:200]}")
            raise ValueError("Invalid JSON response") from exc

        return data

    async def analyze_user(self, username: str, max_posts_per_type: int = 3) -> dict:
        """Analyze a user's Instagram profile and posts."""
        try:
            user_data = await asyncio.to_thread(self.fetch_user_data, username)
        except UserNotFoundError as exc:
            return self._error_response("user_not_found", str(exc))
        except APITimeoutError as exc:
            return self._error_response("api_timeout", str(exc), retryable=True)

        try:
            posts = await asyncio.to_thread(self.fetch_posts, user_data["id"])
        except UserInactiveError as exc:
            return self._error_response("user_inactive", str(exc))
        except APITimeoutError as exc:
            return self._error_response("api_timeout", str(exc), retryable=True)

        image_posts, video_posts = self._select_post_samples(posts, max_posts_per_type)

        image_post_raw = image_posts[0] if image_posts else None
        video_post_raw = video_posts[0] if video_posts else None
        image_post_data = self.format_post_data(image_post_raw, "Image")
        video_post_data = self.format_post_data(video_post_raw, "Video")
        all_image_posts = [self.format_post_data(p, "Image") for p in image_posts]
        all_video_posts = [self.format_post_data(p, "Video") for p in video_posts]

        media_assets = await asyncio.to_thread(
            self._prepare_media_assets, image_post_data, video_post_data
        )
        post_context = {
            "image_post": image_post_data,
            "video_post": video_post_data,
            "all_image_posts": all_image_posts,
            "all_video_posts": all_video_posts,
        }

        analysis_json = await asyncio.to_thread(
            self._run_analysis_with_media_fallback,
            username,
            user_data,
            post_context,
            media_assets,
        )

        # Calculate ROI score from engagement signals
        roi_data = calculate_roi_score(posts, user_data)

        # Fetch user_about for trust signals
        user_id = user_data.get("pk") or user_data.get("id")
        user_about = await asyncio.to_thread(
            fetch_user_about, self.hiker_client, user_id
        )

        # Calculate trust score
        trust_data = analyze_trust(user_data, posts, user_about)

        # Persist images to GCS so CDN URLs don't expire.
        # Failures here must not break the analysis — fall back to CDN URLs.
        original_profile_url = user_data.get("profile_pic_url_hd") or user_data.get("profile_pic_url")
        profile_pic_url = original_profile_url
        try:
            gcs_profile_url = await asyncio.to_thread(
                persist_profile_pic, original_profile_url, username
            )
            if gcs_profile_url:
                profile_pic_url = gcs_profile_url
        except Exception:
            logger.warning("GCS profile pic persistence failed for %s, using CDN URL", username, exc_info=True)

        thumbnail_lookup: dict[str, str] = {}
        try:
            thumbnail_results = await asyncio.to_thread(
                persist_thumbnails, posts, username
            )
            thumbnail_lookup = {r["post_id"]: r["thumbnail_url"] for r in thumbnail_results}
        except Exception:
            logger.warning("GCS thumbnail persistence failed for %s, using CDN URLs", username, exc_info=True)

        return {
            "user": {
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "full_name": user_data.get("full_name"),
                "biography": user_data.get("biography"),
                "follower_count": user_data.get("follower_count"),
                "following_count": user_data.get("following_count"),
                "media_count": user_data.get("media_count"),
                "is_private": user_data.get("is_private"),
                "is_verified": user_data.get("is_verified"),
                "profile_pic_url": profile_pic_url,
            },
            "image_post": image_post_data,
            "video_post": video_post_data,
            "all_image_posts": all_image_posts,
            "all_video_posts": all_video_posts,
            "all_posts": posts,  # Raw posts for ROI calculation
            "analysis": analysis_json,
            "roi": roi_data,
            "trust": trust_data,
            "persisted_thumbnails": thumbnail_lookup,
        }

    def _error_response(self, error_type: str, message: str, retryable: bool = False) -> dict:
        response = {
            "user": None,
            "error": error_type,
            "error_message": message,
            "image_post": None,
            "video_post": None,
            "all_image_posts": [],
            "all_video_posts": [],
            "analysis": None,
        }
        if retryable:
            response["retryable"] = True
        return response

    def _select_post_samples(
        self, posts: list[dict], max_posts_per_type: int
    ) -> tuple[list[dict], list[dict]]:
        image_posts: list[dict] = []
        video_posts: list[dict] = []

        for post in posts:
            if len(image_posts) >= max_posts_per_type and len(video_posts) >= max_posts_per_type:
                break

            media_type = post.get("media_type")
            if media_type == MEDIA_TYPE_IMAGE and len(image_posts) < max_posts_per_type:
                image_posts.append(post)
            elif media_type == MEDIA_TYPE_VIDEO and len(video_posts) < max_posts_per_type:
                video_posts.append(post)
            elif media_type == MEDIA_TYPE_CAROUSEL:
                self._extract_carousel_media(post, image_posts, video_posts, max_posts_per_type)

        return image_posts, video_posts

    def _extract_carousel_media(
        self, post: dict, image_posts: list[dict], video_posts: list[dict], max_posts_per_type: int
    ) -> None:
        if len(image_posts) < max_posts_per_type:
            for resource in post.get("resources", []):
                if resource.get("media_type") == MEDIA_TYPE_IMAGE:
                    carousel_entry = dict(post)
                    carousel_entry["_resource"] = resource
                    image_posts.append(carousel_entry)
                    break

        if len(video_posts) < max_posts_per_type:
            for resource in post.get("resources", []):
                if resource.get("media_type") == MEDIA_TYPE_VIDEO:
                    carousel_entry = dict(post)
                    carousel_entry["_resource"] = resource
                    video_posts.append(carousel_entry)
                    break

    def _prepare_media_assets(
        self, image_post_data: dict | None, video_post_data: dict | None
    ) -> tuple[bytes | None, str | None, bytes | None, str | None]:
        image_bytes: bytes | None = None
        image_mime: str | None = None
        if image_post_data and image_post_data.get("media_url"):
            image_bytes, image_mime, _ = self.download_image(image_post_data["media_url"])

        video_bytes: bytes | None = None
        video_mime: str | None = None
        if image_bytes is None and video_post_data and video_post_data.get("media_url"):
            video_bytes, video_mime = self.download_video(video_post_data["media_url"])

        return image_bytes, image_mime, video_bytes, video_mime

    def _run_analysis_with_media_fallback(
        self,
        username: str,
        user_data: dict,
        post_context: dict[str, Any],
        media_assets: tuple[bytes | None, str | None, bytes | None, str | None],
    ) -> dict:
        image_bytes, image_mime, video_bytes, video_mime = media_assets

        try:
            return self._analyze_with_gemini(
                username,
                user_data,
                post_context["image_post"],
                post_context["video_post"],
                post_context["all_image_posts"],
                post_context["all_video_posts"],
                image_bytes,
                image_mime,
                video_bytes,
                video_mime,
            )
        except ValueError as error:
            error_msg = str(error).lower()
            if "blocked" not in error_msg and "safety" not in error_msg:
                raise

            logger.warning(f"[{username}] Content blocked, retrying without media")
            return self._analyze_with_gemini(
                username,
                user_data,
                post_context["image_post"],
                post_context["video_post"],
                post_context["all_image_posts"],
                post_context["all_video_posts"],
                None,
                None,
                None,
                None,
            )

    def _analyze_with_gemini(
        self,
        username: str,
        user_data: dict,
        image_post: dict | None,
        video_post: dict | None,
        all_image_posts: list[dict],
        all_video_posts: list[dict],
        image_bytes: bytes | None,
        image_mime: str | None,
        video_bytes: bytes | None,
        video_mime: str | None,
    ) -> dict:
        """Perform the Gemini analysis."""
        prompt = self._build_prompt(
            user_data, image_post, video_post, all_image_posts, all_video_posts
        )

        logger.info(f"[{username}] Prompt length: {len(prompt)} characters")

        # Build contents list for the new google-genai API
        contents: list = [prompt]

        if image_bytes:
            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=image_mime or "image/jpeg",
                )
            )
        if video_bytes:
            contents.append(
                types.Part.from_bytes(
                    data=video_bytes,
                    mime_type=video_mime or "image/jpeg",
                )
            )

        try:
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    safety_settings=self.safety_settings,
                ),
            )
        except Exception as e:
            logger.error(f"[{username}] Gemini API error: {e}")
            raise

        try:
            # Check for blocked content
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                feedback = response.prompt_feedback
                if hasattr(feedback, "block_reason") and feedback.block_reason:
                    raise ValueError(f"Content blocked by Gemini: {feedback.block_reason}")

            if not hasattr(response, "candidates") or not response.candidates:
                raise ValueError("Gemini response has no candidates")

            analysis_text = response.text.strip()
            if not analysis_text:
                raise ValueError("Empty response from Gemini")

            return self._parse_json_response(analysis_text)

        except Exception as e:
            logger.error(f"[{username}] Failed to process Gemini response: {e}")
            raise


_analyzer_instance: AudienceIntelligenceAnalyzer | None = None


def get_analyzer() -> AudienceIntelligenceAnalyzer:
    """Get the singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = AudienceIntelligenceAnalyzer()
    return _analyzer_instance


async def analyze_user(username: str) -> dict:
    """Convenience function to analyze a user."""
    analyzer = get_analyzer()
    return await analyzer.analyze_user(username)
