import os
import django
import requests
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from api.models import ShortDrama, ShortDramaEpisode


# ---------------------------------------------
# CONFIG
# ---------------------------------------------
MAX_PAGES = 3
PER_PAGE = 20
EPISODE_WORKERS = 2
REQUEST_TIMEOUT = 20
RETRY_LIMIT = 3
DELAY_BETWEEN_EPISODES = 0.7
DELAY_BETWEEN_DRAMAS = 10
DELAY_BETWEEN_PAGES = 10


# ---------------------------------------------
# API
# ---------------------------------------------
BASE_URL = "https://h5-api.aoneroom.com/wefeed-h5api-bff/vskit/recommend-list"

HEADERS = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_TOKEN",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://vskit.tv",
    "Referer": "https://vskit.tv/",
    "X-Client-Info": '{"timezone":"Asia/Karachi"}',
    "X-Request-Lang": "en",
    "X-Site-Domain": "https://vskit.tv"
}


# ---------------------------------------------
# EPISODE SESSION
# ---------------------------------------------
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

COOKIE_STRING = """
PASTE_FULL_RAW_COOKIE_HERE
"""

COOKIE_STRING = COOKIE_STRING.replace("…", "")
COOKIE_STRING = COOKIE_STRING.encode("ascii", "ignore").decode()

for item in COOKIE_STRING.strip().split("; "):
    if "=" in item:
        key, value = item.split("=", 1)
        session.cookies.set(key, value)


# ---------------------------------------------
# FETCH DRAMA PAGE
# ---------------------------------------------
def fetch_page(page):
    params = {
        "page": page,
        "perPage": PER_PAGE,
        "novelType": 3
    }

    response = requests.get(
        BASE_URL,
        headers=HEADERS,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        print(f"Failed page {page}")
        return []

    return response.json().get("data", {}).get("list", [])


# ---------------------------------------------
# SAVE DRAMA
# ---------------------------------------------
def save_drama(drama_data):
    drama, created = ShortDrama.objects.update_or_create(
        subject_id=drama_data.get("subjectId"),
        defaults={
            "title": drama_data.get("title"),
            "slug": drama_data.get("subjectSeoKey"),
            "cover": drama_data.get("cover") or {},
            "tags": drama_data.get("tags", []),
            "total_episodes": drama_data.get("totalEpisode"),
            "total_views": drama_data.get("totalViews"),
            "description": drama_data.get("description"),
            "is_active": True,
        }
    )

    return drama


# ---------------------------------------------
# EXTRACT EPISODE
# ---------------------------------------------
def extract_current_episode(raw_text):
    match = re.search(
        r'"currentEpisode":({.*?"lockStatus":\d+})',
        raw_text
    )

    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except:
        return None


# ---------------------------------------------
# SAVE EPISODE
# ---------------------------------------------
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


# ---------------------------------------------
# FETCH EPISODE
# ---------------------------------------------
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
                time.sleep(2)
                continue

            episode_data = extract_current_episode(
                response.text
            )

            if episode_data:
                return episode_data

            time.sleep(1)

        except:
            time.sleep(2)

    return None


# ---------------------------------------------
# SCRAPE DRAMA EPISODES
# ---------------------------------------------
def scrape_drama(drama):
    print(f"\nStarting episodes: {drama.title}")

    existing_eps = set(
        drama.episodes.values_list(
            "episode_number",
            flat=True
        )
    )

    pending_eps = [
        ep for ep in range(1, drama.total_episodes + 1)
        if ep not in existing_eps
    ]

    skipped_eps = []

    with ThreadPoolExecutor(max_workers=EPISODE_WORKERS) as executor:
        results = executor.map(
            lambda ep: (ep, fetch_episode(drama, ep)),
            pending_eps
        )

        for ep, episode_data in results:
            if not episode_data:
                skipped_eps.append(ep)
                continue

            save_episode(drama, episode_data)

            print(f"[{drama.title}] Saved Ep {ep}")
            time.sleep(DELAY_BETWEEN_EPISODES)

    if skipped_eps:
        print(f"Recovery pass: {skipped_eps}")

        for ep in skipped_eps:
            episode_data = fetch_episode(drama, ep)

            if episode_data:
                save_episode(drama, episode_data)
                print(f"[{drama.title}] Recovery saved Ep {ep}")

    print(f"Completed: {drama.title}")
    print(f"Sleeping {DELAY_BETWEEN_DRAMAS}s...\n")
    time.sleep(DELAY_BETWEEN_DRAMAS)


# ---------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------
def scrape_all():
    seen_ids = set()

    for page in range(1, MAX_PAGES + 1):
        print(f"\nFetching page {page}")

        dramas = fetch_page(page)

        for drama_data in dramas:
            subject_id = drama_data.get("subjectId")

            if subject_id in seen_ids:
                continue

            seen_ids.add(subject_id)

            drama = save_drama(drama_data)

            print(f"Saved drama: {drama.title}")

            # Immediately scrape episodes
            scrape_drama(drama)

        print(f"Sleeping {DELAY_BETWEEN_PAGES}s after page...")
        time.sleep(DELAY_BETWEEN_PAGES)


# ---------------------------------------------
# RUN
# ---------------------------------------------
if __name__ == "__main__":
    print("Starting merged scraper...")
    scrape_all()