import os
import django
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from api.models import ShortDrama, ShortDramaForyou


URL = "https://h5-api.aoneroom.com/wefeed-h5api-bff/vskit/tab-operation-list"

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Authorization": "Bearer YOUR_TOKEN_HERE",
    "Connection": "keep-alive",
    "Origin": "https://vskit.tv",
    "Referer": "https://vskit.tv/",
    "User-Agent": "Mozilla/5.0",
    "X-Client-Info": '{"timezone":"Asia/Karachi"}',
    "X-Request-Lang": "en",
    "X-Site-Domain": "https://vskit.tv"
}

session = requests.Session()
session.headers.update(HEADERS)


def fetch_foryou():
    response = session.get(URL, timeout=30)

    if response.status_code != 200:
        print(f"Failed: {response.status_code}")
        return []

    data = response.json()

    if data.get("code") != 0:
        print("Invalid API response")
        return []

    return data.get("data", {}).get("list", [])


def save_category(category, index):
    title = category.get("title") or "Untitled"

    category_obj, _ = ShortDramaForyou.objects.update_or_create(
        title=title,
        defaults={
            "order_by": index + 1,
            "is_active": True,
        }
    )

    category_obj.dramas.clear()

    saved_count = 0

    for drama in category.get("novelItems", []):
        drama_obj, _ = ShortDrama.objects.update_or_create(
            subject_id=drama.get("subjectId"),
            defaults={
                "title": drama.get("title"),
                "slug": drama.get("subjectSeoKey") or "",
                "cover": drama.get("cover") or {},
                "tags": drama.get("tags", []),
                "total_episodes": drama.get("totalEpisode"),
                "total_views": drama.get("totalViews"),
                "description": drama.get("description"),
                "is_active": True,
            }
        )

        category_obj.dramas.add(drama_obj)
        saved_count += 1

    print(f"Saved category: {title} ({saved_count} dramas)")


def scrape_and_save_foryou(max_workers=3):
    categories = fetch_foryou()

    if not categories:
        print("No categories found")
        return

    print(f"Found {len(categories)} categories")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(save_category, category, index)
            for index, category in enumerate(categories)
        ]

        for future in as_completed(futures):
            future.result()


if __name__ == "__main__":
    print("Starting ForYou scraper...")
    scrape_and_save_foryou(max_workers=3)