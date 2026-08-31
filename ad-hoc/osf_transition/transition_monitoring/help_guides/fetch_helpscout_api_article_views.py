import json
import requests
import os


HELP_SCOUT_TOKEN = os.environ["HELP_SCOUT_TOKEN"]

BASE_URL = "https://api.helpscout.net/v2/reports/docs"

START_DATE = "2026-08-09T00:00:00Z"
END_DATE = "2026-08-15T23:59:59Z"

PREVIOUS_START_DATE = "2026-08-02T00:00:00Z"
PREVIOUS_END_DATE = "2026-08-08T23:59:59Z"

headers = {
    "Authorization": f"Bearer {HELP_SCOUT_TOKEN}",
    "Content-Type": "application/json",
}

response = requests.get(
    BASE_URL,
    headers=headers,
    params={
        "start": START_DATE,
        "end": END_DATE,
        "previousStart": PREVIOUS_START_DATE,
        "previousEnd": PREVIOUS_END_DATE,
    }
)

response.raise_for_status()

data = response.json()

print(f"Date range: {START_DATE} to {END_DATE}")
print(f"Articles returned: {len(data.get('topArticles', []))}")

# keep article-level statistics
articles = []

for article in data.get("topArticles", []):

    articles.append({
        "id": article.get("id"),
        "name": article.get("name"),
        "collectionId": article.get("collectionId"),
        "siteId": article.get("siteId"),
        "views": article.get("count"),
        "previousCount": article.get("previousCount"),
        "deltaPercent": article.get("deltaPercent")
    })

print(f"\nArticles with views: {len(articles)}")

# print the first few
for article in articles[:5]:
    print(
        f"{article['name']}: "
        f"{article['views']} views"
    )


# save as JSON
with open("/tmp/helpscout_article_views.json", "w") as f:
    json.dump(articles, f, indent=2)

print("\nSaved to /tmp/helpscout_article_views.json")