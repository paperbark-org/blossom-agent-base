"""Persist Instagram images to Google Cloud Storage.

Instagram CDN URLs expire after ~4 hours. This module downloads images at
analysis time, compresses them, uploads to GCS, and returns permanent public
URLs.
"""

import logging
import threading
from io import BytesIO
from urllib.parse import urlparse

import httpx
from google.cloud import storage
from PIL import Image

from agent.config import settings
from api.services.audience_intelligence.matrix_calculator import extract_thumbnail

logger = logging.getLogger(__name__)

_bucket: storage.Bucket | None = None
_bucket_lock = threading.Lock()

MAX_PROFILE_SIZE = (256, 256)
MAX_THUMBNAIL_SIZE = (480, 480)
JPEG_QUALITY = 80
DOWNLOAD_TIMEOUT = 30.0
MAX_THUMBNAILS = 6
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_DOMAINS = frozenset({
    "cdninstagram.com",
    "fbcdn.net",
    "instagram.com",
})


def _is_allowed_url(url: str) -> bool:
    """Return True if *url* points to a known Instagram/Facebook CDN host."""
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in ALLOWED_IMAGE_DOMAINS
        )
    except Exception:
        return False


def _get_bucket() -> storage.Bucket | None:
    """Return a lazy-initialised GCS bucket (thread-safe singleton)."""
    global _bucket

    if _bucket is not None:
        return _bucket

    with _bucket_lock:
        # Double-check after acquiring lock
        if _bucket is not None:
            return _bucket

        bucket_name = settings.GCS_BUCKET_NAME
        project_id = settings.GCS_PROJECT_ID
        if not bucket_name or not project_id:
            logger.warning("GCS_BUCKET_NAME or GCS_PROJECT_ID not configured — image persistence disabled")
            return None

        try:
            client = storage.Client(project=project_id)
            _bucket = client.bucket(bucket_name)
            logger.info("GCS bucket '%s' initialised for image persistence", bucket_name)
            return _bucket
        except Exception:
            logger.exception("Failed to initialise GCS bucket '%s'", bucket_name)
            return None


def _download_image(url: str) -> bytes | None:
    """Download an image from *url*, return raw bytes or None on failure."""
    if not _is_allowed_url(url):
        logger.warning("Rejected non-Instagram URL: %s", url)
        return None

    try:
        resp = httpx.get(url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()

        if len(resp.content) > MAX_DOWNLOAD_BYTES:
            logger.warning("Image too large (%d bytes): %s", len(resp.content), url)
            return None

        content_type = resp.headers.get("content-type", "").lower()
        if content_type and not content_type.startswith("image/"):
            logger.warning("Non-image content-type '%s': %s", content_type, url)
            return None

        return resp.content
    except Exception:
        logger.warning("Failed to download image: %s", url, exc_info=True)
        return None


def _compress_image(data: bytes, max_size: tuple[int, int]) -> bytes:
    """Resize + JPEG-compress *data*, return compressed bytes."""
    img = Image.open(BytesIO(data))
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def upload_image(data: bytes, path: str) -> str | None:
    """Upload *data* to GCS at *path* and return the public URL."""
    bucket = _get_bucket()
    if bucket is None:
        return None

    try:
        blob = bucket.blob(path)
        blob.upload_from_string(data, content_type="image/jpeg")
        return f"https://storage.googleapis.com/{bucket.name}/{path}"
    except Exception:
        logger.exception("Failed to upload image to GCS path '%s'", path)
        return None


def persist_profile_pic(url: str | None, username: str) -> str | None:
    """Download, compress, and upload a profile picture.

    Returns:
        Public GCS URL or None on failure / GCS unavailable.
    """
    if not url:
        return None

    raw = _download_image(url)
    if raw is None:
        return None

    try:
        compressed = _compress_image(raw, MAX_PROFILE_SIZE)
    except Exception:
        logger.warning("Failed to compress profile pic for %s", username, exc_info=True)
        return None

    path = f"profiles/{username}.jpg"
    return upload_image(compressed, path)


def persist_thumbnails(
    posts: list[dict],
    username: str,
    max_count: int = MAX_THUMBNAILS,
) -> list[dict]:
    """Persist thumbnail images for the first *max_count* posts.

    For each post that has a thumbnail, download it, compress, upload to GCS,
    and replace the thumbnail URLs in the post dicts in-place (returns new
    list of dicts with ``thumbnail_url`` added/updated).

    Returns:
        List of ``{"post_id": ..., "thumbnail_url": ...}`` for successfully
        persisted thumbnails.
    """
    results: list[dict] = []
    persisted = 0

    for post in posts:
        if persisted >= max_count:
            break

        thumb_url = extract_thumbnail(post)
        if not thumb_url:
            continue

        post_id = str(post.get("id") or post.get("code") or "")
        if not post_id:
            continue

        raw = _download_image(thumb_url)
        if raw is None:
            continue

        try:
            compressed = _compress_image(raw, MAX_THUMBNAIL_SIZE)
        except Exception:
            logger.warning("Failed to compress thumbnail for post %s", post_id, exc_info=True)
            continue

        gcs_path = f"thumbnails/{username}/{post_id}.jpg"
        gcs_url = upload_image(compressed, gcs_path)
        if gcs_url:
            results.append({"post_id": post_id, "thumbnail_url": gcs_url})
            persisted += 1

    return results
