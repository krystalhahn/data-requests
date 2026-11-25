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

# investigate missing ids
import traceback
import pandas as pd

node_ct = ContentType.objects.get_for_model(Node)
wiki_model = Node()._settings_model('wiki')

failures = []

for guid in missing_ids:
    try:
        node = Node.objects.get(
            guids___id=guid,
            is_public=True,
            deleted__isnull=True,
        )

        if node.spam_status in [1, 2]:
            continue

        preprint_node_ids = set(
            Preprint.objects.filter(node_id=node.pk)
            .values_list('node_id', flat=True)
        )

        wiki_node_ids = set(
            wiki_model.objects.filter(
                owner_id=node.pk,
                is_deleted=False,
            ).values_list('owner_id', flat=True)
        )

        contributor_rows = list(
            Contributor.objects.filter(node_id=node.pk)
            .select_related('user', 'node')
            .order_by('node_id', '_order')
        )

        result = build_node(
            node,
            contributor_rows,
            preprint_node_ids,
            wiki_node_ids,
            node_ct,
        )

    except Exception as e:
        failures.append({
            'node_guid': guid,
            'exception_type': type(e).__name__,
            'error': str(e),
            'traceback': traceback.format_exc(),
        })

failures_df = pd.DataFrame(failures)

print(f'Failed: {len(failures_df)} / {len(missing_ids)}')
print(failures_df[['node_guid', 'exception_type', 'error']].to_string(index=False))