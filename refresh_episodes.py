"""
refresh_short_drama_urls.py

Refreshes signed episode URLs for dramas whose episode URLs are nearing expiry.
Fill in COOKIE_STRING before running.
"""

import os
import json
import time
import logging
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

import django
import requests
from requests.adapters import HTTPAdapter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone as dj_timezone
from django.core.cache import cache
from api.models import ShortDrama

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
RETRY_LIMIT = 3
EPISODE_WORKERS = 3
REFRESH_BUFFER = timedelta(minutes=30)
DELAY_BETWEEN_EPISODES = 0.5
DELAY_BETWEEN_DRAMAS = 10
LOCK_TIMEOUT = 300

SESSION_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) "
        "Gecko/20100101 Firefox/152.0"
    ),
    "Origin": "https://vskit.tv",
    "RSC": "1",
}

session = requests.Session()
session.headers.update(SESSION_HEADERS)
session.mount("https://", HTTPAdapter(pool_connections=5, pool_maxsize=5))

COOKIE_STRING = "PASTE_FULL_RAW_COOKIE_HERE"
COOKIE_STRING = COOKIE_STRING.replace("…", "").encode("ascii", "ignore").decode()

for item in COOKIE_STRING.strip().split("; "):
    if "=" in item:
        k, v = item.split("=", 1)
        session.cookies.set(k, v)


def extract_current_episode(raw_text):
    match = re.search(r'"currentEpisode":({.*?"lockStatus":\d+})', raw_text)
    if not match:
        return None, None
    try:
        episode_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, None
    return episode_data, {}


def extract_expiry(url):
    try:
        ts = int(parse_qs(urlparse(url).query)["Expires"][0])
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (KeyError, ValueError, TypeError):
        return None


def fetch_episode(drama, ep):
    url = f"https://vskit.tv/watch/{drama.slug}?ep={ep}"
    headers = {
        "Referer": f"https://vskit.tv/drama/{drama.slug}",
        "Next-Url": f"/en/drama/{drama.slug}",
    }

    for attempt in range(RETRY_LIMIT):
        try:
            r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()

            episode_data, metadata = extract_current_episode(r.text)
            if episode_data:
                return episode_data, metadata

            logger.warning(
                "[%s] Episode %s parse failed (%s/%s)",
                drama.title,
                ep,
                attempt + 1,
                RETRY_LIMIT,
            )

        except requests.RequestException as e:
            logger.warning(
                "[%s] Episode %s request failed (%s/%s): %s",
                drama.title,
                ep,
                attempt + 1,
                RETRY_LIMIT,
                e,
            )

        time.sleep(2)

    return None, None


def refresh_episode(ep_obj):
    data, _ = fetch_episode(ep_obj.drama, ep_obj.episode_number)

    if not data:
        logger.error("[%s] Failed episode %s", ep_obj.drama.title, ep_obj.episode_number)
        return False

    video = data.get("video") or {}
    addr = video.get("videoAddress") or {}
    cover = video.get("cover") or {}

    url = addr.get("url")
    ep_obj.play_url = url
    ep_obj.expires_at = extract_expiry(url)
    ep_obj.thumbnail = cover.get("url")
    ep_obj.duration = addr.get("duration")
    ep_obj.width = addr.get("width")
    ep_obj.height = addr.get("height")
    ep_obj.file_size = addr.get("size")
    ep_obj.lock_status = data.get("lockStatus", 0)
    ep_obj.save()

    logger.info("[%s] Updated episode %s", ep_obj.drama.title, ep_obj.episode_number)
    time.sleep(DELAY_BETWEEN_EPISODES)
    return True


def refresh_drama(drama):
    lock_key = f"drama_refresh:{drama.id}"

    if not cache.add(lock_key, "1", timeout=LOCK_TIMEOUT):
        logger.info("[%s] Skipped (locked)", drama.title)
        return

    start = time.perf_counter()

    try:
        logger.info("Refreshing '%s'", drama.title)

        episodes = sorted(
            drama.episodes.all(),
            key=lambda e: e.episode_number,
        )

        with ThreadPoolExecutor(max_workers=EPISODE_WORKERS) as executor:
            list(executor.map(refresh_episode, episodes))

        drama.last_episode_refresh = dj_timezone.now()
        drama.save(update_fields=["last_episode_refresh"])

        logger.info(
            "Finished '%s' in %.2fs",
            drama.title,
            time.perf_counter() - start,
        )

    finally:
        cache.delete(lock_key)

    logger.info("Sleeping %ss before next drama", DELAY_BETWEEN_DRAMAS)
    time.sleep(DELAY_BETWEEN_DRAMAS)


def get_dramas_to_refresh():
    return (
        ShortDrama.objects.filter(
            is_active=True,
            episodes__expires_at__lte=dj_timezone.now() + REFRESH_BUFFER,
        )
        .distinct()
        .prefetch_related("episodes")
    )


def main():
    dramas = list(get_dramas_to_refresh())

    logger.info("Found %s dramas requiring refresh", len(dramas))

    for drama in dramas:
        refresh_drama(drama)

    logger.info("=" * 60)
    logger.info("Refresh completed")
    logger.info("Total dramas processed: %s", len(dramas))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()