import json
import requests
import os


HELP_SCOUT_DOCS_KEY = os.environ["HELP_SCOUT_DOCS_KEY"]

BASE_URL = "https://docsapi.helpscout.net/v1"

# set to a collection ID to only retrieve transition-related articles
COLLECTION_ID = "6a1ddbc20a4b7de2ddb494b4"

all_articles = []
page = 1
page_size = 100

while True:

    url = f"{BASE_URL}/collections/{COLLECTION_ID}/articles"

    response = requests.get(
        url,
        auth=(HELP_SCOUT_DOCS_KEY, "X"),
        params={
            "page": page,
            "pageSize": page_size,
            "status": "all",
            "sort": "updatedAt",
            "order": "desc",
        }
    )

    response.raise_for_status()

    data = response.json()

    articles = data.get("articles", {})

    items = articles.get("items", [])
    total_pages = articles.get("pages", 1)
    total_count = articles.get("count", 0)

    if page == 1:
        print(f"Total articles: {total_count}")
        print(f"Total pages: {total_pages}")

    for article in items:

        slim_article = {
            "id": article.get("id"),
            "number": article.get("number"),
            "collectionId": article.get("collectionId"),
            "status": article.get("status"),
            "hasDraft": article.get("hasDraft"),
            "name": article.get("name"),
            "publicUrl": article.get("publicUrl"),
            "popularity": article.get("popularity"),
            "viewCount": article.get("viewCount"),
            "createdBy": article.get("createdBy"),
            "updatedBy": article.get("updatedBy"),
            "createdAt": article.get("createdAt"),
            "updatedAt": article.get("updatedAt"),
            "lastPublishedAt": article.get("lastPublishedAt"),
        }

        all_articles.append(slim_article)

    if page % 10 == 0:
        print(
            f"Fetched page {page} "
            f"({len(all_articles)} articles so far)"
        )

    if page >= total_pages:
        break

    page += 1


print(f"\nDone. Total articles: {len(all_articles)}")


with open("/tmp/helpscout_articles.json", "w") as f:
    json.dump(all_articles, f, indent=2)

print("Saved to /tmp/helpscout_articles.json")