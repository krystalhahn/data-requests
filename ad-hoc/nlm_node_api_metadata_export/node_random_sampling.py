import ijson
import random
import json
from pathlib import Path

input_file = Path("/tmp/node_data.json")
output_dir = Path("/tmp/node_data_sample_10")
output_dir.mkdir(exist_ok=True)

sample_size = 10
sample = []
count = 0

# randomly select 10 records
with input_file.open("rb") as f:
    for count, record in enumerate(ijson.items(f, "item"), start=1):
        if len(sample) < sample_size:
            sample.append(record)
        else:
            index = random.randrange(count)
            if index < sample_size:
                sample[index] = record

# write each sampled record to its own JSON file
for i, record in enumerate(sample, start=1):
    output_file = output_dir / f"sample_{i:02d}.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

print(f"Records scanned: {count:,}")
print(f"Records sampled: {len(sample)}")
print(f"Files saved to: {output_dir}")

# with affiliated insts

output_dir = Path('/tmp/nodes_with_inst_sample')
output_dir.mkdir(exist_ok=True)

base_nodes = Node.objects.filter(
    is_public=True,
    deleted__isnull=True
).exclude(
    spam_status__in=[1, 2]
)

sample_nodes = list(
    base_nodes
    .filter(affiliated_institutions__isnull=False)
    .distinct()
    .order_by('?')[:5]
)

for i, node in enumerate(sample_nodes, start=1):
    result = build_node(
        node,
        list(
            Contributor.objects.filter(node_id=node.pk)
            .select_related('user', 'node')
            .order_by('node_id', '_order')
        ),
        set(
            Preprint.objects.filter(node_id=node.pk)
            .values_list('node_id', flat=True)
        ),
        set(
            Node()._settings_model('wiki').objects.filter(
                owner_id=node.pk,
                is_deleted=False
            ).values_list('owner_id', flat=True)
        ),
        ContentType.objects.get_for_model(Node)
    )

    output_file = output_dir / f'{node._id}.json'

    with output_file.open('w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'{i}/5: {node._id} -> {output_file}')

print(f'\nSaved {len(sample_nodes)} files to {output_dir}')