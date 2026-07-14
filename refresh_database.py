import os
import time
import logging

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from api.models import ShortDrama
from refresh_episodes import refresh_drama

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    start = time.perf_counter()

    dramas = list(
        ShortDrama.objects.filter(is_active=True)
        .prefetch_related("episodes")
        .order_by("id")
    )

    total = len(dramas)

    logger.info("=" * 80)
    logger.info("Refreshing ALL dramas")
    logger.info("Total dramas: %s", total)
    logger.info("=" * 80)

    refreshed = 0
    skipped = 0
    failed = 0

    for index, drama in enumerate(dramas, start=1):
        # Uses prefetched episodes (no extra SQL query)
        if not drama.episodes.all():
            logger.info(
                "[%s/%s] %s - No episodes, skipping.",
                index,
                total,
                drama.title,
            )
            skipped += 1
            continue

        logger.info("[%s/%s] %s", index, total, drama.title)

        try:
            refresh_drama(drama)
            refreshed += 1

        except Exception:
            failed += 1
            logger.exception(
                "[%s/%s] Failed refreshing '%s'",
                index,
                total,
                drama.title,
            )

    elapsed = time.perf_counter() - start

    logger.info("=" * 80)
    logger.info("ALL DRAMAS REFRESHED")
    logger.info("Refreshed : %s", refreshed)
    logger.info("Skipped   : %s", skipped)
    logger.info("Failed    : %s", failed)
    logger.info("Elapsed   : %.2f seconds", elapsed)
    logger.info("=" * 80)


if __name__ == "__main__":
    main()