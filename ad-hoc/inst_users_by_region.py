# example usage
get_inst_users_by_region('mq', 'Australia - Sydney')    # Macquarie users with a default storage location other than Australia

def get_inst_users_by_region(inst_id, excl_region=None, active_only=True, nonspammy_only=True):
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/{inst_id}_users_regions.csv'
    COL_HEADERS = ['username', 'guid', 'fullname', 'storage_region', 'is_active', 'is_spammy']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    inst = Institution.objects.get(_id=inst_id)

    filters = Q(institutionaffiliation__institution=inst, deleted__isnull=True)
    if excl_region:
        filters &= ~Q(addons_osfstorage_user_settings__default_region__name=excl_region)
    if active_only:
        filters &= Q(is_active=True)
    if nonspammy_only:
        filters &= ~Q(spam_status__in=[1,2])

    users = OSFUser.objects.filter(filters)

    pbar = tqdm(total=users.count())

    for user in users:
        writer.writerow({
            'username': user.username,
            'guid': user._id,
            'fullname': user.fullname,
            'storage_region': user.addons_osfstorage_user_settings.default_region.name,
            'is_active': user.is_active,
            'is_spammy': user.spam_status in [1,2]
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")