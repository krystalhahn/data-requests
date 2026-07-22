def get_gfs_contributor_emails():
    import csv
    import io
    from tqdm import tqdm

    filename = '/tmp/gfs_contributor_email_addresses.csv'
    COL_HEADERS = ['reg_guid', 'email_address', 'fullname', 'permissions', 'type']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    gfs_regs = Registration.objects.filter(provider___id="gfs", moderation_state__in=['accepted', 'embargo']).select_related('creator').prefetch_related('_contributors')

    pbar = tqdm(total = gfs_regs.count())

    for reg in gfs_regs:

        writer.writerow({
            'reg_guid': reg._id,
            'email_address': reg.creator.username,
            'fullname': reg.creator.fullname,
            'permissions': reg.get_permissions(reg.creator),
            'type': "creator"
        })
        
        for c in reg._contributors.all():

            permissions = reg.get_permissions(c)

            writer.writerow({
                'reg_guid': reg._id,
                'email_address': c.username,
                'fullname': c.fullname,
                'permissions': reg.get_permissions(c),
                'type': "contributor"
            })

        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")