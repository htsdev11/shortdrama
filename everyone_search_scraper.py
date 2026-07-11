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


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

REQUEST_TIMEOUT = 20
RETRY_LIMIT = 3

EPISODE_WORKERS = 2

DELAY_BETWEEN_EPISODES = 0.7
DELAY_BETWEEN_DRAMAS = 10

URL = "https://h5-api.aoneroom.com/wefeed-h5api-bff/vskit/everyonesearch"


HEADERS = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_TOKEN",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://vskit.tv",
    "Referer": "https://vskit.tv/",
    "X-Client-Info": '{"timezone":"Asia/Karachi"}',
    "X-Request-Lang": "en",
    "X-Site-Domain": "https://vskit.tv",
}


# ---------------------------------------------------
# SESSION FOR EPISODES
# ---------------------------------------------------

SESSION_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0)"
        " Gecko/20100101 Firefox/152.0"
    ),
    "Origin": "https://vskit.tv",
    "RSC": "1",
}

session = requests.Session()
session.headers.update(SESSION_HEADERS)

COOKIE_STRING = """
PASTE_FULL_COOKIE
"""

for item in COOKIE_STRING.strip().split("; "):
    if "=" in item:
        k, v = item.split("=", 1)
        session.cookies.set(k, v)


# ---------------------------------------------------
# EVERYONE SEARCH
# ---------------------------------------------------

def fetch_everyone_search():

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != 0:
        return []

    return data.get("data", {}).get("recommendList", [])


# ---------------------------------------------------
# SAVE DRAMA
# ---------------------------------------------------

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
            "is_everyone_search": True,
            "is_active": True,
        }
    )

    print(
        f"{'Created' if created else 'Updated'}: {drama.title}"
    )

    return drama


# ---------------------------------------------------
# EXTRACT EPISODE
# ---------------------------------------------------

def extract_current_episode(raw_text):

    match = re.search(
        r'"currentEpisode":({.*?"lockStatus":\d+})',
        raw_text,
    )

    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except:
        return None


# ---------------------------------------------------
# FETCH EPISODE
# ---------------------------------------------------

def fetch_episode(drama, ep):

    url = f"https://vskit.tv/watch/{drama.slug}?ep={ep}"

    headers = {
        "Referer": f"https://vskit.tv/drama/{drama.slug}",
        "Next-Url": f"/en/drama/{drama.slug}",
    }

    for _ in range(RETRY_LIMIT):

        try:

            response = session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code != 200:
                time.sleep(2)
                continue

            episode = extract_current_episode(response.text)

            if episode:
                return episode

            time.sleep(1)

        except Exception:
            time.sleep(2)

    return None


# ---------------------------------------------------
# SAVE EPISODE
# ---------------------------------------------------

def save_episode(drama, episode):

    video = episode.get("video") or {}

    address = video.get("videoAddress") or {}

    cover = video.get("cover") or {}

    ShortDramaEpisode.objects.update_or_create(
        drama=drama,
        episode_number=episode["ep"],
        defaults={
            "mini_id": episode.get("miniId"),
            "subject_id": episode.get("subjectId"),
            "season": episode.get("se", 1),
            # "title": f"Episode {episode['ep']}",
            "play_url": address.get("url"),
            "thumbnail": cover.get("url"),
            "duration": address.get("duration"),
            "width": address.get("width"),
            "height": address.get("height"),
            "file_size": address.get("size"),
            "lock_status": episode.get("lockStatus", 0),
            "is_active": True,
        },
    )


# ---------------------------------------------------
# SCRAPE DRAMA
# ---------------------------------------------------

def scrape_drama(drama):

    print(f"\nStarting episodes: {drama.title}")

    existing = set(
        drama.episodes.values_list(
            "episode_number",
            flat=True,
        )
    )

    pending = [
        ep
        for ep in range(1, drama.total_episodes + 1)
        if ep not in existing
    ]

    skipped = []

    with ThreadPoolExecutor(max_workers=EPISODE_WORKERS) as executor:

        results = executor.map(
            lambda ep: (ep, fetch_episode(drama, ep)),
            pending,
        )

        for ep, episode in results:

            if not episode:
                skipped.append(ep)
                continue

            save_episode(drama, episode)

            print(f"[{drama.title}] Saved Ep {ep}")

            time.sleep(DELAY_BETWEEN_EPISODES)

    if skipped:

        print("Recovery:", skipped)

        for ep in skipped:

            episode = fetch_episode(drama, ep)

            if episode:
                save_episode(drama, episode)
                print(f"Recovered Ep {ep}")

    print(f"Completed: {drama.title}")

    print(f"Sleeping {DELAY_BETWEEN_DRAMAS}s...\n")

    time.sleep(DELAY_BETWEEN_DRAMAS)


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def scrape_everyone_search():
    dramas = fetch_everyone_search()

    if not dramas:
        print("No dramas found")
        return

    print(f"Found {len(dramas)} dramas")

    # Reset previous Everyone Search flags
    updated = ShortDrama.objects.filter(
        is_everyone_search=True
    ).update(
        is_everyone_search=False
    )

    print(f"Reset {updated} previous Everyone Search dramas")

    seen = set()

    for drama_data in dramas:
        subject_id = drama_data.get("subjectId")

        if subject_id in seen:
            continue

        seen.add(subject_id)

        drama = save_drama(drama_data)

        print(f"Updated: {drama.title}")

        scrape_drama(drama)

    print("Everyone Search scraper completed.")


# ---------------------------------------------------
# RUN
# ---------------------------------------------------

if __name__ == "__main__":
    print("Starting Everyone Search scraper...")
    scrape_everyone_search()