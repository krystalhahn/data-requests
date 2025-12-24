def get_inst_users(inst):
    import csv
    import io
    import pytz
    filename = f'/tmp/{inst._id}_users.csv'
    COL_HEADERS = ['username', 'guid', 'fullname', 'storage_region', 'department', 'is_active', 'is_spammy']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    for ia in inst.institutionaffiliation_set.exclude(user__deleted__isnull=False):
        writer.writerow({
            'username': ia.user.username,
            'guid': ia.user._id,
            'fullname': ia.user.fullname,
            'storage_region': ia.user.osfstorage_region.name,
            'department': ia.sso_department,
            'is_active': ia.user.is_active,
            'is_spammy': ia.user.is_spammy
        })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())