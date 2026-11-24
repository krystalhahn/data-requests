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