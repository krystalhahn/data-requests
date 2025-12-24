def get_inst_nodes_by_region(inst, public_only=True):
    import csv
    import io
    filename = f'/tmp/{inst._id}_node_regions.csv'
    COL_HEADERS = ['inst.id', 'node.id', 'node.title', 'region.name', 'affiliated_contributors', 'is_public']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    qs = inst.nodes.all()
    if public_only:
        qs = qs.filter(is_public=True)
    for n in qs:
        writer.writerow({
            'inst.id': inst._id,
            'node.id': n._id,
            'node.title': n.title,
            'region.name': n.addons_osfstorage_node_settings.region.name,
            'affiliated_contributors': list(n.contributors.filter(institutionaffiliation__institution=inst).distinct().values_list('guids___id', flat=True)),
            'is_public': n.is_public
        })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())
        
def get_inst_nodes_by_region_2(inst, public_only=True):
    import csv
    import io
    filename = f'/tmp/{inst._id}_node_regions.csv'
    COL_HEADERS = ['inst.id', 'node.id', 'node.type', 'node.title', 'node.created', 'node.modified', 'creator.id', 'storage_bytes', 'region.name', 'affiliated_contributors', 'is_public']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    qs = inst.nodes.filter(deleted__isnull=True)
    if public_only:
        qs = qs.filter(is_public=True)
    for n in qs:
        writer.writerow({
            'inst.id': inst._id,
            'node.id': n._id,
            'node.type': n.type,
            'node.title': n.title,
            'node.created': str(n.created.date()),
            'node.modified': str(n.modified.date()),
            'creator.id': n.creator._id,
            'storage_bytes': n.storage_usage,
            'region.name': n.addons_osfstorage_node_settings.region.name,
            'affiliated_contributors': list(n.contributors.filter(institutionaffiliation__institution=inst).distinct().values_list('guids___id', flat=True)),
            'is_public': n.is_public
        })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())