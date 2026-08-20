import json
import requests
import os


HELP_SCOUT_TOKEN = os.environ["HELP_SCOUT_TOKEN"]

BASE_URL = "https://api.helpscout.net/v2/conversations/"

headers = {
    "Authorization": f"Bearer {HELP_SCOUT_TOKEN}",
    "Content-Type": "application/json",
}

all_conversations = []
page = 1

while True:

    response = requests.get(
        BASE_URL,
        headers=headers,
        params={
            "page": page,
            "status": "all",
            "query": "(createdAt:[2026-08-08T00:00:00Z TO *])",
        }
    )

    response.raise_for_status()

    data = response.json()

    conversations = data.get("_embedded", {}).get("conversations", [])

    # Check pagination information
    page_info = data.get("page", {})
    total_pages = page_info.get("totalPages", 1)

    # Print total pages after first request
    if page == 1:
        print(f"Total pages: {total_pages}")

    # Keep only the fields we want
    for conversation in conversations:

        threads = [
            {
                "id": thread.get("id"),
                "type": thread.get("type"),
                "status": thread.get("status"),
                "body": thread.get("body"),
                "createdAt": thread.get("createdAt"),
            }
            for thread in conversation.get("_embedded", {}).get("threads", [])
        ]

        custom_fields = [
            {
                "name": field.get("name"),
                "text": field.get("text"),
            }
            for field in conversation.get("customFields", [])
        ]

        tags = [
            tag.get("tag")
            for tag in conversation.get("tags", [])
        ]

        slim_conversation = {
            "id": conversation.get("id"),
            "threadsCount": conversation.get("threads"),
            "threads": threads,
            "status": conversation.get("status"),
            "subject": conversation.get("subject"),
            "preview": conversation.get("preview"),
            "createdAt": conversation.get("createdAt"),
            "tags": tags,
            "customFields": custom_fields,
        }

        all_conversations.append(slim_conversation)

    # Print progress every 10 pages
    if page % 10 == 0:
        print(
            f"Fetched page {page} "
            f"({len(all_conversations)} conversations so far)"
        )

    # Stop after the last page
    if page >= total_pages:
        break

    page += 1


print(f"\nDone. Total conversations: {len(all_conversations)}")


# Save as JSON
with open("/tmp/helpscout_conversations.json", "w") as f:
    json.dump(all_conversations, f, indent=2)

print("Saved to /tmp/helpscout_conversations.json")