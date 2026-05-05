def get_node_file_count():
    import csv
    import io
    from django.db.models import Count
    from tqdm import tqdm

    filename = "/tmp/node_file_count.csv"
    COL_HEADERS = ['node_guid', 'is_public', 'file_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    nodes = Node.objects.annotate(
        file_count=Count('files')
    ).prefetch_related(None)

    pbar = tqdm(total = nodes.count())

    for n in nodes.iterator():
        writer.writerow({
            'node_guid': n._id,
            'is_public': "public" if n.is_public else "private",
            'file_count': n.file_count
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")