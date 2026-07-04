import os
import django
import requests
import re
import json
import time
from requests.adapters import HTTPAdapter
from django.db.models import Count, F

# ---------------------------------------------
# Django setup
# ---------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from api.models import ShortDrama, ShortDramaEpisode

REQUEST_TIMEOUT = 20
RETRY_LIMIT = 3
DELAY_BETWEEN_EPISODES = 1
DELAY_BETWEEN_DRAMAS = 5

BASE_HEADERS = {
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
session.headers.update(BASE_HEADERS)

adapter = HTTPAdapter(
    pool_connections=5,
    pool_maxsize=5,
)
session.mount("https://", adapter)

COOKIE_STRING = """
PASTE_FULL_RAW_COOKIE_HERE
"""

COOKIE_STRING = COOKIE_STRING.replace("…", "")
COOKIE_STRING = COOKIE_STRING.encode(
    "ascii",
    "ignore"
).decode()

for item in COOKIE_STRING.strip().split("; "):
    if "=" in item:
        key, value = item.split("=", 1)
        session.cookies.set(key, value)


def extract_current_episode(raw_text):
    match = re.search(
        r'"currentEpisode":({.*?"lockStatus":\d+})',
        raw_text
    )

    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def fetch_episode(drama, ep):
    url = f"https://vskit.tv/watch/{drama.slug}?ep={ep}"

    headers = {
        "Referer": f"https://vskit.tv/drama/{drama.slug}",
        "Next-Url": f"/en/drama/{drama.slug}",
    }

    for attempt in range(RETRY_LIMIT):
        try:
            response = session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code != 200:
                print(
                    f"[{drama.title}] Ep {ep} "
                    f"HTTP {response.status_code}"
                )
                time.sleep(2)
                continue

            episode_data = extract_current_episode(
                response.text
            )

            if episode_data:
                return episode_data

            print(
                f"[{drama.title}] Ep {ep} "
                f"Parse failed ({attempt + 1}/{RETRY_LIMIT})"
            )

            time.sleep(2)

        except Exception as e:
            print(
                f"[{drama.title}] Ep {ep} "
                f"Error: {e}"
            )
            time.sleep(2)

    return None


def save_episode(drama, episode_data):
    video = episode_data.get("video") or {}
    video_address = video.get("videoAddress") or {}
    cover = video.get("cover") or {}

    ShortDramaEpisode.objects.update_or_create(
        drama=drama,
        episode_number=episode_data.get("ep"),
        defaults={
            "mini_id": episode_data.get("miniId"),
            "subject_id": episode_data.get("subjectId"),
            "season": episode_data.get("se", 1),
            "play_url": video_address.get("url"),
            "thumbnail": cover.get("url"),
            "duration": video_address.get("duration"),
            "width": video_address.get("width"),
            "height": video_address.get("height"),
            "file_size": video_address.get("size"),
            "lock_status": episode_data.get("lockStatus", 0),
            "is_active": True,
        }
    )


def retry_missing_episodes():
    BATCH_SIZE = 50

    dramas = (
        ShortDrama.objects.filter(is_active=True)
        .annotate(
            episode_count=Count("episodes")
        )
        .filter(
            episode_count__lt=F("total_episodes")
        )[:BATCH_SIZE]
    )

    print(f"Found {dramas.count()} incomplete dramas")

    for drama in dramas:
        existing_eps = set(
            drama.episodes.values_list(
                "episode_number",
                flat=True
            )
        )

        missing_eps = [
            ep for ep in range(1, drama.total_episodes + 1)
            if ep not in existing_eps
        ]

        if not missing_eps:
            continue

        print(f"\n{drama.title}")
        print(f"Missing episodes: {missing_eps}")

        for ep in missing_eps:
            episode_data = fetch_episode(drama, ep)

            if not episode_data:
                print(
                    f"[{drama.title}] Failed Ep {ep}"
                )
                continue

            save_episode(drama, episode_data)

            print(
                f"[{drama.title}] Saved missing Ep {ep}"
            )

            time.sleep(DELAY_BETWEEN_EPISODES)

        print(
            f"Sleeping {DELAY_BETWEEN_DRAMAS}s..."
        )
        time.sleep(DELAY_BETWEEN_DRAMAS)


if __name__ == "__main__":
    print("Starting missing episodes recovery...")
    retry_missing_episodes()