def count_osfi_files(osfi):
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    filename = f'/tmp/{osfi}_file_count_report.csv'
    COL_HEADERS = [ 'user_guid', 'object_guid', 'object_type', 'object_title', 'object_created', 'associated_file_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    
    target_users = OSFUser.objects.filter(
            institutionaffiliation__institution___id=osfi,
            is_active=True
        ).exclude(spam_status__in=[1,2])
    for u in target_users.distinct():
        for n in u.nodes_created.filter(is_public=True, deleted__isnull=True):
            writer.writerow({
                'user_guid': u._id,
                'object_guid': n._id,
                'object_type': n.type,
                'object_title': n.title,
                'object_created': n.created,
                'associated_file_count': n.files.count()
            })
        for p in u.preprints_created.filter(is_public=True, is_published=True):
            writer.writerow({
                'user_guid': u._id,
                'object_guid': p._id,
                'object_type': 'osf.preprint',
                'object_title': p.title,
                'object_created': p.created,
                'associated_file_count': p.files.count()
            })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())