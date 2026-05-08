def get_child_node_count_by_privacy():
    import csv
    import io
    from django.db.models import Q, Count
    from tqdm import tqdm

    filename = "/tmp/child_node_count_by_privacy.csv"
    COL_HEADERS = ['node_guid', 'is_root', 'type', 'content_type_pk', 'is_public', 'private_children', 'public_children']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    nodes = Node.objects.annotate(
        private_children=Count('descendants', filter=Q(descendants__is_public=False)),
        public_children=Count('descendants', filter=Q(descendants__is_public=True))
    ).prefetch_related(None)

    pbar = tqdm(total = nodes.count())

    for n in nodes.iterator():
        writer.writerow({
            'node_guid': n._id,
            'is_root': n.root == n,
            'type': n.type,
            'content_type_pk': n.content_type_pk,
            'is_public': "public" if n.is_public else "private",
            'private_children': n.private_children,
            'public_children': n.public_children
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")