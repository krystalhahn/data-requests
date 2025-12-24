# example usage
get_inst_nodes_by_region('uom', 'Germany - Frankfurt')  # Manchester nodes not stored in Germany

def get_inst_nodes_by_region(inst_id, excl_region=None, public_only=True):
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/{inst_id}_node_regions.csv'
    COL_HEADERS = ['inst.id', 'node.id', 'node.title', 'node.created', 'node.modified', 'storage_bytes', 'region.name', 'creator.id', 'affiliated_contributors', 'affiliated_emails', 'is_public']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    inst = Institution.objects.get(_id=inst_id)
    qs = inst.nodes.filter(deleted__isnull=True)

    pbar = tqdm(total=qs.count())

    if public_only:
        qs = qs.filter(is_public=True)

    for n in qs:
        region_name = n.addons_osfstorage_node_settings.region.name
        if region_name == excl_region:
            continue

        writer.writerow({
            'inst.id': inst._id,
            'node.id': n._id,
            'node.title': n.title,
            'node.created': str(n.created.date()),
            'node.modified': str(n.modified.date()),
            'storage_bytes': n.storage_usage,
            'region.name': region_name,
            'creator.id': n.creator._id,
            'affiliated_contributors': list(n.contributors.filter(institutionaffiliation__institution=inst).distinct().values_list('guids___id', flat=True)),
            'affiliated_emails': list(n.contributors.filter(institutionaffiliation__institution=inst).distinct().values_list('username', flat=True)),
            'is_public': n.is_public
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")