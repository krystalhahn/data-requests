def get_node_storage_usage():
    import csv
    import io
    from django.db.models import Sum, Count
    from tqdm import tqdm

    filename = f'/tmp/node_storage_usage.csv'
    COL_HEADERS = ['node_id', 'is_public', 'is_spam', 'storage_usage', 'file_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    
    nodes = Node.objects.annotate(
        storage_usage=Sum('files__versions__size'),
        file_count=Count('files', distinct=True)
        ).values('guids___id', 'is_public', 'spam_status', 'storage_usage', 'file_count')

    pbar = tqdm(total = nodes.count())

    for n in nodes.iterator(chunk_size=2000):
        writer.writerow({
            'node_id': n['guids___id'],
            'is_public': n['is_public'],
            'is_spam': n['spam_status'] == 2,
            'storage_usage': n['storage_usage'] or 0,
            'file_count': n['file_count'],
        })
        pbar.update()
    
    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")