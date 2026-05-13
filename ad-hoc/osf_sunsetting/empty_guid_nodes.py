def get_empty_guid_nodes():
    import csv
    import io
    from django.db.models import Q, Count
    from tqdm import tqdm

    filename = "/tmp/empty_guid_nodes.csv"
    COL_HEADERS = ['node_guid', 'root', 'is_public', 'deleted', 'moderation_state', 'node_title']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    nodes = Node.objects.filter(guids___id__isnull=True).prefetch_related(None)

    pbar = tqdm(total = nodes.count())

    for n in nodes.iterator():
        writer.writerow({
            'node_guid': n._id,
            'root': n.root._id,
            'is_public': "public" if n.is_public else "private",
            'deleted': n.deleted,
            'moderation_state': n.moderation_state,
            'node_title': n.title
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")