"""MongoDB cache for audience intelligence analyses."""

import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from agent.config import settings

logger = logging.getLogger(__name__)


class AudienceIntelligenceCache:
    """Cache for audience intelligence analyses in MongoDB."""

    def __init__(self, client: AsyncIOMotorClient | None = None):
        """Initialize the cache with an optional motor client."""
        self._client = client
        self._db = None
        self._collection = None

    async def _get_collection(self):
        """Lazily initialize and return the collection."""
        if self._collection is None:
            if self._client is None:
                from api.dependencies.database import Database

                if Database.client is not None:
                    self._client = Database.client
                else:
                    self._client = AsyncIOMotorClient(settings.MONGODB_URL)
            self._db = self._client[settings.DATABASE_NAME]
            self._collection = self._db[settings.AUDIENCE_INTELLIGENCE_CACHE_COLLECTION]
            # Ensure index on handle for fast lookups
            await self._collection.create_index("handle", unique=True)
            # TTL index: auto-expire cached analyses after 7 days
            await self._collection.create_index(
                "updated_at", expireAfterSeconds=7 * 24 * 60 * 60
            )
        return self._collection

    async def get(self, handle: str) -> dict | None:
        """Get cached analysis for a handle."""
        collection = await self._get_collection()
        doc = await collection.find_one({"handle": handle.lower()})
        if doc:
            # Remove MongoDB _id from response
            doc.pop("_id", None)
            return doc
        return None

    async def set(self, handle: str, analysis_result: dict) -> None:
        """Cache an analysis result for a handle."""
        collection = await self._get_collection()

        # Extract profile info for pill display
        user = analysis_result.get("user") or {}
        profile_pic_url = user.get("profile_pic_url")

        # Extract gallery-ready performance metrics at top level
        performance = analysis_result.get("performance", {})
        engagement_metrics = performance.get("engagement_metrics", {})
        sponsored_metrics = performance.get("sponsored_metrics", {})

        doc = {
            "handle": handle.lower(),
            "profile_pic": profile_pic_url,
            "profile_pic_url": profile_pic_url,
            "follower_count": user.get("follower_count", 0),
            "full_name": user.get("full_name"),
            "avg_engagement_rate": engagement_metrics.get("avg_engagement_rate", 0.0),
            "total_partnerships": sponsored_metrics.get("total_partnerships", 0),
            "analysis": analysis_result,
            "created_at": datetime.now(tz=UTC),
            "updated_at": datetime.now(tz=UTC),
        }

        await collection.update_one(
            {"handle": handle.lower()},
            {"$set": doc},
            upsert=True,
        )
        logger.info(f"Cached analysis for @{handle}")

    async def get_cached_handles(self, limit: int = 20) -> list[dict]:
        """Get list of cached handles with profile info for pill display.

        Returns list of dicts with: handle, profile_pic, follower_count, full_name
        """
        collection = await self._get_collection()

        cursor = collection.find(
            {},
            {
                "_id": 0,
                "handle": 1,
                "profile_pic": 1,
                "follower_count": 1,
                "full_name": 1,
            }
        ).sort("follower_count", -1).limit(limit)

        handles = []
        async for doc in cursor:
            handles.append(doc)

        return handles

    async def delete(self, handle: str) -> bool:
        """Delete cached analysis for a handle."""
        collection = await self._get_collection()
        result = await collection.delete_one({"handle": handle.lower()})
        return result.deleted_count > 0

    async def get_gallery_items(
        self,
        page: int = 1,
        limit: int = 20,
        sort: str = "date",
        min_followers: int | None = None,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        """Get paginated gallery items with sorting and filtering.

        Args:
            page: Page number (1-indexed)
            limit: Items per page
            sort: Sort order: 'date' (newest first), 'followers' (most followers), 'score' (highest ROI)
            min_followers: Minimum follower count filter
            min_score: Minimum ROI score filter (0-1)

        Returns:
            {
                'total': total count,
                'page': current page,
                'limit': items per page,
                'items': [gallery items]
            }
        """
        collection = await self._get_collection()

        # Build filter query
        filters = {}
        if min_followers is not None:
            filters["follower_count"] = {"$gte": min_followers}
        if min_score is not None:
            # Score is stored in analysis.roi.roi_score
            filters["analysis.roi.roi_score"] = {"$gte": min_score}

        # Determine sort order
        sort_field = "created_at"
        sort_direction = -1  # descending

        if sort == "followers":
            sort_field = "follower_count"
            sort_direction = -1
        elif sort == "score":
            sort_field = "analysis.roi.roi_score"
            sort_direction = -1
        # else: sort == "date" (default)

        # Get total count
        total = await collection.count_documents(filters)

        # Get paginated results
        skip = (page - 1) * limit
        cursor = collection.find(
            filters,
            {
                "_id": 0,
                "handle": 1,
                "profile_pic": 1,
                "full_name": 1,
                "follower_count": 1,
                "created_at": 1,
                "avg_engagement_rate": 1,
                "total_partnerships": 1,
                "analysis.roi.roi_score": 1,
                "analysis.roi.verdict": 1,
                "analysis.performance.engagement_metrics.avg_engagement_rate": 1,
                "analysis.performance.sponsored_metrics.total_partnerships": 1,
            }
        ).sort(sort_field, sort_direction).skip(skip).limit(limit)

        items = []
        async for doc in cursor:
            # Extract nested values
            analysis = doc.get("analysis", {})
            roi = analysis.get("roi", {})

            # Prefer top-level gallery metrics (populated by set()), fall back to nested path
            top_level_er = doc.get("avg_engagement_rate")
            top_level_partners = doc.get("total_partnerships")

            if top_level_er is not None and top_level_er > 0:
                avg_engagement_rate = float(top_level_er)
            else:
                performance = analysis.get("performance", {})
                engagement_metrics = performance.get("engagement_metrics", {})
                avg_engagement_rate = float(engagement_metrics.get("avg_engagement_rate", 0))

            if top_level_partners is not None and top_level_partners > 0:
                total_partnerships = int(top_level_partners)
            else:
                performance = analysis.get("performance", {})
                total_partnerships = int(
                    performance.get("sponsored_metrics", {}).get("total_partnerships", 0)
                )

            item = {
                "handle": doc["handle"],
                "profile_pic": doc.get("profile_pic"),
                "full_name": doc.get("full_name"),
                "follower_count": doc.get("follower_count", 0),
                "analyzed_at": doc.get("created_at", "").isoformat()
                if hasattr(doc.get("created_at"), "isoformat")
                else str(doc.get("created_at", "")),
                "roi_score": float(roi.get("roi_score", 0.5)),
                "roi_verdict": roi.get("verdict", "Caution"),
                "avg_engagement_rate": avg_engagement_rate,
                "total_partnerships": total_partnerships,
            }
            items.append(item)

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": items,
        }


# Singleton instance
_cache_instance: AudienceIntelligenceCache | None = None


def get_cache() -> AudienceIntelligenceCache:
    """Get the singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AudienceIntelligenceCache()
    return _cache_instance
