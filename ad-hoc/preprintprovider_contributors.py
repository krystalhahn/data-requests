# example argument
provider = PreprintProvider.objects.get(name = 'PsyArXiv')

def get_ppp_contributors(provider, n=None, batch_size=500):
    import csv
    from tqdm import tqdm

    filename = f'/tmp/{provider._id}_preprint_contributors.csv'

    COL_HEADERS = [
        'preprint_guid_ver',
        'preprint_guid',
        'preprint_version',
        'user_guid',
        'email_address',
        'permissions'
    ]

    preprints = Preprint.objects.filter(
        provider=provider,
        is_public=True
    ).distinct().prefetch_related('_contributors')

    if n is not None:
        preprints = preprints[:n]

    total = preprints.count()

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COL_HEADERS)
        writer.writeheader()

        for p in tqdm(
            preprints.iterator(chunk_size=batch_size),
            total=total
        ):
            preprint_guid, preprint_version = p._id.split('_', 1)

            for c in p._contributors.all():
                writer.writerow({
                    'preprint_guid_ver': p._id,
                    'preprint_guid': preprint_guid,
                    'preprint_version': preprint_version,
                    'user_guid': c._id,
                    'email_address': c.username,
                    'permissions': list(p.get_permissions(c))
                })

    print(f'Output written to {filename}')