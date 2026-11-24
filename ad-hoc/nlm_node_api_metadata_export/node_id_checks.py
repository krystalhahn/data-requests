import ijson

# check for duplicate ids
ids = []
with open("/tmp/node_data.json", "rb") as f:
    for record in ijson.items(f, "item"):
        ids.append(record.get("id"))

print("Total records:", len(ids))
print("Unique IDs:", len(set(ids)))
print("Duplicate IDs:", len(ids) - len(set(ids)))

# check for missing ids
exported_ids = set()

with open('/tmp/node_data.json', 'rb') as f:
    for record in ijson.items(f, 'item'):
        exported_ids.add(record['id'])

base_qs = Node.objects.filter(
    is_public=True,
    deleted__isnull=True
).exclude(spam_status__in=[1, 2])

missing_ids = []

for node in base_qs.prefetch_related('guids').iterator(chunk_size=5000):
    if node._id not in exported_ids:
        missing_ids.append(node._id)

print('Database nodes:', base_qs.count())
print('Exported unique IDs:', len(exported_ids))
print('Missing nodes:', len(missing_ids))
print(missing_ids[:20])