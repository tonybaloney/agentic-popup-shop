"""Insights caching system.

Caches insights per store with weekly expiration using date-encoded filenames.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Default cache path relative to repo root: <repo>/.cache/insights
CACHE_DIR = Path(os.getenv("INSIGHTS_CACHE_DIR", str(Path(__file__).parent.parent.parent.parent.parent / ".cache" / "insights")))
CACHE_VALIDITY_DAYS = int(os.getenv("INSIGHTS_CACHE_DAYS", "7"))


class InsightsCache:
    """Manages caching of weekly insights using date-encoded filenames."""

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        validity_days: int = CACHE_VALIDITY_DAYS,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for storing cache files.
            validity_days: Number of days before cache expires.
        """
        self.cache_dir = cache_dir
        self.validity_days = validity_days
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("📁 Insights cache directory: %s", self.cache_dir)
        except OSError as e:
            logger.error(
                "❌ Failed to create cache directory: %s", e, exc_info=True
            )
            raise

    def _get_cache_filename(self, store_id: int, date: datetime) -> str:
        """Generate cache filename with date.

        Format: YYYY-MM-DD-store-{id}-weekly-insights.json

        Args:
            store_id: Store identifier.
            date: Date for the cache file.

        Returns:
            Cache filename string.
        """
        date_str = date.strftime("%Y-%m-%d")
        return f"{date_str}-store-{store_id}-weekly-insights.json"

    def _parse_cache_filename(
        self, filename: str
    ) -> Optional[tuple[int, datetime]]:
        """Parse cache filename to extract store_id and date.

        Expected format: YYYY-MM-DD-store-{id}-weekly-insights.json

        Args:
            filename: Cache filename to parse.

        Returns:
            Tuple of (store_id, date) or None if invalid format.
        """
        try:
            parts = filename.replace(".json", "").split("-")
            if len(parts) >= 5 and parts[3] == "store":
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                store_id = int(parts[4])
                date = datetime(year, month, day, tzinfo=timezone.utc)
                return (store_id, date)
        except (ValueError, IndexError) as e:
            logger.warning(
                "⚠️ Could not parse cache filename %s: %s", filename, e
            )
        return None

    def _find_latest_cache(
        self, store_id: int
    ) -> Optional[tuple[Path, datetime]]:
        """Find the most recent cache file for a store.

        Args:
            store_id: Store identifier.

        Returns:
            Tuple of (filepath, date) or None if no cache exists.
        """
        pattern = f"*-store-{store_id}-weekly-insights.json"
        cache_files = list(self.cache_dir.glob(pattern))

        if not cache_files:
            return None

        valid_files = []
        for cache_file in cache_files:
            parsed = self._parse_cache_filename(cache_file.name)
            if parsed:
                parsed_store_id, date = parsed
                if parsed_store_id == store_id:
                    valid_files.append((cache_file, date))

        if not valid_files:
            return None

        return max(valid_files, key=lambda x: x[1])

    def _is_cache_valid(self, cached_date: datetime) -> bool:
        """Check if cached data is still valid based on date.

        Args:
            cached_date: Date when cache was created.

        Returns:
            True if cache is still valid, False otherwise.
        """
        now = datetime.now(timezone.utc)
        age_days = (now - cached_date).days
        is_valid = age_days < self.validity_days

        if is_valid:
            remaining_days = self.validity_days - age_days
            logger.info(
                "✅ Cache valid. Expires in %d days", remaining_days
            )
        else:
            logger.info(
                "⏰ Cache expired. Age: %d days (max: %d)",
                age_days,
                self.validity_days,
            )

        return is_valid

    def _delete_cache_file(self, cache_file: Path) -> None:
        """Delete a cache file with error handling.

        Args:
            cache_file: Path to cache file to delete.
        """
        try:
            cache_file.unlink(missing_ok=True)
            logger.info("🧹 Deleted cache file: %s", cache_file.name)
        except OSError as e:
            logger.warning(
                "⚠️ Could not delete cache file %s: %s", cache_file.name, e
            )

    def get(self, store_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve cached insights for a store if valid.

        Args:
            store_id: Store identifier.

        Returns:
            Cached insights data or None if cache doesn't exist or is expired.
        """
        latest_cache = self._find_latest_cache(store_id)

        if not latest_cache:
            logger.info("📭 No cache found for store %d", store_id)
            return None

        cache_file, cached_date = latest_cache

        if not self._is_cache_valid(cached_date):
            logger.info(
                "🗑️ Cache expired for store %d, will regenerate", store_id
            )
            self._delete_cache_file(cache_file)
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                insights_data = json.load(f)

            logger.info(
                "📬 Using cached insights for store %d (generated: %s)",
                store_id,
                cached_date.date(),
            )
            return insights_data

        except (OSError, json.JSONDecodeError) as e:
            logger.error(
                "❌ Error reading cache for store %d: %s",
                store_id,
                e,
                exc_info=True,
            )
            self._delete_cache_file(cache_file)
            return None

    def set(self, store_id: int, insights_data: Dict[str, Any]) -> bool:
        """Cache insights for a store with current date in filename.

        Automatically cleans up old cache files for this store.

        Args:
            store_id: Store identifier.
            insights_data: Insights data to cache.

        Returns:
            True if successful, False otherwise.
        """
        now = datetime.now(timezone.utc)
        filename = self._get_cache_filename(store_id, now)
        cache_file = self.cache_dir / filename

        try:
            temp_file = cache_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(insights_data, f, indent=2, ensure_ascii=False)

            temp_file.replace(cache_file)

            # Only remove older cache files after the fresh cache is in place.
            self._cleanup_old_caches(
                store_id,
                exclude={cache_file.name},
            )

            logger.info(
                "💾 Cached insights for store %d: %s", store_id, filename
            )
            return True

        except (OSError, TypeError) as e:
            logger.error(
                "❌ Error caching insights for store %d: %s",
                store_id,
                e,
                exc_info=True,
            )
            self._cleanup_temp_file(cache_file)
            return False

    @staticmethod
    def _cleanup_temp_file(cache_file: Path) -> None:
        """Clean up temporary file if it exists.

        Args:
            cache_file: Cache file path (temp file will be .tmp version).
        """
        try:
            temp_file = cache_file.with_suffix(".tmp")
            temp_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _cleanup_old_caches(
        self,
        store_id: int,
        *,
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """Delete old cache files for a specific store.

        Args:
            store_id: Store identifier.
            exclude: Filenames that must not be deleted.

        Returns:
            Count of deleted files.
        """
        pattern = f"*-store-{store_id}-weekly-insights.json"
        cache_files = list(self.cache_dir.glob(pattern))
        count = 0

        exclude_files: Set[str] = exclude or set()

        for cache_file in cache_files:
            if cache_file.name in exclude_files:
                continue
            try:
                cache_file.unlink(missing_ok=True)
                count += 1
            except OSError as e:
                logger.warning(
                    "⚠️ Could not delete old cache %s: %s",
                    cache_file.name,
                    e,
                )

        if count > 0:
            logger.info(
                "🧹 Cleaned up %d old cache file(s) for store %d",
                count,
                store_id,
            )
        return count

    def invalidate(self, store_id: int) -> bool:
        """Manually invalidate (delete) all cache files for a store.

        Args:
            store_id: Store identifier.

        Returns:
            True if at least one cache was deleted, False otherwise.
        """
        count = self._cleanup_old_caches(store_id)
        if count > 0:
            logger.info(
                "🗑️ Invalidated %d cache file(s) for store %d",
                count,
                store_id,
            )
            return True

        logger.info("📭 No cache to invalidate for store %d", store_id)
        return False

    def invalidate_all(self) -> int:
        """Invalidate all cached insights across all stores.

        Returns:
            Number of cache files deleted.
        """
        cache_files = list(self.cache_dir.glob("*-weekly-insights.json"))
        count = 0

        for cache_file in cache_files:
            try:
                cache_file.unlink(missing_ok=True)
                count += 1
            except OSError as e:
                logger.warning(
                    "⚠️ Could not delete cache file %s: %s",
                    cache_file.name,
                    e,
                )

        if count > 0:
            logger.info("🗑️ Invalidated %d cached insights", count)
        return count

    def get_cache_info(self, store_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata about cached insights without returning full data.

        Args:
            store_id: Store identifier.

        Returns:
            Dictionary with cache metadata or None if no cache exists.
        """
        latest_cache = self._find_latest_cache(store_id)

        if not latest_cache:
            return None

        cache_file, cached_date = latest_cache
        is_valid = self._is_cache_valid(cached_date)

        now = datetime.now(timezone.utc)
        age = now - cached_date

        return {
            "store_id": store_id,
            "generated_date": cached_date.date().isoformat(),
            "filename": cache_file.name,
            "is_valid": is_valid,
            "age_days": age.days,
            "age_hours": age.seconds // 3600,
        }


_cache_instance: Optional[InsightsCache] = None


def get_cache() -> InsightsCache:
    """Get or create the singleton cache instance.

    Returns:
        Singleton InsightsCache instance.
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = InsightsCache()
    return _cache_instance
