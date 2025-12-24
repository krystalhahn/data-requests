# example usage
get_inst_nodes_by_region('uom', 'Germany - Frankfurt')  # Manchester nodes not stored in Germany

def get_inst_nodes_by_region(inst_id, excl_region=None, public_only=True):
    import csv
    import io
    from django.db.models import Q
    from tqdm import tqdm

    filename = f'/tmp/{inst_id}_node_regions.csv'
    COL_HEADERS = ['inst.id', 'node.id', 'node.title', 'node.created', 'node.modified', 'storage_bytes', 'region.name', 'creator.id', 'creator.username', 'affiliated_contributors', 'affiliated_emails','affiliated_roles', 'is_public']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    inst = Institution.objects.get(_id=inst_id)

    filters = Q(deleted__isnull=True)
    if excl_region:
        filters &= ~Q(addons_osfstorage_node_settings__region__name=excl_region)
    if public_only:
        filters &= Q(is_public=True)

    qs = inst.nodes.filter(filters)

    pbar = tqdm(total=qs.count())

    for n in qs:
        # define affiliated_users
        affiliated_users = n.contributors.filter(institutionaffiliation__institution=inst).distinct()

        # gather roles for each affiliated user
        affiliated_roles = {}
        for user in affiliated_users:
            affiliated_roles[user.username] = list(n.get_permissions(user))

        writer.writerow({
            'inst.id': inst._id,
            'node.id': n._id,
            'node.title': n.title,
            'node.created': str(n.created.date()),
            'node.modified': str(n.modified.date()),
            'storage_bytes': n.storage_usage,
            'region.name': n.addons_osfstorage_node_settings.region.name,
            'creator.id': n.creator._id,
            'creator.username': n.creator.username,
            'affiliated_contributors': list(affiliated_users.values_list('guids___id', flat=True)),
            'affiliated_emails': list(affiliated_users.values_list('username', flat=True)),
            'affiliated_roles': affiliated_roles,
            'is_public': n.is_public
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")