def get_node_file_folder_count():
    import csv
    import io
    from tqdm import tqdm
    from django.db.models import Sum, Count, Q

    filename = '/tmp/node_file_folder_count.csv'
    COL_HEADERS = ['node_id', 'is_public', 'is_spam', 'calc_file_count', 'calc_folder_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    print("Building queryset")
    nodes = Node.objects.annotate(
        file_count=Count('files', filter=Q(files__type__endswith='file'), distinct=True),
        folder_count=Count('files', filter=Q(files__type__endswith='folder'), distinct=True),
    ).values('guids___id', 'is_public', 'spam_status', 'file_count', 'folder_count')

    print("Counting")
    pbar = tqdm(total = nodes.count())

    print("Starting iteration")
    for n in nodes.iterator(chunk_size=2000):
        writer.writerow({
            'node_id': n['guids___id'],
            'is_public': n['is_public'],
            'is_spam': n['spam_status'] == 2,
            'file_count': n['file_count'],
            'folder_count': n['folder_count'],
        })
        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")