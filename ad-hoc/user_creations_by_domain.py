def fetch_user_creations_by_domain(ds):
    import csv
    import io
    filename = '/tmp/user_creations_by_domain.csv'
    COL_HEADERS = [ 'user_domain', 'user_subdomain', 'user_guid', 'object_guid', 'object_type', 'object_title', 'object_created', 'object_storage_region']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    for d in ds:
        target_users = OSFUser.objects.exclude(spam_status__in=[1,2]).filter(is_active=True, emails__address__endswith=d)
        for u in target_users.distinct():
            subdomains = [e.address.split('@')[1].split(d)[0] for e in u.emails.filter(address__endswith=d)]
            if len(subdomains) == 1:
                subdomains = subdomains[0]
            for n in u.nodes_created.filter(is_public=True, deleted__isnull=True):
                writer.writerow({
                    'user_domain': d,
                    'user_subdomain': subdomains,
                    'user_guid': u._id,
                    'object_guid': n._id,
                    'object_type': n.type,
                    'object_title': n.title,
                    'object_created': n.created,
                    'object_storage_region': n.addons_osfstorage_node_settings.region.name
                })
            for p in u.preprints_created.filter(is_public=True, is_published=True):
                writer.writerow({
                    'user_domain': d,
                    'user_subdomain': subdomains,
                    'user_guid': u._id,
                    'object_guid': p._id,
                    'object_type': 'osf.preprint',
                    'object_title': p.title,
                    'object_created': p.created,
                    'object_storage_region': p.region.name
                })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")