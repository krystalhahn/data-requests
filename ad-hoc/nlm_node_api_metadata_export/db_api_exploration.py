def load_json_file(path):
    """Load either a standard JSON file or a JSONL file."""

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

import json