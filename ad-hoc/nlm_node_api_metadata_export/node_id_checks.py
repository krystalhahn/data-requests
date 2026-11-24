import ijson

ids = []
with open("/tmp/node_data.json", "rb") as f:
    for record in ijson.items(f, "item"):
        ids.append(record.get("id"))

print("Total records:", len(ids))
print("Unique IDs:", len(set(ids)))
print("Duplicate IDs:", len(ids) - len(set(ids)))