import json

def load_json_file(path):
    """Load either a standard JSON file or a JSONL file"""

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    if not content:
        return None

# try standard JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

# if that fails, treat it as JSONL
    return [
        json.loads(line)
        for line in content.splitlines()
        if line.strip()
    ]


def compare_json(original, exported, path='$'):
    """Recursively compare two JSON structures"""

    differences = []

    # compare dictionaries
    if isinstance(original, dict) and isinstance(exported, dict):

        original_keys = set(original.keys())
        exported_keys = set(exported.keys())

        # find keys missing from the export
        for key in sorted(original_keys - exported_keys):
            differences.append({
                'path': f'{path}.{key}',
                'original': original[key],
                'exported': '<MISSING>',
            })

        # find extra keys in the export
        for key in sorted(exported_keys - original_keys):
            differences.append({
                'path': f'{path}.{key}',
                'original': '<MISSING>',
                'exported': exported[key],
            })

        # compare shared keys
        for key in sorted(original_keys & exported_keys):
            differences.extend(
                compare_json(
                    original[key],
                    exported[key],
                    f'{path}.{key}',
                )
            )

    # compare lists
    elif isinstance(original, list) and isinstance(exported, list):

        # if all elements are dictionaries with IDs, match by ID
        if (
            all(isinstance(item, dict) and 'id' in item for item in original)
            and all(isinstance(item, dict) and 'id' in item for item in exported)
        ):
            original_by_id = {item['id']: item for item in original}
            exported_by_id = {item['id']: item for item in exported}

            original_ids = set(original_by_id)
            exported_ids = set(exported_by_id)

            for item_id in sorted(original_ids - exported_ids):
                differences.append({
                    'path': f'{path}[id={item_id}]',
                    'original': original_by_id[item_id],
                    'exported': '<MISSING>',
                })

            for item_id in sorted(exported_ids - original_ids):
                differences.append({
                    'path': f'{path}[id={item_id}]',
                    'original': '<MISSING>',
                    'exported': exported_by_id[item_id],
                })

            for item_id in sorted(original_ids & exported_ids):
                differences.extend(
                    compare_json(
                        original_by_id[item_id],
                        exported_by_id[item_id],
                        f'{path}[id={item_id}]',
                    )
                )

        # otherwise, compare by position
        else:
            if len(original) != len(exported):
                differences.append({
                    'path': f'{path}.__length__',
                    'original': len(original),
                    'exported': len(exported),
                })

            for i, (original_item, exported_item) in enumerate(
                zip(original, exported)
            ):
                differences.extend(
                    compare_json(
                        original_item,
                        exported_item,
                        f'{path}[{i}]',
                    )
                )

    # compare individual values and data types
    elif (
        type(original) != type(exported)
        or original != exported
    ):
        differences.append({
            'path': path,
            'original': original,
            'exported': exported,
        })

    return differences