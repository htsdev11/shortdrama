# import os
# import django
# import requests
# import re
# import json
# import time
# from requests.adapters import HTTPAdapter
# from django.db.models import Count, F
#
# # ---------------------------------------------
# # Django setup
# # ---------------------------------------------
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()
#
# from api.models import ShortDrama, ShortDramaEpisode
#
# REQUEST_TIMEOUT = 20
# RETRY_LIMIT = 3
# DELAY_BETWEEN_EPISODES = 1
# DELAY_BETWEEN_DRAMAS = 5
#
# BASE_HEADERS = {
#     "Accept": "*/*",
#     "Accept-Language": "en-US,en;q=0.9",
#     "User-Agent": (
#         "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) "
#         "Gecko/20100101 Firefox/152.0"
#     ),
#     "Origin": "https://vskit.tv",
#     "RSC": "1",
# }
#
# session = requests.Session()
# session.headers.update(BASE_HEADERS)
#
# adapter = HTTPAdapter(
#     pool_connections=5,
#     pool_maxsize=5,
# )
# session.mount("https://", adapter)
#
# COOKIE_STRING = """
# PASTE_FULL_RAW_COOKIE_HERE
# """
#
# COOKIE_STRING = COOKIE_STRING.replace("…", "")
# COOKIE_STRING = COOKIE_STRING.encode(
#     "ascii",
#     "ignore"
# ).decode()
#
# for item in COOKIE_STRING.strip().split("; "):
#     if "=" in item:
#         key, value = item.split("=", 1)
#         session.cookies.set(key, value)
#
#
# def extract_current_episode(raw_text):
#     match = re.search(
#         r'"currentEpisode":({.*?"lockStatus":\d+})',
#         raw_text
#     )
#
#     if not match:
#         return None
#
#     try:
#         return json.loads(match.group(1))
#     except Exception:
#         return None
#
#
# def fetch_episode(drama, ep):
#     url = f"https://vskit.tv/watch/{drama.slug}?ep={ep}"
#
#     headers = {
#         "Referer": f"https://vskit.tv/drama/{drama.slug}",
#         "Next-Url": f"/en/drama/{drama.slug}",
#     }
#
#     for attempt in range(RETRY_LIMIT):
#         try:
#             response = session.get(
#                 url,
#                 headers=headers,
#                 timeout=REQUEST_TIMEOUT
#             )
#
#             if response.status_code != 200:
#                 print(
#                     f"[{drama.title}] Ep {ep} "
#                     f"HTTP {response.status_code}"
#                 )
#                 time.sleep(2)
#                 continue
#
#             episode_data = extract_current_episode(
#                 response.text
#             )
#
#             if episode_data:
#                 return episode_data
#
#             print(
#                 f"[{drama.title}] Ep {ep} "
#                 f"Parse failed ({attempt + 1}/{RETRY_LIMIT})"
#             )
#
#             time.sleep(2)
#
#         except Exception as e:
#             print(
#                 f"[{drama.title}] Ep {ep} "
#                 f"Error: {e}"
#             )
#             time.sleep(2)
#
#     return None
#
#
# def save_episode(drama, episode_data):
#     video = episode_data.get("video") or {}
#     video_address = video.get("videoAddress") or {}
#     cover = video.get("cover") or {}
#
#     ShortDramaEpisode.objects.update_or_create(
#         drama=drama,
#         episode_number=episode_data.get("ep"),
#         defaults={
#             "mini_id": episode_data.get("miniId"),
#             "subject_id": episode_data.get("subjectId"),
#             "season": episode_data.get("se", 1),
#             "play_url": video_address.get("url"),
#             "thumbnail": cover.get("url"),
#             "duration": video_address.get("duration"),
#             "width": video_address.get("width"),
#             "height": video_address.get("height"),
#             "file_size": video_address.get("size"),
#             "lock_status": episode_data.get("lockStatus", 0),
#             "is_active": True,
#         }
#     )
#
#
# def retry_missing_episodes():
#     BATCH_SIZE = 50
#
#     dramas = (
#         ShortDrama.objects.filter(is_active=True)
#         .annotate(
#             episode_count=Count("episodes")
#         )
#         .filter(
#             episode_count__lt=F("total_episodes")
#         )[:BATCH_SIZE]
#     )
#
#     print(f"Found {dramas.count()} incomplete dramas")
#
#     for drama in dramas:
#         existing_eps = set(
#             drama.episodes.values_list(
#                 "episode_number",
#                 flat=True
#             )
#         )
#
#         missing_eps = [
#             ep for ep in range(1, drama.total_episodes + 1)
#             if ep not in existing_eps
#         ]
#
#         if not missing_eps:
#             continue
#
#         print(f"\n{drama.title}")
#         print(f"Missing episodes: {missing_eps}")
#
#         for ep in missing_eps:
#             episode_data = fetch_episode(drama, ep)
#
#             if not episode_data:
#                 print(
#                     f"[{drama.title}] Failed Ep {ep}"
#                 )
#                 continue
#
#             save_episode(drama, episode_data)
#
#             print(
#                 f"[{drama.title}] Saved missing Ep {ep}"
#             )
#
#             time.sleep(DELAY_BETWEEN_EPISODES)
#
#         print(
#             f"Sleeping {DELAY_BETWEEN_DRAMAS}s..."
#         )
#         time.sleep(DELAY_BETWEEN_DRAMAS)
#
#
# if __name__ == "__main__":
#     print("Starting missing episodes recovery...")
#     retry_missing_episodes()

"""
Recovery script for missing ShortDrama episodes.

NOTE:
- Replace COOKIE_STRING with your real cookie.
- This version includes logging, queryset optimization,
  metadata optimization, and safer exception handling.
"""

"""
Recovery script for missing ShortDrama episodes.

NOTE:
- Replace COOKIE_STRING with your real cookie.
- This version includes logging, queryset optimization,
  metadata optimization, and safer exception handling.
"""

import os
import json
import time
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import django
import requests
from django.db.models import Count, F
from django.utils.text import slugify
from requests.adapters import HTTPAdapter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from api.models import (
    ShortDrama,
    ShortDramaEpisode,
    ShortDramaGenre,
    ShortDramaCountry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
RETRY_LIMIT = 3
DELAY_BETWEEN_EPISODES = 1
DELAY_BETWEEN_DRAMAS = 5
BATCH_SIZE = 30

GENRE_CACHE = {}
COUNTRY_CACHE = {}

BASE_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://vskit.tv",
    "RSC": "1",
}

session = requests.Session()
session.headers.update(BASE_HEADERS)
adapter = HTTPAdapter(pool_connections=5, pool_maxsize=5)
session.mount("https://", adapter)

COOKIE_STRING = "PASTE_FULL_RAW_COOKIE_HERE"
for item in COOKIE_STRING.split("; "):
    if "=" in item:
        k, v = item.split("=", 1)
        session.cookies.set(k, v)


def extract_current_episode(raw_text):
    match = re.search(r'"currentEpisode":({.*?"lockStatus":\d+})', raw_text)
    if not match:
        return None, None
    try:
        episode = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, None

    metadata = {}
    for key, regex in {
        "genre": r'"genre":"([^"]*)"',
        "countryName": r'"countryName":"([^"]*)"',
        "releaseDate": r'"releaseDate":"([^"]*)"',
    }.items():
        m = re.search(regex, raw_text)
        if m:
            metadata[key] = m.group(1)
    return episode, metadata


def fetch_episode(drama, ep):
    url = f"https://vskit.tv/watch/{drama.slug}?ep={ep}"
    headers = {
        "Referer": f"https://vskit.tv/drama/{drama.slug}",
        "Next-Url": f"/en/drama/{drama.slug}",
    }

    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            ep_data, meta = extract_current_episode(r.text)
            if ep_data:
                return ep_data, meta
            logger.warning("[%s] Episode %s parse failed (%s/%s)",
                           drama.title, ep, attempt, RETRY_LIMIT)
        except requests.RequestException:
            logger.exception("[%s] Request failed for episode %s", drama.title, ep)
        time.sleep(2)

    return None, None


def extract_expiry(url):
    try:
        expires = int(parse_qs(urlparse(url).query)["Expires"][0])
        return datetime.fromtimestamp(expires, tz=timezone.utc)
    except Exception:
        return None


def save_episode(drama, episode_data, metadata=None):
    video = episode_data.get("video") or {}
    video_address = video.get("videoAddress") or {}
    cover = video.get("cover") or {}
    play_url = video_address.get("url")

    # ----------------------------
    # Update drama metadata
    # ----------------------------
    if metadata:
        updated_fields = []
        genres = []

        genre_string = metadata.get("genre")
        if genre_string:
            for genre_name in genre_string.split(","):
                genre_name = genre_name.strip()

                if not genre_name:
                    continue

                genre = GENRE_CACHE.get(genre_name)
                if genre is None:
                    genre, _ = ShortDramaGenre.objects.get_or_create(
                        name=genre_name,
                        defaults={"slug": slugify(genre_name)},
                    )
                    GENRE_CACHE[genre_name] = genre

                genres.append(genre)

        country_name = metadata.get("countryName")
        if country_name:
            country_name = country_name.strip()

            country = COUNTRY_CACHE.get(country_name)
            if country is None:
                country, _ = ShortDramaCountry.objects.get_or_create(
                    name=country_name,
                    defaults={"slug": slugify(country_name)},
                )
                COUNTRY_CACHE[country_name] = country

            if drama.country_id != country.id:
                drama.country = country
                updated_fields.append("country")

        release_date = metadata.get("releaseDate")
        if release_date:
            try:
                parsed_date = datetime.strptime(
                    release_date,
                    "%Y-%m-%d",
                ).date()

                if drama.release_date != parsed_date:
                    drama.release_date = parsed_date
                    updated_fields.append("release_date")

            except ValueError:
                pass

        if updated_fields:
            drama.save(update_fields=updated_fields)

        if genres:
            drama.genres.set(genres)

    ShortDramaEpisode.objects.update_or_create(
        drama=drama,
        episode_number=episode_data.get("ep"),
        defaults={
            "mini_id": episode_data.get("miniId"),
            "subject_id": episode_data.get("subjectId"),
            "season": episode_data.get("se", 1),
            "play_url": play_url,
            "expires_at": extract_expiry(play_url),
            "thumbnail": cover.get("url"),
            "duration": video_address.get("duration"),
            "width": video_address.get("width"),
            "height": video_address.get("height"),
            "file_size": video_address.get("size"),
            "lock_status": episode_data.get("lockStatus", 0),
            "is_active": True,
        },
    )


def retry_missing_episodes():
    dramas = list(
        ShortDrama.objects.filter(is_active=True)
        .annotate(episode_count=Count("episodes"))
        .filter(episode_count__lt=F("total_episodes"))[:BATCH_SIZE]
    )

    logger.info("Found %s incomplete dramas", len(dramas))

    for idx, drama in enumerate(dramas, start=1):
        logger.info("[%s/%s] %s", idx, len(dramas), drama.title)

        existing = set(drama.episodes.values_list("episode_number", flat=True))
        missing = [i for i in range(1, drama.total_episodes + 1) if i not in existing]

        needs_metadata = (
            drama.country_id is None
            or drama.release_date is None
            or not drama.genres.exists()
        )

        for ep in missing:
            ep_data, meta = fetch_episode(drama, ep)
            if not ep_data:
                logger.error("[%s] Failed episode %s", drama.title, ep)
                continue

            save_episode(drama, ep_data, meta if needs_metadata else None)
            needs_metadata = False
            logger.info("[%s] Saved episode %s", drama.title, ep)
            time.sleep(DELAY_BETWEEN_EPISODES)

        time.sleep(DELAY_BETWEEN_DRAMAS)


if __name__ == "__main__":
    logger.info("Starting recovery")
    retry_missing_episodes()
