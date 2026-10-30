# all contributors to public PsyArXiv preprints
## GUID
## email address
## permission level

def get_ppp_contributors(provider, n=None):
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/{provider._id}_preprint_contributors.csv'
    COL_HEADERS = ['preprint_guid_ver', 'preprint_guid', 'preprint_version', 'user_guid', 'email_address', 'permissions']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    preprints = Preprint.objects.filter(provider=provider, is_public=True).distinct()

    if n:
        preprints = preprints[:n]

    pbar = tqdm(total=preprints.count())

    for p in preprints:

        preprint_guid = p._id.split('_')[0]
        preprint_version = p._id.split('_')[1]

        for c in p.contributors.all():

            writer.writerow({
                'preprint_guid_ver': p._id, 
                'preprint_guid': preprint_guid,
                'preprint_version': preprint_version,
                'user_guid': c._id,
                'email_address': c.username,
                'permissions': list(p.get_permissions(c))
            })

        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f'Output written to {filename}')